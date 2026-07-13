from contextlib import ExitStack
from langchain_core.messages import HumanMessage, SystemMessage
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


# --- State ---

class State(MessagesState):
    next: str


# --- Supervisor ---

members = ["admission", "faq", "scheduling"]

class Router(TypedDict):
    next: Literal["admission", "faq", "scheduling", "FINISH"]

system_prompt = f"""
You are a supervisor managing a conversation between these workers: {members}.

- admission: handles ONLY fee, cost, price, charges, and batch-duration questions.
  It looks up exact fee amounts with a tool. Route here for ANY question that asks
  "how much" or "what is the fee/cost" for a course or batch.
- faq: handles questions about syllabus, schedule, eligibility, exam pattern,
  documents required, refund policy, installments, discipline, and other
  institute policy questions, by searching institute documents. Never route
  fee-amount questions here.
- scheduling: handles booking or scheduling a demo class (e.g. "book a demo",
  "schedule a class", "demo class chahiye"). It reserves an actual slot with a
  tool. Route here for ANY request to book, schedule, or reserve a demo class.

Given the user request, choose which worker should act next.
Each worker will respond with their result.
A single worker's response may only cover PART of the user's original question
(each worker ignores topics outside its own scope). Compare what has been
answered so far against the full ORIGINAL user question (not the workers'
replies) to decide what, if anything, is still missing:
- If every distinct topic actually present in the ORIGINAL question (e.g. both
  a fee part and a separate documents/eligibility/policy part) has now been
  addressed, respond with FINISH.
- If admission replies with "{COVERAGE_GATE_REPLY}", treat the fee part as
  fully handled (it is a deliberate final answer, not an incomplete one) —
  do not route to faq to try to find that same fee or batch elsewhere, since
  faq cannot look up fees either. Only route to faq afterward if the ORIGINAL
  question also explicitly asked about something outside fees.
- Never route to a worker to address a topic the user never actually asked
  about.
Do not route to another worker just to double-check or rephrase an answer that
already fully addresses its part of the question.
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

    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    response = llm.with_structured_output(Router).invoke(messages)
    goto = response["next"]
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
            "messages": [HumanMessage(reply, name="admission")]
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
    "Search institute documents to answer questions about syllabus, schedule, eligibility, exam pattern, or admission policy.",
)

faq_react_agent = create_react_agent(
    llm,
    tools=[retriever_tool],
    prompt=(
        "You are a helpful FAQ assistant for a coaching institute. "
        "Answer questions about syllabus, schedules, eligibility, and policies "
        "by searching the institute documents. "
        "You do NOT handle fee, cost, or price questions — another assistant already "
        "handles those. If the user's question includes a fee/cost part, ignore that "
        "part entirely and answer only the non-fee part."
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
            "messages": [HumanMessage(reply, name="faq")]
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
            "messages": [HumanMessage(reply, name="scheduling")]
        },
    )


# --- Graph ---

workflow = StateGraph(State)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("admission", admission_node)
workflow.add_node("faq", faq_node)
workflow.add_node("scheduling", scheduling_node)

workflow.add_edge(START, "supervisor")

# The connection stays open for the lifetime of the process (module-level,
# same as admissions_agent below); ExitStack just avoids leaving the
# PostgresSaver.from_conn_string context manager unentered.
_checkpointer_ctx = ExitStack()
checkpointer = _checkpointer_ctx.enter_context(PostgresSaver.from_conn_string(DATABASE_URL))

# One-time setup: creates the checkpointer's own tables if they don't exist yet.
# Safe to call on every startup — it only does work the first time.
checkpointer.setup()

admissions_agent = workflow.compile(checkpointer=checkpointer)

with open("graph.png", "wb") as f:
    f.write(admissions_agent.get_graph().draw_mermaid_png())