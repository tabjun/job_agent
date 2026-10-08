import json
import re
import tempfile
import threading
import unittest
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from job_agent.browser.session import find_local_browser
from job_agent.core.paths import ProjectPaths
from job_agent.ui.server import LocalServer
from job_agent.ui.service import WorkspaceService


class ExamplesBrowserTests(unittest.TestCase):
    def test_guides_deep_links_actions_and_no_automatic_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            service = WorkspaceService(ProjectPaths(Path(folder)))
            server = LocalServer(("127.0.0.1", 0), service)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            original = service.profile()
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True, executable_path=find_local_browser()
                    )
                    page = browser.new_page()
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
                    writes, errors = [], []
                    page.on(
                        "request",
                        lambda request: (
                            writes.append(request.url)
                            if request.method == "POST"
                            else None
                        ),
                    )
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    reads = []
                    page.on("request", lambda request: reads.append(request.url))
                    for fragment in ["", "#history", "#sharing"]:
                        page.goto(f"http://127.0.0.1:{server.server_port}/{fragment}")
                        expect(page.locator("#guide-view")).to_be_visible()
                        expect(page.locator("#profile-panel")).to_be_hidden()
                        expect(page.locator("#output")).to_be_hidden()
                    self.assertFalse(
                        any(
                            "/api/runs" in url or "/api/sharing" in url for url in reads
                        )
                    )
                    page.goto(f"http://127.0.0.1:{server.server_port}/#examples/sync")
                    page.reload()
                    expect(page.locator("#example-sync")).to_be_visible()
                    page.locator(".nav[data-view=guide]").click()
                    expect(page.locator("#guide-view")).to_be_visible()
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
                            path=str(evidence / f"guide-{width}.png"), full_page=True
                        )
                    self.assertEqual(
                        page.locator(
                            "#history-view, #sharing-view, .nav[data-view=history], .nav[data-view=sharing]"
                        ).count(),
                        0,
                    )
                    page.locator('[data-guide-action="profile"]').click()
                    expect(page.locator("#profile-panel")).to_be_visible()
                    expect(page.locator("#profile-panel")).to_have_attribute("open", "")
                    page.locator(".nav[data-view=examples]").click()
                    expect(page.locator("#profile-panel")).to_be_hidden()
                    expect(page.locator(".model-bar")).to_be_hidden()
                    evidence = (
                        Path(__file__).resolve().parents[1] / "result/ui_verification"
                    )
                    evidence.mkdir(parents=True, exist_ok=True)
                    for width in [390, 1440]:
                        page.set_viewport_size({"width": width, "height": 960})
                        for topic in [
                            "profile",
                            "search",
                            "resume",
                            "prepare",
                            "platforms",
                            "sync",
                        ]:
                            page.locator(f"#example-tab-{topic}").click()
                            expect(page.locator(f"#example-{topic}")).to_be_visible()
                            shots = page.locator(f"#example-{topic} .tutorial-shot")
                            self.assertGreater(shots.count(), 0)
                            for img in page.locator(
                                f"#example-{topic} .tutorial-shot img"
                            ).all():
                                img.scroll_into_view_if_needed()
                                expect(img).to_be_visible()
                                page.wait_for_function(
                                    "img => img.complete && img.naturalWidth > 0",
                                    arg=img.element_handle(),
                                )
                            shots.first.click()
                            expect(page.locator("#tutorial-dialog")).to_be_visible()
                            page.locator("#tutorial-dialog").press("Escape")
                            expect(page.locator("#tutorial-dialog")).to_be_hidden()
                            self.assertTrue(
                                page.evaluate(
                                    "document.documentElement.scrollWidth <= innerWidth"
                                )
                            )
                        page.screenshot(
                            path=str(evidence / f"examples-{width}.png"), full_page=True
                        )
                    page.locator("#example-tab-search").click()
                    page.get_by_role(
                        "button", name="예시 공고 넣기", exact=True
                    ).click()
                    expect(page.locator("#search-form [name=postings]")).to_have_value(
                        re.compile("가상 테스트 공고")
                    )
                    page.get_by_role(
                        "button", name="이 화면의 사용 예시", exact=True
                    ).click()
                    expect(page.locator("#example-search")).to_be_visible()
                    page.locator("#example-tab-resume").click()
                    page.get_by_role("button", name="가상 JD 넣기", exact=True).click()
                    expect(page.locator("#resume-form [name=jd]")).to_have_value(
                        "[가상 예시] Python과 SQL로 제품 데이터를 분석하고 정기 보고서를 작성하는 데이터 분석가를 찾습니다."
                    )
                    page.get_by_role(
                        "button", name="이 화면의 사용 예시", exact=True
                    ).click()
                    page.locator("#example-tab-profile").click()
                    with page.expect_download() as download:
                        page.get_by_role(
                            "button", name="빈 표준 양식 받기", exact=True
                        ).click()
                    self.assertEqual(
                        download.value.suggested_filename, "resume-template-v1.docx"
                    )
                    page.locator("#example-tab-profile").press("End")
                    expect(page.locator("#example-sync")).to_be_visible()
                    page.reload()
                    expect(page.locator("#example-sync")).to_be_visible()
                    self.assertEqual(writes, [])
                    self.assertEqual(service.profile(), original)
                    self.assertEqual(errors, [])
                    browser.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
