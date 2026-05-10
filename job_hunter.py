import asyncio
import os
import glob
import json
import aiohttp
from typing import List, Dict, Any
from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from agent import LangGraphAgentEngine
from dotenv import load_dotenv

# .env 로드
load_dotenv()

# =====================================================================
# [1. 도구 정의 (재무, 평판, 검색, 저장)]
# =====================================================================

@tool
async def get_financial_health(company_name: str):
    """기업의 재무 건전성(매출, 영업이익 등)을 분석합니다. DART 및 뉴스를 검색합니다."""
    print(f"  [Financial] '{company_name}' 재무 분석 중...")
    search = TavilySearchResults(max_results=5)
    # 쿼리를 구체화하여 재무 데이터를 더 잘 가져오도록 수정
    query = f"{company_name} 최근 3년 매출액 영업이익 당기순이익 DART 공시 리포트"
    try:
        results = await search.ainvoke(query)
        return {"company": company_name, "financial_summary": [r.get('content') for r in results] if results else "정보 없음"}
    except Exception as e: 
        print(f"    >> 재무 조회 에러: {e}")
        return f"재무 조회 실패: {e}"

@tool
async def search_jobs(role: str, experience: str, location: str, keywords: str):
    """
    데이터 분석/사이언티스트 직무 위주로 공고를 검색하며, 라벨링 등 단순 업무는 제외합니다.
    """
    # 사용자가 DA/DS로 고정하길 원함
    fixed_role = "데이터 분석가 OR 데이터 사이언티스트 OR Data Analyst OR Data Scientist"
    exclude_keywords = "-머신러닝 엔지니어 -LLM 개발자 -라벨링 -수집알바 -단순입력 -labeling"
    
    print(f"  [Recruiter] '{keywords}' 기반 전문 직무 공고 검색 중...")
    search = TavilySearchResults(max_results=50) # 결과 수 대폭 증가
    
    sites = "site:saramin.co.kr OR site:wanted.co.kr OR site:catch.co.kr OR site:jobplanet.co.kr OR site:jumpit.co.kr OR site:linkedin.com OR site:rememberapp.co.kr"
    query = f"({fixed_role}) {experience} {location} {keywords} {exclude_keywords} 채용공고 ({sites})"
    
    try:
        results = await search.ainvoke(query)
        return results
    except Exception as e:
        print(f"    >> 공고 검색 에러: {e}")
        return f"검색 중 오류 발생: {e}"

@tool
async def get_company_reputation(company_name: str):
    """잡플래닛 평점 및 리뷰 요약을 가져옵니다."""
    print(f"  [Reputation] '{company_name}' 평판 분석 중...")
    
    # 잡플래닛 내부 검색 JSON API 형태를 모사하거나, 검색 엔진을 통해 직접 평점 추출 시도
    search = TavilySearchResults(max_results=5)
    # 평점을 직접 찾기 위한 구체적 쿼리
    query = f"site:jobplanet.co.kr \"{company_name}\" 평점 별점 장점 단점"
    
    try:
        results = await search.ainvoke(query)
        reputation_data = []
        for r in results:
            content = r.get('content', '')
            # 평점(예: 3.5) 같은 패턴이 있는지 확인 가능 (LLM이 나중에 처리)
            reputation_data.append(content)
        
        return {"company": company_name, "reputation": reputation_data}
    except Exception as e:
        print(f"    >> 평판 조회 에러: {e}")
        return f"평판 조회 에러: {e}"

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
당신은 '데이터 전문 커리어 헤드헌터'입니다. 
당신의 임무는 사용자가 원하는 **데이터 분석가(DA) 및 데이터 사이언티스트(DS)** 직무의 공고를 완벽하게 찾아내어 리포트를 만드는 것입니다.

[필수 지침]:
1. **직무 고정**: 반드시 '데이터 분석', '데이터 사이언티스트', '머신러닝 엔지니어' 등 전문 데이터 직무에만 집중하세요.
2. **필터링**: 유사해서 헷갈릴 수 있지만 머신러닝 엔지니어 직무, LLM 개발 직무 제외하고, 단순 데이터 라벨링, 데이터 수집 알바, AI 학습 데이터 구축 등 단순 반복 업무는 **반드시 제외**하세요.
3. **도구 활용**: `search_jobs`로 공고를 찾은 뒤, 리스트업된 기업들에 대해 `get_financial_health`와 `get_company_reputation`을 사용하여 내실을 확인하세요.
4. **리포트 품질 및 구조 (엄격 준수)**:
   - 다음 표 형식을 반드시 유지하세요:
     | 기업 이름 | 공고 내용 (직무/요건 요약) | 재무 요약 (DART 등) | 평판 상세 (잡플래닛 등) | 링크/기타 |
   - **재무 요약**: 최근 매출액, 영업이익 등 구체적 수치를 포함하세요.
   - **평판 상세**: 
     * **총점**: (예: 3.5/5.0)
     * **장점**: 핵심 장점 요약
     * **단점**: 핵심 단점 요약
     * **총평**: 전반적인 근무 환경 및 분위기 요약
   - 도구 에러가 발생하더라도 검색 결과를 바탕으로 최대한 정보를 찾아 기재하세요.

[상세 조건]:
- 경력 사항: {experience}
- 희망 지역: {location}
- 추가 키워드: {keywords}
"""

async def run_job_hunter():
    print("\n" + "="*60)
    print(" 🔍 전문 데이터 직무 헌터 (DA/DS 전용)")
    print("="*60)
    # 직군은 DA/DS로 고정하므로 질문 생략 가능하지만 사용자 경험 위해 유지 가능
    role = "데이터 분석가 / 데이터 사이언티스트" 
    experience = input("1. 경력 (예: 신입, 3년차 이하): ")
    location = input("2. 희망 지역 (예: 서울/경기): ")
    keywords = input("3. 핵심 기술 키워드 (예: Python, Tableau, PyTorch): ")
    
    print("\n" + "-"*60)
    model_choice = input("어떤 AI 모델을 사용할까요? (1: Gemini(무료), 2: GPT-5-mini(유료)): ")
    use_model = "gpt" if model_choice == "2" else "gemini"
    print("-"*60)

    final_prompt = HUNTER_PROMPT.format(
        experience=experience, 
        location=location, 
        keywords=keywords
    )

    agent = LangGraphAgentEngine(
        use_model=use_model,
        tools=[search_jobs, get_financial_health, get_company_reputation, save_job_search_report],
        system_prompt=final_prompt
    )
    
    user_request = f"'{location}' 지역의 '{experience}' 수준 '{keywords}' 관련 DA/DS 공고를 모두 찾아보고, 라벨링 알바는 제외해서 리포트 써줘."
    
    print(f"\n[전문 데이터 공고 분석 시작...]\n" + "-"*60)

    async for event in agent.run(user_request):
        for node_name, content in event.items():
            for msg in content.get("messages", []):
                if msg.content:
                    content_str = msg.content
                    if len(content_str) > 1000:
                        content_str = content_str[:1000] + "..."
                    print(f"\n>>> {content_str}")

if __name__ == "__main__":
    asyncio.run(run_job_hunter())
