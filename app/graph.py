from langgraph.graph import MessagesState,StateGraph,START,END
from langgraph.prebuilt import ToolNode
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages
from app.config import llm_with_tools
from app.tools import get_fee


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def agent_node(state: AgentState) -> dict:
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

tool_node = ToolNode([get_fee])

def tool_condition(state:AgentState) -> dict:
    last_message=state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END


workflow=StateGraph(AgentState)

workflow.add_node("Agent",agent_node)
workflow.add_node("tools",tool_node)
workflow.add_edge("START","Agent")

workflow.add_conditional_edges(
    "agent",
    tool_condition,
)

admissions_agent = workflow.compile()
result = admissions_agent.invoke(
    {"messages": [{"role": "user", "content": "JEE 2-year ki fees?"}]}
)

for m in result["messages"]:
    m.pretty_print()
