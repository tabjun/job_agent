"""Typed repeatable resume records and deterministic legacy field rendering."""

from datetime import date
import re


def field(key, label, kind="text", options=None):
    result = {"key": key, "label": label, "type": kind}
    if options:
        result["options"] = options
    return result


def section(label, identity, *fields):
    return {"label": label, "identity": identity, "fields": list(fields)}


PERIOD = (
    field("start", "시작일", "month"),
    field("end", "종료일", "month"),
    field("current", "현재 진행 중", "checkbox"),
)
SECTIONS = {
    "experience_description": section(
        "경력",
        "company",
        field("company", "회사명"),
        field("department", "부서"),
        field("role", "직무명"),
        field("position", "직급"),
        field(
            "employment",
            "고용 형태",
            "select",
            ["정규직", "계약직", "인턴", "프리랜서", "기타"],
        ),
        *PERIOD,
        field("description", "담당 업무", "textarea"),
        field("achievements", "성과", "textarea"),
    ),
    "education_description": section(
        "학력",
        "school",
        field("school", "학교명"),
        field("major", "전공"),
        field(
            "degree",
            "학위",
            "select",
            ["고등학교", "전문학사", "학사", "석사", "박사", "기타"],
        ),
        *PERIOD,
        field(
            "status",
            "학적 상태",
            "select",
            ["졸업", "졸업예정", "재학", "휴학", "수료", "중퇴"],
        ),
        field("gpa", "학점"),
        field("gpa_scale", "학점 만점"),
        field("description", "비고", "textarea"),
    ),
    "skills": section(
        "보유 기술",
        "name",
        field("name", "기술명"),
        field("category", "분류"),
        field("level", "숙련도", "select", ["기초", "실무 활용", "숙련"]),
        field("description", "사용 경험", "textarea"),
    ),
    "project_description": section(
        "프로젝트",
        "name",
        field("name", "프로젝트명"),
        field("organization", "소속·주관기관"),
        *PERIOD,
        field("role", "본인 역할"),
        field("team", "팀 규모"),
        field("technologies", "사용 기술"),
        field("description", "문제·수행 내용", "textarea"),
        field("achievements", "성과", "textarea"),
        field("url", "결과물 링크", "url"),
    ),
    "certifications": section(
        "자격증",
        "name",
        field("name", "자격증명"),
        field("number", "자격번호"),
        field("issuer", "발급기관"),
        field("acquired", "취득일", "date"),
        field("expires", "유효기간 종료일", "date"),
        field("description", "비고", "textarea"),
    ),
    "awards": section(
        "수상",
        "name",
        field("name", "수상명"),
        field("organizer", "수여기관"),
        field("date", "수상일", "date"),
        field("rank", "등급·훈격"),
        field("description", "수상 내용", "textarea"),
    ),
    "languages": section(
        "어학",
        "language",
        field("language", "언어"),
        field("test", "시험명"),
        field("score", "점수·등급"),
        field("number", "성적번호"),
        field("date", "응시일", "date"),
        field("expires", "유효기간 종료일", "date"),
    ),
    "training": section(
        "교육",
        "name",
        field("name", "교육명"),
        field("organization", "교육기관"),
        *PERIOD,
        field("hours", "교육 시간"),
        field("description", "교육 내용", "textarea"),
    ),
    "activities": section(
        "대외활동",
        "name",
        field("name", "활동명"),
        field("organization", "소속기관"),
        *PERIOD,
        field("role", "역할"),
        field("description", "활동 내용", "textarea"),
    ),
    "publications": section(
        "논문·발표",
        "title",
        field("title", "제목"),
        field("venue", "학술지·학회"),
        field("role", "저자·발표 역할"),
        field("date", "발표일", "date"),
        field("url", "원문 링크", "url"),
        field("description", "요약", "textarea"),
    ),
    "patents": section(
        "특허",
        "title",
        field("title", "특허명"),
        field("number", "출원·등록번호"),
        field("status", "진행 상태", "select", ["출원", "등록", "기타"]),
        field("date", "출원·등록일", "date"),
        field("role", "발명자 역할"),
        field("description", "내용", "textarea"),
    ),
    "links": section(
        "포트폴리오 링크",
        "url",
        field("label", "링크 이름"),
        field("url", "주소", "url"),
    ),
}


def render_items(key, items):
    schema = SECTIONS[key]
    blocks = []
    for item in items:
        lines = []
        for definition in schema["fields"]:
            value = item[definition["key"]]
            if definition["type"] == "checkbox":
                value = "예" if value else ""
            if value:
                lines.append(f"{definition['label']}: {value}")
        if lines:
            blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def validate_items(key, items, complete=False):
    if key not in SECTIONS or not isinstance(items, list) or len(items) > 50:
        raise ValueError("정형 항목 종류 또는 개수를 확인하세요(최대 50개).")
    schema = SECTIONS[key]
    expected = {definition["key"] for definition in schema["fields"]}
    for item in items:
        if not isinstance(item, dict) or set(item) != expected:
            raise ValueError(f"{schema['label']} 세부 항목 구조가 잘못되었습니다.")
        for definition in schema["fields"]:
            value = item[definition["key"]]
            kind = definition["type"]
            if kind == "checkbox":
                if type(value) is not bool:
                    raise ValueError("진행 중 여부는 참/거짓이어야 합니다.")
                continue
            if not isinstance(value, str) or len(value) > 5000:
                raise ValueError("세부 항목은 최대 5000자 문자열이어야 합니다.")
            if value and kind in {"month", "date"}:
                pattern = r"\d{4}-\d{2}" if kind == "month" else r"\d{4}-\d{2}-\d{2}"
                if not re.fullmatch(pattern, value):
                    raise ValueError("날짜 형식을 확인하세요.")
                try:
                    date.fromisoformat(value + "-01" if kind == "month" else value)
                except ValueError as error:
                    raise ValueError("존재하지 않는 날짜입니다.") from error
            if value and kind == "select" and value not in definition["options"]:
                raise ValueError("선택 항목을 확인하세요.")
            if value and kind == "url" and not re.match(r"^https?://[^\s]+$", value):
                raise ValueError("링크는 http 또는 https 주소를 입력하세요.")
        if item.get("current") and item.get("end"):
            raise ValueError("진행 중인 항목에는 종료일을 입력하지 않습니다.")
        for start, end in (
            ("start", "end"),
            ("acquired", "expires"),
            ("date", "expires"),
        ):
            if item.get(start) and item.get(end) and item[start] > item[end]:
                raise ValueError("종료일은 시작일보다 빠를 수 없습니다.")
        if complete and any(item.values()) and not item[schema["identity"]].strip():
            raise ValueError(f"{schema['label']}의 이름·기관·주소를 입력하세요.")
