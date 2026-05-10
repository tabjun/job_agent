import asyncio
import os
import glob
import json
from typing import List, Dict, Any
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from agent import LangGraphAgentEngine
from dotenv import load_dotenv

# .env 로드
load_dotenv()

# =====================================================================
# [1. 도구 정의 (재무, 평판, 검색, 저장)]
# =====================================================================

@tool
async def get_financial_health(company_name: str):
    """기업의 재무 건전성(매출, 영업이익 등)을 분석합니다. 다트(DART) 정보를 우선 탐색합니다."""
    api_key = os.getenv("DART_API_KEY") or os.getenv("OPENADART_API_KEY")
    # 실제 DART API 연동 로직이 있으면 좋지만, 여기선 Tavily를 활용한 검색 기반 분석 수행
    print(f"  [Financial] '{company_name}' 재무 분석 중...")
    search = TavilySearch(max_results=5)
    query = f"{company_name} 매출액 영업이익 최근 3년 재무제표 DART 공시"
    try:
        results = await search.ainvoke(query)
        return {"company": company_name, "financial_summary": results[0].get('content') if results else "정보 없음"}
    except Exception as e: return f"재무 조회 실패: {e}"

@tool
async def search_jobs(role: str, experience: str, location: str, keywords: str):
    """
    다양한 채용 사이트(사람인, 원티드, 캐치, 잡플래닛, 인디스워크, 링크드인 등)에서 공고를 검색합니다.
    """
    print(f"  [Recruiter] '{keywords}' 기반 공고 광범위 검색 중...")
    search = TavilySearch(max_results=40)
    # 여러 사이트를 포함한 쿼리 구성
    sites = "site:saramin.co.kr OR site:wanted.co.kr OR site:catch.co.kr OR site:jobplanet.co.kr OR site:jumpit.co.kr OR site:linkedin.com OR site:rememberapp.co.kr"
    query = f"{role} {experience} {location} {keywords} 채용 ({sites})"
    results = await search.ainvoke(query)
    return results

@tool
async def get_company_reputation(company_name: str):
    """잡플래닛, 블라인드 등에서 기업의 평점과 리뷰 총평을 분석합니다."""
    print(f"  [Reputation] '{company_name}' 평판 및 리뷰 분석 중...")
    search = TavilySearch(max_results=5)
    query = f"site:jobplanet.co.kr OR site:teamblind.com \"{company_name}\" 리뷰 평점 장단점 총평"
    try:
        results = await search.ainvoke(query)
        return {"company": company_name, "reputation": [r.get('content') for r in results]}
    except Exception as e: return f"평판 조회 에러: {e}"

@tool
async def save_job_search_report(report_content: str, filename: str = "job_search_results.md"):
    """검색 및 분석된 모든 공고 리스트를 마크다운 형식의 리포트로 저장합니다."""
    os.makedirs("result", exist_ok=True)
    file_path = f"result/{filename}"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    return f"채용 공고 리포트 저장 완료: {file_path}"

# =====================================================================
# [2. 전문가 페르소나 설정]
# =====================================================================
HUNTER_PROMPT = """
당신은 '대한민국 최고의 채용 데이터 분석가이자 전략 헤드헌터'입니다.
사용자가 제공한 조건을 바탕으로 모든 채용 플랫폼을 샅샅이 뒤져 최적의 공고 리스트를 생성하는 것이 당신의 목표입니다.

[상세 조건]:
- 희망 직군: {role}
- 경력 사항: {experience}
- 희망 지역: {location}
- 추가 키워드: {keywords}

---
[업무 프로세스]
1. [광범위 공고 검색]: `search_jobs`를 사용하여 제시된 조건과 관련된 모든 공고를 최대한 수집하세요.
2. [공고 선별 및 상세 분석]: 수집된 공고 중 사용자의 조건에 부합하는 기업들을 리스트업하고, 주요 기업들에 대해 `get_financial_health`(재무) 및 `get_company_reputation`(평판)을 수행하세요.
3. [종합 리포트 생성]: 다음 형식을 포함하는 마크다운 표 형태의 리포트를 작성하세요.
   - | 기업 이름 | 공고 내용 (직무, 주요 업무, 자격 요건 등 상세히) | 재무/평판 요약 | 링크/기타 정보 |
   - 각 기업의 '공고 내용'은 사용자가 판단하기 좋게 구체적으로 요약하세요.
   - '재무/평판 요약'은 잡플래닛 평점과 DART 재무 요약을 포함해야 합니다.
4. [저장]: 생성된 리포트를 `save_job_search_report` 도구를 사용해 저장하세요.
5. [완료 보고]: 저장된 파일명과 함께 요약된 결과를 사용자에게 보고하세요.

**주의 사항**:
- 절대 허구의 공고를 만들어내지 마세요. 검색 결과에 기반해야 합니다.
- 최대한 많은 유효 공고를 찾아내어 리스트에 포함시키세요.
- 한 기업에만 집중하지 말고, 조건에 맞는 '모든' 공고를 다루려고 노력하세요.
"""

async def run_job_hunter():
    print("\n" + "="*60)
    print(" 🔍 스마트 채용 공고 헌터 (전체 사이트 통합 검색)")
    print("="*60)
    role = input("1. 찾는 직군 (예: 데이터 분석가): ")
    experience = input("2. 경력 (예: 신입, 3년차 이하): ")
    location = input("3. 희망 지역 (예: 서울/경기): ")
    keywords = input("4. 검색 키워드 (예: 파이썬, SQL, AI): ")
    
    print("\n" + "-"*60)
    model_choice = input("어떤 AI 모델을 사용할까요? (1: Gemini(무료), 2: GPT-5-mini(유료)): ")
    use_model = "gpt" if model_choice == "2" else "gemini"
    print("-"*60)

    final_prompt = HUNTER_PROMPT.format(
        role=role, 
        experience=experience, 
        location=location, 
        keywords=keywords
    )

    agent = LangGraphAgentEngine(
        use_model=use_model,
        tools=[search_jobs, get_financial_health, get_company_reputation, save_job_search_report],
        system_prompt=final_prompt
    )
    
    user_request = f"모든 채용 사이트에서 '{keywords}' 관련 공고를 다 찾아보고, 재무/평판까지 분석해서 표 형식으로 정리해줘."
    
    print(f"\n[공고 수집 및 분석 시작...]\n" + "-"*60)

    async for event in agent.run(user_request):
        for node_name, content in event.items():
            for msg in content.get("messages", []):
                if msg.content:
                    # 너무 길면 잘라서 출력
                    content_str = msg.content
                    if len(content_str) > 1000:
                        content_str = content_str[:1000] + "..."
                    print(f"\n>>> {content_str}")

if __name__ == "__main__":
    asyncio.run(run_job_hunter())
