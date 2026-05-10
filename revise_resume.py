import asyncio
import os
import glob
from typing import List, Dict, Any
from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from agent import LangGraphAgentEngine
from dotenv import load_dotenv

# .env 로드
load_dotenv()

# =====================================================================
# [0. 사용자 로컬 데이터 로드 함수]
# =====================================================================
def load_user_context() -> str:
    """kordoc을 사용하여 다양한 문서(hwp, pdf, docx 등)를 마크다운으로 읽어옵니다."""
    import subprocess
    context = ""
    
    # 1. 원본 이력 및 경력 탐색
    context += "=== [사용자 원본 이력 및 경력 (knowledge)] ===\n"
    
    # 지원 확장자 설정
    extensions = ['*.txt', '*.hwp', '*.hwpx', '*.pdf', '*.docx']
    files = []
    for ext in extensions:
        files.extend(glob.glob(f"knowledge/{ext}"))

    for file_path in files:
        file_name = os.path.basename(file_path)
        
        if file_path.endswith('.txt'):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                content = f"(텍스트 파일 읽기 실패: {e})"
        else:
            # kordoc을 사용하여 마크다운 추출
            print(f"  [Parsing] '{file_name}' 분석 중 (kordoc)...")
            try:
                # npx kordoc <file_path> 실행하여 결과를 stdout으로 받음
                # --format markdown은 기본값이므로 생략 가능
                result = subprocess.run(
                    ["npx", "kordoc", file_path], 
                    capture_output=True, 
                    text=True, 
                    check=True,
                    encoding='utf-8' # 한글 인코딩 대응
                )
                content = result.stdout
            except Exception as e:
                content = f"(문서 파싱 실패: kordoc 실행 중 오류 발생. {e})"
        
        context += f"\n--- 파일: {file_name} ---\n{content}\n"

    # 2. 자소서 작성 가이드 및 방향성 읽기 (more_info)
    context += "\n=== [자소서 작성 가이드라인 및 개인 철학 (more_info)] ===\n"
    for file in glob.glob("more_info/*.txt"):
        with open(file, "r", encoding="utf-8") as f:
            context += f.read() + "\n\n"

    return context

# =====================================================================
# [1. 도구 정의]
# =====================================================================

@tool
async def search_company_tech_info(company_name: str, topic: str):
    """
    특정 기업의 기술 블로그, 채용 후기, 과제 테스트/코딩 테스트 정보를 검색합니다.
    topic 예시: '데이터 분석 과제 테스트', '기술 블로그 데이터 엔지니어링', '면접 후기'
    """
    print(f"  [Research] '{company_name}'의 '{topic}' 정보 검색 중...")
    search = TavilySearchResults(max_results=5)
    query = f"{company_name} {topic}"
    try:
        return await search.ainvoke(query)
    except Exception as e:
        return f"검색 중 오류 발생: {e}"

@tool
async def save_revised_document(content: str, company_name: str, doc_type: str = "cover_letter"):
    """수정된 자기소개서 또는 이력서를 파일로 저장합니다."""
    os.makedirs("result/revised", exist_ok=True)
    file_path = f"result/revised/{company_name}_{doc_type}.md"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"문서 저장 완료: {file_path}"

# =====================================================================
# [2. 전문가 페르소나 설정]
# =====================================================================
REVISER_PROMPT = """
당신은 '대한민국 최고의 커리어 컨설턴트이자 서류 합격 마스터'입니다. 
사용자의 [원본 이력]과 [작성 가이드라인]을 바탕으로, 특정 [채용 공고(JD)]에 완벽히 부합하는 자기소개서와 이력서를 수정/작성하고, 해당 기업의 기술 과제 및 면접 전략을 수립하는 것이 임무입니다.

[사용자 기본 정보 및 가이드라인]:
{user_context}

---
[업무 프로세스 및 지침]
1. [공고 및 기업 분석]: 
   - 사용자가 제공한 JD를 분석하세요.
   - `search_company_tech_info`를 사용하여 해당 기업의 **기술 블로그, 과제 테스트 후기, 코딩 테스트 스타일**을 조사하세요. 특히 에이블리, 토스처럼 과제 전형이 유명한 곳은 도메인(커머스, 금융 등)과 결합된 분석 과제를 예측해야 합니다.
2. [전략 수립]: 원본 이력 중 어떤 에피소드를 강조할지, 기술 과제에서는 어떤 역량을 보여줘야 할지 결정하세요.
3. [문서 작성 및 저장]: 
   - 맞춤형 자기소개서/이력서 보완 포인트를 작성하고 `save_revised_document`로 저장하세요.
4. [기술 평가 대비 자료 제공 (핵심)]:
   - 검색한 정보를 바탕으로 해당 기업에서 나올 법한 **'직무별 예상 기술 과제/코딩 테스트' 예제**를 만드세요.
   - 예: 에이블리라면 "앱 내 유저 로그 데이터를 활용한 리텐션 분석 과제" 등을 구체적인 데이터셋 형태와 함께 제안하세요.
   - 해당 과제 해결을 위한 핵심 SQL 쿼리나 Python 라이브러리 활용 팁을 포함하세요.
5. [면접 포인트]: 서류 기반 예상 질문과 대응 전략을 제공하세요.

[준수 사항]
- **Hallucination 절대 금지**: 이력은 사실에 기반하되, 기업 분석 정보는 검색된 실제 데이터를 바탕으로 추론하세요.
- **도메인 특화**: 기업의 비즈니스 모델(BM)에 맞춘 데이터 분석 주제를 반드시 제시하세요.
"""

async def run_resume_reviser():
    user_context = load_user_context()
    
    print("\n" + "="*60)
    print(" ✍️ 맞춤형 자소서/이력서 & 기술 과제 대비 에이전트")
    print("="*60)
    
    company_name = input("1. 지원하려는 기업 이름: ")
    print("\n2. 채용 공고(JD) 내용을 붙여넣어 주세요 (입력 후 Ctrl+D 또는 빈 줄에서 Enter 두 번):")
    
    jd_lines = []
    while True:
        try:
            line = input()
            if line == "" and jd_lines and jd_lines[-1] == "": break
            jd_lines.append(line)
        except EOFError:
            break
    jd_content = "\n".join(jd_lines)

    print("\n3. 추가 참고 정보 (공고 링크, 분석된 리포트 경로, 이미지 파일 경로 등):")
    extra_info = input("> ")

    print("\n" + "-"*60)
    model_choice = input("어떤 AI 모델을 사용할까요? (1: Gemini(무료), 2: GPT-5-mini(유료)): ")
    use_model = "gpt" if model_choice == "2" else "gemini"
    print("-"*60)

    final_prompt = REVISER_PROMPT.format(user_context=user_context)

    agent = LangGraphAgentEngine(
        use_model=use_model,
        tools=[search_company_tech_info, save_revised_document],
        system_prompt=final_prompt
    )
    
    user_request = f"""기업명: {company_name}

[채용 공고 내용]
{jd_content}

[추가 참고 정보]
{extra_info}

위 기업의 도메인과 기술 블로그 등을 조사해서 내 이력서 수정뿐만 아니라, 예상되는 '데이터 분석 과제 테스트' 예제와 해결 전략도 구체적으로 알려줘. 
특히 추가로 제공된 링크나 파일 경로가 있다면 그 내용을 철저히 반영해서 작성해줘."""
    
    print(f"\n[문서 수정 및 전략 수립 시작...]\n" + "-"*60)

    async for event in agent.run(user_request):
        for node_name, content in event.items():
            for msg in content.get("messages", []):
                if msg.content:
                    print(f"\n>>> {msg.content}")

if __name__ == "__main__":
    asyncio.run(run_resume_reviser())
