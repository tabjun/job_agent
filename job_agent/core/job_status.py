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

from job_agent.core.job_match import experience
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
        self.heading, self.headings = False, []
        self.control, self.controls = None, []
        self.in_head = False
        self.section, self.recommendation_index = None, None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "head":
            self.in_head = True
        if tag in {"h2","h3"}:
            self.section = (tag,len(self.visible),[])
        if tag in {"a", "button"}:
            self.control = (tag, attrs, [])
        if tag == "h1":
            self.heading = True
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
        if self.section and tag==self.section[0]:
            label=" ".join(" ".join(self.section[2]).split())
            if self.headings and re.match(r"^(?:추천\s*(?:공고|채용)|비슷한\s*(?:공고|포지션)|연관\s*공고)",label):
                if self.recommendation_index is None:self.recommendation_index=self.section[1]
            self.section=None
        if tag == "head":
            self.in_head = False
        if self.control and tag == self.control[0]:
            self.controls.append(self.control)
            self.control = None
        if tag == "h1":
            self.heading = False
        if tag == self.skip:
            if self.script is not None:
                self.scripts.append("".join(self.script))
            self.script, self.skip = None, None

    def handle_data(self, data):
        if self.control and not self.skip:
            self.control[2].append(data)
        if self.script is not None:
            self.script.append(data)
        elif not self.skip and not self.in_head:
            self.visible.append(data)
            if self.section:self.section[2].append(data)
            if self.heading:
                self.headings.append(data)


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
    primary = parser.visible[:parser.recommendation_index] if parser.recommendation_index is not None else parser.visible
    page = " ".join(" ".join(primary).split())
    meta = " ".join(" ".join(parser.meta).split())
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
    job = matching[0] if matching else {}
    heading = str(job.get("title") or " ".join(parser.headings)).strip()
    # Find the title in the visible page only; meta text is appended last and
    # must not become the whole body. A header menu may say 'AI 추천 공고'
    # before this posting, so the text split starts at the title.
    start = page.find(heading) if heading else -1
    prefix, body = (page[:start], page[start:]) if start >= 0 else ("", page)
    # Recommendation widgets are different postings, not this page's deadline,
    # even when their title is a plain <div> rather than an h2/h3 heading.
    body = re.split(
        r"이 기업의 취업 전략|추천\s*(?:공고|채용)|비슷한\s*(?:공고|포지션)|연관\s*공고",
        body,
    )[0]
    body = f"{body} {meta}".strip()
    # A closed badge can sit above the title; a false 'closed' only withholds
    # a posting, while a missed one mails an expired posting.
    if closed_text(prefix) or closed_text(body):
        return {"status": "closed", "evidence": "detail_closed_text"}
    addresses = job.get("jobLocation") or []
    addresses = addresses if isinstance(addresses, list) else [addresses]
    locations = []
    for location in addresses:
        address = location.get("address", {}) if isinstance(location, dict) else {}
        if isinstance(address, dict):
            locations.append(
                " ".join(
                    str(address.get(k) or "")
                    for k in ("addressRegion", "addressLocality", "streetAddress")
                )
            )
    location = " ".join(locations).strip()
    if not location:
        match = re.search(
            r"(?:근무지역|근무지(?:주소)?|근무장소|근무위치)\s*[:：]?\s*(.{2,100})",
            body,
        )
        location = match[1].strip() if match else ""
    structured_exp = job.get("experienceRequirements") or ""
    if isinstance(structured_exp, dict):
        structured_exp = structured_exp.get("monthsOfExperience")
        structured_exp = (
            f"경력 {float(structured_exp) / 12:g}년 이상"
            if isinstance(structured_exp, (int, float)) and structured_exp % 12 == 0
            else ""
        )
    exp = experience(structured_exp)
    if exp["kind"] == "unknown":
        qualification = re.search(
            r"(?:자격요건|지원자격|필수요건|필수사항|자격사항)\s*[:：]?\s*(.{1,3500}?)(?=우대사항|우대요건|복리후생|혜택|$)",
            body,
        )
        explicit_exp = re.search(
            r"경력\s*(?:무관|\d{1,2}\s*[~∼～-]\s*\d{1,2}\s*년|\d{1,2}\s*년\s*(?:이상|이하|↑|↓|\+)|신입\s*/\s*경력)",
            body,
        )
        exp = experience(
            qualification[1]
            if qualification
            else explicit_exp[0]
            if explicit_exp
            else ""
        )
    details = {
        "job_location": location,
        "job_title": str(job.get("title") or " ".join(parser.headings)).strip(),
        "experience": exp,
        "company": (job.get("hiringOrganization") or {}).get("name", "")
        if isinstance(job.get("hiringOrganization"), dict)
        else "",
        "job_description": body[:12000],
    }
    apply_controls = [
        attrs
        for _, attrs, parts in parser.controls
        if re.fullmatch(
            r"(?:홈페이지|간편|즉시|온라인)?\s*(?:입사)?지원(?:하기|서\s*작성)?",
            " ".join(" ".join(parts).split()),
        )
        and "disabled" not in attrs
        and attrs.get("aria-disabled") != "true"
        and attrs.get("aria-hidden") != "true"
        and "display:none" not in attrs.get("style", "").replace(" ", "")
    ]
    details["application_available"] = bool(apply_controls)
    details["application_blocked"] = (
        any(
            re.fullmatch(
                r"(?:홈페이지|간편|즉시|온라인)?\s*(?:입사)?지원(?:하기|서\s*작성)?",
                " ".join(" ".join(parts).split()),
            )
            and ("disabled" in attrs or attrs.get("aria-disabled") == "true")
            for _, attrs, parts in parser.controls
        )
        and not apply_controls
    )
    details["application_evidence"] = (
        "공개 원문에 활성 지원 버튼/링크 표시"
        if apply_controls
        else "활성 지원 경로 미확인"
    )
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
        return {
            "status": "open",
            "evidence": "detail_deadline",
            "deadline": str(value),
            **details,
        }
    if re.search(
        r"(?:마감일|접수\s*기간|모집\s*기간)\s*[:：|]?\s*(?:상시\s*(?:채용|모집)|채용\s*시\s*마감)",
        body,
    ):
        return {
            "status": "open",
            "evidence": "detail_ongoing",
            "period": "채용 시 마감 (원문 확인)",
            **details,
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
