import asyncio
import os
import glob
from typing import List, Dict, Any
from langchain_core.tools import tool
from agent import LangGraphAgentEngine
from dotenv import load_dotenv

# .env 로드
load_dotenv()

# =====================================================================
# [0. 사용자 로컬 데이터 로드 함수]
# =====================================================================
def load_user_context() -> str:
    """knowledge, more_info 폴더의 텍스트를 읽어옵니다. (이력서 원본 및 가이드라인)"""
    context = ""
    
    # 1. 원본 이력서/경력기술서 읽기
    context += "=== [사용자 원본 이력 및 경력 (knowledge)] ===\n"
    for file in glob.glob("knowledge/*.txt"):
        with open(file, "r", encoding="utf-8") as f:
            context += f.read() + "\n\n"
    for file in glob.glob("knowledge/*.docx"): # 단순 텍스트 추출이 안될 경우 대비 (실제 환경에선 docx2txt 등 필요)
        context += f"(파일 참고 필요: {os.path.basename(file)})\n"

    # 2. 자소서 작성 가이드 및 방향성 읽기 (가드레일)
    context += "=== [자소서 작성 가이드라인 및 개인 철학 (more_info)] ===\n"
    for file in glob.glob("more_info/*.txt"):
        with open(file, "r", encoding="utf-8") as f:
            context += f.read() + "\n\n"

    return context

# =====================================================================
# [1. 도구 정의]
# =====================================================================

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
사용자의 [원본 이력]과 [작성 가이드라인]을 바탕으로, 특정 [채용 공고(JD)]에 완벽히 부합하는 자기소개서와 이력서를 수정/작성하는 것이 임무입니다.

[사용자 기본 정보 및 가이드라인]:
{user_context}

---
[엄격한 준수 사항 (Guardrails)]
1. **Hallucination 절대 금지**: [원본 이력]에 없는 프로젝트, 기술, 경력, 학력을 절대 지어내지 마세요. 
2. **가이드라인 준수**: [more_info]에 명시된 작성 스타일, 금기 사항, 강조 포인트를 반드시 반영하세요.
3. **JD 매칭**: 기업의 주요 업무와 자격 요건을 분석하여, 사용자의 실제 경험 중 가장 연관성 높은 부분을 강조하세요.
4. **사실 기반 강조**: 없는 실력을 부풀리기보다, 있는 실력을 해당 기업의 언어로 재해석(Reframing)하세요.

[업무 프로세스]
1. [공고 분석]: 사용자가 제공한 JD에서 핵심 키워드와 인재상을 추출하세요.
2. [전략 수립]: 원본 이력 중 어떤 에피소드를 강조할지 결정하세요.
3. [문서 작성]: 
   - 맞춤형 자기소개서 작성 (문항이 없을 경우 자유 양식)
   - 주요 경력 기술서 보완 포인트 제안
4. [저장]: `save_revised_document`를 사용하여 결과물을 저장하세요.
5. [면접 포인트]: 해당 서류를 기반으로 한 예상 질문과 대응 전략을 간략히 제공하세요.
"""

async def run_resume_reviser():
    user_context = load_user_context()
    
    print("\n" + "="*60)
    print(" ✍️ 맞춤형 자소서/이력서 수정 에이전트")
    print("="*60)
    
    company_name = input("1. 지원하려는 기업 이름: ")
    print("\n2. 채용 공고(JD) 내용을 붙여넣어 주세요 (입력 후 Ctrl+D 또는 빈 줄에서 Enter 두 번 - OS에 따라 다름):")
    print("(팁: job_hunter가 생성한 리포트의 내용을 활용하세요)")
    
    jd_lines = []
    while True:
        try:
            line = input()
            if line == "" and jd_lines and jd_lines[-1] == "": break
            jd_lines.append(line)
        except EOFError:
            break
    jd_content = "\n".join(jd_lines)

    print("\n" + "-"*60)
    model_choice = input("어떤 AI 모델을 사용할까요? (1: Gemini(무료), 2: GPT-5-mini(유료)): ")
    use_model = "gpt" if model_choice == "2" else "gemini"
    print("-"*60)

    final_prompt = REVISER_PROMPT.format(user_context=user_context)

    agent = LangGraphAgentEngine(
        use_model=use_model,
        tools=[save_revised_document],
        system_prompt=final_prompt
    )
    
    user_request = f"기업명: {company_name}\n\n[채용 공고 내용]\n{jd_content}\n\n위 공고에 맞춰서 내 이력서와 자소서를 수정해주고 저장해줘. 가이드라인을 엄격히 지켜줘."
    
    print(f"\n[문서 수정 및 전략 수립 시작...]\n" + "-"*60)

    async for event in agent.run(user_request):
        for node_name, content in event.items():
            for msg in content.get("messages", []):
                if msg.content:
                    print(f"\n>>> {msg.content}")

if __name__ == "__main__":
    asyncio.run(run_resume_reviser())
