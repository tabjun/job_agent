import tempfile
import unittest
import json
import os
from pathlib import Path
from zipfile import ZipFile

from resume_library import compile_draft, extract_sources
from site_form_filler import approved_actions, apply_actions
from site_form_mapper import find_local_browser


class LibraryTests(unittest.TestCase):
    def test_deduplication_citations_and_changed_source(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'resume.docx'
            with ZipFile(path, 'w') as archive:
                archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Source fact</w:t></w:r></w:p></w:body></w:document>')
            corpus = extract_sources([path, path])
            self.assertEqual(len(corpus['sources']), 1)
            draft = {'blocks': [{'field': 'summary', 'text': 'Reviewed source fact', 'evidence': [
                {'source_id': 'source_1', 'paragraph_indices': [0]}]}]}
            result = compile_draft(corpus, draft)
            self.assertEqual(result['source_evidence']['summary'][0]['text'], 'Source fact')
            draft['blocks'][0]['evidence'][0]['paragraph_indices'] = [100]
            with self.assertRaises(ValueError):
                compile_draft(corpus, draft)
            draft['blocks'][0]['evidence'] = []
            with self.assertRaises(ValueError):
                compile_draft(corpus, draft)
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                compile_draft(corpus, draft)


class ActualReviewedDraftTests(unittest.IsolatedAsyncioTestCase):
    @unittest.skipUnless(os.environ.get('RESUME_MASTER_PACKAGE'), 'Set RESUME_MASTER_PACKAGE for private draft integration')
    async def test_reviewed_master_package_to_browser(self):
        from playwright.async_api import async_playwright
        package = json.loads(Path(os.environ['RESUME_MASTER_PACKAGE']).read_text(encoding='utf-8'))
        fields = package['package']['field_values']
        plan = {'mappings': [{'package_path': key, 'approved': True,
                             'best_match': {'selector': f'#field_{i}'}}
                            for i, key in enumerate(fields)]}
        async with async_playwright() as p:
            options = {'headless': True}
            executable = find_local_browser()
            if executable:
                options['executable_path'] = executable
            browser = await p.chromium.launch(**options)
            try:
                page = await browser.new_page()
                await page.set_content(''.join(f'<textarea id="field_{i}"></textarea>' for i in range(len(fields))))
                actions = approved_actions(package, plan)
                await apply_actions(page, actions)
                for action in actions:
                    self.assertEqual(await page.locator(action['target']['selector']).input_value(), action['value'])
            finally:
                await browser.close()


if __name__ == '__main__':
    unittest.main()
