"""Loopback workspace with private sharing or isolated anonymous public demos."""

import argparse
import json
import os
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from job_agent.documents.profile import ResumeProfile
from job_agent.documents.sections import SECTIONS
from job_agent.ui.local_kit import local_kit
from job_agent.ui.page import remote_page
from job_agent.ui.service import WorkspaceService
from job_agent.ui.sharing import Sharing
from job_agent.ui.tutorials import TUTORIAL_IMAGES
from job_agent.ui.visitors import VisitorWorkspaces

STATIC = Path(__file__).parent / "static"
ASSETS = {
    "/": ("index.html", "text/html"),
    "/app.js": ("app.js", "text/javascript"),
    "/style.css": ("style.css", "text/css"),
    "/lucide.min.js": ("lucide.min.js", "text/javascript"),
    "/login.js": ("login.js", "text/javascript"),
    "/handoff.js": ("handoff.js", "text/javascript"),
    "/portals.js": ("portals.js", "text/javascript"),
    "/resume-forms.js": ("resume-forms.js", "text/javascript"),
    "/resume-files.js": ("resume-files.js", "text/javascript"),
    "/fflate.min.js": ("fflate.min.js", "text/javascript"),
    "/tutorials.js": ("tutorials.js", "text/javascript"),
}
ASSETS.update(
    {
        f"/tutorials/{name}": (f"tutorials/{name}", "image/jpeg")
        for name in TUTORIAL_IMAGES
    }
)


class LocalServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address,
        service=None,
        remote_providers=(),
        allow_remote_paid_api=False,
        allow_remote_web_search=False,
        public_demo=False,
        handoff_origin="",
    ):
        if handoff_origin:
            origin = urlsplit(handoff_origin)
            if (
                origin.scheme not in {"http", "https"}
                or not origin.netloc
                or not origin.hostname
                or origin.username
                or origin.password
                or origin.path not in {"", "/"}
                or origin.query
                or origin.fragment
                or (
                    origin.scheme == "http"
                    and origin.hostname not in {"localhost", "127.0.0.1"}
                )
            ):
                raise ValueError("An exact HTTPS handoff origin is required")
            origin.port  # Validate an optional numeric port before enabling the handoff.
            handoff_origin = f"{origin.scheme}://{origin.netloc}"
        if public_demo and handoff_origin:
            raise ValueError("Public server cannot receive local handoffs")
        allowed = {"none", "custom", "openai", "gemini"}
        if public_demo and (
            set(remote_providers) - {"none"}
            or allow_remote_paid_api
            or allow_remote_web_search
        ):
            raise ValueError(
                "Public demo cannot use operator model or search resources"
            )
        if any(item not in allowed for item in remote_providers):
            raise ValueError("Invalid remote provider")
        if {"openai", "gemini"}.intersection(
            remote_providers
        ) and not allow_remote_paid_api:
            raise ValueError("Paid remote providers require --allow-remote-paid-api")
        super().__init__(address, Handler)
        self.service = service or WorkspaceService()
        self.token = secrets.token_urlsafe(32)
        self.admin_token = secrets.token_urlsafe(32)
        self.sharing = Sharing(self.server_port)
        self.run_lock = threading.Lock()
        self.remote_providers = tuple(
            item
            for item in ["none", "custom", "openai", "gemini"]
            if item == "none" or item in remote_providers
        )
        self.allow_remote_web_search = allow_remote_web_search
        self.public_demo = public_demo
        self.handoff_origin = handoff_origin
        self.visitors = VisitorWorkspaces() if public_demo else None

    def server_close(self):
        try:
            self.sharing.stop()
            if self.visitors:
                self.visitors.close()
            service = getattr(self, "service", None)
            if service:
                service.close()
        finally:
            super().server_close()


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)
        self.body_read = False

    def log_message(self, format, *args):
        pass

    def _reply(self, status, body, content_type="application/json", cookie=None):
        # Windows can reset a socket closed with an unread small POST body.
        if self.command == "POST" and not self.body_read:
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if 0 < size <= 65536:
                    self.rfile.read(size)
            except (ValueError, OSError):
                pass
            self.body_read = True
        data = (
            json.dumps(body, ensure_ascii=False).encode()
            if content_type == "application/json"
            else body
        )
        self.send_response(status)
        self.send_header(
            "Content-Type",
            f"{content_type}; charset=utf-8"
            if content_type.startswith("text/") or content_type == "application/json"
            else content_type,
        )
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'",
        )
        try:
            self.end_headers()
            self.wfile.write(data)
        except ConnectionError:
            pass  # The browser may close or navigate while a response is in flight.

    def _trusted(self):
        port = self.server.server_port
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        public = urlsplit(self.server.sharing.status()["url"])
        self.local_owner = self.headers.get("Host") in hosts and not self.headers.get(
            "CF-Connecting-IP"
        )
        if not self.local_owner and self.headers.get("Host") != public.netloc:
            self._reply(403, {"error": "Local host required"})
            return False
        self.external_entry = False
        # Only an opted-in top-level local page can open for the handoff UI.
        # Its opener still cannot read local APIs or approve an incoming profile.
        if (
            self.local_owner
            and self.server.handoff_origin
            and self.command == "GET"
            and urlsplit(self.path).path == "/"
            and self.headers.get("Sec-Fetch-Mode") == "navigate"
            and self.headers.get("Sec-Fetch-Dest") == "document"
            and self.headers.get("Origin") in {None, self.server.handoff_origin}
        ):
            return True
        # External links may open the public login shell, never an API or action.
        self.external_entry = (
            not self.local_owner
            and self.command == "GET"
            and urlsplit(self.path).path == "/"
            and self.headers.get("Sec-Fetch-Mode") == "navigate"
            and self.headers.get("Sec-Fetch-Dest") == "document"
            and (
                self.headers.get("Sec-Fetch-Site") == "cross-site"
                or self.headers.get("Origin") not in {None, f"https://{public.netloc}"}
            )
        )
        if self.external_entry:
            return True
        origin = self.headers.get("Origin")
        expected = (
            {f"http://{host}" for host in hosts}
            if self.local_owner
            else {f"https://{public.netloc}"}
        )
        if origin and origin not in expected:
            self._reply(403, {"error": "Same origin required"})
            return False
        if self.headers.get("Sec-Fetch-Site") in {"cross-site"}:
            self._reply(403, {"error": "Same origin required"})
            return False
        return True

    def _authenticated(self):
        self.workspace = self.server.service
        if not self.local_owner and self.server.public_demo:
            self.workspace = self.server.visitors.get(self.headers.get("Cookie"))
            return self.workspace is not None
        return self.local_owner or self.server.sharing.authenticated(
            self.headers.get("Cookie")
        )

    def _admin(self):
        if (
            not self.local_owner
            or self.headers.get("X-Admin-Token") != self.server.admin_token
        ):
            self._reply(
                403,
                {"error": "PC의 로컬 UI에서만 연결·공유 설정을 변경할 수 있습니다."},
            )
            return False
        return True

    def do_GET(self):
        if not self._trusted():
            return
        if self.external_entry and not self.server.public_demo:
            self._reply(200, (STATIC / "login.html").read_bytes(), "text/html")
            return
        path = urlsplit(self.path).path
        cookie = None
        authenticated = self._authenticated()
        if (
            not authenticated
            and self.server.public_demo
            and not self.local_owner
            and path == "/"
        ):
            try:
                self.workspace, cookie = self.server.visitors.create()
                authenticated = True
            except ValueError as exc:
                self._reply(503, {"error": str(exc)})
                return
        if not authenticated and path not in {
            "/style.css",
            "/login.js",
            "/lucide.min.js",
        }:
            if path == "/":
                self._reply(200, (STATIC / "login.html").read_bytes(), "text/html")
            else:
                self._reply(
                    401,
                    {
                        "error": "체험 화면을 먼저 열어 주세요."
                        if self.server.public_demo
                        else "접근 코드 로그인이 필요합니다."
                    },
                )
            return
        if path in ASSETS:
            name, mime = ASSETS[path]
            body = (STATIC / name).read_bytes()
            if path == "/" and not self.local_owner:
                body = remote_page(
                    body.decode("utf-8"),
                    self.server.remote_providers,
                    self.server.allow_remote_web_search
                    and self.workspace.config()["web_search"],
                )
            self._reply(200, body, mime, cookie=cookie)
            return
        if path == "/api/config":
            config = self.workspace.config()
            allowed = (
                self.server.remote_providers
                if not self.local_owner
                else ["none", "openai", "gemini", "custom"]
            )
            if not self.local_owner:
                config["web_search"] = (
                    config["web_search"] and self.server.allow_remote_web_search
                )
                config["providers"] = {
                    key: value
                    for key, value in config["providers"].items()
                    if key in allowed
                }
                config["models"] = {
                    key: value
                    for key, value in config["models"].items()
                    if key in allowed
                }
            self._reply(
                200,
                {
                    **config,
                    "allowed_providers": allowed,
                    "token": self.server.token,
                    "local_owner": self.local_owner,
                    "public_demo": self.server.public_demo,
                    "handoff_origin": self.server.handoff_origin
                    if self.local_owner
                    else "",
                    "privacy_contact": os.getenv("RESUME_PRIVACY_CONTACT", ""),
                    "session_ttl_seconds": self.server.visitors.ttl
                    if self.server.visitors and not self.local_owner
                    else None,
                    **(
                        {"admin_token": self.server.admin_token}
                        if self.local_owner
                        else {}
                    ),
                },
            )
            return
        if self.headers.get("X-Session-Token") != self.server.token:
            self._reply(403, {"error": "Session token required"})
            return
        if path == "/api/model-connection" and not self._admin():
            return
        if path == "/api/local-kit":
            self._reply(200, local_kit(), "application/zip")
            return
        try:
            if path == "/api/runs":
                self._reply(200, self.workspace.runs())
            elif path == "/api/sharing":
                self._reply(
                    200,
                    {
                        **self.server.sharing.status(
                            self.local_owner and not self.server.public_demo
                        ),
                        "allowed_providers": self.server.remote_providers,
                    },
                )
            elif path == "/api/model-connection":
                self._reply(200, self.workspace.custom_model.settings())
            elif path == "/api/profile":
                self._reply(200, self.workspace.profile())
            elif path == "/api/profile/template":
                self._reply(200, ResumeProfile.template().to_dict())
            elif path == "/api/profile/schema":
                self._reply(200, SECTIONS)
            elif path.startswith("/api/runs/"):
                self._reply(200, self.workspace.read_run(path.rsplit("/", 1)[-1]))
            else:
                self._reply(404, {"error": "Not found"})
        except (FileNotFoundError, ValueError):
            self._reply(404, {"error": "Not found"})

    def do_POST(self):
        if not self._trusted():
            return
        path = urlsplit(self.path).path
        if path != "/api/login" and not self._authenticated():
            self._reply(
                401,
                {
                    "error": "체험 화면을 먼저 열어 주세요."
                    if self.server.public_demo
                    else "접근 코드 로그인이 필요합니다."
                },
            )
            return
        if (
            path != "/api/login"
            and self.headers.get("X-Session-Token") != self.server.token
        ):
            self._reply(403, {"error": "Session token required"})
            return
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            self._reply(415, {"error": "JSON required"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 9_000_000:
                raise ValueError("Request size invalid")
            raw = self.rfile.read(size)
            self.body_read = True
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("JSON object required")
        except (ValueError, TypeError):
            self._reply(400, {"error": "잘못된 요청 또는 크기 제한 초과"})
            return
        if path == "/api/login":
            if self.server.public_demo:
                self._reply(404, {"error": "Not found"})
                return
            if self.local_owner:
                self._reply(400, {"error": "외부 공유 주소에서 로그인하세요."})
                return
            try:
                session = self.server.sharing.login(payload.get("code"))
                self._reply(
                    200,
                    {"ok": True},
                    cookie=f"__Host-resume_session={session}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=28800",
                )
            except ValueError as exc:
                self._reply(401, {"error": str(exc)})
            return
        if (
            self.server.public_demo
            and not self.local_owner
            and path in {"/api/sync", "/api/extract"}
        ):
            self._reply(
                403,
                {
                    "error": "공개 체험에서는 문서 업로드와 실제 사이트 저장을 실행하지 않습니다."
                },
            )
            return
        if (
            path == "/api/run"
            and not self.local_owner
            and (
                payload.get("provider", "none") not in self.server.remote_providers
                or (
                    payload.get("source") == "web"
                    and not self.server.allow_remote_web_search
                )
            )
        ):
            self._reply(
                403,
                {
                    "error": "서버 운영자가 외부 사용을 허용하지 않은 모델 또는 검색 API입니다."
                },
            )
            return
        admin_paths = {
            "/api/model-connection",
            "/api/model-list",
            "/api/sharing/start",
            "/api/sharing/stop",
        }
        if path == "/api/session/clear" and (
            self.local_owner or not self.server.public_demo
        ):
            self._reply(403, {"error": "임시 작업 공간에서만 삭제할 수 있습니다."})
            return
        if path in admin_paths and not self._admin():
            return
        if (
            path
            not in {
                "/api/run",
                "/api/extract",
                "/api/profile",
                "/api/profile/import",
                "/api/sync",
                "/api/session/clear",
            }
            | admin_paths
        ):
            self._reply(404, {"error": "Not found"})
            return
        if not self.server.run_lock.acquire(blocking=False):
            self._reply(
                409, {"error": "다른 작업이 진행 중입니다. 완료 후 실행하세요."}
            )
            return
        try:
            method = {
                "/api/run": self.workspace.run,
                "/api/extract": self.workspace.extract,
                "/api/profile": self.workspace.save_profile,
                "/api/profile/import": self.workspace.import_profile,
                "/api/sync": self.workspace.sync,
                "/api/session/clear": self.workspace.clear_private_data,
                "/api/model-connection": self.workspace.custom_model.configure,
                "/api/model-list": lambda data: self.workspace.custom_model.models(),
                "/api/sharing/start": lambda data: self.server.sharing.start(
                    data.get("consent")
                ),
                "/api/sharing/stop": lambda data: self.server.sharing.stop(),
            }[path]
            result = method(payload)
            if self.server.public_demo and path.startswith("/api/sharing"):
                result.pop("access_code", None)
            self._reply(200, result)
        except ValueError as exc:
            message = (
                str(exc)
                if path.startswith("/api/profile")
                or path == "/api/sync"
                or path in admin_paths
                else "입력값·필수 파일·API 사용 동의를 확인하세요."
            )
            self._reply(400, {"error": message})
        except (KeyError, TypeError):
            self._reply(400, {"error": "입력값·필수 파일·API 사용 동의를 확인하세요."})
        except Exception:
            self._reply(
                502,
                {
                    "error": "브라우저 실행·로그인·편집 화면을 확인하세요. 입력 중이었다면 일부 변경이 있을 수 있으니 화면에서 확인하세요."
                    if path == "/api/sync"
                    else "처리 실패. 파일 형식·검색 API 설정·네트워크를 확인하세요."
                },
            )
        finally:
            self.server.run_lock.release()


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local resume workspace UI")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument(
        "--handoff-origin",
        default="",
        help="Exact public website origin allowed to offer a resume to this local UI; local approval required",
    )
    parser.add_argument(
        "--public-demo",
        action="store_true",
        help="Code-free isolated anonymous workspaces; no operator APIs or portal sessions",
    )
    parser.add_argument(
        "--remote-providers",
        nargs="+",
        choices=["none", "custom", "openai", "gemini"],
        default=["none"],
        help="Models allowed for remote visitors; default: none",
    )
    parser.add_argument(
        "--allow-remote-paid-api",
        action="store_true",
        help="Explicitly permit remote OpenAI/Gemini usage on operator keys",
    )
    parser.add_argument(
        "--allow-remote-web-search",
        action="store_true",
        help="Explicitly permit remote Tavily usage on operator key",
    )
    args = parser.parse_args(argv)
    if args.public_demo and (
        set(args.remote_providers) - {"none"}
        or args.allow_remote_paid_api
        or args.allow_remote_web_search
    ):
        parser.error("--public-demo cannot expose operator APIs")
    if {"openai", "gemini"}.intersection(
        args.remote_providers
    ) and not args.allow_remote_paid_api:
        parser.error("OpenAI/Gemini remote access requires --allow-remote-paid-api")
    if not 0 <= args.port <= 65535:
        parser.error("Invalid port")
    server = None
    ports = [0] if args.port == 0 else range(args.port, min(args.port + 10, 65536))
    for port in ports:
        try:
            server = LocalServer(
                ("127.0.0.1", port),
                remote_providers=args.remote_providers,
                allow_remote_paid_api=args.allow_remote_paid_api,
                allow_remote_web_search=args.allow_remote_web_search,
                public_demo=args.public_demo,
                handoff_origin=args.handoff_origin,
            )
            break
        except OSError:
            continue
        except ValueError as exc:
            parser.error(str(exc))
    if server is None:
        parser.error("No available port; choose --port")
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"Resume workspace: {url}", flush=True)
    print("Local only. Ctrl+C to stop. API calls require explicit consent.", flush=True)
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
