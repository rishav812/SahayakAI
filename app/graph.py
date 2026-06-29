from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_chroma import Chroma
from typing import Annotated, TypedDict
from langchain_core.tools.retriever import create_retriever_tool
from langgraph.graph.message import add_messages
from app.config import llm, embeddings, CHROMA_DIR, COLLECTION
from app.tools import get_fee, COVERAGE_GATE_REPLY


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


store = Chroma(
    collection_name=COLLECTION,
    embedding_function=embeddings,
    persist_directory=CHROMA_DIR,
)
vector_retriever = store.as_retriever(search_kwargs={"k": 4})
retriever_tool = create_retriever_tool(
    vector_retriever,
    "search_institute_policies",
    "Search institute documents to answer questions about syllabus, schedule, eligibility, exam pattern, or admission policy.",
)

tools = [get_fee, retriever_tool]
llm_with_tools = llm.bind_tools(tools)


def agent_node(state: AgentState) -> dict:
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


tool_node = ToolNode(tools)


def tool_condition(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


def coverage_gate_node(state: AgentState) -> dict:
    last = state["messages"][-1]
    if isinstance(last, ToolMessage) and last.content == "NOT_FOUND":
        return {"messages": [AIMessage(content=COVERAGE_GATE_REPLY)]}
    return {}


def after_gate_condition(state: AgentState) -> str:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.content == COVERAGE_GATE_REPLY:
        return END
    return "Agent"



workflow = StateGraph(AgentState)

workflow.add_node("Agent", agent_node)
workflow.add_node("tools", tool_node)
workflow.add_node("coverage_gate", coverage_gate_node)

workflow.add_edge(START, "Agent")
workflow.add_conditional_edges("Agent", tool_condition, {"tools": "tools", END: END})
workflow.add_edge("tools", "coverage_gate")
workflow.add_conditional_edges("coverage_gate", after_gate_condition, {"Agent": "Agent", END: END})

admissions_agent = workflow.compile()

with open("graph.png", "wb") as f:
    f.write(admissions_agent.get_graph().draw_mermaid_png())
