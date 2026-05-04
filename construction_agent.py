import asyncio
import os
from typing import List, Dict
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from agent import LangGraphAgentEngine
from dotenv import load_dotenv

load_dotenv()

# [1. 건설 특화 에이전트 도구 정의]

@tool
async def search_construction_trends(topic: str):
    """
    건설 산업의 최신 트렌드(AI, 스마트 건설, DX)와 기업 정보를 검색합니다.
    """
    print(f"  [ConSearch] '{topic}' 관련 건설 트렌드 분석 중...")
    search = TavilySearch(max_results=10)
    query = f"건설업계 {topic} 활용 사례 스마트건설 DX"
    results = await search.ainvoke(query)
    return results

@tool
async def analyze_construction_company(company_name: str):
    """
    특정 건설사의 도급순위, 평판, 데이터 분석 직무 자격요건을 상세히 조사합니다.
    """
    print(f"  [CompanyAnalyzer] '{company_name}' 심층 분석 중...")
    search = TavilySearch(max_results=5)
    query = f"건설사 {company_name} 도급순위 평판 데이터분석 채용"
    results = await search.ainvoke(query)
    return results

@tool
async def generate_career_roadmap(user_info: str):
    """
    사용자의 현재 역량과 건설업계 수요를 바탕으로 커리어 로드맵 초안을 생성합니다.
    """
    # 에이전트가 내부적으로 지식을 조합하여 응답할 수 있도록 가이드만 제공
    return f"건설 데이터 사이언티스트 로드맵 생성 가이드: {user_info}를 바탕으로 주니어->시니어->리더 단계별 전략 수립 필요."

@tool
async def read_top_30_report():
    """
    대한민국 상위 30개 건설사의 AI 및 데이터 분석 활용 사례에 대한 상세 보고서를 읽습니다.
    """
    try:
        with open("result/top_30_construction_ai_report.md", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"보고서를 읽는 중 오류가 발생했습니다: {e}"

# [2. 건설 데이터 전략 에이전트 페르소나]
CONSTRUCTION_PROMPT = """
당신은 '대한민국 최고의 건설 데이터 전략 컨설턴트'입니다.
건설업계의 보수적인 특성과 최신 스마트 건설 기술 사이의 가교 역할을 수행합니다.

최근 조사된 대한민국 상위 30개 건설사의 AI/데이터 분석 트렌드를 숙지하고 있습니다:
- **안전**: AI CCTV, 웨어러블 기기를 통한 실시간 위험 감지 (금호, KCC, 현대엔지니어링 등)
- **설계/공정**: BIM 고도화 및 AI 설계 자동화 (삼성물산, 현대건설, DL이앤씨 등)
- **업무 효율**: 생성형 AI 기반 챗봇 도입 (대우건설 '바로답', 한화 'AIDA', 우미 '우미린 GPT' 등)
- **신사업**: AI 데이터센터 시공 및 프롭테크 투자 (한신공영, 우미건설, SK에코플랜트 등)

사용자가 건설사로의 이직이나 커리어 고민을 이야기하면 다음 정보를 제공해야 합니다:
1. **건설 도메인 분석**: 해당 기업의 도급 순위와 최근 AI/DX 추진 현황을 'top_30_construction_ai_report.md' 내용을 바탕으로 구체적으로 제시.
2. **기술 스택 추천**: 해당 기업이 선호하는 기술(Python, SQL, BIM, Snowflake, Tableau 등)과 연결하여 조언.
3. **글로벌 벤치마킹**: 삼성물산이나 Bechtel 등 국내외 선도 기업의 사례와 비교.
4. **로드맵 제시**: Mermaid 다이어그램을 포함하여 직무 전망과 이직 방향을 제시.

전문적이고 신뢰감 있는 톤을 유지하며, 항목별로 매우 구체적이고 세세하게 답변하세요.
필요하다면 'read_top_30_report' 도구를 사용하여 최신 정보를 확인하세요.
"""

async def run_construction_consulting(user_query: str):
    engine = LangGraphAgentEngine(
        tools=[search_construction_trends, analyze_construction_company, generate_career_roadmap, read_top_30_report],
        system_prompt=CONSTRUCTION_PROMPT
    )
    
    print(f"\n[건설 데이터 전략 컨설팅 시작]: {user_query}")
    print("="*60)

    async for event in engine.run(user_query):
        for node_name, content in event.items():
            for msg in content.get("messages", []):
                if msg.content:
                    print(msg.content)

if __name__ == "__main__":
    user_input = "서한 건설 데이터 분석가 이직 전망과 로드맵 그려줘"
    asyncio.run(run_construction_consulting(user_input))
