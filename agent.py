import asyncio
import operator
import os
from typing import Annotated, TypedDict, List, Any, Dict, AsyncGenerator
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END

load_dotenv()

# 환경 변수 설정
if not os.getenv("GOOGLE_API_KEY") and os.getenv("GOOGLE_AI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_AI_API_KEY")

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]

class LangGraphAgentEngine:
    def __init__(self, use_model: str = "gemini", tools: List[Any] = None, system_prompt: str = ""):
        self.tools = tools or []
        self.system_prompt = system_prompt
        
        # 모델 선택 로직
        if use_model == "gpt":
            print("[System] 메인 모델로 GPT-5-mini를 사용합니다. (유료 토큰 소모)")
            self.llm = ChatOpenAI(model="gpt-5-mini", temperature=0).bind_tools(self.tools)
        else:
            print("[System] 메인 모델로 Gemini 1.5 Pro를 사용합니다. (무료 티어)")
            self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0).bind_tools(self.tools)
        
        self.tools_dict = {t.name: t for t in self.tools}
        self.app = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("llm_think", self.call_model)
        workflow.add_node("execute_tools", self.execute_tools)
        workflow.set_entry_point("llm_think")
        workflow.add_conditional_edges(
            "llm_think",
            self.should_continue,
            {"continue": "execute_tools", "end": END}
        )
        workflow.add_edge("execute_tools", "llm_think")
        return workflow.compile()

    async def call_model(self, state: AgentState) -> Dict[str, List[BaseMessage]]:
        messages = state["messages"]
        if self.system_prompt and not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=self.system_prompt)] + messages
        
        try:
            response = await self.llm.ainvoke(messages)
            return {"messages": [response]}
        except Exception as e:
            print(f"\n[ERROR] 모델 호출 중 오류 발생: {e}")
            raise e

    async def execute_tools(self, state: AgentState) -> Dict[str, List[BaseMessage]]:
        last_message = state["messages"][-1]
        tool_outputs = []
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            if tool_name in self.tools_dict:
                action = self.tools_dict[tool_name]
                print(f"  >> 도구 실행: {tool_name}")
                try:
                    output = await action.ainvoke(tool_args)
                    tool_outputs.append(ToolMessage(content=str(output), tool_call_id=tool_call["id"]))
                except Exception as e:
                    tool_outputs.append(ToolMessage(content=f"Error: {str(e)}", tool_call_id=tool_call["id"]))
        return {"messages": tool_outputs}

    def should_continue(self, state: AgentState) -> str:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
        return "end"

    async def run(self, user_input: str) -> AsyncGenerator[Dict[str, Any], None]:
        inputs = {"messages": [HumanMessage(content=user_input)]}
        async for event in self.app.astream(inputs):
            yield event
