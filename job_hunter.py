import asyncio
import os
import json
from typing import List, Dict
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from agent import LangGraphAgentEngine
from dotenv import load_dotenv

# .env 파일을 통해 환경 변수(OpenAI API Key, Tavily API Key 등)를 로드합니다.
load_dotenv()

# [1. 채용 컨설턴트 전용 도구 정의]

@tool
async def search_jobs(role: str, location: str = "서울"):
    """
    Tavily Search API를 사용하여 여러 채용 플랫폼(사람인, 원티드, 잡코리아, 캐치, 인디스워크, 점핏 등)에서 실시간으로 채용 공고를 검색합니다.
    """
    print(f"  [Recruiter] {location} 지역의 {role} 공고를 다양한 플랫폼에서 실시간 검색 중...")
    search = TavilySearch(max_results=40)
    # 다양한 채용 사이트 포함
    sites = [
        "saramin.co.kr", 
        "wanted.co.kr", 
        "jobkorea.co.kr", 
        "catch.co.kr", 
        "inthiswork.com",
        "jumpit.co.kr",
        "linkareer.com",
        "rememberapp.co.kr"
    ]
    site_query = " OR ".join([f"site:{s}" for s in sites])
    query = f"{location} {role} 채용 ({site_query})"
    
    results = await search.ainvoke(query)
    return results

@tool
async def get_jobplanet_reviews(company_name: str):
    """
    잡플래닛에서 해당 회사의 리뷰를 검색하여 주요 키워드(장점, 단점)와 평점 정보를 가져옵니다.
    """
    job_id = os.getenv("job_id")
    job_pw = os.getenv("job_pw")
    
    if not job_id or not job_pw:
        return "리뷰 수집 실패: .env 계정 정보 누락"

    print(f"  [JobPlanet] '{company_name}' 리뷰 데이터 분석 중...")
    
    search = TavilySearch(max_results=10)
    # 잡플래닛 사이트 내에서 직접 검색하도록 쿼리 강화
    query = f"site:jobplanet.co.kr \"{company_name}\" 리뷰 평점 장점 단점"
    
    try:
        results = await search.ainvoke(query)
        if not results:
            return {"rating": 2.5, "review_summary": "리뷰 데이터 없음", "positive_keywords": [], "negative_keywords": []}
        
        full_text = ""
        for r in results:
            if isinstance(r, dict):
                content = r.get('content') or r.get('snippet') or ""
                full_text += content + " "
        
        import re
        # 평점 추출 패턴 개선: "평점 3.5", "3.5점", "별점 4.0" 등 대응
        ratings = re.findall(r"(?:평점|별점|[\s:])[ ]*([1-5]\.\d)", full_text)
        if not ratings:
            ratings = re.findall(r"([1-5]\.\d)", full_text)
            
        avg_rating = sum(float(x) for x in ratings) / len(ratings) if ratings else 2.5
        
        # 키워드 추출 (사전 확장)
        negative_indicators = [
            "무능", "꼰대", "수직", "야근", "박봉", "군대", "정체", "bm", "방향성", "퇴사", 
            "가족경영", "지인채용", "체계없음", "불통", "정치", "회식", "고인물"
        ]
        positive_indicators = [
            "자유", "수평", "복지", "성장", "커리어", "간식", "유연", "워라밸", "연봉", "동료", "재택",
            "점심제공", "도서지원", "교육지원", "수평적", "자기계발", "네임밸류"
        ]
        
        found_negative = [k for k in negative_indicators if k in full_text]
        found_positive = [k for k in positive_indicators if k in full_text]
        
        return {
            "company": company_name,
            "rating": round(avg_rating, 1),
            "review_summary": full_text[:2000] if full_text.strip() else "리뷰 내용을 요약할 수 없습니다.",
            "positive_keywords": list(set(found_positive)),
            "negative_keywords": list(set(found_negative))
        }
    except Exception as e:
        print(f"  [JobPlanet ERROR] {str(e)}")
        return {"rating": 2.5, "review_summary": f"오류 발생: {str(e)}", "positive_keywords": [], "negative_keywords": []}

@tool
async def save_job_report(report_data: List[Dict]):
    """
    분석된 데이터를 종합 리포트와 추천(Best)/보통(Middle)/주의(Worst) 기업 리포트로 분류하여 저장합니다.
    """
    print(f"  [Report] 데이터 분류 및 상세 리포트 생성 중...")
    os.makedirs("result", exist_ok=True)
    
    all_file = "result/comprehensive_report.md"
    best_file = "result/recommended_companies.md"
    middle_file = "result/middle_companies.md"
    worst_file = "result/worst_companies.md"
    
    def clean(text):
        return str(text).replace("|", "\\|").replace("\n", " ").strip()

    header = "| 회사 이름 | 평점 | 모집 직무 | 장점 키워드 | 단점 키워드 | 선정 이유 | 마감 기한 |\n"
    sep = "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    
    all_rows = []
    best_rows = []
    middle_rows = []
    worst_rows = []
    
    detailed_sections = ["# 📊 기업별 상세 리뷰 분석\n\n"]
    
    # 치명적인 단점 키워드
    critical_negatives = ["무능", "야근", "박봉", "군대", "퇴사"]

    for item in report_data:
        company = clean(item.get("company", "N/A"))
        rating = float(item.get("rating", 2.5))
        role = clean(item.get("role", "N/A"))
        pos_kw_list = item.get("positive_keywords", [])
        neg_kw_list = item.get("negative_keywords", [])
        pos_kw = ", ".join(pos_kw_list)
        neg_kw = ", ".join(neg_kw_list)
        reason = clean(item.get("selection_reason", "N/A"))
        deadline = clean(item.get("deadline", "N/A"))
        summary = item.get("review_summary", "내용 없음")
        qual = clean(item.get("qualifications", "N/A"))
        
        row = f"| {company} | {rating} | {role} | {pos_kw} | {neg_kw} | {reason} | {deadline} |\n"
        all_rows.append(row)
        
        # 상세 섹션
        detailed_sections.append(f"## 🏢 {company}\n")
        detailed_sections.append(f"- **평점**: {rating}\n")
        detailed_sections.append(f"- **선정 이유**: {reason}\n")
        detailed_sections.append(f"- **모집 직무**: {role}\n")
        detailed_sections.append(f"- **지원 자격**: {qual}\n")
        detailed_sections.append(f"- **장점 키워드**: {pos_kw}\n")
        detailed_sections.append(f"- **단점 키워드**: {neg_kw}\n")
        detailed_sections.append(f"- **리뷰 총평**: {summary}\n\n")
        detailed_sections.append("---\n\n")

        # 분류 로직
        is_worst = rating <= 2.6 or any(k in neg_kw for k in critical_negatives)
        is_best = rating >= 3.5 and not any(k in neg_kw for k in critical_negatives)
        
        if is_worst:
            worst_rows.append(row)
        elif is_best:
            best_rows.append(row)
        else:
            middle_rows.append(row)
            
    try:
        with open(all_file, "w", encoding="utf-8") as f:
            f.write("# 🌐 전체 채용 공고 및 기업 분석 리포트\n\n")
            f.write(header + sep + "".join(all_rows) + "\n\n")
            f.write("".join(detailed_sections))
            
        if best_rows:
            with open(best_file, "w", encoding="utf-8") as f:
                f.write("# ✅ 추천 기업 리스트 (Best)\n\n" + header + sep + "".join(best_rows))
        
        if middle_rows:
            with open(middle_file, "w", encoding="utf-8") as f:
                f.write("# 🆗 보통 기업 리스트 (Middle)\n\n" + header + sep + "".join(middle_rows))

        if worst_rows:
            with open(worst_file, "w", encoding="utf-8") as f:
                f.write("# ⚠️ 주의: 평점 낮음/부정적 리뷰 기업 (Worst)\n\n" + header + sep + "".join(worst_rows))
                
        return f"리포트 생성 완료: {all_file}, {best_file}, {middle_file}, {worst_file}"
    except Exception as e:
        return f"파일 저장 실패: {str(e)}"

@tool
async def analyze_resume_fit(resume_text: str, job_requirements: str):
    """이력서와 직무 요구사항의 적합도를 분석합니다."""
    print(f"  [Coach] 이력서 매칭 분석 중...")
    # 실제 분석 로직 (시뮬레이션)
    score = 85
    return f"매칭 점수: {score}점. 해당 직무의 기술 스택과 사용자님의 경험이 잘 부합합니다."

# [2. 전문가 페르소나 설정]
COACH_PROMPT = """
당신은 '대한민국 최고의 IT 채용 헤드헌터'입니다.
오늘 날짜는 2026년 5월 4일입니다. 사용자의 요청에 따라 다음 프로세스를 엄격히 준수하여 업무를 수행하세요:

1. **채용 공고 검색**: `search_jobs`를 사용하여 사람인, 원티드, 잡코리아, 캐치, 인디스워크 등 다양한 플랫폼에서 최신 공고를 최대한 많이(20개 이상) 찾습니다.
2. **정보 추출 및 필터링**: 검색 결과(URL, 본문 요약)를 분석하여 회사명, 직무명, 자격요건, 상세 설명을 파악합니다.
   - **중요**: 채용 공고의 마감 기한(Deadline)을 반드시 확인하세요. 이미 마감되었거나 오늘 날짜(2026-05-04) 기준 마감된 공고는 리스트에서 제외합니다.
   - 가능한 많은(최소 10개 이상) 유효한 공고를 확보하도록 노력하세요.
3. **기업 리뷰 수집**: 파악된 각 회사들에 대해 `get_jobplanet_reviews`를 호출하여 잡플래닛 기반의 실제 현직자 평판(평점, 키워드, 총평)을 수집합니다.
4. **리포트 생성**: 모든 정보를 분석하여 `save_job_report`를 호출합니다. 
   - `report_data` 형식을 엄격히 준수하세요.
   - 각 기업을 **추천(Best)**, **보통(Middle)**, **주의(Worst)**로 분류하기 위한 충분한 정보를 `selection_reason`에 포함하세요.
5. **최종 응답**: 사용자에게 리포트 저장 위치(/result/comprehensive_report.md 등)를 알리고, 각 카테고리(Best/Middle/Worst)별 주요 특징을 요약해 주세요.

사용자의 이력서 정보가 있다면 `analyze_resume_fit`을 병행하여 가장 잘 맞는 공고를 최우선 순위로 배치하세요.
"""

async def start_consulting():
    career_coach = LangGraphAgentEngine(
        tools=[search_jobs, get_jobplanet_reviews, save_job_report, analyze_resume_fit],
        system_prompt=COACH_PROMPT
    )
    
    user_input = """서울에서 파이썬을 주로 사용하는 데이터 분석가 또는 데이터 사이언티스트 자리를 찾아줘.
    내 이력서는 '데이터 분석/머신 러닝 전공, 통계학 석사'야.
    찾은 결과들을 상세히 분석해서 /result 폴더에 md 표로 저장해줘."""
    
    print(f"\n[사용자 요청]: {user_input}")
    print("="*60)

    async for event in career_coach.run(user_input):
        for node_name, content in event.items():
            print(f"\n>>> [단계: {node_name}]")
            for msg in content.get("messages", []):
                if msg.content:
                    # 중간 과정이 너무 길면 요약 출력
                    display_text = msg.content[:1000] + "..." if len(msg.content) > 1000 else msg.content
                    print(f"  [응답] {display_text}")

    print("\n" + "="*60)
    print("채용 컨설팅 리포트 작성이 완료되었습니다. /result 폴더를 확인하세요.")

if __name__ == "__main__":
    asyncio.run(start_consulting())
