import asyncio
import json
import os
import re
from dataclasses import asdict, dataclass
from typing import Dict, List

from dotenv import load_dotenv
from langchain_core.tools import tool

from agent import LangGraphAgentEngine
from revise_resume import load_user_context

load_dotenv()


@dataclass(frozen=True)
class SiteProfile:
    name: str
    aliases: List[str]
    purpose: str
    sections: List[str]
    constraints: List[str]
    save_notes: List[str]


SITE_PROFILES: Dict[str, SiteProfile] = {
    "wanted": SiteProfile(
        name="Wanted",
        aliases=["wanted", "원티드"],
        purpose="간결한 경력 중심 프로필과 프로젝트 임팩트 요약",
        sections=[
            "기본 프로필",
            "간단 소개",
            "경력",
            "프로젝트",
            "스킬",
            "학력",
            "포트폴리오/링크",
        ],
        constraints=[
            "경력과 프로젝트는 성과 중심 bullet로 작성한다.",
            "직무 키워드는 스킬 섹션과 경력 bullet에 중복 없이 반영한다.",
            "근거 없는 수치와 직책을 만들지 않는다.",
        ],
        save_notes=[
            "브라우저 저장 단계에서는 로그인 상태 확인이 먼저 필요하다.",
            "간단 소개와 경력 첫 2개 bullet을 가장 먼저 검수한다.",
        ],
    ),
    "saramin": SiteProfile(
        name="Saramin",
        aliases=["saramin", "사람인"],
        purpose="정형 필드가 많은 국내 채용 사이트용 상세 이력서",
        sections=[
            "인적사항",
            "학력",
            "경력",
            "프로젝트/대외활동",
            "자격/어학",
            "보유기술",
            "자기소개서 문항",
        ],
        constraints=[
            "정형 필드에는 확인된 사실만 넣고 모르는 값은 확인 필요로 둔다.",
            "자기소개서 문항은 STAR 구조로 정리한다.",
            "개인 식별 정보는 사용자가 제공한 값만 사용한다.",
        ],
        save_notes=[
            "사이트 저장 전 필수 입력 누락 필드를 별도 체크한다.",
            "문항별 글자수 제한은 실제 공고 화면에서 확인한다.",
        ],
    ),
    "jobkorea": SiteProfile(
        name="JobKorea",
        aliases=["jobkorea", "잡코리아"],
        purpose="경력/스킬/자기소개서를 균형 있게 채우는 범용 국내 이력서",
        sections=[
            "기본정보",
            "희망근무조건",
            "학력",
            "경력",
            "수행 프로젝트",
            "보유기술",
            "자기소개서",
        ],
        constraints=[
            "희망조건은 사용자가 명시한 범위만 반영한다.",
            "경력기술서는 업무, 도구, 성과를 분리한다.",
            "기업별 JD 키워드는 자기소개서보다 경력기술서에 우선 반영한다.",
        ],
        save_notes=[
            "희망연봉, 근무지 등 민감 필드는 자동 추정하지 않는다.",
            "지원 직무별 대표 이력서 복사본으로 저장하는 흐름을 권장한다.",
        ],
    ),
    "jumpit": SiteProfile(
        name="Jumpit",
        aliases=["jumpit", "점핏"],
        purpose="개발/데이터 직무에 맞춘 기술 스택 중심 프로필",
        sections=[
            "기본 프로필",
            "직무 소개",
            "기술 스택",
            "경력",
            "프로젝트",
            "링크",
        ],
        constraints=[
            "기술 스택은 실제 사용 경험이 있는 도구만 넣는다.",
            "프로젝트 설명에는 문제, 역할, 기술, 결과를 포함한다.",
            "기술 숙련도를 과장하지 않는다.",
        ],
        save_notes=[
            "기술 스택 태그 매칭이 핵심이므로 사이트 후보 태그와 수동 대조한다.",
            "링크는 공개 가능한 포트폴리오만 사용한다.",
        ],
    ),
    "catch": SiteProfile(
        name="Catch",
        aliases=["catch", "캐치"],
        purpose="신입/주니어 채용용 직무 적합성 중심 이력서",
        sections=[
            "기본정보",
            "학력",
            "경험/활동",
            "프로젝트",
            "스킬",
            "자기소개",
        ],
        constraints=[
            "직무 적합성, 학습 역량, 협업 경험을 분명히 드러낸다.",
            "경험이 부족한 항목은 프로젝트와 학습 이력으로 보완한다.",
            "없는 인턴/실무 경험을 만들지 않는다.",
        ],
        save_notes=[
            "신입 채용에서는 자기소개 문항별 톤을 별도 검수한다.",
            "공고별 요구 역량을 프로젝트 bullet에 연결한다.",
        ],
    ),
    "linkedin": SiteProfile(
        name="LinkedIn",
        aliases=["linkedin", "링크드인"],
        purpose="영문/글로벌 프로필과 공개 경력 브랜딩",
        sections=[
            "Headline",
            "About",
            "Experience",
            "Projects",
            "Skills",
            "Education",
            "Links",
        ],
        constraints=[
            "영문 표현은 간결하고 검증 가능한 경력 중심으로 작성한다.",
            "국문 이력의 의미를 바꾸지 않고 번역한다.",
            "공개 프로필에 민감한 개인정보를 넣지 않는다.",
        ],
        save_notes=[
            "공개 노출 범위를 사용자가 직접 확인한다.",
            "About 섹션은 3~5문단 이하로 유지한다.",
        ],
    ),
}


def normalize_site_name(site_name: str) -> str:
    site = site_name.strip().lower()
    for key, profile in SITE_PROFILES.items():
        if site == key or site in [alias.lower() for alias in profile.aliases]:
            return key
    return site


def slugify(value: str) -> str:
    value = re.sub(r"[^\w가-힣.-]+", "_", value.strip(), flags=re.UNICODE)
    return value.strip("_") or "resume"


def profile_markdown(profile: SiteProfile) -> str:
    return "\n".join(
        [
            f"### {profile.name}",
            f"- 목적: {profile.purpose}",
            f"- 섹션: {', '.join(profile.sections)}",
            f"- 제약: {' / '.join(profile.constraints)}",
            f"- 저장 주의: {' / '.join(profile.save_notes)}",
        ]
    )


@tool
async def list_supported_resume_sites() -> str:
    """지원하는 채용 사이트별 이력서 양식 프로필을 요약합니다."""
    return "\n\n".join(profile_markdown(profile) for profile in SITE_PROFILES.values())


@tool
async def get_resume_site_profile(site_name: str) -> str:
    """특정 채용 사이트의 이력서 양식 프로필을 반환합니다."""
    key = normalize_site_name(site_name)
    if key not in SITE_PROFILES:
        return (
            f"'{site_name}' 사이트 프로필이 아직 없습니다. "
            "지원 사이트 목록을 확인하고, 모르면 generic 형식으로 작성하세요."
        )
    return json.dumps(asdict(SITE_PROFILES[key]), ensure_ascii=False, indent=2)


@tool
async def save_site_resume_package(
    site_name: str,
    company_name: str,
    package_json: str,
    review_notes: str,
) -> str:
    """
    사이트별 이력서 입력 패키지를 JSON과 Markdown으로 저장합니다.
    package_json은 사이트 섹션별 입력값을 담은 JSON 문자열이어야 합니다.
    """
    key = normalize_site_name(site_name)
    site_label = SITE_PROFILES[key].name if key in SITE_PROFILES else site_name
    company_slug = slugify(company_name)
    site_slug = slugify(key)

    output_dir = os.path.join("result", "site_resumes")
    os.makedirs(output_dir, exist_ok=True)
    base_path = os.path.join(output_dir, f"{company_slug}_{site_slug}")
    json_path = f"{base_path}.json"
    md_path = f"{base_path}.md"

    try:
        parsed = json.loads(package_json)
    except json.JSONDecodeError:
        parsed = {
            "raw_package": package_json,
            "parse_warning": "package_json was not valid JSON. Stored raw content.",
        }

    payload = {
        "site": site_label,
        "company": company_name,
        "package": parsed,
        "review_notes": review_notes,
        "automation_status": "draft_only_no_browser_save",
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {company_name} - {site_label} 이력서 입력 패키지\n\n")
        f.write("## 자동 저장 상태\n\n")
        f.write("- 현재 단계: 사이트 입력용 초안 생성\n")
        f.write("- 실제 사이트 저장: 로그인/화면 확인 후 별도 브라우저 자동화 단계에서 수행\n\n")
        f.write("## 입력 패키지\n\n")
        f.write("```json\n")
        f.write(json.dumps(parsed, ensure_ascii=False, indent=2))
        f.write("\n```\n\n")
        f.write("## 검수 메모\n\n")
        f.write(review_notes.strip() + "\n")

    return f"사이트별 이력서 패키지 저장 완료: {json_path}, {md_path}"


SITE_RESUME_PROMPT = """
당신은 채용 사이트별 이력서 양식에 맞춰 사용자의 실제 이력 정보를 정리하는 Resume Form Agent입니다.

[사용자 사실 데이터]
{user_context}

[핵심 임무]
1. 사용자가 지정한 채용 사이트의 양식 프로필을 확인한다.
2. 사용자의 실제 이력과 JD를 바탕으로 사이트 입력 필드별 값을 만든다.
3. 확인되지 않은 값은 추정하지 말고 "확인 필요"로 둔다.
4. 최종 결과는 반드시 `save_site_resume_package` 도구로 저장한다.

[중요한 제한]
- 실제 채용 사이트에 로그인하거나 저장 버튼을 누르지 않는다.
- 개인정보, 연락처, 희망연봉, 주소 등 민감 필드는 사용자가 명시한 경우에만 채운다.
- `knowledge/` 또는 사용자가 제공한 내용에 없는 경력, 수치, 자격증, 프로젝트를 만들지 않는다.
- 사이트별 글자수 제한이 불명확하면 보수적으로 짧게 작성하고, 검수 메모에 "실제 화면에서 제한 확인 필요"를 남긴다.

[저장 패키지 JSON 권장 구조]
{
  "site_profile_used": "사이트명",
  "target_company": "기업명",
  "target_role": "직무명 또는 확인 필요",
  "field_values": {
    "섹션명": {
      "필드명": "입력값"
    }
  },
  "jd_alignment": [
    {
      "jd_requirement": "JD 요구사항",
      "resume_evidence": "사용자 이력 근거",
      "field_to_update": "반영할 사이트 필드"
    }
  ],
  "missing_information": ["사용자 확인이 필요한 항목"],
  "manual_save_checklist": ["사이트에서 수동 또는 자동 저장 전에 확인할 항목"]
}
"""


async def run_site_resume_agent():
    user_context = load_user_context()

    print("\n" + "=" * 60)
    print(" 🧾 채용 사이트별 이력서 입력 패키지 에이전트")
    print("=" * 60)
    print("지원 사이트 예: wanted, saramin, jobkorea, jumpit, catch, linkedin")

    site_name = input("1. 저장할 채용 사이트: ").strip()
    company_name = input("2. 지원 기업명: ").strip()
    role_name = input("3. 지원 직무명 (모르면 빈칸): ").strip() or "확인 필요"

    print("\n4. 채용 공고(JD) 또는 사이트 문항을 붙여넣어 주세요. 빈 줄 두 번이면 종료:")
    jd_lines = []
    while True:
        try:
            line = input()
            if line == "" and jd_lines and jd_lines[-1] == "":
                break
            jd_lines.append(line)
        except EOFError:
            break
    jd_content = "\n".join(jd_lines).strip() or "제공된 JD 없음"

    print("\n5. 추가 지시사항 (예: 특정 문항 우선, 공개 프로필용, 경력기술서 짧게):")
    extra_instructions = input("> ").strip() or "추가 지시사항 없음"

    print("\n" + "-" * 60)
    model_choice = input("어떤 AI 모델을 사용할까요? (1: Gemini, 2: GPT-5-mini): ").strip()
    use_model = "gpt" if model_choice == "2" else "gemini"
    print("-" * 60)

    agent = LangGraphAgentEngine(
        use_model=use_model,
        tools=[
            list_supported_resume_sites,
            get_resume_site_profile,
            save_site_resume_package,
        ],
        system_prompt=SITE_RESUME_PROMPT.format(user_context=user_context),
    )

    user_request = f"""
채용 사이트: {site_name}
지원 기업: {company_name}
지원 직무: {role_name}

[JD/사이트 문항]
{jd_content}

[추가 지시사항]
{extra_instructions}

위 정보를 바탕으로 해당 채용 사이트 양식에 맞춘 이력서 입력 패키지를 만들어 저장해줘.
먼저 사이트 프로필을 확인하고, 확인되지 않은 사실은 반드시 "확인 필요"로 남겨.
"""

    async for event in agent.run(user_request):
        for node_name, content in event.items():
            for msg in content.get("messages", []):
                if msg.content:
                    print(f"\n[{node_name}] {msg.content[:800]}{'...' if len(msg.content) > 800 else ''}")


if __name__ == "__main__":
    asyncio.run(run_site_resume_agent())
