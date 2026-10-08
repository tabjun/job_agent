import unittest
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from job_agent.ui.local_kit import local_kit
from job_agent.ui.server import ASSETS, STATIC
from job_agent.ui.tutorials import TUTORIAL_IMAGES


class TutorialAssetsTests(unittest.TestCase):
    def test_only_reviewed_jpeg_routes_exist(self):
        expected = {f"/tutorials/{name}" for name in TUTORIAL_IMAGES}
        self.assertEqual(
            {path for path in ASSETS if path.startswith("/tutorials/")}, expected
        )
        for name in TUTORIAL_IMAGES:
            route = f"/tutorials/{name}"
            self.assertEqual(ASSETS[route], (f"tutorials/{name}", "image/jpeg"))
            body = (STATIC / "tutorials" / name).read_bytes()
            self.assertTrue(body.startswith(b"\xff\xd8\xff"))
            self.assertGreater(len(body), 10_000)
        self.assertNotIn("/tutorials/../../.env", ASSETS)

    def test_connector_includes_documentation_not_capture_fixture(self):
        with ZipFile(BytesIO(local_kit())) as kit:
            prefix = "job_agent/ui/static/tutorials/"
            self.assertEqual(
                {name for name in kit.namelist() if name.startswith(prefix)},
                {prefix + name for name in TUTORIAL_IMAGES},
            )
            self.assertFalse(
                any("capture_tutorial_fixture" in name for name in kit.namelist())
            )
            for name in TUTORIAL_IMAGES:
                self.assertEqual(
                    kit.read(prefix + name), (STATIC / "tutorials" / name).read_bytes()
                )

    def test_gallery_references_exact_reviewed_image_set(self):
        import re

        script = (STATIC / "tutorials.js").read_text(encoding="utf-8")
        self.assertEqual(
            set(re.findall(r'["/]([a-z-]+\.jpg)', script)), set(TUTORIAL_IMAGES)
        )
        self.assertNotIn("knowledge/", script)
        self.assertTrue(
            (Path(__file__).parent / "capture_tutorial_fixture.py").is_file()
        )
