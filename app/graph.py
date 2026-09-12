from contextlib import ExitStack
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.types import Command
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_chroma import Chroma
from typing import TypedDict, Literal
from langchain_core.tools.retriever import create_retriever_tool
from langgraph.prebuilt import create_react_agent
from app.config import llm, embeddings, CHROMA_DIR, COLLECTION, DATABASE_URL
from app.tools import get_fee, COVERAGE_GATE_REPLY
from app.scheduling_agent import scheduling_agent
import os


# --- State ---

class State(MessagesState):
    next: str


from pydantic import BaseModel, Field

# --- Supervisor ---

members = ["admission", "faq", "scheduling"]

class Router(BaseModel):
    next: Literal["admission", "faq", "scheduling", "FINISH"] = Field(
        default="FINISH",
        description="The next worker agent to handle the request, or FINISH if completed."
    )

system_prompt = f"""
You are a supervisor managing a conversation between these workers: {members}.

- admission: handles ONLY fee, cost, price, charges, and batch-duration numerical lookups.
  It looks up exact fee amounts with a tool. Route here for ANY question that asks
  "how much" or "what is the fee/cost" for a specific course or batch.
- faq: handles questions about syllabus, schedule, eligibility, exam pattern,
  documents required, refund policy, installment rules, discipline, and other
  institute policy questions, by searching institute documents. Route refund policy
  and installment rules questions here. Never route specific course fee-amount questions here.
- scheduling: handles booking or scheduling a demo class (e.g. "book a demo",
  "schedule a class", "demo class chahiye", or providing a time/date for a demo).
  It reserves an actual slot with a tool. Route here for ANY request to book, schedule,
  or reserve a demo class, or when the user provides a time/slot choice, date, or
  follow-up response to demo booking (e.g. "Kal subah 11 baje", "13 September", "book karni h").

Given the user request, choose which worker should act next.
Each worker will respond with their result.
- ALWAYS route to scheduling if the user's latest message is a follow-up answer or slot choice (e.g. providing a time, date, or repeat booking request) to a previous scheduling prompt or alternative options offer, unless scheduling has ALREADY responded in this current user turn.
A single worker's response may only cover PART of the user's original question.
Compare what has been answered so far against the full ORIGINAL user question to decide what, if anything, is still missing:
- If every distinct topic actually present in the user request has now been addressed in the current turn, respond with FINISH.
- If admission replies with "{COVERAGE_GATE_REPLY}", treat the fee part as fully handled — do not route to faq to try to find that same fee.
"""



def supervisor_node(state: State) -> Command[Literal["admission", "faq", "scheduling", "__end__"]]:
    # Workers that already responded since the user's last message. The router
    # LLM doesn't reliably self-limit (it can re-pick the same worker forever
    # on a hedge-y answer), so this is a deterministic backstop against loops.
    visited = set()
    for msg in reversed(state["messages"]):
        name = getattr(msg, "name", None)
        if name in members:
            visited.add(name)
        else:
            break

    if visited >= set(members):
        print(f"[supervisor] all workers visited ({visited}) -> FINISH")
        return Command(goto=END, update={"next": END})

    # Check if the previous turn's last AI message was from scheduling (asking for slot/time or offering alternatives).
    # If the user is giving a follow-up response to scheduling, and scheduling hasn't run yet in this turn,
    # deterministically route to scheduling.
    if "scheduling" not in visited:
        last_ai_worker = None
        for msg in reversed(state["messages"][:-1]):  # exclude current user message
            msg_name = getattr(msg, "name", None)
            if msg_name in members:
                last_ai_worker = msg_name
                break
        
        if last_ai_worker == "scheduling":
            latest_text = getattr(state["messages"][-1], "content", "").lower()
            fee_keywords = ["fee", "cost", "price", "kitni fee", "kitne paise", "kitna fee"]
            if not any(k in latest_text for k in fee_keywords):
                print("[supervisor] deterministic follow-up -> scheduling")
                return Command(goto="scheduling", update={"next": "scheduling"})

    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    response = llm.with_structured_output(Router).invoke(messages)

    if isinstance(response, Router):
        goto = response.next
    elif isinstance(response, dict):
        goto = response.get("next", "FINISH")
    else:
        goto = "FINISH"

    if goto == "FINISH" or goto in visited:
        goto = END
    print(f"[supervisor] decided next -> {goto}")
    return Command(goto=goto, update={"next": goto})


# --- Admission agent (fee lookups) ---

admission_react_agent = create_react_agent(
    llm,
    tools=[get_fee],
    prompt=(
        "You are an admissions assistant for a coaching institute. "
        "You ONLY answer the fee, cost, and batch-duration part of a question, using "
        "the get_fee tool for every fee query. Never state a fee from memory.\n\n"
        "These two rules are INDEPENDENT — never combine or mix their wording:\n"
        f"1. If get_fee returns 'NOT_FOUND' for the fee part, your entire response must "
        f"be exactly this and nothing else: '{COVERAGE_GATE_REPLY}'\n"
        "2. If the question also asks about anything other than fees (documents, "
        "eligibility, schedule, syllabus, refunds, policies, etc.), that other part is "
        "not your job. Do not answer it, guess at it, apologize for it, or say anything "
        "about it at all — act as if that part of the question was never asked, and "
        "give a clean answer for the fee part alone."
    ),
)


def admission_node(state: State) -> Command[Literal["supervisor"]]:
    print("[admission] invoked")
    result = admission_react_agent.invoke(state)
    reply = result["messages"][-1].content
    print(f"[admission] reply -> {reply}")
    return Command(
        goto="supervisor",
        update={
            "messages": [AIMessage(content=reply, name="admission")]
        },
    )


# --- FAQ agent (document retrieval) ---

store = Chroma(
    collection_name=COLLECTION,
    embedding_function=embeddings,
    persist_directory=CHROMA_DIR,
)
retriever_tool = create_retriever_tool(
    store.as_retriever(search_kwargs={"k": 4}),
    "search_institute_docs",
    "Search institute documents to answer questions about syllabus, schedule, eligibility, exam pattern, refund policy, or admission policy.",
)

faq_react_agent = create_react_agent(
    llm,
    tools=[retriever_tool],
    prompt=(
        "You are a helpful FAQ assistant for a coaching institute. "
        "Answer questions about syllabus, schedules, eligibility, refund policies, installment rules, and other policies "
        "by searching the institute documents with your search_institute_docs tool. "
        "You do NOT handle course fee amount lookup questions (e.g. 'how much is the course fee?') — another assistant handles those. "
        "However, you DO handle policy questions including refund policy, fee installments, rules, and cancellation terms. "
        "If a user asks whether fees are refundable or what the refund policy is, search the documents for refund policy and answer clearly."
    ),
)


def faq_node(state: State) -> Command[Literal["supervisor"]]:
    print("[faq] invoked")
    result = faq_react_agent.invoke(state)
    reply = result["messages"][-1].content
    print(f"[faq] reply -> {reply}")
    return Command(
        goto="supervisor",
        update={
            "messages": [AIMessage(content=reply, name="faq")]
        },
    )


# --- Scheduling agent (demo booking) ---

def scheduling_node(state: State, config: RunnableConfig) -> Command[Literal["supervisor"]]:
    print("[scheduling] invoked")
    phone = config["configurable"]["thread_id"]
    messages = [
        SystemMessage(
            f"The user's phone number is {phone}. Use this automatically for "
            "any book_demo call — never ask the user for their phone number."
        )
    ] + state["messages"]
    result = scheduling_agent.invoke({"messages": messages})
    reply = result["messages"][-1].content
    print(f"[scheduling] reply -> {reply}")
    return Command(
        goto="supervisor",
        update={
            "messages": [AIMessage(content=reply, name="scheduling")]
        },
    )




# --- Graph ---

workflow = StateGraph(State)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("admission", admission_node)
workflow.add_node("faq", faq_node)
workflow.add_node("scheduling", scheduling_node)

workflow.add_edge(START, "supervisor")

from psycopg_pool import ConnectionPool

# Use ConnectionPool to automatically manage and reconnect dropped idle database connections (e.g. Neon serverless auto-suspend)
pool = ConnectionPool(
    conninfo=DATABASE_URL,
    max_size=20,
    max_idle=30,
    reconnect_timeout=60,
    check=ConnectionPool.check_connection,
    kwargs={"autocommit": True, "prepare_threshold": 0},
)

checkpointer = PostgresSaver(pool)
checkpointer.setup()

admissions_agent = workflow.compile(checkpointer=checkpointer)

if os.getenv("GENERATE_GRAPH_PNG", "false").lower() == "true":
    try:
        with open("graph.png", "wb") as f:
            f.write(admissions_agent.get_graph().draw_mermaid_png())
        print("[graph] graph.png regenerated")
    except Exception as e:
        print(f"[graph] skipped graph.png generation: {e}")