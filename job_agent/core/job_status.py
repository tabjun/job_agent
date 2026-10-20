"""Recheck public posting details before email; unknown is never sendable.

No login, cookies, scripts or private APIs. Only known platform detail URLs
are fetched; redirects are revalidated and responses are bounded.
"""

import json
import re
from datetime import datetime, time, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import httpx

from job_agent.core.postings import (
    DATE_VALUE,
    canonical_url,
    closed_text,
    deadline_values,
    full_date,
)

KST = timezone(timedelta(hours=9))


def confirmation_current(check, now):
    """A deadline can pass while other candidates are being checked."""
    now = now.replace(tzinfo=KST) if now.tzinfo is None else now.astimezone(KST)
    if check.get("status") != "open":
        return False
    if check.get("deadline"):
        end = _expiry(check["deadline"])
        return end is not None and end >= now
    return True


class Detail(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.scripts, self.visible, self.meta = [], [], []
        self.script, self.skip = None, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            self.skip = tag
            self.script = (
                [] if attrs.get("type", "").lower() == "application/ld+json" else None
            )
        elif tag in {"style", "noscript"}:
            self.skip = tag
        elif tag == "meta" and attrs.get("name", "").lower() == "description":
            self.meta.append(attrs.get("content", ""))

    def handle_endtag(self, tag):
        if tag == self.skip:
            if self.script is not None:
                self.scripts.append("".join(self.script))
            self.script, self.skip = None, None

    def handle_data(self, data):
        if self.script is not None:
            self.script.append(data)
        elif not self.skip:
            self.visible.append(data)


def _jobs(value):
    if isinstance(value, list):
        for item in value:
            yield from _jobs(item)
    elif isinstance(value, dict):
        types = value.get("@type", [])
        if types == "JobPosting" or isinstance(types, list) and "JobPosting" in types:
            yield value
        if "@graph" in value:
            yield from _jobs(value["@graph"])


def _expiry(value):
    day = full_date(value)
    if not day:
        return None
    raw = str(value).strip()
    if "T" in raw:
        try:
            stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return stamp.replace(tzinfo=KST) if stamp.tzinfo is None else stamp
        except ValueError:
            return None
    clock = re.search(
        r"(?:\d{4}\s*[-./년]\s*\d{1,2}\s*[-./월]\s*\d{1,2}\s*일?)"
        r"\s*(?:\([월화수목금토일]\))?\s+(\d{1,2})(?::(\d{2})(?::(\d{2}))?|\s*시(?:\s*(\d{1,2})\s*분)?)",
        raw,
    )
    if clock:
        try:
            return datetime.combine(
                day,
                time(int(clock[1]), int(clock[2] or clock[4] or 0), int(clock[3] or 0)),
                KST,
            )
        except ValueError:
            return None
    return datetime.combine(day, time.max, KST)


def detail_status(html, url, now):
    """Closed evidence wins even when a generic '채용 시 마감' also appears."""
    now = now.replace(tzinfo=KST) if now.tzinfo is None else now.astimezone(KST)
    parser = Detail()
    parser.feed(html)
    body = " ".join(" ".join(parser.visible + parser.meta).split())
    # Recommendation widgets are different postings, not this page's deadline.
    body = re.split(
        r"이 기업의 취업 전략|추천\s*(?:공고|채용)|비슷한\s*(?:공고|포지션)|연관\s*공고",
        body,
    )[0]
    if closed_text(body):
        return {"status": "closed", "evidence": "detail_closed_text"}
    postings = []
    for script in parser.scripts:
        try:
            postings.extend(_jobs(json.loads(script)))
        except (ValueError, RecursionError):
            continue
    matching = [
        p for p in postings if p.get("url") and canonical_url(str(p["url"])) == url
    ]
    if not matching and len(postings) == 1 and not postings[0].get("url"):
        matching = postings
    if postings and not matching:
        return {"status": "unknown", "evidence": "unmatched_job_schema"}
    values = [p.get("validThrough") for p in matching]
    # Metadata can expose deadlines when the body requires JavaScript.
    values += deadline_values(body)
    parsed = [(value, _expiry(value)) for value in values if value]
    if any(end and end < now for _, end in parsed):
        return {"status": "closed", "evidence": "detail_deadline"}
    # Invalid/conflicting structured dates must not become an open confirmation.
    if any(end is None for _, end in parsed):
        return {"status": "unknown", "evidence": "invalid_deadline"}
    starts = re.findall(
        rf"(?:(?:접수|모집|채용|공고)\s*기간|시작일)\s*[:：|]?\s*({DATE_VALUE})",
        body,
    )
    if any((day := full_date(value)) and day > now.date() for value in starts):
        return {"status": "unknown", "evidence": "not_started"}
    if parsed:
        value, _ = min(parsed, key=lambda item: item[1])
        return {"status": "open", "evidence": "detail_deadline", "deadline": str(value)}
    if re.search(
        r"(?:마감일|접수\s*기간|모집\s*기간)\s*[:：|]?\s*(?:상시\s*(?:채용|모집)|채용\s*시\s*마감)",
        body,
    ):
        return {
            "status": "open",
            "evidence": "detail_ongoing",
            "period": "채용 시 마감 (원문 확인)",
        }
    return {"status": "unknown", "evidence": "no_current_deadline"}


def detail_url(url):
    """Build requests only for the five supported public posting routes."""
    source = urlsplit(str(url))
    hosts = {"job.incruit.com"} | {
        prefix + domain
        for prefix in ("", "www.", "m.", "mobile.")
        for domain in (
            "jobkorea.co.kr",
            "saramin.co.kr",
            "wanted.co.kr",
            "catch.co.kr",
            "incruit.com",
        )
    }
    if source.hostname not in hosts or source.username or source.password:
        return ""
    url = canonical_url(url)
    p = urlsplit(url)
    routes = {
        "www.jobkorea.co.kr": r"/Recruit/GI_Read/\d+",
        "www.saramin.co.kr": r"/zf_user/jobs/relay/view",
        "www.wanted.co.kr": r"/wd/\d+",
        "www.catch.co.kr": r"/NCS/RecruitInfoDetails/\d+",
        "job.incruit.com": r"/jobdb_info/jobpost.asp",
    }
    if p.hostname not in routes or not re.fullmatch(
        routes[p.hostname], p.path, re.IGNORECASE
    ):
        return ""
    if p.hostname == "www.saramin.co.kr" and not re.fullmatch(r"rec_idx=\d+", p.query):
        return ""
    if p.hostname == "job.incruit.com" and not re.fullmatch(r"job=\d+", p.query):
        return ""
    return url


def verify_posting(url, now):
    original = detail_url(url)
    if not original:
        return {"status": "unknown", "evidence": "unsupported_detail_url"}
    target = original
    try:
        with httpx.Client(timeout=8, follow_redirects=False, trust_env=False) as client:
            for _ in range(3):
                client.cookies.clear()
                with client.stream("GET", target) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        target = detail_url(
                            urljoin(target, response.headers.get("location", ""))
                        )
                        if target != original:
                            return {
                                "status": "unknown",
                                "evidence": "redirected_detail",
                            }
                        continue
                    if response.status_code in {404, 410}:
                        return {"status": "closed", "evidence": "detail_removed"}
                    if response.status_code != 200:
                        return {"status": "unknown", "evidence": "detail_unavailable"}
                    if "html" not in response.headers.get("content-type", "").lower():
                        return {"status": "unknown", "evidence": "not_html"}
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > 3_000_000:
                            return {"status": "unknown", "evidence": "detail_too_large"}
                        chunks.append(chunk)
                    encoding = response.encoding or "utf-8"
                    return detail_status(
                        b"".join(chunks).decode(encoding, errors="replace"),
                        original,
                        now,
                    )
    except (httpx.HTTPError, ValueError, RecursionError, LookupError):
        pass
    return {"status": "unknown", "evidence": "detail_unavailable"}
