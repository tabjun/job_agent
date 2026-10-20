"""Evidence-based requirements shared by search results and email collection."""

import re
from urllib.parse import urlsplit

from job_agent.core.postings import allowed_regions, region_check

DEFAULT_EXPERIENCE = {"entry": True, "any": True, "min_years": 1, "max_years": 5}


def _word(pattern):
    # Korean letters are word characters, so a \b word boundary misses 'AI엔지니어'.
    return rf"(?<![A-Za-z]){pattern}(?![A-Za-z])"


FAMILIES = {
    "analysis": r"데이터\s*분석|데이터\s*애널리|data\s*analy(?:st|tics)|analytics\s*engineer"
    rf"|{_word('BI')}|비즈니스\s*인텔리전스|business\s*intelligence"
    r"|product\s*analy|프로덕트\s*(?:데이터\s*)?분석"
    r"|그로스\s*(?:분석|해커|해킹|데이터|애널리)|growth\s*(?:analy|hack)"
    r"|통계\s*분석|statistician|statistical\s*analy|바이오\s*통계|biostatistic",
    "science": r"데이터\s*사이언|data\s*scien|데이터\s*과학|research\s*scientist"
    r"|applied\s*scientist|(?:AI|ML|리서치)\s*사이언티스트",
    "ml": r"머신\s*러닝|기계\s*학습|딥\s*러닝|machine\s*learning|deep\s*learning"
    rf"|{_word('ML(?:Ops)?')}|{_word('MLE')}",
    "ai": rf"인공\s*지능|{_word('AI')}|{_word('LLM')}|{_word('GenAI')}|생성형\s*AI"
    rf"|컴퓨터\s*비전|computer\s*vision|자연어\s*처리|{_word('NLP')}",
    "engineering": r"데이터\s*엔지니어|data\s*engineer|데이터\s*플랫폼|data\s*platform",
    "statistics": r"통계|statistic|리서치|researcher",
}
# Asking for AI/ML also covers the data platform roles that ship those models.
IMPLIED_FAMILIES = {"ml": {"engineering"}, "ai": {"engineering"}}
# Teaching, training programmes, licensed clinical roles and data collection or
# labelling labour mention data/AI but are not data jobs; sales titles only
# count when no analysis work is named.
EXCLUDED_TITLE = (
    r"강사|교육생|수강생|훈련생|국비|부트\s*캠프|방사선사|간호사|보험\s*설계사|튜터"
    r"|라벨링|레이블링|어노테이션|labeling|annotation|단순\s*입력"
    r"|데이터\s*수집\s*(?:직원|알바|아르바이트|요원)|수집\s*알바"
)
SALES_TITLE = rf"영업|세일즈|{_word('sales')}"
WORK_TITLE = r"분석|analy|사이언|scien|엔지니어|engineer|개발|연구|research"


def requested_experience(value):
    """'신입, 경력무관, 1~5년' -> one request covering every listed part."""
    parts = [
        p.strip()
        for p in re.split(r"[,，、]|\s+또는\s+", str(value or ""))
        if p.strip()
    ]
    parsed = [experience(part) for part in parts]
    if not parsed or any(p["kind"] == "unknown" for p in parsed):
        raise ValueError("경력은 신입, 경력무관, 1~5년처럼 명시해주세요.")
    years = [p for p in parsed if p["kind"] == "years"]
    return {
        "entry": any(p["kind"] == "entry" or "신입" in part for p, part in zip(parsed, parts)),
        "any": any(p["kind"] == "any" or "무관" in part for p, part in zip(parsed, parts)),
        "min_years": min((p["min_years"] for p in years), default=0),
        "max_years": max(
            (50 if p["max_years"] is None else p["max_years"] for p in years),
            default=0,
        ),
    }


def experience(value):
    value = " ".join(str(value or "").split())
    if re.search(r"경력\s*무관|신입\s*[/·ㆍ및-]\s*경력", value):
        return {"kind": "any", "evidence": value[:240]}
    span = re.search(
        r"(?:경력\s*)?(\d{1,2})\s*년?\s*[~∼～-]\s*(\d{1,2})\s*년", value
    )
    minimum = re.search(
        r"(?:경력\s*)?(\d{1,2})\s*년\s*차?\s*(?:이상|↑|\+)"
        r"|(\d{1,2})\s*\+\s*years?|(?:at\s*least|minimum(?:\s*of)?)\s*(\d{1,2})\s*years?"
        r"|(\d{1,2})\s*years?\s+(?:of\s+)?(?:\w+\s+)?experience",
        value,
        re.IGNORECASE,
    )
    maximum = re.search(r"(?:경력\s*)?(\d{1,2})\s*년\s*차?\s*(?:이하|미만|↓)", value)
    if span:
        low, high = int(span[1]), int(span[2])
        if high >= low:
            return {
                "kind": "years",
                "min_years": low,
                "max_years": high,
                "evidence": span[0],
            }
    if minimum:
        low = int(next(group for group in minimum.groups() if group))
        high = int(maximum[1]) if maximum and int(maximum[1]) >= low else None
        return {
            "kind": "years",
            "min_years": low,
            "max_years": high,
            "evidence": minimum[0] if high is None else f"{minimum[0]} {maximum[0]}",
        }
    if maximum:
        return {
            "kind": "years",
            "min_years": 0,
            "max_years": int(maximum[1]),
            "evidence": maximum[0],
        }
    if re.search(r"신입|new\s*grad|entry\s*level", value, re.IGNORECASE):
        return {"kind": "entry", "evidence": value[:240]}
    junior = re.search(rf"주니어|{_word('junior')}", value, re.IGNORECASE)
    if junior:
        return {"kind": "years", "min_years": 0, "max_years": 3, "evidence": junior[0]}
    return {"kind": "unknown", "evidence": "경력 조건 근거 없음"}


def role_families(requested):
    families = {
        k
        for k, pattern in FAMILIES.items()
        if re.search(pattern, requested, re.IGNORECASE)
    }
    # Generic '데이터' is the common umbrella for the supported data/AI roles.
    if not families and "데이터" in requested:
        families = set(FAMILIES)
    for family in list(families):
        families |= IMPLIED_FAMILIES.get(family, set())
    return families


def title_check(title, requested):
    """'' when the title fits the requested role, else the reject reason."""
    if re.search(EXCLUDED_TITLE, title) or (
        re.search(SALES_TITLE, title, re.IGNORECASE)
        and not re.search(WORK_TITLE, title, re.IGNORECASE)
    ):
        return "role_excluded"
    families = role_families(requested)
    if families and not any(
        re.search(FAMILIES[k], title, re.IGNORECASE) for k in families
    ):
        return "role_mismatch"
    return ""


def validate_experience(value):
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("경력 조건을 확인하세요.")  # noqa: TRY004 - UI validation contract
    low, high = value.get("min_years", 1), value.get("max_years", 5)
    if type(low) is not int or type(high) is not int or not 0 <= low <= high <= 50:
        raise ValueError("경력 연차는 0~50년 범위로 입력하세요.")
    return {
        "entry": value.get("entry") is True,
        "any": value.get("any") is True,
        "min_years": low,
        "max_years": high,
    }


def requirements(posting, rule):
    """Pass/hold/reject; missing evidence is never treated as a match."""
    title = str(
        posting.get("job_title") or posting.get("role") or posting.get("title") or ""
    )
    reason = title_check(title, str(rule.get("role") or ""))
    if reason:
        return {"decision": "reject", "reason": reason}
    location = str(posting.get("job_location") or "")
    for english, korean in {
        "seoul": "서울",
        "gyeonggi": "경기",
        "seongnam": "성남",
        "pangyo": "판교",
        "suwon": "수원",
    }.items():
        location = re.sub(rf"\b{english}\b", korean, location, flags=re.IGNORECASE)
    if rule.get("location"):
        if not location:
            return {"decision": "hold", "reason": "location_unknown"}
        keep, found = region_check(
            location.casefold(), allowed_regions(rule["location"])
        )
        if not keep or not found:
            return {"decision": "reject", "reason": "location_mismatch"}
    requested_exp = rule.get("experience")
    evidence = posting.get("experience") or {"kind": "unknown"}
    if requested_exp is not None:
        kind = evidence.get("kind")
        if kind == "unknown":
            return {"decision": "hold", "reason": "experience_unknown"}
        # '경력무관' is open to every applicant, whatever range was requested.
        matches = kind == "any" or (kind == "entry" and requested_exp["entry"])
        if kind == "years":
            low, high = evidence["min_years"], evidence.get("max_years")
            matches = low <= requested_exp["max_years"] and (
                high is None or high >= requested_exp["min_years"]
            )
        if not matches:
            return {"decision": "reject", "reason": "experience_mismatch"}
    # Many platforms render the apply button with JavaScript. Callers only
    # pass postings whose current deadline/ongoing status was confirmed, so a
    # missing button is labelled for the reader; a disabled one is held.
    if posting.get("application_blocked"):
        return {"decision": "hold", "reason": "application_blocked"}
    confirmed = bool(posting.get("application_available"))
    if not confirmed and posting.get("status", "open") != "open":
        return {"decision": "hold", "reason": "application_unknown"}
    return {
        "decision": "pass",
        "reason": "requirements_confirmed",
        "application_confirmed": confirmed,
        "experience": evidence,
        "job_location": location,
        "job_title": title,
    }


def cross_platform_key(job):
    """Conservative duplicate evidence; never collapse different teams/levels."""
    company = str(job.get("company") or "")
    role = str(job.get("role") or job.get("title") or "")
    check = job.get("status_check", {})
    # Without all three independent fields, keep the distinct posting.
    if company in {"", "원문 확인"} or not role or not check.get("deadline"):
        return ""
    company = re.sub(r"주식회사|\(주\)|㈜|\s", "", company).casefold()
    role = re.sub(r"\s|[\[\]()]|(?:채용|모집)$", "", role).casefold()
    return "|".join(
        [company, role, str(check.get("job_location", "")), str(check["deadline"])]
    )


def merge_cross_platform(jobs):
    found, result = {}, []
    for job in jobs:
        key = cross_platform_key(job)
        if (
            key
            and key in found
            and urlsplit(found[key]["url"]).hostname != urlsplit(job["url"]).hostname
        ):
            found[key].setdefault("alternate_urls", []).append(job["url"])
        else:
            result.append(job)
            if key:
                found[key] = job
    return result
