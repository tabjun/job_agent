import json
import os
import subprocess
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen
from zipfile import ZipFile

from job_agent.ui.launcher import DEFAULT_ORIGIN, connector_origin, ensure_browser, main
from job_agent.ui.local_kit import local_kit


class ConnectorLauncherTests(unittest.TestCase):
    def test_extracted_launcher_starts_real_private_server(self):
        import sys

        with tempfile.TemporaryDirectory(prefix="connector-launch-") as folder:
            with ZipFile(BytesIO(local_kit())) as kit:
                kit.extractall(folder)
            env = {**os.environ, "PYTHONUTF8": "1"}
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "job_agent.ui.launcher",
                    "--port",
                    "0",
                    "--no-open",
                ],
                cwd=folder,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
            )
            try:
                address = ""
                for _ in range(6):
                    line = process.stdout.readline()
                    if line.startswith("Resume workspace: "):
                        address = line.strip().split(" ")[-1]
                        break
                self.assertTrue(address.startswith("http://127.0.0.1:"), address)
                with urlopen(address + "/api/config", timeout=5) as response:
                    config = json.load(response)
                self.assertTrue(config["local_owner"])
                self.assertEqual(config["handoff_origin"], DEFAULT_ORIGIN)
                self.assertFalse(config.get("public_demo", False))
            finally:
                process.terminate()
                process.communicate(timeout=10)

    def test_exact_origin_configuration(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "connector.json"
            self.assertEqual(connector_origin(root), DEFAULT_ORIGIN)
            for value in ["https://example.test", "http://127.0.0.1:8780"]:
                path.write_text(json.dumps({"origin": value}))
                self.assertEqual(connector_origin(root), value)
            for value in [
                "*",
                "http://evil.test",
                "https://user:secret@example.test",
                "https://example.test/path",
                "https://example.test:bad",
                "https://example.test?secret=abc",
                None,
            ]:
                path.write_text(json.dumps({"origin": value}))
                with self.assertRaises(ValueError):
                    connector_origin(root)

    def test_existing_browser_skips_install_and_launcher_passes_private_options(self):
        with (
            patch(
                "job_agent.ui.launcher.find_local_browser", return_value="chrome.exe"
            ),
            patch("job_agent.ui.launcher.subprocess.run") as run,
        ):
            ensure_browser()
            run.assert_not_called()
        with (
            patch(
                "job_agent.ui.launcher.connector_origin", return_value=DEFAULT_ORIGIN
            ),
            patch("job_agent.ui.launcher.ensure_browser"),
            patch("job_agent.ui.server.main") as server,
        ):
            self.assertEqual(main(["--port", "8790", "--no-open"]), 0)
            server.assert_called_once_with(
                ["--port", "8790", "--handoff-origin", DEFAULT_ORIGIN, "--no-open"]
            )

    def test_invalid_config_never_installs_or_starts(self):
        with (
            patch("job_agent.ui.launcher.connector_origin", side_effect=ValueError),
            patch("job_agent.ui.launcher.ensure_browser") as browser,
            patch("job_agent.ui.server.main") as server,
        ):
            self.assertEqual(main([]), 1)
            browser.assert_not_called()
            server.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Windows CMD launcher")
    def test_double_click_script_quoted_folder_and_failure_stop(self):
        with tempfile.TemporaryDirectory(prefix="연결 도구 ") as folder:
            root = Path(folder)
            with ZipFile(BytesIO(local_kit())) as kit:
                kit.extractall(root)
            fake = root / "user/.local/bin"
            fake.mkdir(parents=True)
            calls = root / "calls.txt"
            stub = fake / "uv.cmd"
            env = {
                **os.environ,
                "USERPROFILE": str(root / "user"),
                "TEST_CALLS": str(calls),
            }
            script = root / "Start-Resume-Connector.cmd"
            for sync_failure in [False, True]:
                calls.unlink(missing_ok=True)
                stub.write_text(
                    '@echo off\necho %*>>"%TEST_CALLS%"\n'
                    + ("exit /b 1\n" if sync_failure else "exit /b 0\n"),
                    encoding="ascii",
                )
                result = subprocess.run(
                    ["cmd.exe", "/d", "/c", str(script)],
                    cwd=root,
                    env=env,
                    input="\n",
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=20,
                )
                self.assertEqual(
                    result.returncode, 1 if sync_failure else 0, result.stdout
                )
                lines = calls.read_text().splitlines()
                self.assertEqual(lines[0], "sync --locked --extra browser")
                self.assertEqual(len(lines), 1 if sync_failure else 2)
                if not sync_failure:
                    self.assertEqual(
                        lines[1], "run --no-sync python -m job_agent.ui.launcher"
                    )
