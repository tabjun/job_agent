import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError
from zipfile import ZipFile

import test_ui
from playwright.sync_api import expect, sync_playwright

from job_agent.browser.session import find_local_browser
from job_agent.core.paths import ProjectPaths
from job_agent.ui.local_kit import local_kit
from job_agent.ui.server import LocalServer
from job_agent.ui.service import WorkspaceService


class LocalKitTests(unittest.TestCase):
    def test_only_code_and_dependency_files_no_operator_data(self):
        with ZipFile(BytesIO(local_kit())) as archive:
            names = archive.namelist()
            self.assertIn("job_agent/ui/static/handoff.js", names)
            self.assertIn("pyproject.toml", names)
            self.assertIn("uv.lock", names)
            for name in names:
                self.assertFalse(
                    set(Path(name).parts)
                    & {
                        ".env",
                        "result",
                        "knowledge",
                        "more_info",
                        ".agents",
                        ".codex",
                        "__pycache__",
                    }
                )
                self.assertTrue(
                    name.startswith("job_agent/")
                    or name
                    in {
                        "pyproject.toml",
                        "uv.lock",
                        "README.md",
                        "Start-Resume-Connector.cmd",
                        "connector.json",
                        "START-HERE.txt",
                    }
                )
            self.assertNotIn(b"OPENAI_API_KEY=", archive.read("README.md"))
            with tempfile.TemporaryDirectory() as folder:
                archive.extractall(folder)
                result = subprocess.run(
                    [sys.executable, "-m", "job_agent", "ui", "--help"],
                    cwd=folder,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("--handoff-origin", result.stdout)

    def test_exact_origin_guard(self):
        for origin in [
            "*",
            "http://evil.test",
            "https://user:secret@example.test",
            "https://example.test/path",
            "https://example.test?code=secret",
        ]:
            with self.assertRaises(ValueError):
                LocalServer(("127.0.0.1", 0), handoff_origin=origin)
        with self.assertRaises(ValueError):
            LocalServer(
                ("127.0.0.1", 0),
                public_demo=True,
                handoff_origin="https://example.test",
            )


class HandoffHttpTests(test_ui.HttpTests):
    def test_only_opted_in_navigation_not_cross_origin_api(self):
        self.server.handoff_origin = "https://fixture.test"
        headers = {
            "Origin": "https://fixture.test",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
        }
        with self.request("/", **headers) as response:
            self.assertIn('id="handoff-approval"', response.read().decode())
        for path, payload, changes in [
            ("/api/config", None, {}),
            ("/api/profile", None, {}),
            ("/api/profile", {}, {}),
            ("/", {}, {}),
            ("/", None, {"Origin": "https://evil.test"}),
            ("/", None, {"Sec-Fetch-Mode": "cors"}),
        ]:
            with self.assertRaises(HTTPError) as error:
                self.request(path, payload, **{**headers, **changes})
            self.assertEqual(error.exception.code, 403)


class ConnectionBrowserTests(unittest.TestCase):
    def test_own_pc_popup_origin_consent_import_and_no_account_actions(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = ProjectPaths(Path(folder))
            public_service = WorkspaceService(
                ProjectPaths(Path(folder) / "public"), ephemeral=True
            )
            public = LocalServer(("127.0.0.1", 0), public_service)
            public_url = (
                os.environ.get("RESUME_PUBLIC_TEST_URL")
                or f"http://127.0.0.1:{public.server_port}"
            )
            local_service = WorkspaceService(paths)
            local = LocalServer(
                ("127.0.0.1", 0), local_service, handoff_origin=public_url
            )
            threads = [
                threading.Thread(target=server.serve_forever, daemon=True)
                for server in [public, local]
            ]
            for thread in threads:
                thread.start()
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True, executable_path=find_local_browser()
                    )
                    try:
                        page = browser.new_page(viewport={"width": 390, "height": 960})
                        config = {
                            **public_service.config(),
                            "token": public.token,
                            "local_owner": False,
                            "public_demo": True,
                            "session_ttl_seconds": 3600,
                            "allowed_providers": ["none"],
                            "providers": {},
                            "models": {},
                            "web_search": False,
                        }
                        if not os.environ.get("RESUME_PUBLIC_TEST_URL"):
                            page.route(
                                "**/api/config",
                                lambda route: (
                                    route.fulfill(
                                        content_type="application/json",
                                        body=json.dumps(config),
                                    )
                                    if route.request.url.startswith(public_url)
                                    else route.continue_()
                                ),
                            )
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.goto(public_url + "/#resume")
                        page.locator("#profile-panel > summary").click()
                        page.locator("#profile-fields textarea").first.fill(
                            "Synthetic connection fact"
                        )
                        page.locator("#profile-form button[type=submit]").click()
                        expect(page.locator("#profile-feedback")).to_contain_text(
                            "임시 반영"
                        )
                        page.locator('.nav[data-view="platforms"]').click()
                        with page.expect_download() as kit_download:
                            page.locator("#local-kit-download").click()
                        with ZipFile(kit_download.value.path()) as archive:
                            self.assertIn(
                                "job_agent/ui/static/handoff.js", archive.namelist()
                            )
                            self.assertEqual(
                                json.loads(archive.read("connector.json"))["origin"],
                                public_url,
                            )
                            self.assertIn(
                                "Start-Resume-Connector.cmd", archive.namelist()
                            )
                        for site in [
                            "catch",
                            "jobkorea",
                            "saramin",
                            "wanted",
                            "incruit",
                        ]:
                            page.locator("#platform-site").select_option(site)
                            expect(page.locator("#platform-route")).to_contain_text(
                                "2차 인증"
                            )
                        page.locator("#device-url").fill(
                            f"http://127.0.0.1:{local.server_port}"
                        )
                        page.locator("#device-open").click()
                        expect(page.locator("#notice")).to_contain_text("동의")
                        self.assertTrue(
                            all(
                                not row["value"]
                                for row in local_service.profile()["fields"]
                            )
                        )
                        page.locator("#device-consent").check()
                        with page.expect_popup() as opened:
                            page.locator("#device-open").click()
                        popup = opened.value
                        popup.on("pageerror", lambda error: errors.append(str(error)))
                        expect(popup.locator("#handoff-approval")).to_be_visible()
                        expect(popup.locator("#handoff-accept")).to_be_disabled()
                        expect(popup.locator("#handoff-preview")).to_contain_text(
                            "Synthetic connection fact"
                        )
                        self.assertTrue(
                            all(
                                not row["value"]
                                for row in local_service.profile()["fields"]
                            )
                        )
                        popup.locator("#handoff-allow").check()
                        popup.locator("#handoff-accept").click()
                        expect(page.locator("#device-status")).to_contain_text(
                            "이력서 전달 완료"
                        )
                        expect(
                            popup.locator("#profile-fields textarea").first
                        ).to_have_value("Synthetic connection fact")
                        self.assertEqual(
                            popup.locator("#portal-sites input:checked").count(), 1
                        )
                        self.assertTrue(
                            popup.locator(
                                '#portal-sites input[value="incruit"]'
                            ).is_checked()
                        )
                        self.assertIsNone(local_service._sync_worker)
                        self.assertFalse(paths.results.exists())
                        expect(
                            popup.locator("#profile-fields input[type=checkbox]").first
                        ).not_to_be_checked()
                        popup.locator("#profile-form button[type=submit]").click()
                        expect(popup.locator("#profile-feedback")).to_contain_text(
                            "저장 완료"
                        )
                        self.assertEqual(
                            next(
                                row
                                for row in local_service.profile()["fields"]
                                if row["id"] == "summary"
                            )["value"],
                            "Synthetic connection fact",
                        )
                        # Messages without the trusted opener identity cannot replace local data.
                        popup.evaluate(
                            "window.dispatchEvent(new MessageEvent('message', {origin: 'https://evil.test', source: window, data: {type: 'resume-workspace.offer'}}))"
                        )
                        expect(popup.locator("#handoff-approval")).to_be_hidden()
                        page.locator('.nav[data-view="resume"]').click()
                        page.locator('[data-field="summary"] > .consent input').check()
                        page.locator("#profile-form button[type=submit]").click()
                        expect(page.locator("#profile-status")).to_contain_text(
                            "미검수 0"
                        )
                        page.locator('.nav[data-view="prepare"]').click()
                        for site in ["catch", "wanted"]:
                            page.locator(f'#portal-sites input[value="{site}"]').check()
                        page.locator("#portal-consent").check()
                        with page.expect_popup() as second_opened:
                            page.locator("#portal-proceed").click()
                        second_popup = second_opened.value
                        expect(
                            second_popup.locator("#handoff-preview")
                        ).to_contain_text("catch, wanted")
                        expect(second_popup.locator("#handoff-accept")).to_be_disabled()
                        second_popup.locator("#handoff-allow").check()
                        second_popup.locator("#handoff-accept").click()
                        expect(
                            second_popup.locator("#portal-sites input:checked")
                        ).to_have_count(2)
                        self.assertIsNone(local_service._sync_worker)
                        second_popup.close()
                        for width in [390, 1440]:
                            page.set_viewport_size({"width": width, "height": 960})
                            self.assertTrue(
                                page.evaluate(
                                    "document.documentElement.scrollWidth <= innerWidth"
                                )
                            )
                            evidence = (
                                Path(__file__).resolve().parents[1]
                                / "result/ui_verification"
                            )
                            evidence.mkdir(parents=True, exist_ok=True)
                            page.screenshot(
                                path=str(evidence / f"platform-connection-{width}.png"),
                                full_page=True,
                            )
                        self.assertEqual(errors, [])
                    finally:
                        browser.close()
            finally:
                for server in [public, local]:
                    server.shutdown()
                    server.server_close()
                for thread in threads:
                    thread.join()
