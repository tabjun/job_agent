"""Local browser checks with synthetic sources and mocked paid providers."""

import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import AsyncMock, patch
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright

from job_agent.browser.session import find_local_browser
from job_agent.core.paths import ProjectPaths
from job_agent.ui.server import LocalServer
from job_agent.ui.service import WorkspaceService


class UiBrowserTests(unittest.TestCase):
    def test_offline_and_mock_ai_forms_history_uploads_and_responsive_layout(self):
        from test_company_applications import form, master, registry

        with (
            tempfile.TemporaryDirectory() as folder,
            patch.dict(os.environ, {"OPENAI_API_KEY": "mock-key"}),
        ):
            root = Path(folder)
            analyzer = AsyncMock(
                return_value={
                    "text": "[모의 테스트] 원문 검수 필요",
                    "usage": {"total_tokens": 12},
                }
            )
            service = WorkspaceService(ProjectPaths(root), analyzer=analyzer)
            server = LocalServer(("127.0.0.1", 0), service)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with sync_playwright() as playwright:
                    options = {"headless": True}
                    if find_local_browser():
                        options["executable_path"] = find_local_browser()
                    browser = playwright.chromium.launch(**options)
                    try:
                        page = browser.new_page(
                            viewport={"width": 1440, "height": 1000}
                        )
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.goto(f"http://127.0.0.1:{server.server_port}")
                        page.locator(".nav[data-view=search]").click()
                        expect(page.locator("#key-status")).to_contain_text(
                            "LLM 호출 없음"
                        )
                        self.assertGreater(page.locator("svg.lucide").count(), 8)
                        self.assertEqual(
                            page.locator("#provider").input_value(), "none"
                        )
                        self.assertEqual(page.locator("#provider option").count(), 4)
                        self.screenshot(page, "desktop-empty")
                        page.locator("#sample").click()
                        page.locator("#search-form button[type=submit]").click()
                        page.wait_for_selector(".job-row")
                        self.assertEqual(page.locator(".job-row").count(), 2)
                        analyzer.assert_not_called()
                        self.screenshot(page, "desktop-results")
                        page.locator("#provider").select_option("openai")
                        page.locator("#model").fill("mock-model")
                        page.locator("#ai-consent").check()
                        page.locator("#search-form button[type=submit]").click()
                        expect(page.locator("#ai-tab")).to_be_enabled()
                        page.locator("#ai-tab").click()
                        expect(page.locator("#report")).to_contain_text("모의 테스트")
                        analyzer.assert_awaited_once()
                        page.set_viewport_size({"width": 390, "height": 950})
                        self.assertLessEqual(
                            page.evaluate("document.documentElement.scrollWidth"), 390
                        )
                        self.screenshot(page, "mobile-ai")
                        page.set_viewport_size({"width": 1440, "height": 1000})
                        with page.expect_download() as download:
                            page.locator("#download").click()
                        self.assertTrue(
                            download.value.suggested_filename.endswith(".json")
                        )
                        page.locator(".nav[data-view=resume]").click()
                        page.locator("#provider").select_option("none")
                        page.locator("#profile-panel > summary").click()
                        page.locator("#profile-format").select_option("json")
                        with page.expect_download() as download:
                            page.locator("#template-download").click()
                        self.assertEqual(
                            download.value.suggested_filename, "resume-template-v1.json"
                        )
                        docx = root / "fixture.docx"
                        with ZipFile(docx, "w") as archive:
                            archive.writestr(
                                "word/document.xml",
                                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>운영 경험</w:t></w:r></w:p><w:p><w:r><w:t>SQL 분석 경험</w:t></w:r></w:p></w:body></w:document>',
                            )
                        page.locator("#docx").set_input_files(str(docx))
                        expect(
                            page.locator(
                                '[data-field="experience_description"] textarea'
                            )
                        ).to_have_value("운영 경험\nSQL 분석 경험")
                        page.locator("#profile-form button[type=submit]").click()
                        expect(page.locator("#profile-status")).to_contain_text(
                            "미검수 1개"
                        )
                        page.locator(
                            '[data-field="experience_description"] input[type=checkbox]'
                        ).check()
                        page.locator("#profile-form button[type=submit]").click()
                        expect(page.locator("#profile-status")).to_contain_text(
                            "미검수 0개"
                        )
                        page.locator("#profile-panel > summary").click()
                        page.locator("#resume-form [name=keywords]").fill("SQL")
                        page.locator("#resume-form button[type=submit]").click()
                        expect(page.locator("#report")).to_have_text(
                            "SQL 분석 경험\n\n운영 경험"
                        )
                        page.locator(".nav[data-view=prepare]").click()
                        imported = master()
                        for key, refs in imported["package"]["source_evidence"].items():
                            for ref in refs:
                                ref["text"] = imported["package"]["field_values"][key]
                        file = root / "profile-master.json"
                        file.write_text(json.dumps(imported), encoding="utf-8")
                        page.locator("#profile-panel > summary").click()
                        page.locator("#profile-file").set_input_files(str(file))
                        expect(page.locator("#profile-status")).to_contain_text(
                            "저장 전 변경"
                        )
                        page.locator("#profile-form button[type=submit]").click()
                        expect(page.locator("#profile-status")).to_contain_text(
                            "미검수 3개"
                        )
                        for key in ["name", "summary", "employment"]:
                            page.locator(
                                f'[data-field="{key}"] input[type=checkbox]'
                            ).check()
                        page.locator("#profile-form button[type=submit]").click()
                        expect(page.locator("#profile-status")).to_contain_text(
                            "미검수 0개"
                        )
                        self.screenshot(page, "profile-desktop")
                        page.set_viewport_size({"width": 390, "height": 950})
                        self.assertLessEqual(
                            page.evaluate("document.documentElement.scrollWidth"), 390
                        )
                        self.screenshot(page, "profile-mobile")
                        page.set_viewport_size({"width": 1440, "height": 1000})
                        with page.expect_download() as download:
                            page.locator("#profile-download").click()
                        self.assertEqual(
                            download.value.suggested_filename, "resume-profile-v1.json"
                        )
                        page.locator("#profile-panel > summary").click()
                        for name, data in [
                            ("target", registry().target("company-example")),
                            ("form_map", form()),
                        ]:
                            file = root / f"{name}.json"
                            file.write_text(json.dumps(data), encoding="utf-8")
                            page.locator("#company-advanced").evaluate(
                                "element => element.open = true"
                            )
                            page.locator(
                                f"#prepare-form [name={name}]"
                            ).set_input_files(str(file))
                        page.locator("#prepare-form button[type=submit]").click()
                        expect(page.locator("#report")).to_contain_text(
                            "draft_only_no_browser_save"
                        )

                        class Worker:
                            def call(self, operation, payload):
                                if operation == "capture":
                                    return {
                                        "site": "catch",
                                        "nonce": "fixture",
                                        "url": "https://example.test/edit",
                                        "profile_fields": [
                                            {
                                                "id": "summary",
                                                "value": "Reviewed experience",
                                            }
                                        ],
                                        "fields": [
                                            {"selector": "#summary", "labels": ["소개"]}
                                        ],
                                        "buttons": [
                                            {"selector": "#save", "label": "저장"}
                                        ],
                                        "saved_mappings": [],
                                        "saved_save_index": None,
                                        "autosave_available": False,
                                    }
                                if operation == "apply":
                                    if (
                                        payload["mappings"]
                                        != [{"field_id": "summary", "target_index": 0}]
                                        or not payload["consent"]
                                    ):
                                        raise ValueError("Invalid approval")
                                    return {
                                        "site": "catch",
                                        "status": "saved_verified",
                                        "message": "[모의] 저장 확인",
                                        "changed_fields": ["summary"],
                                    }
                                return {"message": "[모의] 로그인 화면"}

                            def close(self):
                                pass

                        service._sync_worker = Worker()
                        page.locator("#sync-open").click()
                        expect(page.locator("#notice")).to_contain_text("로그인 화면")
                        page.locator("#sync-capture").click()
                        expect(page.locator("#sync-apply")).to_be_enabled()
                        page.locator("#sync-fields select").select_option("0")
                        page.locator("#sync-save").select_option("0")
                        for width in [1440, 390]:
                            page.set_viewport_size({"width": width, "height": 950})
                            self.assertLessEqual(
                                page.evaluate("document.documentElement.scrollWidth"),
                                width,
                            )
                            self.screenshot(page, f"sync-{width}")
                        page.locator("#sync-consent").check()
                        page.locator("#sync-apply").click()
                        expect(page.locator("#sync-result")).to_contain_text(
                            "저장 확인 완료"
                        )
                        expect(page.locator("#sync-apply")).to_be_disabled()
                        page.set_viewport_size({"width": 1440, "height": 1000})
                        self.assertEqual(
                            page.locator("#history-view, #sharing-view").count(), 0
                        )
                        page.reload()
                        expect(page.locator("#result-body")).to_be_hidden()
                        self.assertEqual(len(service.runs()), 4)
                        for width in [390, 768, 1440]:
                            page.set_viewport_size({"width": width, "height": 950})
                            page.locator(".nav[data-view=search]").click()
                            self.assertLessEqual(
                                page.evaluate("document.documentElement.scrollWidth"),
                                width,
                            )
                            self.screenshot(page, f"viewport-{width}")
                        self.assertFalse(errors, errors)
                    finally:
                        browser.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    @staticmethod
    def screenshot(page, name):
        directory = os.getenv("UI_SCREENSHOT_DIR")
        if directory:
            target = Path(directory)
            target.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(target / f"{name}.png"), full_page=True)


if __name__ == "__main__":
    unittest.main()
