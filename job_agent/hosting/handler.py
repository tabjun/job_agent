"""One stateless deterministic request; no accounts, secrets, or saved sessions."""

from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import urlsplit

from job_agent.ui.service import WorkspaceService


LIMIT = 2_000_000


def execute(payload):
    if (
        not isinstance(payload, dict)
        or payload.get("task") not in {"search", "resume", "prepare"}
        or payload.get("provider", "none") != "none"
        or payload.get("source", "manual") != "manual"
    ):
        raise ValueError("공개 웹에서 허용되지 않는 작업입니다.")
    workspace = WorkspaceService(ephemeral=True)
    try:
        return workspace.run(payload)
    finally:
        workspace.close()


class handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        # Provider access logs are separate; never emit request bodies or facts here.
        pass

    def respond(self, status, value):
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        if len(data) > LIMIT:
            status = 413
            data = b'{"error":"Result exceeds 2MB. Reduce the input."}'
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.respond(405, {"error": "POST required"})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= LIMIT:
                self.respond(413, {"error": "Request must be at most 2MB"})
                return
            # Drain bounded bodies before rejecting headers. Closing a socket with
            # unread data can reset it on Windows instead of delivering the error.
            self.connection.settimeout(10)
            body = self.rfile.read(length)
            if urlsplit(self.path).path != "/api/run":
                self.respond(404, {"error": "Not found"})
                return
            origin = urlsplit(self.headers.get("Origin", ""))
            host = self.headers.get("Host", "")
            if (
                origin.scheme not in {"http", "https"}
                or origin.netloc != host
                or origin.username
                or origin.password
                or origin.path
                or origin.query
                or origin.fragment
                or self.headers.get("Sec-Fetch-Site", "same-origin")
                not in {"same-origin", "none"}
            ):
                self.respond(403, {"error": "Same origin required"})
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self.respond(415, {"error": "JSON required"})
                return
            payload = json.loads(body)
            self.respond(200, execute(payload))
        except (ValueError, TypeError, KeyError):
            # Validation errors can contain input labels: do not echo private facts.
            self.respond(400, {"error": "입력 형식·검수·근거·대상 양식을 확인하세요."})
        except Exception:
            self.respond(
                500, {"error": "처리 실패. 입력을 줄이거나 로컬 도구에서 확인하세요."}
            )
