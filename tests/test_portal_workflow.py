from pathlib import Path
import tempfile
import threading
import unittest

from playwright.sync_api import expect, sync_playwright

from job_agent.browser.session import find_local_browser
from job_agent.browser.suggestions import propose_mappings
from job_agent.core.paths import ProjectPaths
from job_agent.ui.server import LocalServer
from job_agent.ui.service import WorkspaceService


class SuggestionsTests(unittest.TestCase):
    def test_exact_unique_fits_and_no_single_company_input(self):
        fields = [
            {"tag": "textarea", "labels": ["소개"], "id": "summary"},
            {"tag": "input", "labels": ["경력사항"]},
            {
                "tag": "select",
                "labels": ["재직 형태"],
                "options": [{"label": "정규직", "value": "full"}],
            },
        ]
        self.assertEqual(
            propose_mappings(
                {
                    "summary": "fact",
                    "experience_description": "many companies",
                    "employment_type": "정규직",
                },
                fields,
            ),
            [
                {"field_id": "summary", "target_index": 0},
                {"field_id": "employment_type", "target_index": 2},
            ],
        )
        self.assertEqual(
            propose_mappings({"summary": "fact"}, [fields[0], fields[0]]), []
        )
        self.assertEqual(
            propose_mappings({"summary": "fact"}, [{**fields[0], "max_length": 2}]), []
        )


class PortalBrowserTests(unittest.TestCase):
    def test_selected_sites_open_review_save_and_no_unapproved_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            service = WorkspaceService(ProjectPaths(Path(folder)))
            server = LocalServer(("127.0.0.1", 0), service)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            calls = []

            class Worker:
                def call(self, operation, payload):
                    calls.append((operation, payload))
                    site = payload["site"]
                    if operation == "capture":
                        return {
                            "site": site,
                            "nonce": "fixture",
                            "url": "https://example.test/editor",
                            "profile_fields": [
                                {"id": "summary", "value": "Synthetic fact"}
                            ],
                            "fields": [
                                {
                                    "tag": "textarea",
                                    "labels": ["소개"],
                                    "selector": "#summary",
                                }
                            ],
                            "buttons": [{"label": "저장", "selector": "#save"}],
                            "saved_mappings": [],
                            "suggested_mappings": [
                                {"field_id": "summary", "target_index": 0}
                            ],
                            "saved_save_index": None,
                            "suggested_save_index": 0,
                            "autosave_available": site == "wanted",
                        }
                    if operation == "apply":
                        assert payload["consent"]
                        assert payload["mappings"] == [
                            {"field_id": "summary", "target_index": 0}
                        ]
                        return {
                            "site": site,
                            "status": "saved_verified",
                            "message": "verified",
                            "changed_fields": ["summary"],
                        }
                    return {
                        "site": site,
                        "status": "editor_candidate",
                        "message": "로그인·편집 화면 확인 필요",
                    }

                def close(self):
                    pass

            service._sync_worker = Worker()
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True, executable_path=find_local_browser()
                    )
                    page = browser.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(f"http://127.0.0.1:{server.server_port}/#resume")
                    page.locator("#profile-panel > summary").click()
                    page.locator('[data-field="summary"] textarea').fill(
                        "Synthetic fact"
                    )
                    page.locator("#profile-form button[type=submit]").click()
                    expect(page.locator("#profile-feedback")).to_contain_text(
                        "저장 완료"
                    )
                    page.locator('[data-field="summary"] > .consent input').check()
                    page.locator("#profile-form button[type=submit]").click()
                    expect(page.locator("#profile-status")).to_contain_text("미검수 0")
                    page.locator('.nav[data-view="prepare"]').click()
                    expect(page.locator("#company-advanced form")).to_be_hidden()
                    page.locator("#portal-proceed").click()
                    expect(page.locator("#notice")).to_contain_text("하나 이상")
                    for site in ["catch", "wanted"]:
                        page.locator(f'#portal-sites input[value="{site}"]').check()
                    page.locator("#portal-proceed").click()
                    expect(page.locator("#notice")).to_contain_text("동의")
                    self.assertEqual(calls, [])
                    page.locator("#portal-consent").check()
                    page.locator("#portal-proceed").click()
                    expect(page.locator("#portal-status")).to_contain_text("열었습니다")
                    self.assertEqual(
                        [
                            payload["site"]
                            for operation, payload in calls
                            if operation == "open"
                        ],
                        ["catch", "wanted"],
                    )
                    self.assertFalse(
                        any(operation in {"capture", "apply"} for operation, _ in calls)
                    )
                    for site in ["catch", "wanted"]:
                        page.locator(f'.portal-row[data-site="{site}"] button').click()
                        expect(page.locator("#sync-fields select")).to_have_value("0")
                        expect(page.locator("#sync-save")).to_have_value("0")
                        expect(page.locator("#sync-consent")).not_to_be_checked()
                        page.locator("#sync-apply").click()
                        expect(page.locator("#notice")).to_contain_text("동의")
                        self.assertFalse(
                            any(
                                operation == "apply" and payload["site"] == site
                                for operation, payload in calls
                            )
                        )
                        page.locator("#sync-consent").check()
                        page.locator("#sync-apply").click()
                        expect(
                            page.locator(f'.portal-row[data-site="{site}"] p')
                        ).to_contain_text("확인 완료")
                    for width in [390, 1440]:
                        page.set_viewport_size({"width": width, "height": 960})
                        self.assertTrue(
                            page.evaluate(
                                "document.documentElement.scrollWidth <= innerWidth"
                            )
                        )
                        qa = (
                            Path(__file__).resolve().parents[1]
                            / "result/ui_verification"
                        )
                        qa.mkdir(parents=True, exist_ok=True)
                        page.screenshot(
                            path=str(qa / f"portal-workflow-{width}.png"),
                            full_page=True,
                        )
                    self.assertEqual(errors, [])
                    browser.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
