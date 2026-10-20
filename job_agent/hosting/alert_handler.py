"""Isolated public subscription routes; resume API stays stateless/manual-only."""

import hmac
import json
from http.server import BaseHTTPRequestHandler

import httpx

from job_agent.alerts.cloud import CloudBackend, CloudConfig, ServerWorker


def dispatch(backend, payload, token="", ip=""):
    if not isinstance(payload, dict):
        raise TypeError("요청 형식을 확인하세요.")
    action = payload.get("action")
    allowed = {
        "request_code": {"action", "email", "auth_consent"},
        "verify": {"action", "email", "code"},
        "status": {"action"},
        "save": {
            "action",
            "id",
            "name",
            "platforms",
            "schedule",
            "max_results",
            "enabled",
            "search_consent",
            "storage_consent",
        },
        "delete": {"action", "id"},
        "unsubscribe": {"action", "token"},
        "delete_account": {"action"},
    }
    if action not in allowed or set(payload) - allowed[action]:
        raise ValueError("지원하지 않는 구독 요청입니다.")
    if action == "request_code":
        if payload.get("auth_consent") is not True:
            raise ValueError("이메일 인증 정보 전송에 동의해주세요.")
        return backend.code(payload.get("email"), ip)
    if action == "verify":
        return backend.verify(payload.get("email"), payload.get("code"))
    if action == "status":
        return backend.status(token)
    if action == "save":
        return backend.save(token, payload)
    if action == "delete":
        return backend.delete(token, payload.get("id"))
    if action == "delete_account":
        return backend.delete_account(token)
    return backend.unsubscribe(payload.get("token"))


class SubscriptionHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, status, payload):
        data = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        try:
            ready = CloudConfig.environment().ready()
        except (ValueError, TypeError):
            ready = False
        self.respond(
            200,
            {
                "ready": ready,
                "mode": "server_subscription",
                "message": "서비스 서버가 예약 발송합니다."
                if ready
                else "서버 메일 연결 준비 중입니다. 현재는 등록할 수 없습니다.",
            },
        )

    def do_POST(self):
        backend = None
        try:
            config = CloudConfig.environment()
            if not config.ready():
                self.respond(503, {"error": "서버 구독 연결 준비 중입니다."})
                return
            if self.headers.get("Origin") != config.origin:
                self.respond(403, {"error": "허용되지 않은 요청 출처입니다."})
                return
            size = int(self.headers.get("Content-Length", "0"))
            if (
                not 0 < size <= 32000
                or self.headers.get_content_type() != "application/json"
            ):
                self.respond(400, {"error": "구독 요청은 32KB 이하 JSON이어야 합니다."})
                return
            payload = json.loads(self.rfile.read(size))
            authorization = self.headers.get("Authorization", "")
            token = (
                authorization.removeprefix("Bearer ")
                if authorization.startswith("Bearer ")
                else ""
            )
            ip = self.headers.get("x-vercel-forwarded-for") or self.client_address[0]
            backend = CloudBackend(config)
            result = dispatch(backend, payload, token, ip)
            self.respond(200, result)
        except PermissionError:
            self.respond(
                401, {"error": "이메일 인증 또는 유효한 수신 해지 링크가 필요합니다."}
            )
        except (ValueError, TypeError, KeyError):
            self.respond(400, {"error": "구독 조건·인증 코드를 확인하세요."})
        except httpx.HTTPStatusError as exc:
            status = 401 if exc.response.status_code in {401, 403} else 503
            self.respond(
                status,
                {
                    "error": "인증이 만료됐거나 서버 연결에 실패했습니다. 다시 인증해주세요."
                },
            )
        except Exception:  # noqa: BLE001 - never include provider response/body/credentials in public errors
            self.respond(
                503,
                {"error": "서버 연결을 확인하는 중입니다. 잠시 후 다시 시도하세요."},
            )
        finally:
            if backend:
                backend.close()


class WorkerHandler(SubscriptionHandler):
    def do_GET(self):
        backend = None
        try:
            config = CloudConfig.environment()
            if not config.ready():
                self.respond(503, {"error": "worker_unconfigured"})
                return
            if not hmac.compare_digest(
                self.headers.get("Authorization", ""), "Bearer " + config.secret
            ):
                self.respond(401, {"error": "unauthorized"})
                return
            backend = CloudBackend(config)
            self.respond(200, ServerWorker(backend).run_one())
        except Exception:  # noqa: BLE001 - scheduler receives redacted state only
            self.respond(503, {"error": "worker_unavailable"})
        finally:
            if backend:
                backend.close()

    def do_POST(self):
        self.respond(405, {"error": "GET required"})
