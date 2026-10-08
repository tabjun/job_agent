import os
from pathlib import Path
import unittest

from playwright.sync_api import expect, sync_playwright

from job_agent.browser.session import find_local_browser


@unittest.skipUnless(
    os.environ.get("RESUME_PUBLIC_TEST_URL"), "Explicit public demo URL required"
)
class PublicDemoBrowserTests(unittest.TestCase):
    def test_mobile_and_desktop_without_access_code(self):
        url = os.environ["RESUME_PUBLIC_TEST_URL"]
        evidence = Path(__file__).resolve().parents[1] / "result/ui_verification"
        evidence.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, executable_path=find_local_browser()
            )
            try:
                contexts = []
                for width in [390, 1440]:
                    context = browser.new_context(
                        viewport={"width": width, "height": 960}
                    )
                    contexts.append(context)
                    page = context.new_page()
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(url + "/#examples/search", wait_until="networkidle")
                    expect(page.locator("#example-search")).to_be_visible()
                    expect(page.locator("#visitor-notice")).to_be_visible()
                    expect(page.locator("#visitor-clear")).to_be_visible()
                    page.locator("#privacy-policy summary").click()
                    expect(page.locator("#privacy-storage")).to_contain_text(
                        "60초 이내"
                    )
                    expect(page.locator("#privacy-browser")).to_contain_text(
                        "localStorage/IndexedDB"
                    )
                    self.assertEqual(
                        page.locator("#login-form, #sharing-code").count(), 0
                    )
                    expect(page.locator(".model-bar")).to_be_hidden()
                    text = page.locator("body").inner_text()
                    for term in ["접근 코드", "OpenAI", "Gemini", "LLM 없음", "과금"]:
                        self.assertNotIn(term, text)
                    page.get_by_role(
                        "button", name="예시 공고 넣기", exact=True
                    ).click()
                    page.locator("#search-form button[type=submit]").click()
                    expect(page.locator("#jobs article")).to_have_count(2, timeout=15000)
                    page.locator('.nav[data-view="prepare"]').click()
                    expect(page.locator("#sync-panel")).to_be_hidden()
                    expect(page.locator("#profile-panel .source-line")).to_be_hidden()
                    page.locator("#profile-panel > summary").click()
                    page.locator("#profile-format").select_option("json")
                    first_field = page.locator("#profile-fields textarea").first
                    first_field.fill(f"Synthetic local download {width}")
                    page.locator("#profile-form button[type=submit]").click()
                    expect(page.locator("#profile-feedback")).to_contain_text(
                        "임시 반영 완료"
                    )
                    with page.expect_download() as pending:
                        page.locator("#profile-download").click()
                    download = pending.value
                    self.assertEqual(
                        download.suggested_filename, "resume-profile-v1.json"
                    )
                    self.assertIn(
                        f"Synthetic local download {width}",
                        Path(download.path()).read_text(encoding="utf-8"),
                    )
                    page.locator('.nav[data-view="guide"]').click()
                    expect(page.locator("#guide-view")).to_be_visible()
                    self.assertEqual(page.locator("#history-view, #sharing-view").count(), 0)
                    self.assertNotIn("접근 코드", page.locator("body").inner_text())
                    self.assertTrue(
                        page.evaluate(
                            "document.documentElement.scrollWidth <= innerWidth"
                        )
                    )
                    page.screenshot(
                        path=str(evidence / f"public-demo-{width}.png"), full_page=True
                    )
                    self.assertEqual(errors, [])
                # Two separate browser cookies have independent run stores.
                for context in contexts:
                    page = context.pages[0]
                    page.reload(wait_until="networkidle")
                    expect(page.locator("#result-body")).to_be_hidden()
                    self.assertEqual(page.evaluate("localStorage.length"), 0)
                    self.assertEqual(page.evaluate("sessionStorage.length"), 0)
                    self.assertEqual(
                        page.evaluate(
                            "async () => (await indexedDB.databases()).length"
                        ),
                        0,
                    )
                first = contexts[0].pages[0]
                first.on("dialog", lambda dialog: dialog.accept())
                first.locator("#visitor-clear").click()
                expect(first.locator("#result-body")).to_be_hidden()
                expect(first.locator("#search-form [name=postings]")).to_have_value("")
                expect(first.locator("#profile-fields textarea").first).to_have_value(
                    ""
                )
                second = contexts[1].pages[0]
                second.reload(wait_until="networkidle")
                expect(second.locator("#result-body")).to_be_hidden()
                expect(second.locator("#profile-fields textarea").first).to_have_value(
                    "Synthetic local download 1440"
                )
            finally:
                browser.close()
