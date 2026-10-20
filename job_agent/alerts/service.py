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
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta
from email.message import EmailMessage
from urllib.parse import urlsplit
from uuid import uuid4

from job_agent.alerts.mail import compose, posting_fields
from job_agent.alerts.sheet import SheetExporter, sheet_rows
from job_agent.core.job_match import (
    DEFAULT_EXPERIENCE,
    merge_cross_platform,
    requirements,
    title_check,
    validate_experience,
)
from job_agent.core.job_status import confirmation_current, detail_url, verify_posting
from job_agent.core.paths import ProjectPaths
from job_agent.core.postings import (
    allowed_regions,
    canonical_url,
    diverse_jobs,
    matches,
    queries,
    region_check,
    rejection,
)
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
SENT_MEMORY = 5000
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


# Search/listing pages that Tavily returns alongside individual postings.
LISTING = re.compile(
    r"검색결과|직무별 채용|직업별 채용|채용정보 \| 총|기업정보|관련 📢 채용공고"
)


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
    # Detail pages fetched per run; None checks every candidate (local runs,
    # whose matches all go to the sheet). Time-limited callers pass a number.
    # Candidates are interleaved by platform, so a budget is shared equally.
    DETAIL_BUDGET = None

    def __init__(
        self,
        paths=None,
        searcher=None,
        mailer=None,
        clock=None,
        verifier=None,
        supported=None,
        sheet=None,
        detail_budget=None,
    ):
        self.paths = paths or ProjectPaths()
        self.folder = self.paths.results / "job_alerts"
        self.file = self.folder / "alerts.json"
        self.searcher = searcher or WorkspaceService._web_search
        self.mailer = mailer or Mailer()
        self.clock = clock or datetime.now
        self.verifier = verifier or verify_posting
        # The public detail checker only reads known posting routes; anything
        # else would come back unknown, so it never spends the detail budget.
        self.supported = supported or (
            detail_url if self.verifier is verify_posting else bool
        )
        self.sheet = sheet or SheetExporter()
        if detail_budget is not None:
            self.DETAIL_BUDGET = detail_budget

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
            stale=3600,  # every candidate is checked, which can take a while
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
    @staticmethod
    def _conditions(payload):
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
                "require_keywords": rule.get("require_keywords") is True,
                "experience": validate_experience(
                    rule.get("experience", DEFAULT_EXPERIENCE)
                ),
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
    def collect(self, alert, diagnostics=None, trace=None, stop_at_limit=False):
        """Search each platform with its own conditions; drop already-mailed URLs.

        ``trace`` (a list) receives one outcome per candidate URL so a run's
        omissions can be explained later; it is kept out of ``diagnostics``.
        Every confirmed match is returned unless ``stop_at_limit`` asks to stop
        once ``max_results`` are found (time-limited callers).
        """
        seen = {canonical_url(url) for url in alert.get("sent_urls", [])}
        jobs, errors = {}, []
        counts = Counter()
        outcomes = {}

        def note(site, url, title, outcome):
            outcomes.setdefault(
                url, {"site": site, "url": url, "title": title[:120], "outcome": outcome}
            )
        for site, rule in alert["platforms"].items():
            rows = []
            failed = []
            for query in queries(rule["role"], rule["location"], rule["keywords"]):
                try:
                    result = self.searcher(query, [SITES[site]])
                    if not isinstance(result, list):
                        raise TypeError("Invalid search results")
                    rows.extend(result[:120])
                except Exception as exc:  # noqa: BLE001 - preserve other queries and platforms
                    failed.append(type(exc).__name__)
            if failed:
                errors.append(
                    f"{NAMES[site]} 검색 일부/전체 실패: {', '.join(dict.fromkeys(failed))}"
                )
            counts["fetched"] += len(rows)
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
                reason = rejection(row, SITES[site], self.clock().date())
                if reason:
                    counts[reason] += 1
                    note(site, canonical_url(url), title, reason)
                    continue
                url = canonical_url(url)
                content = str(
                    row.get("raw_content")
                    or row.get("content")
                    or row.get("description", "")
                )[:10000]
                body = f"{title} {content}".casefold()
                # A title is not a posting identity: employers and requisitions
                # can share it. Deduplicate by URL to avoid hiding valid jobs.
                if LISTING.search(title):
                    counts["listing"] += 1
                    note(site, url, title, "listing")
                    continue
                if (
                    url in seen
                    or url in jobs
                    or any(matches(t, body) for t in excluded)
                ):
                    counts["sent_duplicate_or_excluded"] += 1
                    if url not in jobs:  # a repeated hit is the same candidate
                        note(
                            site,
                            url,
                            title,
                            "already_sent" if url in seen else "excluded_keyword",
                        )
                    continue
                hits = [t for t in wanted if matches(t, body)]
                if wanted and not hits:
                    counts["keyword_deferred"] += 1
                keep, region = region_check(body, regions) if regions else (True, "")
                if not keep:
                    counts["region"] += 1
                    note(site, url, title, "region")
                    continue
                jobs[url] = {
                    "site": site,
                    "title": title or url,
                    "url": url,
                    "excerpt": " ".join(content.split())[:240],
                    "matched_keywords": hits,
                    "region": region if regions else None,
                    "rule": {
                        **rule,
                        "experience": rule.get("experience", DEFAULT_EXPERIENCE),
                    },
                    "requirements_card": row.get("requirements_card", {})
                    if row.get("retrieval_source") == "native_search"
                    else {},
                    **posting_fields({**row, "title": title, "content": content}),
                }
        candidates = list(jobs.values())
        checkable = []
        for job in candidates:
            if self.supported(job["url"]):
                checkable.append(job)
            else:
                counts["unsupported_detail_url"] += 1
                note(job["site"], job["url"], job["title"], "unsupported_detail_url")
        # Titles that already fit the role are checked first; the rest only
        # use what is left of the budget (the detail title can still differ).
        ranked = sorted(
            checkable,
            key=lambda j: (
                title_check(j["title"], j["rule"].get("role") or "") == "",
                len(j["matched_keywords"]),
            ),
            reverse=True,
        )
        # Search snippets are candidates, not proof that applications are open.
        # Verify in small batches so closed/unknown rows do not consume mail slots.
        ordered = diverse_jobs(ranked, len(ranked))
        selected = []
        limit = alert.get("max_results", 10)
        budget = len(ordered) if self.DETAIL_BUDGET is None else self.DETAIL_BUDGET
        # A site that starts refusing requests is left alone for the rest of
        # the run rather than asked again (and blocked for longer).
        limited = set()

        def verify(job):
            try:
                result = self.verifier(job["url"], self.clock())
                return (
                    {**result, "checked_at": self.clock().isoformat(timespec="seconds")}
                    if isinstance(result, dict)
                    else {}
                )
            except Exception:  # noqa: BLE001 - an unreadable detail is withheld
                return {}

        with ThreadPoolExecutor(max_workers=4) as pool:
            for offset in range(0, min(len(ordered), budget), 8):
                batch = []
                for job in ordered[offset : min(offset + 8, budget)]:
                    if job["site"] in limited:
                        counts["rate_limited_skipped"] += 1
                        counts["detail_checked"] += 1  # decided: not fetched
                        note(job["site"], job["url"], job["title"], "rate_limited_skipped")
                    else:
                        batch.append(job)
                checks = list(pool.map(verify, batch))
                counts["detail_checked"] += len(batch)
                for job, check in zip(batch, checks):
                    if check.get("evidence") == "rate_limited":
                        limited.add(job["site"])
                    if check.get("status") == "closed":
                        counts["detail_closed"] += 1
                        note(job["site"], job["url"], job["title"], "detail_closed")
                    elif check.get("status") != "open":
                        counts["status_unverified"] += 1
                        note(
                            job["site"],
                            job["url"],
                            job["title"],
                            "status_unverified:" + str(check.get("evidence", "error")),
                        )
                    else:
                        card = job.get("requirements_card", {})
                        check = dict(check)
                        for field in ("job_title", "job_location"):
                            if not check.get(field) and card.get(field):
                                check[field] = card[field]
                                check["condition_source"] = "detail_and_native_card"
                        if (check.get("experience") or {}).get(
                            "kind", "unknown"
                        ) == "unknown" and card.get("experience"):
                            check["experience"] = card["experience"]
                            check["condition_source"] = "detail_and_native_card"
                        if (
                            not check.get("application_available")
                            and not check.get("application_blocked")
                            and card.get("application_available")
                        ):
                            check["application_available"] = True
                            check["application_evidence"] = (
                                "현재 공개 검색 카드의 지원 버튼 확인"
                            )
                            check["condition_source"] = "detail_and_native_card"
                        evidence = str(check.get("job_description") or "")
                        if evidence:
                            full_body = job["title"] + " " + evidence
                            wanted = terms(job["rule"]["keywords"])
                            hits = [t for t in wanted if matches(t, full_body)]
                            if (
                                job["rule"].get("require_keywords") is True
                                and wanted
                                and not hits
                            ):
                                counts["missing_keyword_evidence"] += 1
                                note(job["site"], job["url"], job["title"], "missing_keyword_evidence")
                                continue
                            if any(
                                matches(t, full_body)
                                for t in terms(job["rule"]["exclude"])
                            ):
                                counts["excluded_keyword"] += 1
                                note(job["site"], job["url"], job["title"], "excluded_keyword")
                                continue
                            job["matched_keywords"] = hits
                        elif (
                            terms(job["rule"]["keywords"])
                            and not job["matched_keywords"]
                            and job["rule"].get("require_keywords") is True
                        ):
                            counts["missing_keyword_evidence"] += 1
                            note(job["site"], job["url"], job["title"], "missing_keyword_evidence")
                            continue
                        match = requirements({**job, **check}, job["rule"])
                        if match["decision"] != "pass":
                            counts[match["reason"]] += 1
                            counts[
                                "requirements_held"
                                if match["decision"] == "hold"
                                else "requirements_rejected"
                            ] += 1
                            note(job["site"], job["url"], job["title"], match["reason"])
                            continue
                        confirmed = {
                            **job,
                            "status_check": {
                                k: v for k, v in check.items() if k != "job_description"
                            },
                        }
                        confirmed.pop("rule", None)
                        confirmed.pop("requirements_card", None)
                        confirmed["requirements_check"] = match
                        counts["requirements_confirmed"] += 1
                        if not match.get("application_confirmed"):
                            counts["application_unconfirmed"] += 1
                        if check.get("job_title"):
                            confirmed["role"] = check["job_title"]
                        if check.get("company"):
                            confirmed["company"] = check["company"]
                        if check.get("deadline"):
                            confirmed["period"] = "~ " + check["deadline"]
                        elif check.get("period"):
                            confirmed["period"] = check["period"]
                        selected.append(confirmed)
                before_merge = len(selected)
                selected = merge_cross_platform(selected)
                counts["cross_platform_duplicate"] += before_merge - len(selected)
                if stop_at_limit and len(selected) >= limit:
                    break
        counts["detail_not_checked"] = len(ordered) - counts["detail_checked"]
        for job in ordered[counts["detail_checked"] :]:
            note(job["site"], job["url"], job["title"], "detail_not_checked")
        for index, job in enumerate(selected):
            note(
                job["site"],
                job["url"],
                job["title"],
                "matched" if index < limit or not stop_at_limit else "over_limit",
            )
            for url in job.get("alternate_urls", []):
                note(job["site"], url, job["title"], "cross_platform_duplicate")
        if stop_at_limit:
            selected = selected[:limit]
        if trace is not None:
            trace.extend(outcomes.values())
        if diagnostics is not None:
            diagnostics.update(
                {
                    **counts,
                    "candidates": len(candidates),
                    "eligible": counts["requirements_confirmed"] - counts["cross_platform_duplicate"],
                    "selected": min(len(selected), limit),
                    "limit": alert.get("max_results", 10),
                    "complete": False,
                }
            )
        return selected, errors

    def _write_trace(self, alert_id, collection, trace):
        """Latest run's per-candidate outcomes, for explaining omissions."""
        if not re.fullmatch(r"[0-9a-f]{32}", str(alert_id)):
            return
        folder = self.folder / "runs"
        folder.mkdir(parents=True, exist_ok=True)
        temp = folder / f"{alert_id}.{secrets.token_hex(4)}.tmp"
        temp.write_text(
            json.dumps(
                {
                    "run_at": self.clock().isoformat(timespec="seconds"),
                    "collection": collection,
                    "candidates": trace,
                },
                ensure_ascii=False,
                indent=1,
            ),
            "utf-8",
        )
        temp.replace(folder / f"{alert_id}.json")

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
        collection, trace = {}, []
        jobs, errors = self.collect(alert, collection, trace)
        self._write_trace(alert_id, collection, trace)
        limit = alert.get("max_results", 10)
        if not send:
            status = f"조건 통과 {len(jobs)}건 중 메일 {min(len(jobs), limit)}건 (미리보기 · 미발송)"
            jobs = jobs[:limit]
            status += self._held_summary(collection)
            if errors:
                status += " · " + "; ".join(errors)
            return {
                "id": alert_id,
                "status": status,
                "mailed": False,
                "jobs": jobs,
                "collection": collection,
            }
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
            sent = {canonical_url(url) for url in stored.get("sent_urls", [])}
            jobs = [j for j in jobs if j["url"] not in sent]
            current = [
                j
                for j in jobs
                if confirmation_current(j.get("status_check", {}), self.clock())
            ]
            collection["closed_before_send"] = len(jobs) - len(current)
            # Every current match goes to the sheet; the mail keeps its cap and
            # the rest stay unsent, so later mails pick them up in order.
            matches = current
            jobs = matches[:limit]
            collection["matched"] = len(matches)
            collection["selected"] = len(jobs)
            if stored.get("revision") != alert.get("revision"):
                status = "검색 중 설정이 바뀌어 이번 발송을 건너뜀"
            elif not jobs and errors and len(errors) == len(alert["platforms"]):
                status = "검색 실패 · " + "; ".join(errors)
            elif not jobs:
                status = "새 공고 없음 · 메일 미발송"
            else:
                try:
                    self.mailer.send(
                        stored["email"],
                        *compose({**stored, "collection": collection}, jobs, NAMES),
                    )
                    mailed = True
                    status = f"새 공고 {len(jobs)}건 발송"
                except Exception as exc:  # noqa: BLE001 - keep URLs unsent and record why
                    status = f"메일 발송 실패: {type(exc).__name__}"
            status += self._held_summary(collection)
            if errors and not status.startswith("검색 실패"):
                status += " · " + "; ".join(errors)
            stored["last_run_at"] = self.clock().isoformat(timespec="seconds")
            stored["last_status"] = status
            stored["last_collection"] = collection
            if mailed:
                stored["sent_urls"] = (
                    stored.get("sent_urls", [])
                    + [
                        url
                        for j in jobs
                        for url in [j["url"], *j.get("alternate_urls", [])]
                    ]
                )[-SENT_MEMORY:]
            self._save(data)
        sheet_note = self._export_sheet(stored, matches, jobs if mailed else [])
        if sheet_note:
            status += sheet_note
            with self._state():
                data = self._load()
                for item in data["alerts"]:
                    if item["id"] == alert_id:
                        item["last_status"] = status
                self._save(data)
        return {
            "id": alert_id,
            "status": status,
            "mailed": mailed,
            "jobs": jobs,
            "collection": collection,
        }

    def _export_sheet(self, alert, matches, mailed_jobs):
        """Write every match to the owner's sheet; never blocks the mail."""
        if not matches or not self.sheet.configured():
            return ""
        mailed = {
            url for j in mailed_jobs for url in [j["url"], *j.get("alternate_urls", [])]
        }
        try:
            self.sheet.export(
                sheet_rows(
                    alert["name"], matches, mailed, self.clock().date().isoformat()
                )
            )
        except Exception as exc:  # noqa: BLE001 - the mail result stands on its own
            return f" · 시트 저장 실패: {type(exc).__name__}"
        return f" · 시트 {len(matches)}건 저장"

    @staticmethod
    def _held_summary(collection):
        parts = []
        if collection.get("application_unconfirmed"):
            parts.append(f"지원 버튼 미확인 표시 {collection['application_unconfirmed']}건")
        if collection.get("status_unverified"):
            parts.append(f"접수상태 미확인 {collection['status_unverified']}건 보류")
        if collection.get("requirements_held"):
            parts.append(f"조건 근거 미확인 {collection['requirements_held']}건 보류")
        if collection.get("rate_limited_skipped"):
            parts.append(
                f"사이트 접속 제한(rate_limited)으로 {collection['rate_limited_skipped']}건 건너뜀"
            )
        if collection.get("detail_not_checked"):
            parts.append(f"상세 미확인 {collection['detail_not_checked']}건")
        return "".join(" · " + part for part in parts)

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
