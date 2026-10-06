"""Site-specific writing contracts, independent of LLM and browser clients."""

from dataclasses import dataclass
from typing import Dict, List


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
    "incruit": SiteProfile(
        name="Incruit",
        aliases=["incruit", "인크루트"],
        purpose="국내 채용용 상세 이력서 입력 패키지",
        sections=["기본정보", "학력", "경력", "보유기술", "자격/어학", "자기소개서"],
        constraints=[
            "확인된 경력과 학력만 사용한다.",
            "실제 편집 화면 조사 전 필수 항목과 글자수 제한을 단정하지 않는다.",
        ],
        save_notes=[
            "로그인 후 기존 이력서 편집 화면을 확인한다.",
            "저장과 제출은 사용자가 검수 후 처리한다.",
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
