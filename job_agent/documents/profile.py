"""Versioned, reviewed resume input shared by deterministic consumers."""

from copy import deepcopy
import re
from job_agent.documents.sections import SECTIONS, render_items, validate_items


FORMAT = "job-agent.resume/v1"
FIELDS = {
    "headline": "이력서 제목",
    "summary": "소개",
    "experience_description": "경력",
    "department": "직무·부서",
    "education_description": "학력",
    "project_description": "프로젝트",
    "award_certification_description": "자격·수상",
    "cover_letter": "자기소개서",
    "skills": "보유 기술",
    "name": "이름",
    "email": "이메일",
    "phone": "연락처",
    "links": "포트폴리오 링크",
    "employment_type": "재직 형태",
    **{
        key: value["label"]
        for key, value in SECTIONS.items()
        if key
        not in {
            "experience_description",
            "education_description",
            "skills",
            "project_description",
            "links",
        }
    },
}


class ResumeProfile:
    def __init__(self, data):
        if not isinstance(data, dict) or set(data) != {"format", "fields"}:
            raise ValueError("공통 이력서의 format/fields를 확인하세요.")
        if data["format"] != FORMAT:
            raise ValueError("지원하지 않는 이력서 버전입니다.")
        fields = data["fields"]
        if not isinstance(fields, list) or len(fields) > 200:
            raise ValueError("fields는 최대 200개 배열이어야 합니다.")
        seen = set()
        for field in fields:
            if not isinstance(field, dict) or set(field) - {"items"} != {
                "id",
                "label",
                "value",
                "reviewed",
                "evidence",
            }:
                raise ValueError("이력서 필드 구조가 잘못되었습니다.")
            key = field["id"]
            if (
                not isinstance(key, str)
                or not re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)*", key)
                or len(key) > 120
                or key in seen
            ):
                raise ValueError("필드 ID는 고유한 영문 경로여야 합니다.")
            seen.add(key)
            if "items" in field:
                validate_items(key, field["items"])
                if field["value"] != render_items(key, field["items"]):
                    raise ValueError("정형 항목과 표시 내용이 일치하지 않습니다.")
            for name, limit in (("label", 120), ("value", 30000)):
                if not isinstance(field[name], str) or len(field[name]) > limit:
                    raise ValueError("필드 문자열 또는 길이가 잘못되었습니다.")
            if type(field["reviewed"]) is not bool or not isinstance(
                field["evidence"], list
            ):
                raise ValueError("검수 여부와 근거 배열이 필요합니다.")
            if len(field["evidence"]) > 500:
                raise ValueError("근거 개수가 너무 많습니다.")
            for ref in field["evidence"]:
                if not isinstance(ref, dict) or set(ref) != {
                    "source_id",
                    "paragraph_index",
                    "text",
                }:
                    raise ValueError(
                        "근거는 source_id/paragraph_index/text가 필요합니다."
                    )
                if (
                    not isinstance(ref["source_id"], str)
                    or not ref["source_id"]
                    or len(ref["source_id"]) > 200
                ):
                    raise ValueError("근거 출처가 필요합니다.")
                if (
                    type(ref["paragraph_index"]) is not int
                    or ref["paragraph_index"] < 0
                ):
                    raise ValueError("근거 문단 번호가 잘못되었습니다.")
                if (
                    not isinstance(ref["text"], str)
                    or not ref["text"].strip()
                    or len(ref["text"]) > 30000
                ):
                    raise ValueError("근거 원문이 필요합니다.")
            if field["reviewed"] and field["value"].strip() and not field["evidence"]:
                raise ValueError("검수된 값에는 출처 근거가 필요합니다.")
        self._data = deepcopy(data)

    @classmethod
    def template(cls):
        return cls(
            {
                "format": FORMAT,
                "fields": [
                    {
                        "id": key,
                        "label": label,
                        "value": "",
                        "reviewed": False,
                        "evidence": [],
                    }
                    for key, label in FIELDS.items()
                ],
            }
        )

    @classmethod
    def from_package(cls, master, reviewed=False):
        package = master.get("package", master)
        values = package.get("field_values")
        if not isinstance(values, dict):
            raise ValueError("기존 마스터의 field_values가 필요합니다.")
        evidence = package.get("source_evidence", {})
        keys = list(dict.fromkeys([*values, *FIELDS]))
        return cls(
            {
                "format": FORMAT,
                "fields": [
                    {
                        "id": key,
                        "label": FIELDS.get(key, key),
                        "value": value,
                        "reviewed": reviewed if value else False,
                        "evidence": deepcopy(evidence.get(key, [])),
                    }
                    for key in keys
                    for value in [values.get(key, "")]
                ],
            }
        )

    def to_dict(self):
        return deepcopy(self._data)

    def package(self):
        values, evidence = {}, {}
        for field in self._data["fields"]:
            if "items" in field:
                validate_items(field["id"], field["items"], complete=True)
            if not field["value"].strip():
                continue
            if not field["reviewed"]:
                raise ValueError(f"미검수 항목: {field['label']}")
            values[field["id"]] = field["value"]
            evidence[field["id"]] = deepcopy(field["evidence"])
        # Existing portal adapters still consume text; records remain in the profile.
        combined = [
            values.get(key, "")
            for key in ("award_certification_description", "certifications", "awards")
        ]
        if any(combined):
            values["award_certification_description"] = "\n\n".join(
                value for value in combined if value
            )
            evidence["award_certification_description"] = [
                ref
                for key in (
                    "award_certification_description",
                    "certifications",
                    "awards",
                )
                for ref in evidence.get(key, [])
            ]
        if not values:
            raise ValueError("검수된 이력서 내용을 입력하세요.")
        return {
            "package": {
                "field_values": values,
                "source_evidence": evidence,
                "generation_method": "human_reviewed_standard_profile",
                "review_notes": ["검수는 사용자 확인이며 자동 사실 판정이 아닙니다."],
            }
        }

    def paragraphs(self):
        self.package()
        rows = []
        for field in self._data["fields"]:
            if "items" in field:
                rows.extend(
                    {
                        "field_id": field["id"],
                        "paragraph_index": index,
                        "text": render_items(field["id"], [item]),
                        "evidence_field": field["id"],
                    }
                    for index, item in enumerate(field["items"])
                    if render_items(field["id"], [item]).strip()
                )
                continue
            for index, line in enumerate(field["value"].splitlines()):
                if line.strip():
                    rows.append(
                        {
                            "field_id": field["id"],
                            "paragraph_index": index,
                            "text": line.strip(),
                            "evidence_field": field["id"],
                        }
                    )
        return rows
