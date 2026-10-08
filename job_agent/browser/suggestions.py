"""Conservative exact-label proposals; never approve or write portal fields."""

from collections import Counter
import re


ALIASES = {
    "name": ["이름", "성명", "name", "fullname"],
    "email": ["이메일", "email"],
    "phone": ["연락처", "휴대폰", "휴대전화", "phone", "mobile"],
    "headline": ["이력서 제목", "headline"],
    "summary": ["소개", "간단소개", "summary", "about"],
    "experience_description": ["경력 기술", "경력사항", "experience_description"],
    "education_description": ["학력사항", "education_description"],
    "project_description": ["프로젝트", "project_description"],
    "skills": ["보유 기술", "skills"],
    "cover_letter": ["자기소개서", "cover_letter"],
    "employment_type": ["재직 형태", "employment_type"],
}
ATOMIC = {"name", "email", "phone", "employment_type"}


def normalized(text):
    return re.sub(r"[\s_-]", "", str(text or "").lower())


def propose_mappings(values, fields):
    proposals = []
    for key, value in values.items():
        names = {normalized(name) for name in ALIASES.get(key, [])}
        matches = []
        for index, target in enumerate(fields):
            if (
                key not in ATOMIC
                and target.get("tag") != "textarea"
                and not target.get("contenteditable")
            ):
                continue
            labels = [
                *target.get("labels", []),
                target.get("aria_label"),
                target.get("id"),
                target.get("name"),
            ]
            if not names.intersection(normalized(label) for label in labels):
                continue
            limit = target.get("max_length")
            if isinstance(limit, int) and limit >= 0 and len(value) > limit:
                continue
            if target.get("tag") == "select":
                options = [
                    option
                    for option in target.get("options", [])
                    if not option.get("disabled")
                ]
                exact = [option for option in options if option.get("value") == value]
                matches_by_label = [
                    option for option in options if option.get("label") == value
                ]
                if len(exact or matches_by_label) != 1:
                    continue
            matches.append(index)
        if len(matches) == 1:
            proposals.append({"field_id": key, "target_index": matches[0]})
    counts = Counter(row["target_index"] for row in proposals)
    return [row for row in proposals if counts[row["target_index"]] == 1]
