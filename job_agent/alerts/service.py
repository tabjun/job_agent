"""Verify an address by code, keep per-platform conditions, mail new postings.

Everything lives in ignored ``result/job_alerts/`` on the owner's PC. Searches
use the owner's Tavily key and mail goes through the owner's SMTP account, so
the feature is never offered to shared or public visitors.
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import smtplib
import ssl
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from email.message import EmailMessage
from urllib.parse import urlsplit
from uuid import uuid4

from job_agent.alerts.mail import compose, posting_fields
from job_agent.core.paths import ProjectPaths
from job_agent.ui.service import SITES, WorkspaceService, safe_url, terms

NAMES = {
    "catch": "캐치",
    "jobkorea": "잡코리아",
    "saramin": "사람인",
    "wanted": "원티드",
    "incruit": "인크루트",
}
FREQUENCIES = {"daily": "매일", "weekdays": "평일", "weekly": "매주"}
WEEKDAYS = "월화수목금토일"
CODE_TTL = 600
CODE_ATTEMPTS = 5
RESEND_SECONDS = 60
CODES_PER_HOUR = 5
MAX_ALERTS = 20
SENT_MEMORY = 1000
EMAIL = re.compile(r"^[^@\s]{1,64}@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$")


def normalize_email(value):
    email = str(value or "").strip().lower()
    if len(email) > 254 or not EMAIL.match(email):
        raise ValueError("올바른 이메일 주소를 입력하세요.")
    return email


def _text(data, key, limit):
    value = data.get(key, "")
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError(f"{key} 값이 너무 길거나 올바르지 않습니다.")
    return value.strip()


# Cities people write instead of the province; a region name also covers these.
REGION_ALIASES = {
    "서울": "강남 서초 송파 강동 강서 마포 영등포 여의도 용산 성동 성수 광진 구로 가산 금천 "
    "관악 동작 종로 중구 을지로 서대문 은평 노원 도봉 강북 성북 동대문 중랑 양천 상암",
    "경기": "성남 판교 분당 수원 용인 수지 기흥 화성 동탄 안양 평촌 과천 의왕 군포 광명 "
    "부천 고양 일산 파주 김포 하남 구리 남양주 의정부 양주 안산 시흥 평택 오산 이천",
}
OTHER_REGIONS = re.compile(
    r"(인천|부산|대구|대전|울산|세종|강원|충북|충남|충청|전북|전남|전라|경북|경남|경상|제주)"
    r"(?=광역시|특별자치|도\b|시\b|\s|$|[,·/()\[\]])|광주광역시"
)


# Search/listing pages that Tavily returns alongside individual postings.
LISTING = re.compile(
    r"검색결과|직무별 채용|직업별 채용|채용정보 \| 총|기업정보|관련 📢 채용공고"
)


def allowed_regions(location):
    """'서울, 경기' -> every name that counts as inside those regions."""
    names = set()
    for term in terms(location):
        names.add(term)
        names.update(REGION_ALIASES.get(term, "").split())
    return names


def region_check(body, allowed):
    """(keep, label): keep postings in or without a stated region, drop others."""
    inside = sorted((name for name in allowed if name in body), key=body.index)
    if inside:
        return True, inside[0]
    other = OTHER_REGIONS.search(body)
    if other:
        return False, other.group(0)
    return True, ""


def matches(term, body):
    """English/number terms match whole words (R, AI, ML); Korean matches inside words."""
    if re.fullmatch(r"[a-z0-9+#.]+", term):
        return (
            re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", body) is not None
        )
    return term in body


def _hash(salt, code):
    return hashlib.sha256(f"{salt}:{code}".encode()).hexdigest()


class Mailer:
    """Send plain text with an optional HTML alternative through owner SMTP."""

    @staticmethod
    def settings():
        host = os.getenv("ALERT_SMTP_HOST", "").strip()
        port = int(os.getenv("ALERT_SMTP_PORT", "587") or 587)
        user = os.getenv("ALERT_SMTP_USER", "").strip()
        sender = os.getenv("ALERT_SMTP_FROM", "").strip() or user
        security = (
            os.getenv("ALERT_SMTP_SECURITY", "ssl" if port == 465 else "starttls")
            .strip()
            .lower()
        )
        if security not in {"ssl", "starttls"}:
            raise ValueError("ALERT_SMTP_SECURITY는 ssl 또는 starttls여야 합니다.")
        return host, port, user, sender, security

    def configured(self):
        host, _, _, sender, _ = self.settings()
        return bool(host and sender)

    def send(self, to, subject, text, html=None):
        host, port, user, sender, security = self.settings()
        if not (host and sender):
            raise ValueError(
                "메일 발송 설정이 없습니다. .env에 ALERT_SMTP_HOST·ALERT_SMTP_USER·ALERT_SMTP_PASSWORD를 설정하세요."
            )
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = to
        message.set_content(text)
        if html is not None:
            message.add_alternative(html, subtype="html")
        context = ssl.create_default_context()
        if security == "ssl":
            client = smtplib.SMTP_SSL(host, port, context=context, timeout=20)
        else:
            client = smtplib.SMTP(host, port, timeout=20)
        with client:
            if security == "starttls":
                client.starttls(context=context)
            if user:
                client.login(user, os.getenv("ALERT_SMTP_PASSWORD", ""))
            client.send_message(message)


def _slots(schedule, now, step):
    """Scheduled moments walking from ``now``'s day in ``step`` days."""
    day = now.replace(hour=schedule["hour"], minute=0, second=0, microsecond=0)
    for _ in range(9):
        weekday = day.weekday()
        if (
            schedule["frequency"] == "daily"
            or (schedule["frequency"] == "weekdays" and weekday < 5)
            or (
                schedule["frequency"] == "weekly"
                and weekday == schedule.get("weekday", 0)
            )
        ):
            yield day
        day += timedelta(days=step)


def latest_slot(schedule, now):
    """Most recent scheduled moment at or before ``now``."""
    return next(s for s in _slots(schedule, now, -1) if s <= now)


def next_slot(schedule, now):
    """First scheduled moment after ``now``."""
    return next(s for s in _slots(schedule, now, 1) if s > now)


@contextmanager
def file_lock(path, timeout, stale, busy):
    """Exclusive marker file shared by UI threads and scheduled CLI processes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    while True:
        try:
            handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                if time.time() - path.stat().st_mtime > stale:
                    path.unlink()
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise ValueError(busy) from None
            time.sleep(0.05)
    try:
        yield
    finally:
        os.close(handle)
        path.unlink(missing_ok=True)


class JobAlerts:
    def __init__(self, paths=None, searcher=None, mailer=None, clock=None):
        self.paths = paths or ProjectPaths()
        self.folder = self.paths.results / "job_alerts"
        self.file = self.folder / "alerts.json"
        self.searcher = searcher or WorkspaceService._web_search
        self.mailer = mailer or Mailer()
        self.clock = clock or datetime.now

    # storage -------------------------------------------------------------
    def _load(self):
        try:
            data = json.loads(self.file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            data = {}
        data.setdefault("version", 1)
        for key in ["emails", "pending"]:
            data.setdefault(key, {})
        data.setdefault("alerts", [])
        return data

    def _save(self, data):
        self.folder.mkdir(parents=True, exist_ok=True)
        temp = self.folder / f"alerts.{os.getpid()}.{secrets.token_hex(4)}.tmp"
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        temp.replace(self.file)

    def _state(self):
        """Serialize each read-modify-write (and the send it guards) across processes."""
        return file_lock(
            self.folder / ".state.lock",
            timeout=60,
            stale=180,
            busy="공고 알림 저장소가 사용 중입니다. 잠시 후 다시 시도하세요.",
        )

    def _process_lock(self):
        """Keep the UI scheduler and a scheduled CLI run from searching twice."""
        return file_lock(
            self.folder / ".run.lock",
            timeout=0,
            stale=900,
            busy="다른 공고 알림 실행이 진행 중입니다.",
        )

    # public view ---------------------------------------------------------
    def status(self):
        with self._state():
            data = self._load()
        now = self.clock()
        alerts = []
        for alert in data["alerts"]:
            view = {
                k: v for k, v in alert.items() if k not in {"sent_urls", "sent_titles"}
            }
            view["sent_count"] = len(alert.get("sent_urls", []))
            view["next_run"] = next_slot(alert["schedule"], now).isoformat(
                timespec="minutes"
            )
            alerts.append(view)
        return {
            "mail_configured": self.mailer.configured(),
            "web_search": bool(os.getenv("TAVILY_API_KEY")),
            "emails": sorted(data["emails"]),
            "alerts": alerts,
            "platforms": [{"key": k, "name": NAMES[k]} for k in SITES],
        }

    # email verification -------------------------------------------------
    def request_code(self, payload):
        email = normalize_email(payload.get("email"))
        if not self.mailer.configured():
            raise ValueError(
                "메일 발송 설정이 없습니다. .env에 ALERT_SMTP_HOST·ALERT_SMTP_USER·ALERT_SMTP_PASSWORD를 설정하고 다시 실행하세요."
            )
        now = time.time()
        with self._state():
            data = self._load()
            pending = data["pending"].get(email, {})
            sent = [t for t in pending.get("sent", []) if now - t < 3600]
            if sent and now - sent[-1] < RESEND_SECONDS:
                raise ValueError("인증 코드는 1분 후에 다시 요청할 수 있습니다.")
            if len(sent) >= CODES_PER_HOUR:
                raise ValueError("인증 코드 요청이 많습니다. 1시간 후 다시 시도하세요.")
            code = f"{secrets.randbelow(10**6):06d}"
            salt = secrets.token_hex(16)
            self.mailer.send(
                email,
                "[이력서 작업 공간] 공고 알림 이메일 인증 코드",
                f"인증 코드: {code}\n\n"
                "10분 안에 공고 알림 화면에 입력하세요.\n"
                "직접 요청하지 않았다면 이 메일을 무시하세요. 인증하지 않으면 알림이 등록되지 않습니다.\n",
            )
            data["pending"][email] = {
                "salt": salt,
                "hash": _hash(salt, code),
                "expires": now + CODE_TTL,
                "attempts": 0,
                "sent": [*sent, now],
            }
            self._save(data)
        return {"sent": True, "email": email, "expires_in": CODE_TTL}

    def verify(self, payload):
        email = normalize_email(payload.get("email"))
        code = str(payload.get("code", "")).strip()
        with self._state():
            data = self._load()
            pending = data["pending"].get(email)
            if not pending or "hash" not in pending or pending["expires"] < time.time():
                raise ValueError(
                    "인증 코드가 없거나 만료되었습니다. 코드를 다시 요청하세요."
                )
            pending["attempts"] += 1
            if not hmac.compare_digest(pending["hash"], _hash(pending["salt"], code)):
                if pending["attempts"] >= CODE_ATTEMPTS:
                    for key in ["hash", "salt", "expires"]:
                        pending.pop(key, None)
                    self._save(data)
                    raise ValueError("시도 횟수를 넘었습니다. 코드를 다시 요청하세요.")
                self._save(data)
                raise ValueError("인증 코드가 일치하지 않습니다.")
            data["emails"][email] = {
                "verified_at": self.clock().isoformat(timespec="seconds")
            }
            del data["pending"][email]
            self._save(data)
        return {"verified": True, "email": email}

    def forget_email(self, payload):
        email = normalize_email(payload.get("email"))
        with self._state():
            data = self._load()
            data["emails"].pop(email, None)
            data["pending"].pop(email, None)
            data["alerts"] = [a for a in data["alerts"] if a["email"] != email]
            self._save(data)
        return {"removed": email}

    # conditions ----------------------------------------------------------
    def _conditions(self, payload):
        platforms = payload.get("platforms")
        if not isinstance(platforms, dict) or not platforms:
            raise ValueError("알림을 받을 플랫폼을 하나 이상 선택하세요.")
        cleaned = {}
        for site, rule in platforms.items():
            if site not in SITES or not isinstance(rule, dict):
                raise ValueError("지원하지 않는 플랫폼입니다.")
            entry = {
                "role": _text(rule, "role", 100),
                "location": _text(rule, "location", 100),
                "keywords": _text(rule, "keywords", 300),
                "exclude": _text(rule, "exclude", 300),
            }
            if not entry["role"] and not entry["keywords"]:
                raise ValueError(f"{NAMES[site]}: 직무 또는 키워드를 입력하세요.")
            cleaned[site] = entry
        schedule = payload.get("schedule") or {}
        frequency = schedule.get("frequency")
        hour = schedule.get("hour")
        weekday = schedule.get("weekday", 0)
        if (
            frequency not in FREQUENCIES
            or not isinstance(hour, int)
            or not 0 <= hour <= 23
            or not isinstance(weekday, int)
            or not 0 <= weekday <= 6
        ):
            raise ValueError("발송 주기와 시간을 확인하세요.")
        limit = payload.get("max_results", 10)
        if not isinstance(limit, int) or not 1 <= limit <= 30:
            raise ValueError("메일당 공고 수는 1~30개입니다.")
        return (
            cleaned,
            {"frequency": frequency, "hour": hour, "weekday": weekday},
            limit,
        )

    def save(self, payload):
        email = normalize_email(payload.get("email"))
        if payload.get("search_consent") is not True:
            raise ValueError("조건 검색어를 웹 검색 API로 보내는 데 동의해야 합니다.")
        if not os.getenv("TAVILY_API_KEY"):
            raise ValueError("공고 검색에 TAVILY_API_KEY가 필요합니다.")
        platforms, schedule, limit = self._conditions(payload)
        name = _text(payload, "name", 60) or "공고 알림"
        enabled = payload.get("enabled", True) is True
        now = self.clock().isoformat(timespec="seconds")
        with self._state():
            data = self._load()
            if email not in data["emails"]:
                raise ValueError("먼저 이메일 인증을 완료하세요.")
            alert = next(
                (a for a in data["alerts"] if a["id"] == payload.get("id")), None
            )
            if alert is None:
                if len(data["alerts"]) >= MAX_ALERTS:
                    raise ValueError(
                        f"알림은 최대 {MAX_ALERTS}개까지 등록할 수 있습니다."
                    )
                alert = {"id": uuid4().hex, "created_at": now, "sent_urls": []}
                data["alerts"].append(alert)
            alert.update(
                name=name,
                email=email,
                enabled=enabled,
                platforms=platforms,
                schedule=schedule,
                max_results=limit,
                updated_at=now,
                revision=alert.get("revision", 0) + 1,
            )
            self._save(data)
        return self.status()

    def delete(self, payload):
        with self._state():
            data = self._load()
            data["alerts"] = [a for a in data["alerts"] if a["id"] != payload.get("id")]
            self._save(data)
        return self.status()

    # running -------------------------------------------------------------
    def collect(self, alert):
        """Search each platform with its own conditions; drop already-mailed URLs."""
        seen = set(alert.get("sent_urls", []))
        jobs, errors = {}, []
        year = self.clock().year
        for site, rule in alert["platforms"].items():
            query = " ".join(
                x for x in [rule["role"], rule["location"], rule["keywords"]] if x
            )
            try:
                rows = self.searcher(f"{query} 채용 {year}", [SITES[site]])
            except Exception as exc:  # noqa: BLE001 - one platform failing must not stop others
                errors.append(f"{NAMES[site]} 검색 실패: {type(exc).__name__}")
                continue
            wanted, excluded = terms(rule["keywords"]), terms(rule["exclude"])
            regions = allowed_regions(rule["location"])
            for row in rows if isinstance(rows, list) else []:
                if not isinstance(row, dict):
                    continue
                url = safe_url(row.get("url", ""))
                host = (urlsplit(url).hostname or "") if url else ""
                if not url or not (
                    host == SITES[site] or host.endswith("." + SITES[site])
                ):
                    continue
                title = str(row.get("title", "")).strip()[:300]
                content = str(row.get("content", row.get("description", "")))[:2000]
                body = f"{title} {content}".casefold()
                # A title is not a posting identity: employers and requisitions
                # can share it. Deduplicate by URL to avoid hiding valid jobs.
                if LISTING.search(title):
                    continue
                if (
                    url in seen
                    or url in jobs
                    or any(matches(t, body) for t in excluded)
                ):
                    continue
                hits = [t for t in wanted if matches(t, body)]
                if wanted and not hits:
                    continue
                keep, region = region_check(body, regions) if regions else (True, "")
                if not keep:
                    continue
                jobs[url] = {
                    "site": site,
                    "title": title or url,
                    "url": url,
                    "excerpt": " ".join(content.split())[:240],
                    "matched_keywords": hits,
                    "region": region if regions else None,
                    **posting_fields({**row, "title": title, "content": content}),
                }
        ranked = sorted(
            jobs.values(), key=lambda j: len(j["matched_keywords"]), reverse=True
        )
        return ranked[: alert.get("max_results", 10)], errors

    @staticmethod
    def compose(alert, jobs):
        subject, plain, _ = compose(alert, jobs, NAMES)
        return subject, plain

    def _run(self, alert_id, send=True):
        with self._state():
            alert = next(
                (a for a in self._load()["alerts"] if a["id"] == alert_id), None
            )
        if alert is None:
            raise ValueError("알림을 찾을 수 없습니다.")
        jobs, errors = self.collect(alert)
        if not send:
            status = f"새 공고 {len(jobs)}건 (미리보기 · 미발송)"
            if errors:
                status += " · " + "; ".join(errors)
            return {"id": alert_id, "status": status, "mailed": False, "jobs": jobs}
        with self._state():
            # The search ran unlocked: honour deletes, revoked addresses and edits.
            data = self._load()
            stored = next((a for a in data["alerts"] if a["id"] == alert_id), None)
            if stored is None or stored["email"] not in data["emails"]:
                return {
                    "id": alert_id,
                    "status": "알림 또는 이메일 인증이 삭제되어 발송하지 않았습니다.",
                    "mailed": False,
                    "jobs": [],
                }
            mailed = False
            sent = set(stored.get("sent_urls", []))
            jobs = [j for j in jobs if j["url"] not in sent]
            if stored.get("revision") != alert.get("revision"):
                status = "검색 중 설정이 바뀌어 이번 발송을 건너뜀"
            elif errors and len(errors) == len(alert["platforms"]):
                status = "검색 실패 · " + "; ".join(errors)
            elif not jobs:
                status = "새 공고 없음 · 메일 미발송"
            else:
                try:
                    self.mailer.send(stored["email"], *compose(stored, jobs, NAMES))
                    mailed = True
                    status = f"새 공고 {len(jobs)}건 발송"
                except Exception as exc:  # noqa: BLE001 - keep URLs unsent and record why
                    status = f"메일 발송 실패: {type(exc).__name__}"
            if errors and not status.startswith("검색 실패"):
                status += " · " + "; ".join(errors)
            stored["last_run_at"] = self.clock().isoformat(timespec="seconds")
            stored["last_status"] = status
            if mailed:
                stored["sent_urls"] = (
                    stored.get("sent_urls", []) + [j["url"] for j in jobs]
                )[-SENT_MEMORY:]
            self._save(data)
        return {"id": alert_id, "status": status, "mailed": mailed, "jobs": jobs}

    def run_now(self, payload):
        with self._process_lock():
            return self._run(payload.get("id"), send=payload.get("send", True) is True)

    def due(self, now=None):
        now = now or self.clock()
        with self._state():
            alerts = self._load()["alerts"]
        result = []
        for alert in alerts:
            if not alert.get("enabled"):
                continue
            reference = datetime.fromisoformat(
                alert.get("last_run_at") or alert["created_at"]
            )
            if latest_slot(alert["schedule"], now) > reference:
                result.append(alert["id"])
        return result

    def run_due(self):
        if not os.getenv("TAVILY_API_KEY") or not self.mailer.configured():
            return []
        try:
            lock = self._process_lock()
            lock.__enter__()
        except ValueError:
            return []  # Another process is already running alerts.
        try:
            results = []
            for alert_id in self.due():
                try:
                    results.append(self._run(alert_id))
                except ValueError:
                    continue  # Deleted or busy meanwhile; the rest still run.
            return results
        finally:
            lock.__exit__(None, None, None)


class AlertScheduler:
    """Check due alerts once a minute while the local UI is running."""

    def __init__(self, alerts, interval=60):
        self.alerts, self.interval = alerts, interval
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        while not self.stop.wait(self.interval):
            try:
                self.alerts.run_due()
            except Exception:  # noqa: BLE001, S110 - status is recorded per alert
                pass  # Keep the loop alive for the next minute.

    def close(self):
        self.stop.set()
        self.thread.join(timeout=5)
