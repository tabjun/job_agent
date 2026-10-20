"""Server subscription module: Supabase Auth/RLS, durable outbox, server sender.

Separate credentials and explicit enablement; never reads .env or local alert
files. Resume/profile data is not accepted by this interface. It is run for the
owner only: ``ALERT_ALLOWED_EMAILS`` lists the addresses that may sign in, and
each secret has a single purpose so one leak does not unlock the others.
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


def allowed_emails(value):
    """'a@x.kr, b@y.kr' -> normalized set; invalid entries are dropped."""
    found = set()
    for item in str(value or "").split(","):
        try:
            found.add(normalize_email(item))
        except ValueError:
            continue
    return frozenset(found)


@dataclass(frozen=True)
class CloudConfig:
    database_url: str
    anon_key: str
    service_key: str
    worker_secret: str
    unsubscribe_secret: str
    rate_pepper: str
    search_key: str
    origin: str
    sender: str
    allowed: frozenset = frozenset()
    unsubscribe_previous: str = ""
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
            database_url=os.getenv("ALERT_SUPABASE_URL", "").rstrip("/"),
            anon_key=os.getenv("ALERT_SUPABASE_ANON_KEY", ""),
            service_key=os.getenv("ALERT_SUPABASE_SERVICE_KEY", ""),
            worker_secret=os.getenv("ALERT_WORKER_SECRET", ""),
            unsubscribe_secret=os.getenv("ALERT_UNSUBSCRIBE_SECRET", ""),
            rate_pepper=os.getenv("ALERT_RATE_PEPPER", ""),
            search_key=os.getenv("ALERT_SERVER_SEARCH_KEY", ""),
            origin=os.getenv("ALERT_PUBLIC_ORIGIN", "").rstrip("/"),
            sender=os.getenv("ALERT_SERVER_FROM", ""),
            allowed=allowed_emails(os.getenv("ALERT_ALLOWED_EMAILS", "")),
            unsubscribe_previous=os.getenv("ALERT_UNSUBSCRIBE_SECRET_PREVIOUS", ""),
            resend_key=os.getenv("ALERT_RESEND_KEY", ""),
            smtp_host=os.getenv("ALERT_SERVER_SMTP_HOST", ""),
            smtp_user=os.getenv("ALERT_SERVER_SMTP_USER", ""),
            smtp_password=os.getenv("ALERT_SERVER_SMTP_PASSWORD", ""),
            smtp_port=int(os.getenv("ALERT_SERVER_SMTP_PORT", "587")),
            enabled=os.getenv("ALERT_SERVICE_ENABLED") == "true"
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
        secrets = [self.worker_secret, self.unsubscribe_secret, self.rate_pepper]
        return bool(
            self.enabled
            and https
            and self.anon_key
            and self.service_key
            # One purpose per secret: worker call, unsubscribe link, rate keys.
            and all(len(value) >= 32 for value in secrets)
            and len(set(secrets)) == len(secrets)
            and self.allowed
            and self.search_key
            and self.sender
            and mail
        )


CONSENT_VERSION = "job-alerts/v2"


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

    def digest(self, value):
        return hmac.new(
            self.config.rate_pepper.encode(), value.encode(), hashlib.sha256
        ).hexdigest()

    def reserve(self, keys):
        if not self.rpc("alert_reserve_code", {"p_keys": keys}):
            raise ValueError("인증 요청이 많습니다. 잠시 후 다시 시도하세요.")

    def allowed(self, email):
        return normalize_email(email) in self.config.allowed

    def health(self):
        """The database's own view of migration, scheduler and Vault setup."""
        result = self.rpc("alert_health")
        return result if isinstance(result, dict) else {"ready": False}

    def code(self, email, ip):
        email = normalize_email(email)
        if not self.allowed(email):
            # Same answer as success: the page must not reveal the allowlist.
            return {"requested": True}
        self.reserve(
            [
                "global",
                "minute:" + self.digest(email),
                "recipient:" + self.digest(email),
                "ip:" + self.digest(str(ip)),
            ]
        )
        # Users are created by the owner in the Supabase dashboard; signups
        # stay off, so a leaked publishable key cannot add accounts here.
        self.request(
            "POST", "/auth/v1/otp", data={"email": email, "create_user": False}
        )
        return {"requested": True}

    def verify(self, email, code, ip=""):
        email = normalize_email(email)
        if not isinstance(code, str) or not re.fullmatch(r"\d{6,8}", code):
            raise ValueError("메일의 인증 코드를 입력하세요.")
        if not self.allowed(email):
            raise PermissionError("이메일 인증이 필요합니다.")
        # Supabase limits /verify per caller IP, and every visitor shares this
        # server's IP: count attempts per address and per visitor here.
        self.reserve(
            [
                "verifyglobal",
                "verify:" + self.digest(email),
                "verifyip:" + self.digest(str(ip)),
            ]
        )
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
        if not user.get("email_confirmed_at") or not self.allowed(
            user.get("email")
        ):
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
        if self.health().get("ready") is not True:
            raise ConnectionError("scheduler_not_ready")
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
                "p_consent_version": CONSENT_VERSION,
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

    def unsubscribe_token(self, subscription_id, secret=None):
        identity = valid_id(subscription_id)
        signature = hmac.new(
            (secret or self.config.unsubscribe_secret).encode(),
            ("unsubscribe:v1:" + identity).encode(),
            hashlib.sha256,
        ).hexdigest()
        return "v1." + identity + "." + signature

    def unsubscribe(self, token):
        version, _, rest = str(token).partition(".")
        identity, _, _ = rest.partition(".")
        try:
            identity = valid_id(identity)
        except ValueError as exc:
            raise PermissionError("수신 해지 링크가 올바르지 않습니다.") from exc
        # A rotated key keeps already-mailed links valid until it is removed.
        keys = [k for k in (self.config.unsubscribe_secret, self.config.unsubscribe_previous) if k]
        if version != "v1" or not any(
            hmac.compare_digest(self.unsubscribe_token(identity, key), str(token))
            for key in keys
        ):
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
        return native[:100] + rows[:20]

    def run_one(self):
        claim = self.backend.rpc("alert_claim")
        if not claim:
            return {"processed": 0}
        delivery, subscription = claim["delivery"], claim["subscription"]
        identity = valid_id(delivery["id"])
        payload = delivery.get("payload")
        # A delivery claimed while 'sending' may already have reached the
        # provider: resend the stored payload under the same idempotency key.
        resume = delivery.get("state") == "sending" and bool(payload)
        handed_over = False
        try:
            if not payload:
                # Use only validated conditions, even if a row was written by
                # a direct RPC call rather than this API.
                platforms, schedule, limit = JobAlerts._conditions(subscription)
                stats = {}
                jobs, errors = JobAlerts(
                    searcher=self.searcher, verifier=self.verifier, clock=self.clock
                ).collect(
                    {
                        **subscription,
                        "platforms": platforms,
                        "schedule": schedule,
                        "max_results": limit,
                        "sent_urls": claim.get("sent_urls", []),
                    },
                    stats,
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
            # under the same provider idempotency key. A resumed send is not
            # rechecked: cancelling it could hide a mail that was delivered.
            if not resume and any(
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
            if not resume and not self.backend.rpc(
                "alert_can_send", {"p_id": identity}
            ):
                return {"processed": 1, "state": "cancelled"}
            handed_over = True
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
            # Before the hand-over nothing left the server, so retry. After it,
            # SMTP cannot tell whether the mail went out; Resend dedupes by key.
            state = (
                "retry" if self.config.resend_key or not handed_over else "unknown"
            )
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
