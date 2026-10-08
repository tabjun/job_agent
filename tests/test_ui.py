import base64
from io import BytesIO
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import AsyncMock, Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zipfile import ZipFile

from job_agent.core.paths import ProjectPaths
from job_agent.ui.server import LocalServer
from job_agent.ui.service import WorkspaceService


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.ai = AsyncMock(
            return_value={"text": "검수 초안", "usage": {"total_tokens": 20}}
        )
        self.search = Mock(
            return_value=[
                {"title": "분석가", "url": "https://example.com/a", "content": "SQL"}
            ]
        )
        self.service = WorkspaceService(
            ProjectPaths(Path(self.folder.name)), self.search, self.ai
        )

    def search_payload(self):
        return {
            "task": "search",
            "provider": "none",
            "keywords": "SQL",
            "postings": json.dumps(
                [
                    {
                        "title": "분석가",
                        "url": "https://example.com/a",
                        "content": "SQL 마감일 2099-01-01",
                    },
                    {
                        "title": "duplicate",
                        "url": "https://example.com/a",
                        "content": "SQL",
                    },
                    {
                        "title": "입력",
                        "url": "javascript:alert(1)",
                        "content": "단순입력",
                    },
                ]
            ),
            "exclude": "단순입력",
        }

    def test_offline_search_no_ai_or_network_and_keeps_deadline(self):
        result = self.service.run(self.search_payload())
        self.assertEqual(len(result["result"]["jobs"]), 1)
        self.assertEqual(result["result"]["jobs"][0]["status"], "unknown")
        self.ai.assert_not_called()
        self.search.assert_not_called()
        self.assertEqual(self.service.read_run(result["id"]), result)
        self.assertEqual(len(self.service.runs()), 1)
        with self.assertRaises(ValueError):
            self.service.read_run("../.env")

    def test_verbatim_resume_reorder(self):
        run = self.service.run(
            {"task": "resume", "resume": "운영 경험\nSQL 분석 경험", "keywords": "SQL"}
        )
        self.assertEqual(run["result"]["report"], "SQL 분석 경험\n\n운영 경험")
        self.assertEqual(run["result"]["paragraphs"][0]["paragraph_index"], 1)
        self.ai.assert_not_called()

    def test_consent_and_keys_required_before_any_external_call(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "TAVILY_API_KEY": ""}):
            with self.assertRaises(ValueError):
                self.service.run(
                    {
                        **self.search_payload(),
                        "provider": "openai",
                        "model": "model",
                        "ai_consent": True,
                    }
                )
            with self.assertRaises(ValueError):
                self.service.run(
                    {
                        "task": "search",
                        "source": "web",
                        "role": "분석",
                        "sites": ["wanted"],
                        "search_consent": True,
                    }
                )
        self.ai.assert_not_called()
        self.search.assert_not_called()

    def test_shared_baseline_one_ai_call_and_no_key_exposure(self):
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "secret-fixture", "TAVILY_API_KEY": "search-secret"},
        ):
            run = self.service.run(
                {
                    "task": "search",
                    "source": "web",
                    "role": "분석가",
                    "sites": ["wanted"],
                    "search_consent": True,
                    "provider": "openai",
                    "model": "model-fixture",
                    "ai_consent": True,
                }
            )
            self.assertNotIn("secret-fixture", json.dumps(self.service.config()))
        self.search.assert_called_once()
        self.ai.assert_awaited_once()
        self.assertEqual(run["ai"]["usage"]["total_tokens"], 20)
        self.assertNotIn("secret", json.dumps(run))

    def test_ai_failure_preserves_baseline_and_redacts_error(self):
        self.ai.side_effect = RuntimeError("api_key=secret-token")
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret-token"}):
            run = self.service.run(
                {
                    "task": "resume",
                    "resume": "실제 경험",
                    "provider": "openai",
                    "model": "model-fixture",
                    "ai_consent": True,
                }
            )
        self.assertEqual(run["result"]["report"], "실제 경험")
        self.assertNotIn("secret-token", json.dumps(run))
        self.assertIn("error", run["ai"])

    def test_docx_extraction_without_ai(self):
        buffer = BytesIO()
        with ZipFile(buffer, "w") as archive:
            archive.writestr(
                "word/document.xml",
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Source fact</w:t></w:r></w:p></w:body></w:document>',
            )
        result = self.service.extract(
            {"data": base64.b64encode(buffer.getvalue()).decode()}
        )
        self.assertEqual(result["text"], "Source fact")
        self.assertFalse(list(self.service.store.directory.glob("*/source.docx")))

    def test_prepare_reuses_reviewed_adapter_without_ai(self):
        from test_company_applications import form, master, registry

        run = self.service.run(
            {
                "task": "prepare",
                "target": registry().target("company-example"),
                "master": master(),
                "form_map": form(),
            }
        )
        self.assertEqual(run["result"]["mapping"]["mapping_status"], "review_required")
        self.assertTrue(
            all(not row.get("approved") for row in run["result"]["mapping"]["mappings"])
        )
        self.ai.assert_not_called()


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.server = LocalServer(
            ("127.0.0.1", 0), WorkspaceService(ProjectPaths(Path(self.folder.name)))
        )
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.folder.cleanup()

    def request(self, path, payload=None, **headers):
        data = json.dumps(payload).encode() if payload is not None else None
        return urlopen(
            Request(
                self.url + path,
                data=data,
                headers={"Content-Type": "application/json", **headers},
            ),
            timeout=5,
        )

    def test_config_token_and_post_protection(self):
        with self.request("/api/config") as response:
            config = json.load(response)
        with self.assertRaises(HTTPError) as error:
            self.request("/api/run", {"task": "resume", "resume": "fact"})
        self.assertEqual(error.exception.code, 403)
        with self.request(
            "/api/run",
            {"task": "resume", "resume": "fact"},
            **{"X-Session-Token": config["token"]},
        ) as response:
            result = json.load(response)
        self.assertEqual(result["result"]["report"], "fact")

    def test_blocks_cross_origin_host_rebinding_and_private_files(self):
        for headers in [{"Origin": "https://evil.test"}, {"Host": "evil.test"}]:
            with self.assertRaises(HTTPError) as error:
                self.request("/api/config", **headers)
            self.assertEqual(error.exception.code, 403)
        with self.assertRaises(HTTPError):
            self.request("/.env", **{"X-Session-Token": self.server.token})
        with self.request("/") as response:
            self.assertIn(
                "frame-ancestors 'none'", response.headers["Content-Security-Policy"]
            )
            self.assertIn("Resume Workspace", response.read().decode())

    def test_profile_endpoints_require_token_and_reset_import_review(self):
        from test_resume_profile import sample

        for path, data in [
            ("/api/profile", None),
            ("/api/profile/template", None),
            ("/api/sync", {"operation": "open", "site": "wanted"}),
            ("/api/profile", {"profile": sample()}),
            ("/api/profile/import", {"document": sample()}),
        ]:
            with self.assertRaises(HTTPError) as error:
                self.request(path, data)
            self.assertEqual(error.exception.code, 403)
        headers = {"X-Session-Token": self.server.token}
        with self.request("/api/profile/template", **headers) as response:
            template = json.load(response)
        self.assertTrue(
            all(not row["value"] and not row["reviewed"] for row in template["fields"])
        )
        with self.request(
            "/api/profile/import", {"document": sample()}, **headers
        ) as response:
            profile = json.load(response)
        self.assertFalse(profile["fields"][0]["reviewed"])
        with self.request("/api/profile", {"profile": profile}, **headers) as response:
            saved = json.load(response)
        with self.request("/api/profile", **headers) as response:
            self.assertEqual(json.load(response), saved)

    def test_busy_and_invalid_json(self):
        self.server.run_lock.acquire()
        try:
            with self.assertRaises(HTTPError) as error:
                self.request(
                    "/api/run",
                    {"task": "resume", "resume": "fact"},
                    **{"X-Session-Token": self.server.token},
                )
            self.assertEqual(error.exception.code, 409)
        finally:
            self.server.run_lock.release()


if __name__ == "__main__":
    unittest.main()
