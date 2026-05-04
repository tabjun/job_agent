import asyncio
import os
import glob
from typing import List, Dict, Any
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from agent import LangGraphAgentEngine
from dotenv import load_dotenv

# .env 로드
load_dotenv()

# =====================================================================
# [0. 사용자 로컬 데이터 로드 함수]
# =====================================================================
def load_user_context() -> str:
    """knowledge, more_info, self_introduction 폴더의 텍스트를 읽어옵니다."""
    context = ""
    
    # 1. 이력서 읽기
    context += "=== [내 이력서 (knowledge)] ===\n"
    for file in glob.glob("knowledge/*.txt"):
        with open(file, "r", encoding="utf-8") as f:
            context += f.read() + "\n\n"
            
    # 2. 자기소개서 작성 가이드 및 방향성 읽기
    context += "=== [자소서 작성 가이드라인 (more_info)] ===\n"
    for file in glob.glob("more_info/*.txt"):
        with open(file, "r", encoding="utf-8") as f:
            context += f.read() + "\n\n"

    # 3. 기존 자소서 샘플 읽기 (pdf, hwp 확장은 추후 패키지 추가 시 연동)
    context += "=== [기존 작성 자소서 샘플 (self_introduction)] ===\n"
    for file in glob.glob("self_introduction/*.txt"):
        with open(file, "r", encoding="utf-8") as f:
            context += f.read() + "\n\n"
            
    return context

# =====================================================================
# [1. 도구 정의 (재무, 평판, 검색, 저장)]
# =====================================================================

@tool
async def get_financial_health(company_name: str):
    """기업의 재무 건전성(매출, 영업이익 등)을 분석합니다."""
    api_key = os.getenv("DART_API_KEY") or os.getenv("OPENADART_API_KEY")
    if not api_key: return "DART API 키 미설정"
    
    print(f"  [Financial] '{company_name}' 재무 분석 중...")
    search = TavilySearch(max_results=5)
    query = f"{company_name} 매출액 영업이익 최근 3년 재무제표 DART"
    try:
        results = await search.ainvoke(query)
        return {"company": company_name, "financial_summary": results[0].get('content') if results else "정보 없음"}
    except Exception as e: return f"재무 조회 실패: {e}"

@tool
async def search_jobs(role: str, experience: str, location: str, pref: str):
    """상세 조건에 맞는 채용 공고를 검색합니다."""
    print(f"  [Recruiter] {location} 지역 {role}({experience}) 공고 검색 중...")
    search = TavilySearch(max_results=30)
    query = f"{location} {role} {experience} 채용 {pref} (site:saramin.co.kr OR site:wanted.co.kr OR site:jumpit.co.kr)"
    results = await search.ainvoke(query)
    return results

@tool
async def get_company_reputation(company_name: str):
    """현직자 평판 및 조직 문화를 분석합니다."""
    search = TavilySearch(max_results=5)
    query = f"site:jobplanet.co.kr OR site:teamblind.com \"{company_name}\" 리뷰 평점 장단점"
    try:
        results = await search.ainvoke(query)
        return {"company": company_name, "reputation": [r.get('content') for r in results]}
    except Exception as e: return f"평판 조회 에러: {e}"

@tool
async def save_cover_letter(cover_letter_content: str, company_name: str):
    """생성된 맞춤형 자기소개서를 파일로 저장합니다."""
    print(f"  [Write] '{company_name}' 맞춤형 자소서 저장 중...")
    os.makedirs("result", exist_ok=True)
    file_path = f"result/{company_name}_cover_letter.md"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(cover_letter_content)
    return f"자소서 저장 완료: {file_path}"

@tool
async def save_final_guide(guide_content: str, company_name: str):
    """최종 분석 리포트 저장."""
    os.makedirs("result", exist_ok=True)
    file_path = f"result/{company_name}_final_guide.md"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(guide_content)
    return f"가이드 저장 완료: {file_path}"

# =====================================================================
# [2. 전문가 페르소나 설정]
# =====================================================================
COACH_PROMPT = """
당신은 '대한민국 최고의 IT 채용 헤드헌터이자 전문 커리어 코치'입니다. 
사용자가 제공한 [상세 조건]과 [나의 기본 정보(이력서, 가이드라인)]를 활용하여 다음 6단계 파이프라인을 엄격히 수행하세요.

[상세 조건]:
- 희망 직군: {role}
- 경력 사항: {experience}
- 희망 지역: {location}
- 추가 선호: {preference}

[나의 기본 정보 및 자소서 가이드라인]:
{user_context}

---
[업무 프로세스 6단계]
1. [공고 검색]: 위 조건에 맞는 공고를 `search_jobs`로 최대한 수집하세요.
2. [최종 1픽 선정]: 수집된 공고와 [나의 기본 정보]를 매칭하여 가장 적합한 단 하나의 기업을 선정하세요.
3. [기업 분석]: 선정된 기업에 대해 `get_financial_health`(재무) 및 `get_company_reputation`(평판)을 심층 분석합니다.
4. [맞춤형 자기소개서 작성]: 
   - **경고 (Hallucination 방지)**: 절대 이력서에 없는 경험(스킬, 프로젝트 등)을 꾸며내지 마세요!
   - [나의 기본 정보]에 포함된 이력 및 [자소서 작성 가이드라인(more_info)]을 정확히 반영하여 해당 기업의 JD에 맞춘 자기소개서를 작성하세요.
   - 단순한 기업 찬양("AI DX 비전에 감명받았다" 등)을 배제하고, 사용자의 진짜 커리어 지향점(예: '인사이트 도출의 즐거움')을 기업의 니즈와 연결하세요.
   - 작성된 자소서는 `save_cover_letter` 도구를 사용해 저장하세요.
5. [면접 준비 가이드 작성]: 기업 분석 데이터와 내 이력서를 바탕으로 면접 예상 질문과 답변 전략을 담은 최종 가이드를 작성하여 `save_final_guide`로 저장하세요.
6. [종료]: 사용자에게 모든 작업이 완료되었음을 보고하세요.
"""

async def run_consulting():
    # 1. 파일 시스템에서 사용자 데이터 로드
    user_context = load_user_context()
    
    # 2. 사용자로부터 상세 조건 입력 받기
    print("\n" + "="*60)
    print(" 🎯 커리어 에이전트 맞춤형 조건 입력 (Local DB 연동)")
    print("="*60)
    role = input("1. 찾는 직군 (예: 데이터 분석가): ")
    experience = input("2. 경력 (예: 신입, 3년차 이하): ")
    location = input("3. 희망 지역 (예: 서울/경기): ")
    preference = input("4. 기타 선호 (예: 중견 이상, 매출 100억 이상): ")
    
    # 3. 모델 선택 질문
    print("\n" + "-"*60)
    model_choice = input("어떤 AI 모델을 사용할까요? (1: Gemini(무료), 2: GPT-5-mini(유료)): ")
    use_model = "gpt" if model_choice == "2" else "gemini"
    print("-"*60)

    # 4. 프롬프트에 입력값 및 컨텍스트 주입
    final_prompt = COACH_PROMPT.format(
        role=role, 
        experience=experience, 
        location=location, 
        preference=preference,
        user_context=user_context
    )

    # 5. 에이전트 엔진 초기화
    agent = LangGraphAgentEngine(
        use_model=use_model,
        tools=[search_jobs, get_financial_health, get_company_reputation, save_cover_letter, save_final_guide],
        system_prompt=final_prompt
    )
    
    user_request = f"내 이력서(Knowledge)와 가이드라인(more_info)을 바탕으로 가장 적합한 기업을 찾고, 거짓말 없는 진짜 내 맞춤형 자소서와 면접 가이드를 작성해줘."
    
    print(f"\n[분석 시작...]\n" + "-"*60)

    async for event in agent.run(user_request):
        for node_name, content in event.items():
            for msg in content.get("messages", []):
                if msg.content:
                    print(f"\n>>> {msg.content[:800]}...")

if __name__ == "__main__":
    asyncio.run(run_consulting())
