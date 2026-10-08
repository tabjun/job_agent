from pathlib import Path
import json
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from playwright.sync_api import expect, sync_playwright

from job_agent.browser.session import find_local_browser
from job_agent.core.paths import ProjectPaths
from job_agent.ui.server import LocalServer
from job_agent.ui.service import WorkspaceService


class SettingsBrowserTests(unittest.TestCase):
    def test_remote_views_hide_all_processing_modes(self):
        with tempfile.TemporaryDirectory() as folder:
            service = WorkspaceService(ProjectPaths(Path(folder)))
            server = LocalServer(("127.0.0.1", 0), service)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True, executable_path=find_local_browser()
                    )
                    page = browser.new_page(viewport={"width": 390, "height": 844})
                    config = {
                        **service.config(),
                        "token": server.token,
                        "local_owner": False,
                        "allowed_providers": ["none"],
                        "providers": {},
                        "models": {},
                        "web_search": False,
                    }
                    page.route(
                        "**/api/config",
                        lambda route: route.fulfill(
                            status=200,
                            content_type="application/json",
                            body=json.dumps(config),
                        ),
                    )
                    page.goto(f"http://127.0.0.1:{server.server_port}")
                    expect(page.locator(".local-badge")).to_contain_text("REMOTE")
                    expect(page.locator(".model-bar")).to_be_hidden()
                    expect(page.locator(".nav[data-view=connection]")).to_be_hidden()
                    page.locator(".nav[data-view=search]").click()
                    page.locator("#sample").click()
                    page.locator("#search-form button[type=submit]").click()
                    expect(page.locator(".job-row")).to_have_count(2)
                    self.assertNotIn("모드", page.locator("#metrics").inner_text())
                    for view in ["guide", "prepare", "resume", "search"]:
                        page.locator(f".nav[data-view={view}]").click()
                        expect(page.locator(".model-bar")).to_be_hidden()
                        text = page.locator("body").inner_text()
                        for name in ["LLM 없음", "OpenAI", "Gemini", "과금"]:
                            self.assertNotIn(name, text)
                    browser.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_custom_connection_sharing_and_mobile_layout(self):
        with tempfile.TemporaryDirectory() as folder:
            service = WorkspaceService(ProjectPaths(Path(folder)))
            server = LocalServer(("127.0.0.1", 0), service)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()

            def activate(consent):
                if consent is not True:
                    raise ValueError("동의 필요")
                server.sharing.process = Mock()
                server.sharing.process.poll.return_value = None
                server.sharing.url = "https://fixture-only.trycloudflare.com"
                server.sharing.code = "fixture-access-code"
                return server.sharing.status(True)

            try:
                with (
                    patch.object(server.sharing, "start", side_effect=activate),
                    patch.object(
                        service.custom_model,
                        "models",
                        return_value={"models": ["local-fixture:small"]},
                    ),
                    sync_playwright() as p,
                ):
                    browser = p.chromium.launch(
                        headless=True, executable_path=find_local_browser()
                    )
                    context = browser.new_context(
                        permissions=["clipboard-read", "clipboard-write"]
                    )
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(f"http://127.0.0.1:{server.server_port}")
                    page.get_by_role("button", name="자체 LLM 연결", exact=True).click()
                    page.locator("#connection-preset").select_option("ollama")
                    expect(page.locator("#connection-url")).to_have_value(
                        "http://127.0.0.1:11434/v1"
                    )
                    page.locator("#connection-model").fill("local-fixture:small")
                    page.locator("#connection-key").fill("fixture-api-key")
                    page.locator("#connection-consent").check()
                    page.get_by_role("button", name="연결 적용", exact=True).click()
                    expect(page.locator("#provider")).to_have_value("custom")
                    expect(page.locator("#connection-key")).to_have_value("")
                    page.get_by_role("button", name="모델 목록", exact=True).click()
                    expect(page.locator("#available-models option")).to_have_attribute(
                        "value", "local-fixture:small"
                    )
                    self.assertEqual(
                        page.locator("#sharing-view, .nav[data-view=sharing]").count(),
                        0,
                    )
                    evidence = (
                        Path(__file__).resolve().parents[1]
                        / "result"
                        / "ui_verification"
                    )
                    evidence.mkdir(parents=True, exist_ok=True)
                    for view in ["guide", "connection"]:
                        page.get_by_role(
                            "button",
                            name="처음 사용하기"
                            if view == "guide"
                            else "자체 LLM 연결",
                            exact=True,
                        ).click()
                        for width in [1440, 390]:
                            page.set_viewport_size({"width": width, "height": 960})
                            page.screenshot(
                                path=str(evidence / f"{view}-{width}.png"),
                                full_page=True,
                            )
                            self.assertTrue(
                                page.evaluate(
                                    "document.documentElement.scrollWidth <= window.innerWidth"
                                )
                            )
                    self.assertEqual(errors, [])
                    browser.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
