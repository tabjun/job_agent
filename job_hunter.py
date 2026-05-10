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
    데이터 분석/사이언티스트 직무 위주로 현재 채용 중인 공고를 검색합니다.
    - 라벨링, 단순 입력 등 단순 반복 업무는 자동으로 제외 쿼리가 포함됩니다.
    - 검색 결과에서 공고의 신선도(마감 여부)와 경력 요건을 1차적으로 확인합니다.
    """
    fixed_role = "데이터 분석가 OR 데이터 사이언티스트 OR Data Analyst OR Data Scientist"
    exclude_keywords = "-라벨링 -수집알바 -단순입력 -labeling -마감 -종료 -지원마감"
    # 현재 날짜 기준 (2026-05-11 기준)
    current_date_info = "2026년 5월 채용공고"

    print(f"  [Recruiter] '{keywords}' 기반 '{experience}' 공고 검색 중...")
    search = TavilySearchResults(max_results=20)

    # 더 정확한 필터링을 위한 쿼리 고도화
    queries = [
        f"(\"{fixed_role}\") {experience} {location} {keywords} {exclude_keywords} {current_date_info} site:wanted.co.kr OR site:rememberapp.co.kr",
        f"(\"{fixed_role}\") {experience} {location} {keywords} {exclude_keywords} {current_date_info} site:saramin.co.kr OR site:jobkorea.co.kr",
        f"(\"{fixed_role}\") {experience} {location} {keywords} {exclude_keywords} {current_date_info} site:jumpit.co.kr OR site:catch.co.kr"
    ]

    all_results = []
    for q in queries:
        try:
            res = await search.ainvoke(q)
            if isinstance(res, list):
                all_results.extend(res)
        except Exception as e:
            print(f"    >> 검색 쿼리 에러: {e}")

    # URL 중복 제거 및 검색 결과 품질 향상
    unique_results = {}
    for r in all_results:
        url = r.get('url')
        if url and url not in unique_results:
            # 제목이나 내용에 '마감', '종료'가 있으면 1차 제외
            content = r.get('content', '').lower()
            if any(term in content for term in ['마감', '종료', '채용 완료', 'expired']):
                continue
            unique_results[url] = r
            
    return list(unique_results.values())


@tool
async def get_company_reputation(company_name: str):
    """잡플래닛 평점 및 리뷰 요약을 가져옵니다."""
    print(f"  [Reputation] '{company_name}' 평판 분석 중...")
    
    search = TavilySearchResults(max_results=5)
    query = f"site:jobplanet.co.kr \"{company_name}\" 평점 별점 장점 단점 후기"
    
    try:
        results = await search.ainvoke(query)
        return {"company": company_name, "reputation": [r.get('content') for r in results] if results else "정보 없음"}
    except Exception as e:
        print(f"    >> 평판 조회 에러: {e}")
        return f"평판 조회 에러: {e}"

@tool
async def save_job_search_report(report_content: str, filename: str = "job_search_results.md"):
    """검색 및 분석된 모든 공고 리스트를 마크다운 형식의 리포트로 저장합니다."""
    os.makedirs("result", exist_ok=True)
    file_path = f"result/{filename}"
    # 리포트 헤더 보강
    header = f"# 🔍 데이터 직무 채용 분석 리포트\n- 생성 일시: 2026-05-11\n\n"
    full_content = header + report_content
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(full_content)
    print(f"  >> [System] 리포트가 {file_path}에 저장되었습니다.")
    return f"채용 공고 리포트 저장 완료: {file_path}"

# =====================================================================
# [2. 전문가 페르소나 설정]
# =====================================================================
HUNTER_PROMPT = """
당신은 '데이터 전문 커리어 헤드헌터'입니다. 
당신의 임무는 사용자가 원하는 **데이터 분석가(DA) 및 데이터 사이언티스트(DS)** 직무의 공고를 완벽하게 찾아내어 리포트를 만드는 것입니다.

[필수 지침 - 토큰 낭비 방지 및 정확도 향상]:
1. **엄격한 1차 스크리닝 (매우 중요)**:
   - `search_jobs` 결과 중 사용자 조건({experience}, {location}, {keywords})에 **완벽히 부합**하는 공고만 최대 5~7개 선별하세요.
   - **경력 검증**: 사용자가 '3년 이하'를 원하는데 공고가 '5년 이상'이나 '시니어'를 요구하면 **무조건 제외**하세요. (예: CJ Olive Young 등 대형 공고라도 요건 불일치 시 과감히 삭제)
   - **직무 검증**: 단순히 기업 이름에 '데이터'가 들어가는 것이 아니라, 실제 '데이터 분석/사이언스' 업무인지 확인하세요. 오늘의집 등 특정 시점에 해당 직무를 뽑지 않는 기업은 검색 결과에서 제외하거나 검증하세요.
   - **최신성**: 공고 내용에 '마감', '종료'가 언급된 경우 즉시 제외하세요.

2. **선별 후 심층 분석**:
   - 1차 스크리닝을 통과한 **정예 공고(최대 7개)**에 대해서만 `get_financial_health`와 `get_company_reputation`을 호출하세요.
   - 모든 검색 결과에 대해 도구를 호출하는 것은 토큰 낭비이며 비효율적입니다.

3. **결과 저장 (필수)**:
   - 분석이 완료되면 **반드시** `save_job_search_report`를 호출하여 결과를 'result/job_search_results.md' 파일로 저장하세요.
   - 사용자에게는 "리포트 저장이 완료되었습니다"라는 메시지와 함께 요약본을 보여주세요.

4. **리포트 구조**:
   - 다음 표 형식을 반드시 유지하세요:
     | 기업 이름 | 공고 내용 (직무/요건 요약) | 재무 요약 (DART 등) | 평판 상세 (잡플래닛 등) | 링크 |
   - **재무 요약**: 최근 매출액, 영업이익 수치를 명시하세요.
   - **평판 상세**: 총점(X.X/5.0), 장점, 단점을 명확히 구분하세요.

[상세 조건]:
- 현재 날짜: 2026-05-11
- 경력 사항: {experience}
- 희망 지역: {location}
- 추가 키워드: {keywords}
"""

async def run_job_hunter():
    print("\n" + "="*60)
    print(" 🔍 전문 데이터 직무 헌터 (DA/DS 전용)")
    print("="*60)
    
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
    
    user_request = f"'{location}' 지역의 '{experience}' 수준 '{keywords}' 관련 DA/DS 공고를 정밀 조사해서 리포트를 '/result' 폴더에 저장해줘. 조건에 맞지 않는 공고는 철저히 제외해."
    
    print(f"\n[전문 데이터 공고 분석 및 리포팅 시작...]\n" + "-"*60)

    async for event in agent.run(user_request):
        for node_name, content in event.items():
            for msg in content.get("messages", []):
                if msg.content:
                    # 사용자에게 진행 상황을 알기 쉽게 출력
                    print(f"\n[{node_name}] {msg.content[:500]}{'...' if len(msg.content) > 500 else ''}")


if __name__ == "__main__":
    asyncio.run(run_job_hunter())
