"""Evidence-based requirements shared by search results and email collection."""

import re
from urllib.parse import urlsplit

from job_agent.core.postings import allowed_regions, region_check

DEFAULT_EXPERIENCE = {"entry": True, "any": True, "min_years": 1, "max_years": 5}
FAMILIES = {
    "analysis": r"데이터\s*분석|data\s*analy(?:st|tics)|analytics\s*engineer|BI\s*(?:개발|분석|엔지니어)",
    "science": r"데이터\s*사이언|data\s*scien|데이터\s*과학",
    "ml": r"머신\s*러닝|기계\s*학습|딥\s*러닝|machine\s*learning|deep\s*learning|\bML(?:Ops)?\b",
    "ai": r"인공\s*지능|\bAI\b|\bLLM\b|컴퓨터\s*비전|computer\s*vision|자연어\s*처리|\bNLP\b",
    "statistics": r"통계|statistic|리서치|researcher",
}


def requested_experience(value):
    parsed = experience(value)
    if parsed["kind"] == "unknown":
        raise ValueError("경력은 신입, 경력무관, 1~5년처럼 명시해주세요.")
    return {
        "entry": "신입" in value or parsed["kind"] == "entry",
        "any": "무관" in value,
        "min_years": parsed.get("min_years", 0),
        "max_years": parsed.get("max_years")
        if parsed.get("max_years") is not None
        else 50
        if parsed["kind"] == "years"
        else 0,
    }


def experience(value):
    value = " ".join(str(value or "").split())
    if re.search(r"경력\s*무관|신입\s*[/·ㆍ및-]\s*경력", value):
        return {"kind": "any", "evidence": value[:240]}
    span = re.search(r"(?:경력\s*)?(\d{1,2})\s*[~∼～-]\s*(\d{1,2})\s*년", value)
    minimum = re.search(r"(?:경력\s*)?(\d{1,2})\s*년\s*(?:이상|↑|\+)", value)
    maximum = re.search(r"(?:경력\s*)?(\d{1,2})\s*년\s*(?:이하|미만|↓)", value)
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
        return {
            "kind": "years",
            "min_years": int(minimum[1]),
            "max_years": None,
            "evidence": minimum[0],
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
    return {"kind": "unknown", "evidence": "경력 조건 근거 없음"}


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
    requested = str(rule.get("role") or "")
    families = {
        k
        for k, pattern in FAMILIES.items()
        if re.search(pattern, requested, re.IGNORECASE)
    }
    # Generic '데이터' is the common umbrella for the supported data/AI roles.
    if not families and "데이터" in requested:
        families = set(FAMILIES)
    if families and not any(
        re.search(FAMILIES[k], title, re.IGNORECASE) for k in families
    ):
        return {"decision": "reject", "reason": "role_mismatch"}
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
        matches = (
            kind == "entry"
            and requested_exp["entry"]
            or kind == "any"
            and requested_exp["any"]
        )
        if kind == "years":
            low, high = evidence["min_years"], evidence.get("max_years")
            matches = low <= requested_exp["max_years"] and (
                high is None or high >= requested_exp["min_years"]
            )
        if not matches:
            return {"decision": "reject", "reason": "experience_mismatch"}
    if not posting.get("application_available"):
        return {"decision": "hold", "reason": "application_unknown"}
    return {
        "decision": "pass",
        "reason": "requirements_confirmed",
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
