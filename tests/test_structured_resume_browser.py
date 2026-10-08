import os
from pathlib import Path
import tempfile
import threading
import unittest
from zipfile import ZipFile

from playwright.sync_api import expect, sync_playwright

from job_agent.browser.session import find_local_browser
from job_agent.core.paths import ProjectPaths
from job_agent.hosting.build import ROOT, build
from job_agent.hosting.preview import server as preview_server
from job_agent.ui.server import LocalServer
from job_agent.ui.service import WorkspaceService


class StructuredBrowserTests(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get("RESUME_SOURCE_TEST_DOCX"), "Private source is explicitly opt-in"
    )
    def test_private_reference_docx_is_local_unreviewed_and_not_persisted(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            sync_playwright() as playwright,
        ):
            paths = ProjectPaths(Path(directory))
            app = LocalServer(("127.0.0.1", 0), WorkspaceService(paths, ephemeral=True))
            thread = threading.Thread(target=app.serve_forever, daemon=True)
            thread.start()
            browser = playwright.chromium.launch(
                headless=True, executable_path=find_local_browser()
            )
            try:
                page = browser.new_page()
                page.goto(f"http://127.0.0.1:{app.server_port}/#resume")
                expect(page.locator("#profile-status")).to_contain_text("0개 항목")
                page.locator("#profile-panel > summary").click()
                page.locator("#profile-file").set_input_files(
                    os.environ["RESUME_SOURCE_TEST_DOCX"]
                )
                expect(page.locator("#notice")).to_contain_text("일반 DOCX 원문")
                self.assertGreater(
                    page.evaluate(
                        'profile.fields.find(r => r.id === "summary").value.length'
                    ),
                    100,
                )
                self.assertFalse(page.evaluate("profile.fields.some(r => r.reviewed)"))
                self.assertFalse(paths.results.exists())
            finally:
                browser.close()
                app.shutdown()
                thread.join(timeout=3)
                app.server_close()

    def test_local_and_public_documents_editor_and_conversion_handoff(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            sync_playwright() as playwright,
        ):
            root = Path(directory)
            export = build(root / "export")
            local = LocalServer(
                ("127.0.0.1", 0),
                WorkspaceService(ProjectPaths(root / "local"), ephemeral=True),
            )
            public = preview_server(export, 0)
            browser = playwright.chromium.launch(
                headless=True, executable_path=find_local_browser()
            )
            try:
                for app, mode in ((local, "local"), (public, "public")):
                    thread = threading.Thread(target=app.serve_forever, daemon=True)
                    thread.start()
                    context = browser.new_context(
                        viewport={"width": 1440, "height": 1000}
                    )
                    page = context.new_page()
                    errors = []
                    requests = []
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    page.on("request", lambda r: requests.append(r.url))
                    try:
                        url = (
                            os.environ.get("RESUME_STRUCTURED_TEST_URL")
                            if mode == "public"
                            else None
                        )
                        page.goto(
                            (url or f"http://127.0.0.1:{app.server_port}/") + "#resume"
                        )
                        expect(page.locator("#profile-status")).to_contain_text(
                            "0개 항목"
                        )
                        page.locator("#profile-panel > summary").click()
                        self.assertEqual(
                            page.locator("#profile-format").input_value(), "docx"
                        )
                        with page.expect_download() as pending:
                            page.locator("#template-download").click()
                        blank = root / f"{mode}-template.docx"
                        pending.value.save_as(blank)
                        with ZipFile(blank) as archive:
                            self.assertIn("word/styles.xml", archive.namelist())
                        for key in (
                            "experience_description",
                            "skills",
                            "certifications",
                            "awards",
                            "project_description",
                            "education_description",
                            "languages",
                            "training",
                            "activities",
                            "publications",
                            "patents",
                            "links",
                        ):
                            block = page.locator(f'[data-field="{key}"]')
                            block.locator(".entry-heading > .text-button").click()
                            expect(block.locator(".resume-entry")).to_have_count(1)
                        experience = page.locator(
                            '[data-field="experience_description"]'
                        )
                        experience.locator('[data-key="company"]').fill(
                            "Synthetic Company"
                        )
                        experience.locator('[data-key="start"]').fill("2024-02")
                        experience.locator('[data-key="current"]').check()
                        expect(experience.locator('[data-key="end"]')).to_be_disabled()
                        experience.locator('[data-key="description"]').fill(
                            "SQL report\nsecond line"
                        )
                        skills = page.locator('[data-field="skills"]')
                        skills.locator('[data-key="name"]').fill("Python")
                        skills.locator(".entry-heading > .text-button").first.click()
                        skills.locator('[data-key="name"]').nth(1).fill("SQL")
                        certificate = page.locator('[data-field="certifications"]')
                        certificate.locator('[data-key="name"]').fill(
                            "Synthetic Certificate"
                        )
                        certificate.locator('[data-key="number"]').fill("TEST-001")
                        certificate.locator('[data-key="acquired"]').fill("2024-02-29")
                        page.locator("#profile-form button[type=submit]").click()
                        expect(page.locator("#profile-status")).to_contain_text(
                            "미검수 3개"
                        )
                        expect(
                            page.locator(
                                '[data-field="experience_description"] [data-key="end"]'
                            )
                        ).to_be_disabled()
                        for key in (
                            "experience_description",
                            "skills",
                            "certifications",
                        ):
                            page.locator(
                                f'[data-field="{key}"] > .consent input'
                            ).check()
                        page.locator("#profile-form button[type=submit]").click()
                        expect(page.locator("#profile-status")).to_contain_text(
                            "미검수 0개"
                        )
                        original = page.evaluate("profile")
                        qa = ROOT / "result/ui_verification"
                        qa.mkdir(parents=True, exist_ok=True)
                        for width in (1440, 390):
                            page.set_viewport_size({"width": width, "height": 1000})
                            page.locator(
                                '[data-field="experience_description"]'
                            ).scroll_into_view_if_needed()
                            self.assertLessEqual(
                                page.evaluate("document.documentElement.scrollWidth"),
                                width,
                            )
                            page.screenshot(
                                path=str(qa / f"structured-{mode}-{width}.png")
                            )
                        page.set_viewport_size({"width": 1440, "height": 1000})
                        for extension in ("docx", "md", "json"):
                            page.locator("#profile-format").select_option(extension)
                            with page.expect_download() as pending:
                                page.locator("#profile-download").click()
                            path = root / f"profile.{extension}"
                            pending.value.save_as(path)
                            page.locator("#profile-file").set_input_files(str(path))
                            expect(page.locator("#notice")).to_contain_text(
                                "표준 이력서를 가져왔습니다"
                            )
                            loaded = page.evaluate("profile")
                            for key in (
                                "experience_description",
                                "skills",
                                "certifications",
                            ):
                                wanted = next(
                                    r for r in original["fields"] if r["id"] == key
                                )
                                actual = next(
                                    r for r in loaded["fields"] if r["id"] == key
                                )
                                self.assertEqual(actual["items"], wanted["items"])
                                self.assertEqual(actual["value"], wanted["value"])
                                self.assertFalse(actual["reviewed"])
                            page.locator("#profile-form button[type=submit]").click()
                            expect(page.locator("#profile-status")).to_contain_text(
                                "미검수 3개"
                            )
                            for key in (
                                "experience_description",
                                "skills",
                                "certifications",
                            ):
                                page.locator(
                                    f'[data-field="{key}"] > .consent input'
                                ).check()
                            page.locator("#profile-form button[type=submit]").click()
                            expect(page.locator("#profile-status")).to_contain_text(
                                "미검수 0개"
                            )
                            if mode == "public" and extension == "docx":
                                Path(qa / "standard-resume-template.docx").write_bytes(
                                    blank.read_bytes()
                                )
                                Path(qa / "structured-example.docx").write_bytes(
                                    path.read_bytes()
                                )
                        page.locator('.nav[data-view="resume"]').click()
                        page.locator('#resume-form [name="keywords"]').fill("SQL")
                        page.locator("#resume-form button[type=submit]").click()
                        expect(page.locator("#use-organized")).to_be_visible()
                        expect(page.locator("#report")).to_contain_text(
                            "Synthetic Company"
                        )
                        page.once("dialog", lambda dialog: dialog.accept())
                        page.locator("#use-organized").click()
                        expect(page.locator("#conversion-source")).to_have_value(
                            "organized"
                        )
                        self.assertEqual(
                            page.evaluate(
                                'organizedProfile.fields.find(r => r.id === "skills").items[0].name'
                            ),
                            "SQL",
                        )
                        self.assertEqual(
                            page.evaluate(
                                'profile.fields.find(r => r.id === "skills").items[0].name'
                            ),
                            "Python",
                        )
                        if mode == "public":
                            self.assertFalse(any("/api/extract" in r for r in requests))
                            self.assertEqual(
                                page.evaluate(
                                    "[localStorage.length, sessionStorage.length]"
                                ),
                                [0, 0],
                            )
                            self.assertEqual(context.cookies(), [])
                        self.assertEqual(errors, [])
                    finally:
                        context.close()
                        app.shutdown()
                        thread.join(timeout=3)
                        app.server_close()
            finally:
                browser.close()
