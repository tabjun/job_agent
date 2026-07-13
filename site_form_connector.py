import argparse
import json
import os
import re
from datetime import datetime
from typing import Any, Dict, Iterable, List, Tuple


FIELD_KEYWORDS: Dict[str, List[str]] = {
    "name": ["이름", "성명", "name", "fullname", "full name"],
    "email": ["이메일", "email", "mail"],
    "phone": ["전화", "휴대폰", "연락처", "mobile", "phone", "tel"],
    "headline": ["헤드라인", "직무", "희망직무", "headline", "title", "position"],
    "summary": ["소개", "간단소개", "자기소개", "about", "summary", "intro", "description"],
    "experience": ["경력", "회사", "재직", "experience", "career", "company"],
    "project": ["프로젝트", "project", "portfolio"],
    "skill": ["스킬", "기술", "skill", "tech", "stack"],
    "education": ["학력", "학교", "전공", "education", "school", "major"],
    "link": ["링크", "포트폴리오", "github", "blog", "url", "website", "linkedin"],
    "cover_letter": ["자기소개서", "지원동기", "입사후", "문항", "essay", "cover"],
}


def normalize(text: Any) -> str:
    value = str(text or "").lower()
    value = re.sub(r"\s+", "", value)
    value = re.sub(r"[^0-9a-z가-힣@._+-]", "", value)
    return value


def field_haystack(field: Dict[str, Any]) -> str:
    parts: List[str] = []
    for key in [
        "tag",
        "type",
        "name",
        "id",
        "placeholder",
        "autocomplete",
        "aria_label",
        "role",
        "selector",
    ]:
        parts.append(str(field.get(key, "")))
    parts.extend(str(label) for label in field.get("labels", []))
    return normalize(" ".join(parts))


def flatten_package_values(package_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    package = package_payload.get("package", package_payload)
    if isinstance(package, str):
        try:
            package = json.loads(package)
        except json.JSONDecodeError:
            package = {"raw_package": package}

    field_values = package.get("field_values", {})
    rows: List[Dict[str, Any]] = []

    def walk(prefix: Tuple[str, ...], value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk((*prefix, str(key)), child)
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                walk((*prefix, str(idx)), child)
        else:
            text = str(value or "").strip()
            if text:
                rows.append(
                    {
                        "path": ".".join(prefix),
                        "label": prefix[-1] if prefix else "",
                        "section": prefix[0] if prefix else "",
                        "value": text,
                    }
                )

    walk((), field_values)
    return rows


def semantic_categories(text: str) -> List[str]:
    hay = normalize(text)
    cats = []
    for category, keywords in FIELD_KEYWORDS.items():
        if any(normalize(keyword) in hay for keyword in keywords):
            cats.append(category)
    return cats


def score_match(package_field: Dict[str, Any], browser_field: Dict[str, Any]) -> Tuple[int, List[str]]:
    score = 0
    reasons: List[str] = []
    browser_hay = field_haystack(browser_field)
    package_hay = normalize(" ".join([package_field["path"], package_field["label"], package_field["section"]]))

    if not browser_field.get("visible", True):
        score -= 20
        reasons.append("hidden")
    if browser_field.get("disabled") or browser_field.get("read_only"):
        score -= 30
        reasons.append("disabled_or_readonly")

    package_tokens = [token for token in re.split(r"[._\s/]+", package_field["path"]) if token]
    for token in package_tokens:
        n = normalize(token)
        if n and n in browser_hay:
            score += 25
            reasons.append(f"path_token:{token}")

    package_cats = semantic_categories(package_hay)
    browser_cats = semantic_categories(browser_hay)
    overlap = sorted(set(package_cats) & set(browser_cats))
    if overlap:
        score += 60 * len(overlap)
        reasons.append("category:" + ",".join(overlap))

    tag = browser_field.get("tag")
    value_len = len(package_field["value"])
    if value_len > 120 and tag == "textarea":
        score += 25
        reasons.append("long_text_textarea")
    if value_len <= 120 and tag == "input":
        score += 10
        reasons.append("short_text_input")

    max_length = str(browser_field.get("max_length") or "")
    if max_length.isdigit() and len(package_field["value"]) > int(max_length):
        score -= 25
        reasons.append(f"over_maxlength:{max_length}")

    return score, reasons


def candidate_fields(form_map_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    snapshot = form_map_payload.get("snapshot", form_map_payload)
    fields = snapshot.get("fields", [])
    return [
        field
        for field in fields
        if field.get("tag") in {"input", "textarea", "select"} or field.get("role")
    ]


def build_mapping(package_payload: Dict[str, Any], form_map_payload: Dict[str, Any]) -> Dict[str, Any]:
    package_fields = flatten_package_values(package_payload)
    browser_fields = candidate_fields(form_map_payload)
    mappings = []

    for package_field in package_fields:
        scored = []
        for browser_field in browser_fields:
            score, reasons = score_match(package_field, browser_field)
            if score > 0:
                scored.append((score, reasons, browser_field))
        scored.sort(key=lambda item: item[0], reverse=True)
        best = scored[0] if scored else None
        mappings.append(
            {
                "package_path": package_field["path"],
                "package_label": package_field["label"],
                "value_preview": package_field["value"][:160],
                "best_match": {
                    "score": best[0],
                    "reasons": best[1],
                    "selector": best[2].get("selector"),
                    "tag": best[2].get("tag"),
                    "type": best[2].get("type"),
                    "name": best[2].get("name"),
                    "id": best[2].get("id"),
                    "placeholder": best[2].get("placeholder"),
                    "labels": best[2].get("labels"),
                    "max_length": best[2].get("max_length"),
                    "visible": best[2].get("visible"),
                }
                if best
                else None,
                "alternatives": [
                    {
                        "score": score,
                        "selector": field.get("selector"),
                        "placeholder": field.get("placeholder"),
                        "labels": field.get("labels"),
                    }
                    for score, _reasons, field in scored[1:4]
                ],
            }
        )

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "package_site": package_payload.get("site"),
        "package_company": package_payload.get("company"),
        "form_site": form_map_payload.get("site_name"),
        "form_url": form_map_payload.get("snapshot", {}).get("url"),
        "mapping_status": "review_required",
        "mappings": mappings,
        "unmatched_count": sum(1 for item in mappings if not item["best_match"]),
        "notes": [
            "이 매핑은 selector 후보 계획이다. 실제 저장 전 브라우저 화면에서 사용자 검수가 필요하다.",
            "로그인 페이지에서 추출한 form map은 이력서 필드와 매칭되지 않을 수 있다.",
        ],
    }


def write_output(payload: Dict[str, Any], output_path: str | None) -> str:
    if not output_path:
        out_dir = os.path.join("result", "site_field_mappings")
        os.makedirs(out_dir, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        site = normalize(payload.get("form_site", "site"))
        company = normalize(payload.get("package_company", "company"))[:40] or "company"
        output_path = os.path.join(out_dir, f"{company}_{site}_{stamp}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return output_path


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser(description="사이트별 이력서 패키지와 Playwright 폼 추출 결과를 selector 매핑으로 연결")
    parser.add_argument("--package", required=True, help="result/site_resumes/*.json")
    parser.add_argument("--form-map", required=True, help="result/site_form_maps/*_playwright_*.json")
    parser.add_argument("--output", default=None, help="저장할 mapping json 경로")
    args = parser.parse_args()

    package_payload = load_json(args.package)
    form_map_payload = load_json(args.form_map)
    mapping = build_mapping(package_payload, form_map_payload)
    path = write_output(mapping, args.output)
    print(f"필드 매핑 계획 저장: {path}")
    print(f"총 매핑 후보: {len(mapping['mappings'])}, 미매칭: {mapping['unmatched_count']}")


if __name__ == "__main__":
    main()
