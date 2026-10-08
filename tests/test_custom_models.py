import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest

from job_agent.core.paths import ProjectPaths
from job_agent.ui.models import CustomModel
from job_agent.ui.service import WorkspaceService


class ModelHandler(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, *args):
        pass

    def do_GET(self):
        self.server.calls.append((self.path, self.headers.get("Authorization")))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps({"data": [{"id": "local/test:small"}]}).encode())

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.calls.append((self.path, self.headers.get("Authorization"), body))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(
            json.dumps(
                {
                    "choices": [{"message": {"content": "Fixture grounded draft"}}],
                    "usage": {"total_tokens": 15},
                }
            ).encode()
        )


class CustomModelsTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ModelHandler)
        self.server.calls = []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.folder = tempfile.TemporaryDirectory()
        self.service = WorkspaceService(ProjectPaths(Path(self.folder.name)))
        self.connection = {
            "base_url": f"http://127.0.0.1:{self.server.server_port}/v1",
            "model": "local/test:small",
            "api_key": "fixture-private-key",
            "connection_consent": True,
        }

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.service.close()
        self.folder.cleanup()

    def test_endpoint_models_and_real_http_analysis_with_no_paid_model(self):
        self.service.custom_model.configure(self.connection)
        self.assertEqual(
            self.service.custom_model.models()["models"], ["local/test:small"]
        )
        payload = {
            "task": "resume",
            "resume": "Source SQL experience",
            "provider": "custom",
            "model": "local/test:small",
            "ai_consent": True,
        }
        run = self.service.run(payload)
        self.assertEqual(run["ai"]["text"], "Fixture grounded draft")
        self.assertEqual(run["ai"]["usage"]["total_tokens"], 15)
        self.assertEqual(len(self.server.calls), 2)
        self.assertEqual(self.server.calls[1][0], "/v1/chat/completions")
        self.assertEqual(self.server.calls[1][1], "Bearer fixture-private-key")
        self.assertFalse(self.server.calls[1][2]["stream"])
        self.assertNotIn("fixture-private-key", json.dumps(run))
        self.assertNotIn("fixture-private-key", json.dumps(self.service.config()))
        self.assertNotIn("api_key", self.service.custom_model.settings())
        self.assertFalse(
            list(self.service.store.directory.parent.glob("**/*connection*"))
        )

    def test_no_connection_or_consent_never_calls(self):
        payload = {
            "task": "resume",
            "resume": "fact",
            "provider": "custom",
            "model": "local",
            "ai_consent": True,
        }
        with self.assertRaises(ValueError):
            self.service.run(payload)
        self.service.custom_model.configure(self.connection)
        with self.assertRaises(ValueError):
            self.service.run({**payload, "ai_consent": False})
        self.assertEqual(self.server.calls, [])

    def test_invalid_url_and_credentials_not_in_url(self):
        for url in [
            "file:///tmp/a",
            "http://user:secret@localhost/v1",
            "http://169.254.169.254/v1",
            "http://localhost:bad/v1",
            "http://host/v1?token=secret",
            "http://host/v1#secret",
        ]:
            with self.assertRaises(ValueError):
                CustomModel().configure({**self.connection, "base_url": url})
        with self.assertRaises(ValueError):
            CustomModel().configure({**self.connection, "connection_consent": False})

    def test_connection_failure_preserves_baseline_and_redacts(self):
        self.service.custom_model.configure(
            {**self.connection, "base_url": "http://127.0.0.1:1/v1"}
        )
        run = self.service.run(
            {
                "task": "resume",
                "resume": "fact",
                "provider": "custom",
                "model": "local",
                "ai_consent": True,
            }
        )
        self.assertEqual(run["result"]["report"], "fact")
        self.assertIn("error", run["ai"])
        self.assertNotIn("fixture-private-key", json.dumps(run))
