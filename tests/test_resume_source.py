import tempfile
import unittest
import os
from pathlib import Path
from zipfile import ZipFile

from job_agent.documents.source import (
    build_source_package,
    career_evidence,
    DocxReader,
    summary_evidence,
)
from job_agent.browser.filler import approved_actions, FormFiller
from job_agent.browser.session import find_local_browser


class SourceTests(unittest.TestCase):
    def test_document_order_includes_tables_and_excludes_deleted_revision_text(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.docx"
            with ZipFile(path, "w") as archive:
                archive.writestr(
                    "word/document.xml",
                    """
                <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                  <w:body><w:p><w:r><w:t>First</w:t></w:r></w:p>
                  <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Table</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
                  <w:p><w:del><w:r><w:delText>Old</w:delText></w:r></w:del><w:ins><w:r><w:t>Current</w:t></w:r></w:ins></w:p>
                  </w:body></w:document>""",
                )
            self.assertEqual(
                [row["text"] for row in DocxReader(path).read()],
                ["First", "Table", "Current"],
            )

    def test_career_block_is_verbatim_and_missing_boundaries_fail(self):
        rows = [
            {"paragraph_index": i, "text": text}
            for i, text in enumerate(
                [
                    "경력사항",
                    "2025-current",
                    "Company",
                    "역할",
                    "Original qualifier",
                    "핵심역량",
                    "Other",
                ]
            )
        ]
        self.assertEqual(career_evidence(rows), [rows[4]])
        with self.assertRaises(ValueError):
            career_evidence(rows[:5])

    def test_summary_has_explicit_boundaries(self):
        rows = [
            {"paragraph_index": i, "text": text}
            for i, text in enumerate(
                ["Github / Notion portfolio", "Exact source summary", "Profile"]
            )
        ]
        self.assertEqual(summary_evidence(rows), [rows[1]])
        with self.assertRaises(ValueError):
            summary_evidence(rows[:2])


class ActualSourceTests(unittest.IsolatedAsyncioTestCase):
    @unittest.skipUnless(
        os.environ.get("RESUME_TEST_DOCX"),
        "Set RESUME_TEST_DOCX for private source integration",
    )
    async def test_actual_docx_package_to_python_browser_filler(self):
        from playwright.async_api import async_playwright

        source = Path(os.environ["RESUME_TEST_DOCX"])
        paragraphs = DocxReader(source).read()
        async with async_playwright() as p:
            options = {"headless": True}
            executable = find_local_browser()
            if executable:
                options["executable_path"] = executable
            browser = await p.chromium.launch(**options)
            try:
                page = await browser.new_page()
                # Local fixture only: no authentication or production save is exercised.
                await page.set_content("""<textarea id="career" onblur="document.querySelector('#committed').textContent=this.value"></textarea>
                    <textarea id="summary" maxlength="5000" onblur="document.querySelector('#committed').textContent=this.value"></textarea>
                    <output id="committed"></output>""")
                for site in ["catch", "jobkorea", "saramin", "wanted", "incruit"]:
                    package = build_source_package(source, paragraphs, site)
                    path = "summary" if site == "wanted" else "experience.description"
                    selector = "#summary" if site == "wanted" else "#career"
                    actions = approved_actions(
                        package,
                        {
                            "mappings": [
                                {
                                    "package_path": path,
                                    "approved": True,
                                    "best_match": {"selector": selector},
                                }
                            ]
                        },
                    )
                    self.assertTrue(actions[0]["value"])
                    await FormFiller(page, actions).apply()
                    self.assertEqual(
                        await page.locator(selector).input_value(), actions[0]["value"]
                    )
                    self.assertEqual(
                        await page.locator("#committed").text_content(),
                        actions[0]["value"],
                    )
            finally:
                await browser.close()


if __name__ == "__main__":
    unittest.main()
