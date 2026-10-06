import asyncio
import json
import re
from dataclasses import asdict

from job_agent.core.paths import ProjectPaths, load_environment
from langchain_core.tools import tool

from job_agent.core.engine import LangGraphAgentEngine
from job_agent.documents.context import UserContextLoader
from job_agent.core.storage import ArtifactStore
from job_agent.sites.profiles import SiteProfile, SITE_PROFILES, normalize_site_name

load_environment()


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

    store = ArtifactStore(ProjectPaths().results / "site_resumes")
    base_name = f"{company_slug}_{site_slug}"

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

    json_path = store.write_json(f"{base_name}.json", payload)
    md_path = store.write_text(
        f"{base_name}.md",
        "".join(
            [
                f"# {company_name} - {site_label} 이력서 입력 패키지\n\n",
                "## 자동 저장 상태\n\n",
                "- 현재 단계: 사이트 입력용 초안 생성\n",
                "- 실제 사이트 저장: 로그인/화면 확인 후 별도 브라우저 자동화 단계에서 수행\n\n",
                "## 입력 패키지\n\n",
                "```json\n",
                json.dumps(parsed, ensure_ascii=False, indent=2),
                "\n```\n\n",
                "## 검수 메모\n\n",
                review_notes.strip() + "\n",
            ]
        ),
    )

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
    user_context = UserContextLoader().load()

    print("\n" + "=" * 60)
    print(" 🧾 채용 사이트별 이력서 입력 패키지 에이전트")
    print("=" * 60)
    print("우선 대상: catch, jobkorea, saramin, wanted, incruit")

    site_name = input("1. 저장할 채용 사이트: ").strip()
    company_name = input("2. 지원 기업명: ").strip()
    role_name = input("3. 지원 직무명 (모르면 빈칸): ").strip() or "확인 필요"

    print(
        "\n4. 채용 공고(JD) 또는 사이트 문항을 붙여넣어 주세요. 빈 줄 두 번이면 종료:"
    )
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
    model_choice = input(
        "어떤 AI 모델을 사용할까요? (1: Gemini, 2: OpenAI / 기본 GPT-6 Luna): "
    ).strip()
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
                if msg.text:
                    print(
                        f"\n[{node_name}] {msg.text[:800]}{'...' if len(msg.text) > 800 else ''}"
                    )


if __name__ == "__main__":
    asyncio.run(run_site_resume_agent())
