import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from playwright.sync_api import expect, sync_playwright
from test_job_alerts import FakeMailer, code_from

from job_agent.browser.session import find_local_browser
from job_agent.core.paths import ProjectPaths
from job_agent.ui.server import LocalServer
from job_agent.ui.service import WorkspaceService

SHOTS = os.getenv("UI_SCREENSHOT_DIR")


class AlertBrowserTests(unittest.TestCase):
    def test_verify_email_save_conditions_and_preview(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.dict(os.environ, {"TAVILY_API_KEY": "fixture"}),
        ):
            server = LocalServer(
                ("127.0.0.1", 0), WorkspaceService(ProjectPaths(Path(folder)))
            )
            mailer = FakeMailer()
            server.alerts.mailer = mailer
            server.alerts.verifier = Mock(
                return_value={"status": "open", "evidence": "fixture"}
            )
            server.alerts.searcher = Mock(
                return_value=[
                    {
                        "title": "데이터 분석가 (Python, SQL)",
                        "url": "https://www.wanted.co.kr/wd/101",
                        "content": "서울 강남 · 경력 1~3년",
                    }
                ]
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True, executable_path=find_local_browser()
                    )
                    page = browser.new_page(viewport={"width": 1280, "height": 1000})
                    page.on("dialog", lambda dialog: dialog.accept())
                    page.goto(f"http://127.0.0.1:{server.server_port}/#alerts")
                    expect(page.locator("#alerts-view")).to_be_visible()
                    expect(page.locator(".alert-platform")).to_have_count(5)
                    expect(page.locator("#alert-setup")).to_be_hidden()
                    page.fill("#alert-email", "me@example.com")
                    page.click("#alert-send-code")
                    expect(page.locator("#notice")).to_contain_text(
                        "인증 코드를 보냈습니다"
                    )
                    page.fill("#alert-code", code_from(mailer))
                    page.click("#alert-email-form button[type=submit]")
                    expect(page.locator("#alert-emails")).to_contain_text(
                        "me@example.com"
                    )
                    page.fill("#alert-name", "데이터 분석 경력")
                    page.check("#alert-site-wanted")
                    page.fill("#alert-wanted-role", "데이터 분석가")
                    page.fill("#alert-wanted-keywords", "Python, SQL")
                    page.check("#alert-site-saramin")
                    page.click("#alert-copy")
                    expect(page.locator("#alert-saramin-keywords")).to_have_value(
                        "Python, SQL"
                    )
                    page.check("#alert-consent")
                    page.click("#alert-form button[type=submit]")
                    expect(page.locator(".alert-row")).to_have_count(1)
                    expect(page.locator(".alert-row")).to_contain_text(
                        "사람인 · 원티드"
                    )
                    expect(page.locator(".alert-row")).to_contain_text("평일 08:00")
                    page.locator(".alert-row button", has_text="미리보기").click()
                    expect(page.locator(".alert-preview a")).to_have_text(
                        "데이터 분석가 (Python, SQL)"
                    )
                    self.assertEqual(len(mailer.sent), 1)  # only the code mail
                    if SHOTS:
                        page.screenshot(
                            path=str(Path(SHOTS) / "job_alerts.png"), full_page=True
                        )
                    page.set_viewport_size({"width": 390, "height": 844})
                    width = page.evaluate("document.documentElement.scrollWidth")
                    self.assertLessEqual(width, 390)
                    browser.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == "__main__":
    unittest.main()
