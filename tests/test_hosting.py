import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zipfile import ZipFile

from job_agent.documents.profile import ResumeProfile
from job_agent.hosting.build import ROOT, build
from job_agent.hosting.handler import execute
from job_agent.hosting.preview import server
from job_agent.ui.service import WorkspaceService


def profile():
    result = ResumeProfile.template().to_dict()
    row = result["fields"][1]
    row.update(
        value="Synthetic SQL fact",
        reviewed=True,
        evidence=[
            {"source_id": "fixture", "paragraph_index": 0, "text": "Synthetic SQL fact"}
        ],
    )
    return result


def search():
    return {
        "task": "search",
        "provider": "none",
        "source": "manual",
        "keywords": "SQL",
        "postings": json.dumps(
            [
                {
                    "title": "Synthetic role",
                    "content": "SQL",
                    "url": "https://example.test/job",
                }
            ]
        ),
    }


class ExportTests(unittest.TestCase):
    def test_code_only_new_directory_and_standalone_import(self):
        with tempfile.TemporaryDirectory() as folder:
            output = build(Path(folder) / "public-export")
            names = [
                p.relative_to(output).as_posix()
                for p in output.rglob("*")
                if p.is_file()
            ]
            self.assertIn("api/run.py", names)
            entrypoint = ast.parse((output / "api/run.py").read_text())
            self.assertTrue(
                any(
                    isinstance(node, ast.ClassDef) and node.name == "handler"
                    for node in entrypoint.body
                )
            )
            for name in names:
                self.assertFalse(
                    set(Path(name).parts)
                    & {
                        ".env",
                        ".venv",
                        "result",
                        "knowledge",
                        "more_info",
                        ".agents",
                        ".codex",
                    }
                )
            with ZipFile(output / "public/resume-local-connector.zip") as kit:
                self.assertNotIn(".env", kit.namelist())
                self.assertFalse(
                    any(name.startswith("result/") for name in kit.namelist())
                )
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from api.run import handler; from job_agent.hosting.handler import execute; assert execute({'task':'resume','resume':'SQL fixture'})['result']['report']=='SQL fixture'",
                ],
                cwd=output,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertFalse((output / "result").exists())
            previous = (output / "public/index.html").read_bytes()
            with self.assertRaises(ValueError):
                build(output)
            self.assertEqual(previous, (output / "public/index.html").read_bytes())
            manifest = json.loads((output / "export-manifest.json").read_text())
            self.assertEqual(
                set(names) - {"export-manifest.json"}, set(manifest["files"])
            )

    def test_stateless_exact_deterministic_parity_and_no_resources(self):
        baseline = WorkspaceService(ephemeral=True)
        self.addCleanup(baseline.close)
        for payload in [
            search(),
            {"task": "resume", "profile": profile(), "keywords": "SQL"},
        ]:
            self.assertEqual(
                execute(payload)["result"], baseline.run(payload)["result"]
            )
        with (
            patch("job_agent.ui.service.load_environment") as env,
            patch("job_agent.ui.service.ArtifactStore") as store,
        ):
            execute(search())
            env.assert_not_called()
            store.assert_not_called()
        for payload in [
            {**search(), "provider": provider}
            for provider in ["openai", "gemini", "custom"]
        ] + [{**search(), "source": "web"}, {"task": "sync"}]:
            with self.assertRaises(ValueError):
                execute(payload)
        unreviewed = profile()
        unreviewed["fields"][1]["reviewed"] = False
        with self.assertRaises(ValueError):
            execute({"task": "resume", "profile": unreviewed})

    def test_company_adapter_is_identical(self):
        target = {
            "key": "company-fixture",
            "name": "Fixture Company",
            "candidate_urls": ["https://company.example.test/apply"],
            "allowed_origins": ["https://company.example.test"],
        }
        form = {
            "site_key": "company-fixture",
            "snapshot": {
                "url": "https://company.example.test/apply",
                "fields": [
                    {
                        "tag": "textarea",
                        "type": "textarea",
                        "selector": "#summary",
                        "labels": ["Summary"],
                        "selector_count": 1,
                        "required": True,
                    }
                ],
            },
        }
        payload = {
            "task": "prepare",
            "profile": profile(),
            "target": target,
            "form_map": form,
        }
        baseline = WorkspaceService(ephemeral=True)
        try:
            self.assertEqual(
                execute(payload)["result"], baseline.run(payload)["result"]
            )
        finally:
            baseline.close()


class HostingHttpTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.bundle = build(Path(self.folder.name) / "export")
        self.server = server(self.bundle, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = (
            os.environ.get("RESUME_HOSTING_TEST_URL")
            or f"http://127.0.0.1:{self.server.server_port}"
        )

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.folder.cleanup()

    def request(self, path, payload=None, **headers):
        return urlopen(
            Request(
                self.url + path,
                data=json.dumps(payload).encode() if payload is not None else None,
                headers={
                    "Origin": self.url,
                    "Content-Type": "application/json",
                    **headers,
                },
            ),
            timeout=15,
        )

    def test_http_guards_and_no_private_routes(self):
        with self.request("/api/run", search()) as response:
            self.assertEqual(
                json.load(response)["result"]["jobs"][0]["title"], "Synthetic role"
            )
            self.assertEqual(response.headers["Cache-Control"], "no-store")
        for path, payload, headers, code in [
            ("/api/run", search(), {"Origin": "https://evil.test"}, 403),
            ("/api/run", search(), {"Sec-Fetch-Site": "cross-site"}, 403),
            ("/api/run", {**search(), "provider": "openai"}, {}, 400),
            ("/api/run", search(), {"Content-Type": "text/plain"}, 415),
            (
                "/api/run",
                {"task": "resume", "profile": {"PRIVATE": "never echo me"}},
                {},
                400,
            ),
            ("/api/profile", None, {}, 404),
            ("/api/sync", {}, {}, 404),
            ("/.env", None, {}, 404),
        ]:
            with self.assertRaises(HTTPError) as failure:
                self.request(path, payload, **headers)
            self.assertEqual(failure.exception.code, code)
            self.assertNotIn(b"never echo me", failure.exception.read())
        self.assertFalse((self.bundle / "result").exists())

    def test_browser_workflow_download_isolation_reload_mobile(self):
        from playwright.sync_api import expect, sync_playwright
        from job_agent.browser.session import find_local_browser

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, executable_path=find_local_browser()
            )
            try:
                context = browser.new_context(viewport={"width": 390, "height": 900})
                page = context.new_page()
                requests, errors = [], []
                page.on("request", lambda request: requests.append(request.url))
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(self.url)
                expect(page.locator("#guide-view")).to_be_visible()
                expect(page.locator("#profile-panel")).to_be_hidden()
                expect(page.locator("#output")).to_be_hidden()
                self.assertEqual(
                    page.locator("#history-view, #sharing-view").count(), 0
                )
                for width in [390, 1440]:
                    page.set_viewport_size({"width": width, "height": 960})
                    self.assertTrue(
                        page.evaluate(
                            "document.documentElement.scrollWidth <= innerWidth"
                        )
                    )
                    screenshots = ROOT / "result/ui_verification"
                    screenshots.mkdir(parents=True, exist_ok=True)
                    page.screenshot(
                        path=str(screenshots / f"public-guide-{width}.png"),
                        full_page=True,
                    )
                page.locator('[data-guide-action="profile"]').click()
                expect(page.locator("#resume-view")).to_be_visible()
                expect(page.locator("#profile-panel")).to_have_attribute("open", "")
                page.locator("#profile-panel > summary").click()
                expect(page.locator("#visitor-notice")).to_contain_text("이 탭")
                expect(page.locator(".model-bar")).to_be_hidden()
                page.locator("#profile-panel > summary").click()
                page.locator('[data-field="summary"] textarea').fill(
                    "Synthetic SQL fact"
                )
                page.locator('[data-field="summary"] > .consent input').check()
                page.locator("#profile-form button[type=submit]").click()
                expect(page.locator("#profile-feedback")).to_contain_text("임시 반영")
                page.locator('[data-field="summary"] > .consent input').check()
                page.locator("#profile-form button[type=submit]").click()
                expect(page.locator("#profile-status")).to_contain_text("미검수 0")
                with page.expect_download() as download:
                    page.locator("#profile-format").select_option("json")
                    page.locator("#profile-download").click()
                saved = json.loads(
                    Path(download.value.path()).read_text(encoding="utf-8")
                )
                self.assertTrue(saved["fields"][1]["reviewed"])
                page.locator('.nav[data-view="resume"]').click()
                page.locator('#resume-form [name="keywords"]').fill("SQL")
                page.locator("#resume-form button[type=submit]").click()
                expect(page.locator("#report")).to_have_text("Synthetic SQL fact")
                other = context.new_page()
                other.goto(self.url + "/#resume")
                other.locator("#profile-panel > summary").click()
                expect(other.locator('[data-field="summary"] textarea')).to_have_value(
                    ""
                )
                self.assertEqual(
                    page.evaluate("[localStorage.length, sessionStorage.length]"),
                    [0, 0],
                )
                self.assertEqual(context.cookies(), [])
                self.assertFalse(
                    any("/api/profile" in url or "/api/runs" in url for url in requests)
                )
                with page.expect_download() as template_download:
                    page.locator("#template-download").click()
                template = json.loads(
                    Path(template_download.value.path()).read_text(encoding="utf-8")
                )
                self.assertEqual(template, ResumeProfile.template().to_dict())
                page.reload()
                expect(page.locator("#profile-status")).to_contain_text("0개 항목")
                page.locator("#profile-panel > summary").click()
                page.locator("#profile-file").set_input_files(
                    {
                        "name": "fixture.json",
                        "mimeType": "application/json",
                        "buffer": json.dumps(saved).encode(),
                    }
                )
                expect(
                    page.locator('[data-field="summary"] > .consent input')
                ).not_to_be_checked()
                page.locator("#profile-form button[type=submit]").click()
                expect(page.locator("#profile-feedback")).to_contain_text("임시 반영")
                page.locator('.nav[data-view="search"]').click()
                page.locator("#sample").click()
                page.locator("#search-form button[type=submit]").click()
                expect(page.locator("#jobs article")).to_have_count(2)
                page.locator('.nav[data-view="prepare"]').click()
                expect(page.locator("#portal-sites input")).to_have_count(5)
                expect(page.locator("#company-advanced form")).to_be_hidden()
                expect(page.locator("#sync-panel")).to_be_hidden()
                page.locator("#profile-panel").evaluate(
                    "element => element.open = false"
                )
                screenshots = ROOT / "result/ui_verification"
                screenshots.mkdir(parents=True, exist_ok=True)
                for width in [390, 1440]:
                    page.set_viewport_size({"width": width, "height": 960})
                    self.assertTrue(
                        page.evaluate(
                            "document.documentElement.scrollWidth <= innerWidth"
                        )
                    )
                    page.screenshot(
                        path=str(screenshots / f"public-portals-{width}.png"),
                        full_page=True,
                    )
                self.assertEqual(
                    page.locator('#prepare-view input[type="password"]').count(), 0
                )
                page.locator('.nav[data-view="guide"]').click()
                expect(page.locator("#guide-view")).to_be_visible()
                self.assertEqual(
                    page.locator("#sharing-view, #history-view").count(), 0
                )
                page.locator('.nav[data-view="platforms"]').click()
                with page.expect_download() as kit:
                    page.locator("#local-kit-download").click()
                with ZipFile(kit.value.path()) as archive:
                    self.assertIn("job_agent/ui/static/handoff.js", archive.namelist())
                screenshots = ROOT / "result/ui_verification"
                screenshots.mkdir(parents=True, exist_ok=True)
                for width in [390, 1440]:
                    page.set_viewport_size({"width": width, "height": 960})
                    self.assertFalse(
                        page.evaluate(
                            "document.documentElement.scrollWidth > innerWidth"
                        )
                    )
                    page.screenshot(
                        path=str(screenshots / f"hosting-{width}.png"), full_page=True
                    )
                self.assertFalse(errors, errors)
            finally:
                browser.close()
