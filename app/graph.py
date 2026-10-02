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

Each worker is a STRICT SPECIALIST — they only handle their own domain and will
not answer topics belonging to another worker. YOUR job is to route each topic
to the correct worker. For multi-part questions, route to each responsible worker
one at a time (sequentially) — never assume one worker will cover another's topic.

- admission: handles ONLY fee, cost, price, charges, and batch-duration numerical lookups.
  It looks up exact fee amounts with a database tool. Route here for ANY question that asks
  "how much" or "what is the fee/cost" for a specific course or batch.
  It will NOT answer booking, FAQ, or policy questions.
- faq: handles questions about syllabus, schedule, eligibility, exam pattern,
  documents required, refund policy, installment rules, discipline, and other
  institute policy questions, by searching institute documents. Route refund policy
  and installment rules questions here. Never route specific course fee-amount questions here.
  It will NOT answer fee amounts or booking questions.
- scheduling: handles ONLY booking or scheduling a demo class (e.g. "book a demo",
  "schedule a class", "demo class chahiye", or providing a time/date for a demo).
  It reserves an actual slot with a tool. Route here for ANY request to book, schedule,
  or reserve a demo class, or when the user provides a time/slot choice, date, or
  follow-up response to demo booking (e.g. "Kal subah 11 baje", "13 September", "book karni h").
  It will NOT answer fee amounts or FAQ/policy questions.

CRITICAL ROUTING RULES:
1. For multi-part questions (e.g. "fee kitni h AUR demo book karna h"), you MUST
   route to EACH responsible worker separately. Example: route to admission first
   for the fee part, then come back and route to scheduling for the booking part.
   NEVER assume scheduling or faq will also answer the fee — they won't.
2. ALWAYS route to scheduling if the user's latest message is a follow-up answer or
   slot choice to a previous scheduling prompt, unless scheduling has ALREADY responded
   in this current user turn.
3. A single worker's response covers only their own topic. After each worker responds,
   check the FULL original question — if any other topic is still unanswered by its
   responsible worker, route to that worker next.
4. Respond with FINISH only when EVERY distinct topic in the user's request has been
   answered by the correct specialist worker in this turn.
5. If admission replies with "{COVERAGE_GATE_REPLY}", treat the fee part as fully
   handled — do not route to faq to try to find that same fee.
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

    messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
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

# ── LANE RULE (generic boundary enforcement) ────────────────────────────────
# Every agent gets an explicit list of domains it must NEVER touch.
# This prevents any agent from hallucinating an answer that belongs to
# another specialist, regardless of how the user phrases the question.
# ────────────────────────────────────────────────────────────────────────────
ADMISSION_LANE_RULE = (
    "\n\nSTRICT LANE RULE — YOU ARE A FEE SPECIALIST ONLY:\n"
    "Your ONLY job is to look up and return the exact fee/cost/batch-duration "
    "using the get_fee tool. You must NEVER answer, guess, or comment on:\n"
    "  • Demo class booking, scheduling, or slot availability (scheduling agent's job)\n"
    "  • Syllabus, eligibility, exam pattern, documents, refund policy, installment "
    "rules, or any other institute policy (faq agent's job)\n"
    "If the user's message also contains any of those topics, act as if those parts "
    "were never asked — answer only the fee part and nothing else. "
    "Never apologize for not covering other topics. Just give the fee and stop."
)

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
        + ADMISSION_LANE_RULE
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

FAQ_LANE_RULE = (
    "\n\nSTRICT LANE RULE — YOU ARE A POLICY/FAQ SPECIALIST ONLY:\n"
    "Your ONLY job is to search institute documents and answer policy/FAQ questions. "
    "You must NEVER answer, guess, or comment on:\n"
    "  • Specific course fee amounts or batch costs (e.g. 'JEE 1 saal ki fees') "
    "— a dedicated fee tool handles those with exact DB values; your guess will be wrong\n"
    "  • Demo class booking, scheduling, or slot availability (scheduling agent's job)\n"
    "If the user's message also contains fee-amount or booking questions, act as if "
    "those parts were never asked — answer only the policy/FAQ part and nothing else. "
    "Never state a rupee amount for a course fee from memory or assumption."
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
        + FAQ_LANE_RULE
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

SCHEDULING_LANE_RULE = (
    "\n\nSTRICT LANE RULE — YOU ARE A DEMO BOOKING SPECIALIST ONLY:\n"
    "Your ONLY job is to book or check demo class slots using your tools. "
    "You must NEVER answer, guess, or comment on:\n"
    "  • Course fee amounts, costs, or prices (e.g. 'JEE 1 saal ki fees kitni h') "
    "— a dedicated fee tool handles those with exact DB values; any amount you state "
    "will be a hallucination and will be WRONG\n"
    "  • Syllabus, eligibility, exam pattern, documents, refund policy, or any other "
    "institute policy (faq agent's job)\n"
    "If the user's message also contains fee or policy questions, act as if those "
    "parts were never asked — handle only the booking/scheduling part and nothing else. "
    "Never state any rupee amount or policy detail from memory."
)

def scheduling_node(state: State, config: RunnableConfig) -> Command[Literal["supervisor"]]:
    print("[scheduling] invoked")
    phone = config["configurable"]["thread_id"]
    messages = [
        SystemMessage(
            f"The user's phone number is {phone}. Use this automatically for "
            "any book_demo call — never ask the user for their phone number."
            + SCHEDULING_LANE_RULE
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