import asyncio
import os
from langchain_tavily import TavilySearchResults
from dotenv import load_dotenv

# =====================================================================
# [테스트 전용 모듈] 
# 이 파일은 Tavily 검색 엔진의 쿼리 결과가 의도대로 나오는지 확인하기 위한 
# 독립적인 프로토타입/테스트 스크립트입니다. 
# 실제 에이전트(job_hunter.py)에 적용하기 전, 검색 결과의 질을 미리 
# 확인하는 용도로만 사용하십시오.
# =====================================================================

load_dotenv()

async def fetch_jobs():
    search = TavilySearchResults(max_results=30)
    fixed_role = "데이터 분석가 OR 데이터 사이언티스트 OR Data Analyst OR Data Scientist"
    exclude_keywords = "-라벨링 -수집알바 -단순입력 -labeling"
    experience = "신입 3년차 이하"
    location = "서울 경기"
    keywords = "Python SQL AI"
    sites = "site:saramin.co.kr OR site:wanted.co.kr OR site:catch.co.kr OR site:jobplanet.co.kr OR site:jumpit.co.kr OR site:linkedin.com"
    
    query = f"({fixed_role}) {experience} {location} {keywords} {exclude_keywords} 채용 ({sites})"
    
    try:
        results = await search.ainvoke(query)
        for idx, r in enumerate(results):
            print(f"--- RESULT {idx+1} ---")
            print(f"URL: {r.get('url')}")
            print(f"Content: {r.get('content')}")
            print()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(fetch_jobs())
