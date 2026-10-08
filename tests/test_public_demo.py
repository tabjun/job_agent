import json
from pathlib import Path
import tempfile
from urllib.error import HTTPError
from unittest.mock import Mock, patch
from io import BytesIO
from zipfile import ZipFile
import unittest

from job_agent.ui.server import LocalServer
from job_agent.ui.visitors import VisitorWorkspaces
from job_agent.core.paths import ProjectPaths
from job_agent.ui.service import WorkspaceService
import test_ui


class VisitorTests(unittest.TestCase):
    def test_expiry_limit_and_cleanup(self):
        with tempfile.TemporaryDirectory() as folder:
            visitors = VisitorWorkspaces(ttl=10, limit=1)
            try:
                with patch("job_agent.ui.visitors.time.monotonic", return_value=0):
                    service, cookie = visitors.create()
                    self.assertIs(visitors.get(cookie), service)
                    for flag in ["HttpOnly", "Secure", "SameSite=Strict"]:
                        self.assertIn(flag, cookie)
                    with self.assertRaises(ValueError):
                        visitors.create()
                with patch("job_agent.ui.visitors.time.monotonic", return_value=11):
                    self.assertIsNone(visitors.get(cookie))
                    self.assertEqual(service.runs(), [])
            finally:
                visitors.close()
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_memory_only_profile_runs_clear_and_no_file_writes(self):
        from test_resume_profile import sample

        with (
            tempfile.TemporaryDirectory() as folder,
            patch(
                "job_agent.ui.service.ArtifactStore.write_json",
                side_effect=AssertionError("Unexpected disk write"),
            ),
        ):
            service = WorkspaceService(ProjectPaths(Path(folder)), ephemeral=True)
            first = service.save_profile({"profile": sample()})
            self.assertFalse(first["fields"][0]["reviewed"])
            first["fields"][0]["reviewed"] = True
            saved = service.save_profile({"profile": first})
            run = service.run({"task": "resume", "profile": saved})
            self.assertEqual(service.read_run(run["id"]), run)
            saved["fields"][0]["value"] = "Changed client copy"
            self.assertNotEqual(service.profile(), saved)
            self.assertEqual(list(Path(folder).rglob("*")), [])
            for payload in [{"provider": "openai"}, {"source": "web"}]:
                with self.assertRaises(ValueError):
                    service.run(payload)
            service.clear_private_data({})
            self.assertEqual(service.runs(), [])
            self.assertTrue(
                all(not row["value"] for row in service.profile()["fields"])
            )
            service.close()

    def test_reaper_releases_expired_memory_without_new_request(self):
        visitors = VisitorWorkspaces(ttl=10)
        try:
            with patch("job_agent.ui.visitors.time.monotonic", return_value=0):
                service, cookie = visitors.create()
                service.run({"task": "resume", "resume": "Synthetic memory only"})
            with (
                patch("job_agent.ui.visitors.time.monotonic", return_value=11),
                patch.object(visitors.stop, "wait", side_effect=[False, True]),
            ):
                visitors._reap()
            self.assertEqual(visitors.sessions, {})
            self.assertEqual(service.runs(), [])
        finally:
            visitors.close()


class PublicHttpTests(test_ui.HttpTests):
    def enable_demo(self):
        self.server.public_demo = True
        self.server.visitors = VisitorWorkspaces()
        self.server.sharing.process = Mock()
        self.server.sharing.process.poll.return_value = None
        self.server.sharing.process.stdout = None
        self.server.sharing.url = "https://fixture.trycloudflare.com"
        return {
            "Host": "fixture.trycloudflare.com",
            "Origin": "https://fixture.trycloudflare.com",
            "CF-Connecting-IP": "192.0.2.1",
        }

    def visit(self, headers):
        with self.request("/", **headers) as response:
            document = response.read().decode()
            self.assertNotIn('id="login-form"', document)
            self.assertNotIn('id="sharing-code"', document)
            self.assertNotIn("접근 코드", document)
            cookie = response.headers["Set-Cookie"].split(";")[0]
        return {**headers, "Cookie": cookie, "X-Session-Token": self.server.token}

    def test_code_free_entry_and_workspace_isolation(self):
        headers = self.enable_demo()
        from test_resume_profile import sample

        empty = self.server.service.profile()
        self.server.service.save_profile({"profile": sample()})
        original = self.server.service.profile()
        first = self.visit(
            {
                **headers,
                "Origin": "https://chatgpt.com",
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Dest": "document",
            }
        )
        first.update(headers)
        first.pop("Sec-Fetch-Site")
        with self.request("/api/profile", **first) as response:
            profile = json.load(response)
        self.assertEqual(profile, empty)
        profile["fields"][0]["value"] = "Synthetic visitor fact"
        with self.request("/api/profile", {"profile": profile}, **first) as response:
            saved = json.load(response)
        with self.request("/api/profile", **first) as response:
            self.assertEqual(json.load(response), saved)
        second = self.visit(headers)
        with self.request("/api/profile", **second) as response:
            self.assertEqual(json.load(response), empty)
        with self.request(
            "/api/run", {"task": "resume", "resume": "Synthetic visitor fact"}, **first
        ) as response:
            run = json.load(response)
        with self.request("/api/runs", **second) as response:
            self.assertEqual(json.load(response), [])
        with self.assertRaises(HTTPError) as error:
            self.request("/api/runs/" + run["id"], **second)
        self.assertEqual(error.exception.code, 404)
        self.assertEqual(self.server.service.profile(), original)
        self.assertEqual(self.server.service.runs(), [])
        with self.request("/api/session/clear", {}, **first) as response:
            self.assertTrue(json.load(response)["ok"])
        with self.request("/api/profile", **first) as response:
            self.assertEqual(json.load(response), empty)
        with self.request("/api/runs", **first) as response:
            self.assertEqual(json.load(response), [])
        self.assertEqual(self.server.service.profile(), original)
        self.assertFalse(
            (self.server.service.paths.results / "public_visitors").exists()
        )

    def test_public_demo_blocks_operator_resources(self):
        headers = self.enable_demo()
        auth = self.visit(headers)
        with self.request("/api/local-kit", **auth) as response:
            self.assertEqual(response.headers["Content-Type"], "application/zip")
            with ZipFile(BytesIO(response.read())) as archive:
                self.assertIn("job_agent/ui/static/handoff.js", archive.namelist())
        with self.request("/api/config", **auth) as response:
            config = json.load(response)
            self.assertTrue(config["public_demo"])
            self.assertNotIn("admin_token", config)
            self.assertEqual(config["allowed_providers"], ["none"])
        for path, payload in [
            ("/api/run", {"provider": "openai", "ai_consent": True}),
            ("/api/run", {"provider": "gemini", "ai_consent": True}),
            ("/api/run", {"provider": "custom"}),
            ("/api/run", {"source": "web"}),
            ("/api/sync", {"operation": "open"}),
            ("/api/extract", {"data": ""}),
            ("/api/model-connection", {}),
            ("/api/sharing/start", {"consent": True}),
        ]:
            with self.assertRaises(HTTPError) as error:
                self.request(path, payload, **auth)
            self.assertEqual(error.exception.code, 403)
        with self.assertRaises(HTTPError) as error:
            self.request("/api/login", {"code": "anything"}, **headers)
        self.assertEqual(error.exception.code, 404)
        with self.request(
            "/api/sharing", **{"X-Session-Token": self.server.token}
        ) as response:
            self.assertNotIn("access_code", json.load(response))
        with self.assertRaises(ValueError):
            LocalServer(("127.0.0.1", 0), public_demo=True, remote_providers=["custom"])
