"""Server subscription module: Supabase Auth/RLS, durable outbox, server sender.

Separate credentials and explicit enablement; never reads .env or local alert
files. Resume/profile data is not accepted by this interface.
"""

import hashlib
import hmac
import os
import re
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from html import escape
from urllib.parse import urlsplit
from uuid import UUID

import httpx

from job_agent.alerts.mail import compose
from job_agent.alerts.service import NAMES, JobAlerts, normalize_email
from job_agent.core.job_status import KST, confirmation_current
from job_agent.core.native_jobs import native_search


@dataclass(frozen=True)
class CloudConfig:
    database_url: str
    anon_key: str
    service_key: str
    secret: str
    search_key: str
    origin: str
    sender: str
    resend_key: str = ""
    smtp_host: str = ""
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_port: int = 587
    enabled: bool = False

    @classmethod
    def environment(cls):
        # No fallback to any of the owner's local SMTP/Tavily variables.
        return cls(
            os.getenv("ALERT_SUPABASE_URL", "").rstrip("/"),
            os.getenv("ALERT_SUPABASE_ANON_KEY", ""),
            os.getenv("ALERT_SUPABASE_SERVICE_KEY", ""),
            os.getenv("ALERT_SERVER_SECRET", ""),
            os.getenv("ALERT_SERVER_SEARCH_KEY", ""),
            os.getenv("ALERT_PUBLIC_ORIGIN", "").rstrip("/"),
            os.getenv("ALERT_SERVER_FROM", ""),
            os.getenv("ALERT_RESEND_KEY", ""),
            os.getenv("ALERT_SERVER_SMTP_HOST", ""),
            os.getenv("ALERT_SERVER_SMTP_USER", ""),
            os.getenv("ALERT_SERVER_SMTP_PASSWORD", ""),
            int(os.getenv("ALERT_SERVER_SMTP_PORT", "587")),
            os.getenv("ALERT_SERVICE_ENABLED") == "true"
            and os.getenv("ALERT_SCHEDULER_READY") == "true",
        )

    def ready(self):
        https = all(
            urlsplit(v).scheme == "https"
            and urlsplit(v).hostname
            and not urlsplit(v).username
            and not urlsplit(v).query
            and not urlsplit(v).fragment
            for v in (self.database_url, self.origin)
        )
        mail = bool(
            self.resend_key
            or self.smtp_host
            and self.smtp_user
            and self.smtp_password
            and self.smtp_port in {465, 587}
        )
        return bool(
            self.enabled
            and https
            and self.anon_key
            and self.service_key
            and len(self.secret) >= 32
            and self.search_key
            and self.sender
            and mail
        )


def valid_id(value):
    try:
        return str(UUID(str(value)))
    except ValueError as exc:
        raise ValueError("알림 ID를 확인하세요.") from exc


class CloudBackend:
    def __init__(self, config, client=None):
        self.config = config
        self.client = client or httpx.Client(
            timeout=20, follow_redirects=False, trust_env=False
        )

    def close(self):
        self.client.close()

    def request(self, method, path, *, token=None, admin=False, data=None, params=None):
        key = self.config.service_key if admin else self.config.anon_key
        response = self.client.request(
            method,
            self.config.database_url + path,
            headers={"apikey": key, "Authorization": "Bearer " + (token or key)},
            json=data,
            params=params,
        )
        response.raise_for_status()
        return response.json() if response.content else None

    def rpc(self, name, data=None, token=None):
        return self.request(
            "POST",
            "/rest/v1/rpc/" + name,
            data=data or {},
            token=token,
            admin=token is None,
        )

    def code(self, email, ip):
        email = normalize_email(email)
        digest = lambda value: hmac.new(
            self.config.secret.encode(), value.encode(), hashlib.sha256
        ).hexdigest()
        keys = [
            "global",
            "minute:" + digest(email),
            "recipient:" + digest(email),
            "ip:" + digest(str(ip)),
        ]
        if not self.rpc("alert_reserve_code", {"p_keys": keys}):
            raise ValueError("인증 요청이 많습니다. 잠시 후 다시 시도하세요.")
        self.request("POST", "/auth/v1/otp", data={"email": email, "create_user": True})
        return {"requested": True}

    def verify(self, email, code):
        email = normalize_email(email)
        if not isinstance(code, str) or not re.fullmatch(r"\d{6,8}", code):
            raise ValueError("메일의 인증 코드를 입력하세요.")
        result = self.request(
            "POST",
            "/auth/v1/verify",
            data={"email": email, "token": code, "type": "email"},
        )
        token = result.get("access_token", "")
        user = self.user(token)
        return {
            "access_token": token,
            "email": user["email"],
            "expires_in": result.get("expires_in", 3600),
        }

    def user(self, token):
        if not isinstance(token, str) or not 20 <= len(token) <= 8000:
            raise PermissionError("이메일 인증이 필요합니다.")
        user = self.request("GET", "/auth/v1/user", token=token)
        if not user.get("email_confirmed_at"):
            raise PermissionError("이메일 인증이 필요합니다.")
        return {
            "id": valid_id(user.get("id")),
            "email": normalize_email(user.get("email")),
        }

    def status(self, token):
        user = self.user(token)
        rows = self.request(
            "GET",
            "/rest/v1/alert_subscriptions",
            token=token,
            params={
                "select": "id,name,email,platforms,schedule,max_results,enabled,last_status,last_collection",
                "owner_id": "eq." + user["id"],
                "order": "created_at.asc",
            },
        )
        return {"email": user["email"], "alerts": rows}

    def save(self, token, payload):
        self.user(token)
        if (
            payload.get("search_consent") is not True
            or payload.get("storage_consent") is not True
        ):
            raise ValueError("검색어 전송과 구독 정보 저장에 동의해야 합니다.")
        platforms, schedule, limit = JobAlerts._conditions(payload)
        name = payload.get("name", "맞춤 공고")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:
            raise ValueError("알림 이름은 1~60자로 입력하세요.")
        result = self.rpc(
            "alert_save",
            {
                "p_id": valid_id(payload["id"]) if payload.get("id") else None,
                "p_name": name.strip(),
                "p_platforms": platforms,
                "p_schedule": schedule,
                "p_limit": limit,
                "p_enabled": payload.get("enabled", True) is True,
            },
            token,
        )
        return {"saved": result, "status": "저장 완료 · 서버에서 예약 발송합니다."}

    def delete(self, token, subscription_id):
        self.user(token)
        self.rpc("alert_delete", {"p_id": valid_id(subscription_id)}, token)
        return {"removed": True}

    def delete_account(self, token):
        user = self.user(token)
        self.request("DELETE", "/auth/v1/admin/users/" + user["id"], admin=True)
        return {"deleted": True}

    def unsubscribe_token(self, subscription_id):
        identity = valid_id(subscription_id)
        signature = hmac.new(
            self.config.secret.encode(),
            ("unsubscribe:" + identity).encode(),
            hashlib.sha256,
        ).hexdigest()
        return identity + "." + signature

    def unsubscribe(self, token):
        identity, _, _ = str(token).partition(".")
        if not hmac.compare_digest(self.unsubscribe_token(identity), str(token)):
            raise PermissionError("수신 해지 링크가 올바르지 않습니다.")
        self.rpc("alert_unsubscribe", {"p_id": identity})
        return {"unsubscribed": True}


class ServerMailer:
    def __init__(self, config, client=None):
        self.config = config
        self.client = client or httpx.Client(
            timeout=20, follow_redirects=False, trust_env=False
        )

    def send(self, payload, identity):
        if self.config.resend_key:
            result = self.client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": "Bearer " + self.config.resend_key,
                    "Idempotency-Key": "job-alert/" + identity,
                },
                json={
                    "from": self.config.sender,
                    "to": [payload["email"]],
                    "subject": payload["subject"],
                    "text": payload["text"],
                    "html": payload["html"],
                },
            )
            result.raise_for_status()
            return str(result.json()["id"])
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = (
            self.config.sender,
            payload["email"],
            payload["subject"],
        )
        message.set_content(payload["text"])
        message.add_alternative(payload["html"], subtype="html")
        context = ssl.create_default_context()
        if self.config.smtp_port == 465:
            connection = smtplib.SMTP_SSL(
                self.config.smtp_host, 465, context=context, timeout=20
            )
        elif self.config.smtp_port == 587:
            connection = smtplib.SMTP(self.config.smtp_host, 587, timeout=20)
        else:
            raise ValueError("서버 SMTP는 465 또는 587 포트를 사용하세요.")
        with connection:
            if self.config.smtp_port == 587:
                connection.starttls(context=context)
            connection.login(self.config.smtp_user, self.config.smtp_password)
            connection.send_message(message)
        return "smtp-accepted"


class ServerWorker:
    def __init__(self, backend, mailer=None, searcher=None, verifier=None, clock=None):
        self.backend = backend
        self.config = backend.config
        self.mailer = mailer or ServerMailer(self.config, backend.client)
        self.searcher = searcher or self.search
        self.verifier = verifier
        self.clock = clock or (lambda: datetime.now(KST))

    def search(self, query, domains):
        native = []
        try:
            if len(domains) == 1:
                native = native_search(query, domains[0])
        except Exception:  # noqa: BLE001 - preserve index fallback without exposing provider details
            native = []
        try:
            response = self.backend.client.post(
                "https://api.tavily.com/search",
                headers={"Authorization": "Bearer " + self.config.search_key},
                json={
                    "query": query,
                    "include_domains": domains,
                    "max_results": 20,
                    "search_depth": "basic",
                    "include_answer": False,
                    "include_raw_content": "markdown",
                },
            )
            response.raise_for_status()
            rows = [
                {**r, "retrieval_source": "search_index"}
                for r in response.json().get("results", [])
            ]
        except httpx.HTTPError:
            if native:
                return native[:80]
            raise
        return native[:60] + rows[:20]

    def run_one(self):
        claim = self.backend.rpc("alert_claim")
        if not claim:
            return {"processed": 0}
        delivery, subscription = claim["delivery"], claim["subscription"]
        identity = valid_id(delivery["id"])
        payload = delivery.get("payload")
        try:
            if not payload:
                JobAlerts._conditions(subscription)  # validate DB/direct-RPC input too
                stats = {}
                jobs, errors = JobAlerts(
                    searcher=self.searcher, verifier=self.verifier, clock=self.clock
                ).collect(
                    {**subscription, "sent_urls": claim.get("sent_urls", [])}, stats
                )
                if not jobs:
                    if not errors:
                        self.backend.rpc(
                            "alert_prepare",
                            {
                                "p_id": identity,
                                "p_payload": {
                                    "collection": stats,
                                    "urls": [],
                                    "jobs": [],
                                },
                            },
                        )
                    self.backend.rpc(
                        "alert_finish",
                        {
                            "p_id": identity,
                            "p_state": "retry" if errors else "empty",
                            "p_provider_id": None,
                            "p_error": "search_unavailable" if errors else None,
                        },
                    )
                    return {"processed": 1, "state": "retry" if errors else "empty"}
                jobs = [
                    j
                    for j in jobs
                    if confirmation_current(j["status_check"], self.clock())
                ]
                if not jobs:
                    self.backend.rpc(
                        "alert_finish",
                        {
                            "p_id": identity,
                            "p_state": "empty",
                            "p_provider_id": None,
                            "p_error": None,
                        },
                    )
                    return {"processed": 1, "state": "empty"}
                subject, text, html = compose(
                    {**subscription, "collection": stats}, jobs, NAMES
                )
                link = (
                    self.config.origin
                    + "/job-alerts.html#unsubscribe="
                    + self.backend.unsubscribe_token(subscription["id"])
                )
                text += "\n\n수신 해지: " + link
                html = html.replace(
                    "</body>",
                    '<p><a href="'
                    + escape(link, quote=True)
                    + '">수신 해지</a></p></body>',
                )
                payload = {
                    "email": normalize_email(subscription["email"]),
                    "subject": subject,
                    "text": text,
                    "html": html,
                    "collection": stats,
                    "jobs": jobs,
                    "transport": "resend" if self.config.resend_key else "smtp",
                    "urls": [
                        url
                        for j in jobs
                        for url in [j["url"], *j.get("alternate_urls", [])]
                    ],
                }
                if not self.backend.rpc(
                    "alert_prepare", {"p_id": identity, "p_payload": payload}
                ):
                    return {"processed": 1, "state": "cancelled"}
            # Recheck the persisted payload on retries; never regenerate content
            # under the same provider idempotency key.
            if any(
                not confirmation_current(j.get("status_check", {}), self.clock())
                for j in payload.get("jobs", [])
            ):
                self.backend.rpc(
                    "alert_finish",
                    {
                        "p_id": identity,
                        "p_state": "cancelled",
                        "p_provider_id": None,
                        "p_error": "deadline_passed",
                    },
                )
                return {"processed": 1, "state": "cancelled"}
            if not self.backend.rpc("alert_can_send", {"p_id": identity}):
                return {"processed": 1, "state": "cancelled"}
            provider_id = self.mailer.send(payload, identity)
            self.backend.rpc(
                "alert_finish",
                {
                    "p_id": identity,
                    "p_state": "sent",
                    "p_provider_id": provider_id,
                    "p_error": None,
                },
            )
            return {"processed": 1, "state": "sent"}
        except Exception:  # noqa: BLE001 - store redacted outcome; never recipient/content/credentials
            state = "retry" if self.config.resend_key else "unknown"
            self.backend.rpc(
                "alert_finish",
                {
                    "p_id": identity,
                    "p_state": state,
                    "p_provider_id": None,
                    "p_error": "worker_unavailable",
                },
            )
            return {"processed": 1, "state": state}
