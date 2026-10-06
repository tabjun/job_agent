import asyncio
from job_agent.core.paths import load_environment
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

# 환경 변수 로드
load_environment()


@tool
def get_info(query: str):
    """
    [기본 검색 도구] 사용자의 질의어에 대해 기초 정보를 검색하여 반환합니다.
    """
    return f"'{query}'에 대해 검색된 기초 정보입니다. (LangChain 표준 에이전트 방식)"


async def start_langchain_agent():
    """
    LangGraph가 아닌, LangChain의 표준 AgentExecutor 방식을 사용하여
    에이전트를 구동하는 예시입니다. (선형 구조)
    """
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent

    llm = ChatOpenAI(model="gpt-4o")
    tools = [get_info]

    # LangChain 표준 프롬프트 설정 (agent_scratchpad는 에이전트의 내부 사고 기록용입니다)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "당신은 유능하고 친절한 조수입니다."),
            ("human", "{input}"),
            ("placeholder", "{agent_scratchpad}"),
        ]
    )

    # Agent 생성 및 실행기 설정
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    print("\n--- LangChain 단순 에이전트 실행 ---")
    result = await agent_executor.ainvoke(
        {"input": "LangChain 에이전트의 장점에 대해 알려줘"}
    )
    print(f"\n최종 답변: {result['output']}")


# Run with: python -m job_agent.examples.langchain_demo
if __name__ == "__main__":
    asyncio.run(start_langchain_agent())
