"""Shared posting identity, evidence extraction and bounded search planning."""

import re
from datetime import date
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SITES = {
    "catch": "catch.co.kr",
    "jobkorea": "jobkorea.co.kr",
    "saramin": "saramin.co.kr",
    "wanted": "wanted.co.kr",
    "incruit": "incruit.com",
}
NAMES = {
    "catch": "캐치",
    "jobkorea": "잡코리아",
    "saramin": "사람인",
    "wanted": "원티드",
    "incruit": "인크루트",
}


def diverse_jobs(jobs, limit):
    """Prefer distinct known employers, round-robin across available platforms."""
    sites = list(dict.fromkeys(job.get("site") for job in jobs))
    buckets = [[job for job in jobs if job.get("site") == site] for site in sites]
    ordered = []
    while any(buckets):
        for bucket in buckets:
            if bucket:
                ordered.append(bucket.pop(0))
    first, rest, companies = [], [], set()
    for job in ordered:
        company = str(job.get("company", "")).casefold().strip()
        if company and company != "원문 확인" and company in companies:
            rest.append(job)
        else:
            first.append(job)
            if company and company != "원문 확인":
                companies.add(company)
    return (first + rest)[:limit]


def matches(term, body):
    if re.fullmatch(r"[a-z0-9+#.]+", term):
        return (
            re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", body) is not None
        )
    return term in body


def queries(role, location, keywords):
    # Alternatives are separate searches, not an accidental AND of every role.
    roles = [
        r.strip()
        for r in re.split(r"[,·;/\n]|\s+OR\s+", role, flags=re.IGNORECASE)
        if r.strip()
    ]
    if len(roles) == 1:
        # Older saved alerts joined independent role families with spaces.
        families = re.findall(
            r"데이터\s*분석(?:가)?|데이터\s*사이언티스트|머신러닝|통계|인공지능|\bAI\b|\bML\b",
            role,
            re.IGNORECASE,
        )
        if len(families) > 1:
            roles = families
    roles = list(dict.fromkeys(roles)) or [keywords]
    if len(roles) > 3:
        roles = roles[:2] + [" OR ".join(roles[2:])]
    # A list of regions is an OR preference, not a requirement to mention all.
    if re.search(r"[,·;/]", location):
        location = ""
    return [" ".join(v for v in (role, location, "채용") if v) for role in roles]


def canonical_url(url):
    p = urlsplit(url)
    host = (p.hostname or "").lower()
    host = host.removeprefix("m.")
    host = host.removeprefix("www.")
    domain = next(
        (v for v in SITES.values() if host == v or host.endswith("." + v)), ""
    )
    if not domain:
        return url
    identities = {
        "wanted.co.kr": r"/wd/(\d+)",
        "catch.co.kr": r"/NCS/RecruitInfoDetails/(\d+)",
        "jobkorea.co.kr": r"/Recruit/GI_Read/(\d+)",
    }
    if domain in identities:
        detail = re.fullmatch(identities[domain], p.path.rstrip("/"), re.IGNORECASE)
        if detail:
            prefix = {
                "wanted.co.kr": "/wd/",
                "catch.co.kr": "/NCS/RecruitInfoDetails/",
                "jobkorea.co.kr": "/Recruit/GI_Read/",
            }[domain]
            return "https://www." + domain + prefix + detail[1]
    params = [
        (k, v)
        for k, v in parse_qsl(p.query, keep_blank_values=True)
        if not k.lower().startswith("utm_")
        and k.lower()
        not in {
            "gclid",
            "fbclid",
            "startno",
            "ct",
            "ty",
            "cd",
            "occ2",
            "page",
            "pageno",
        }
    ]
    if domain == "saramin.co.kr" and dict(params).get("rec_idx", "").isdigit():
        return (
            "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx="
            + dict(params)["rec_idx"]
        )
    # Same Incruit posting is indexed on desktop, mobile and lab paths.
    job = re.search(r"/jobs/(\d+)", p.path, re.IGNORECASE)
    if domain == "incruit.com" and (job or dict(params).get("job")):
        return "https://job.incruit.com/jobdb_info/jobpost.asp?job=" + (
            job[1] if job else dict(params)["job"]
        )
    return urlunsplit(
        (
            "https",
            "www." + domain if host == domain else host,
            p.path.rstrip("/"),
            urlencode(sorted(params)),
            "",
        )
    )


def rejection(row, domain, today=None):
    p = urlsplit(str(row.get("url", "")))
    host = (p.hostname or "").lower()
    if not (host == domain or host.endswith("." + domain)):
        return "outside_platform"
    if host.startswith(("jumpit.", "career.", "help.", "hr.", "static.")):
        return "other_service"
    title = str(row.get("title", ""))
    if re.search(
        r"검색결과|직무별 채용|직업별 채용|기업정보|관련 📢 채용공고|채용정보 \| 총",
        title,
    ):
        return "listing"
    if re.search(
        r"/(?:search|jobdb_list|company|comp|events|news|community|tags|wdlist|cv)(?:/|\?|$)|/jobs/list/",
        p.path,
        re.IGNORECASE,
    ):
        return "listing"
    body = title + " " + str(row.get("raw_content") or row.get("content") or "")
    if closed_text(body):
        return "closed"
    deadlines = [row.get(k) for k in ("validThrough", "end_date", "deadline")]
    deadlines += deadline_values(body)
    if any(
        (parsed := full_date(value)) and parsed < (today or date.today())
        for value in deadlines
    ):
        return "closed"
    return ""


DATE_VALUE = r"\d{4}\s*(?:[-./]|년)\s*\d{1,2}\s*(?:[-./]|월)\s*\d{1,2}\s*일?"
SHORT_DATE = r"\d{1,2}\s*[-./월]\s*\d{1,2}\s*일?"
DAY_SUFFIX = r"\s*(?:\([월화수목금토일]\))?"
CLOCK_SUFFIX = r"(?:\s*(?:\d{1,2}:\d{2}(?::\d{2})?|\d{1,2}\s*시(?:\s*\d{1,2}\s*분)?))?"


def full_date(value):
    """Parse a full calendar date, never treat publication dates as deadlines."""
    match = re.match(rf"\s*({DATE_VALUE})(?!\d)", str(value or ""))
    if match:
        try:
            return date(*map(int, re.findall(r"\d+", match[1])))
        except ValueError:
            pass
    return None


def deadline_values(body):
    """Only labeled closing dates/range ends; a yearless lone date stays unknown."""
    values = re.findall(
        rf"(?:마감(?:일|날짜)?|접수\s*마감(?:일)?)\s*[:：|(~∼～]*\s*({DATE_VALUE}{DAY_SUFFIX}{CLOCK_SUFFIX})",
        body,
    )
    for match in re.finditer(
        rf"(?:접수|모집|채용|공고)\s*기간\s*[:：|]?\s*({DATE_VALUE}){DAY_SUFFIX}"
        rf"\s*[~∼～]\s*({DATE_VALUE}|{SHORT_DATE})({DAY_SUFFIX}{CLOCK_SUFFIX})",
        body,
    ):
        start, end = full_date(match[1]), full_date(match[2])
        if start and not end:
            parts = re.findall(r"\d+", match[2])
            try:
                month, day = map(int, parts)
                end = date(
                    start.year + ((month, day) < (start.month, start.day)), month, day
                )
            except ValueError:
                pass
        if start and end and end >= start:
            values.append(end.isoformat() + " " + match[3].strip())
    return values


def closed_text(body):
    return bool(
        re.search(
            r"(?:마감|종료)\s*(?:되었습니다|되었|됐|된\s*공고|했습니다)"
            r"|(?:채용|접수|모집)(?:이|가|은|는)?\s*(?:종료|마감)\s*(?:되었습니다|됐|된|했습니다|되었)"
            r"|(?:^|[\n|])(?:채용|접수|모집)\s*(?:종료|마감)\s*(?:[.。]|$)"
            r"|(?:마감|종료)\s*\(\s*[~∼～]"
            r"|마감일\s*[:：]\s*(?:마감|종료)(?=\s|[.,]|$)",
            body,
        )
    )


def text(value, limit=180):
    return " ".join(str(value or "").split())[:limit]


def posting_fields(row):
    company = (
        row.get("company_name") or row.get("company") or row.get("hiringOrganization")
    )
    if isinstance(company, dict):
        company = company.get("name")
    if not company or company == "원문 확인":
        label = re.search(
            r"(?:회사명|기업명|채용기업)\s*[:：|]\s*([^\n|]{2,100})",
            str(row.get("raw_content") or row.get("content") or ""),
        )
        if label:
            company = label[1].strip().strip("*")
    title = text(row.get("title"), 300)
    if not company:
        suffix = re.search(r"\s+-\s+(.{2,80}?)\s+채용$", title)
        prefix = re.match(r"^((?:\(주\)|㈜|주식회사)\s*[^\s\[]+)\s+", title)
        if suffix:
            company = suffix[1]
        elif prefix:
            company = prefix[1]
    role = text(row.get("role") or row.get("position") or row.get("job_title"))
    # Explicit company markers only: generic hyphens can be part of a job title.
    match = re.match(r"^\[([^\[\]]{2,80})\]\s*(.+)$", title)
    if match is None:
        match = re.match(r"^(.{2,80}?)\s+채용\s*[-:|]\s*(.+)$", title)
    if match and not re.fullmatch(
        r"신입|경력|신입[·/ ]경력|정규직|계약직|인턴|상시|채용|서울|경기|.*(?:팀|부문|분석실|직군)|\d{4}.*",
        match[1],
    ):
        company = company or re.sub(r"\s+채용$", "", match[1])
        role = role or match[2]
    role = re.sub(
        r"\s*[-|]\s*(캐치|잡코리아|사람인|원티드|인크루트)\s*$", "", role or title
    )
    period = text(row.get("period") or row.get("recruitment_period"), 100)
    start, end = (
        text(row.get("start_date"), 40),
        text(row.get("end_date") or row.get("validThrough") or row.get("deadline"), 40),
    )
    if not period and end:
        period = f"{start} ~ {end}" if start else f"~ {end}"
    if not period:
        source = title + " " + text(row.get("content") or row.get("excerpt"), 2000)
        date = r"(?:\d{4}[./-])?\d{1,2}[./-]\d{1,2}(?:\s*\([월화수목금토일]\))?"
        match = re.search(
            rf"(?:접수|모집|채용|공고)\s*기간\s*[:：]?\s*({date}\s*[~∼～]\s*{date})",
            source,
        )
        if match:
            period = match[1]
        else:
            match = re.search(rf"마감(?:일|날짜)?\s*[:：]?\s*({date})", source)
            if match:
                period = f"~ {match[1]}"
    return {
        "company": text(company, 100) or "원문 확인",
        "role": text(role) or "원문 확인",
        "period": period or "원문 확인",
    }


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


def allowed_regions(location):
    """'서울, 경기' -> every name that counts as inside those regions."""
    names = set()
    for term in re.split(r"[,\s]+", location.casefold()):
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
