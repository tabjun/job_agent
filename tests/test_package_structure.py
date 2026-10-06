import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch
from zipfile import ZipFile

from job_agent.cli import COMMANDS, main
from job_agent.core.paths import ProjectPaths
from job_agent.core.storage import ArtifactStore
from job_agent.documents.context import UserContextLoader
from job_agent.documents.library import ResumeLibrary
from job_agent.browser.session import BrowserSession


def create_docx(path):
    with ZipFile(path, "w") as archive:
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body><w:p><w:r><w:t>Source fact</w:t></w:r></w:p></w:body></w:document>",
        )


class PackageTests(unittest.TestCase):
    def test_paths_are_not_relative_to_cwd(self):
        expected = Path(__file__).resolve().parents[1]
        with (
            tempfile.TemporaryDirectory() as folder,
            patch("os.getcwd", return_value=folder),
        ):
            paths = ProjectPaths()
            self.assertEqual(paths.root, expected)
            self.assertEqual(
                paths.resolve("result/example.json"), expected / "result/example.json"
            )
            self.assertEqual(
                paths.browser_profile("wanted"),
                expected / "result/browser_profiles/wanted",
            )

    def test_storage_rejects_escape_and_creates_parents(self):
        with tempfile.TemporaryDirectory() as folder:
            store = ArtifactStore(Path(folder) / "output")
            path = store.write_json("nested/data.json", {"value": "fact"})
            self.assertEqual(json.loads(path.read_text()), {"value": "fact"})
            for name in ["../outside.json", ".", str(Path(folder) / "outside.json")]:
                with self.assertRaises(ValueError):
                    store.write_text(name, "no")

    def test_context_loader_uses_injected_paths_and_converter(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = ProjectPaths(Path(folder))
            paths.knowledge.mkdir()
            paths.guidelines.mkdir()
            (paths.knowledge / "resume.txt").write_text("Text fact", encoding="utf-8")
            create_docx(paths.knowledge / "resume.docx")
            pdf = paths.knowledge / "resume.pdf"
            pdf.write_bytes(b"fixture")
            (paths.guidelines / "style.txt").write_text("Style guide", encoding="utf-8")
            converter = Mock(return_value="Converted fact")
            content = UserContextLoader(paths, converter).load()
            for value in ["Text fact", "Source fact", "Converted fact", "Style guide"]:
                self.assertIn(value, content)
            converter.assert_called_once_with(pdf)

    def test_library_does_not_expose_owned_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "resume.docx"
            create_docx(source)
            corpus = ResumeLibrary.from_sources([source]).to_dict()
            library = ResumeLibrary(corpus)
            corpus["sources"].clear()
            exported = library.to_dict()
            exported["sources"].clear()
            self.assertEqual(len(library.to_dict()["sources"]), 1)

    def test_all_command_help_is_safe_without_model_credentials(self):
        with (
            contextlib.redirect_stdout(io.StringIO()),
            patch(
                "job_agent.cli.importlib.import_module", wraps=importlib.import_module
            ) as loader,
        ):
            main(["--help"])
            loader.assert_not_called()
            for command in COMMANDS:
                with self.assertRaises(SystemExit) as exit_context:
                    main([command, "--help"])
                self.assertEqual(exit_context.exception.code, 0)
            loaded = [call.args[0] for call in loader.call_args_list]
            self.assertFalse(
                any(module.startswith("job_agent.agents.") for module in loaded)
            )

    def test_cli_library_round_trip_from_unrelated_cwd(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "resume.docx"
            create_docx(source)
            draft = root / "draft.json"
            draft.write_text(
                json.dumps(
                    {
                        "blocks": [
                            {
                                "field": "summary",
                                "text": "Reviewed fact",
                                "evidence": [
                                    {"source_id": "source_1", "paragraph_indices": [0]}
                                ],
                            }
                        ]
                    }
                )
            )
            env = dict(os.environ, PYTHONPATH=str(ProjectPaths().root))

            def run(*args):
                result = subprocess.run(
                    [sys.executable, "-m", "job_agent", *args],
                    cwd=root,
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                return result

            run(
                "library",
                "extract",
                "--source",
                str(source),
                "--output-dir",
                str(root / "library"),
            )
            run(
                "library",
                "build",
                "--corpus",
                str(root / "library/corpus.json"),
                "--draft",
                str(draft),
                "--output-dir",
                str(root / "output"),
            )
            files = list((root / "output").glob("*_package.json"))
            self.assertEqual(len(files), 5)
            package = json.loads(files[0].read_text())
            self.assertEqual(
                package["package"]["field_values"]["summary"], "Reviewed fact"
            )
            self.assertFalse((root / "result").exists())


class SessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_session_closes_on_error_and_reuses_profile_path(self):
        context = Mock(close=AsyncMock())
        playwright = Mock()
        playwright.chromium.launch_persistent_context = AsyncMock(return_value=context)
        with tempfile.TemporaryDirectory() as folder:
            paths = ProjectPaths(Path(folder))
            session = BrowserSession(
                playwright,
                "wanted",
                headed=False,
                browser_path="browser.exe",
                paths=paths,
            )
            with self.assertRaisesRegex(RuntimeError, "fixture"):
                async with session as opened:
                    self.assertIs(opened, context)
                    raise RuntimeError("fixture")
            context.close.assert_awaited_once()
            playwright.chromium.launch_persistent_context.assert_awaited_once_with(
                str(paths.browser_profile("wanted")),
                headless=True,
                locale="ko-KR",
                viewport={"width": 1440, "height": 1100},
                executable_path="browser.exe",
            )


if __name__ == "__main__":
    unittest.main()
