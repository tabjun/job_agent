"""Disposable loopback-only fixture for capturing the real review/save UI."""

import json
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from job_agent.browser.sync import ResumeSync, SyncWorker
from job_agent.core.paths import ProjectPaths
from job_agent.ui.server import LocalServer
from job_agent.ui.service import WorkspaceService


class Editor(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        body = """<!doctype html><meta charset="utf-8"><title>로컬 저장 테스트</title>
<h1>로컬 테스트 양식 · 실제 채용사이트 아님</h1>
<label for="summary">소개</label><textarea id="summary"></textarea>
<button onclick="fetch('/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({summary:document.querySelector('#summary').value})})">저장</button>
<script>document.querySelector('#summary').value=VALUE;</script>""".replace(
            "VALUE", json.dumps(self.server.value).replace("<", "\\u003c")
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/save":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", 0))
        if not 0 < length < 100_000:
            self.send_error(413)
            return
        self.server.value = json.loads(self.rfile.read(length))["summary"]
        self.send_response(200)
        self.end_headers()


class Registry:
    def __init__(self, url):
        self.url = url

    def normalize(self, site):
        return site

    def target(self, site):
        return {"candidate_urls": [self.url], "name": "로컬 테스트 양식"}

    def is_custom(self, site):
        return False

    def matches_url(self, site, url):
        return url == self.url


def main():
    with tempfile.TemporaryDirectory(prefix="resume-tutorial-") as folder:
        editor = ThreadingHTTPServer(("127.0.0.1", 0), Editor)
        editor.value = "[가상 예시] 기존 소개"
        paths = ProjectPaths(Path(folder))
        service = WorkspaceService(paths)
        url = f"http://127.0.0.1:{editor.server_port}/editor"
        service._sync_worker = SyncWorker(
            ResumeSync(
                paths,
                service.profile,
                registry=Registry(url),
                headed=False,
                editor_check=lambda site, current: current == url,
            )
        )
        app = LocalServer(
            ("127.0.0.1", 0),
            service,
            handoff_origin="https://job-agent-resume-web.vercel.app",
        )
        threads = [
            threading.Thread(target=server.serve_forever, daemon=True)
            for server in [editor, app]
        ]
        for thread in threads:
            thread.start()
        print(f"TUTORIAL_LOCAL=http://127.0.0.1:{app.server_port}", flush=True)
        print(
            "TEST FIXTURE ONLY. No real portal or user profile. Type stop to close.",
            flush=True,
        )
        try:
            input()
        finally:
            service.close()
            for server in [app, editor]:
                server.shutdown()
                server.server_close()
            for thread in threads:
                thread.join()


if __name__ == "__main__":
    main()
