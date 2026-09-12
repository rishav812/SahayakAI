# SahayakAI — Project Overview & Deployment Planning Reference

## Brief

SahayakAI is a WhatsApp-first assistant for coaching institutes (JEE/NEET/foundation
centres, Tier-2/3 India) that answers parent and student queries in Hindi, books demo
classes, sends fee/demo reminders, and hands off to a human counsellor when needed. It
is built as a multi-agent system with a supervisor that routes each incoming message to
one or more specialist agents.

| Agent | Responsibility |
|---|---|
| Supervisor | Classifies intent and routes each message to the right specialist |
| Admissions agent | Answers fee/batch questions via a tool-backed lookup, qualifies leads |
| Scheduling agent | Books demo classes; sends fee-due and demo reminders |
| Doubt / FAQ agent | Answers syllabus/policy questions via RAG over institute docs |
| Human handoff | Notifies a counsellor with full transcript on escalation |

Current build stage (per README): API + supervisor + multi-agent LangGraph routing +
persistent per-user conversation state are implemented. Real WhatsApp channel wiring
and proactive reminders/analytics are not yet implemented.

## Tech stack

- **Language / runtime:** Python 3.10
- **Web framework:** FastAPI, served by Uvicorn
- **Agent orchestration:** LangGraph (`StateGraph`, supervisor pattern with
  `Command`-based routing between nodes)
- **LLM:** OpenAI `gpt-4o-mini` via `langchain-openai` (README lists Claude/Sarvam as a
  target for Indic-language support, but the current code path uses OpenAI only)
- **Embeddings:** OpenAI embeddings (`langchain-openai`)
- **Vector store / RAG:** Chroma, persisted locally to `chroma_db/`, used by the FAQ
  agent to search institute documents
- **Conversation state / checkpointing:** `langgraph-checkpoint-postgres`
  (`PostgresSaver`) — persists LangGraph thread state per `thread_id` (phone number)
- **Relational database:** PostgreSQL — also used directly (via SQLAlchemy 2.0 +
  `psycopg` v3) for app tables: `leads` and `demo_slots`
- **Messaging channel (planned):** WhatsApp Business Platform — `.env` currently holds
  Twilio-style credentials (`account_sid`, `auth_token`), but no code in `app/`
  currently references them; channel integration is not yet wired up
- **Testing:** pytest
- **Dependency management:** `requirements.txt` / pip, local `.venv`

## Project infra (current state)

- No containerization — no Dockerfile in the repo.
- No infrastructure-as-code (Terraform/CDK/etc.) present.
- No CI/CD pipeline present yet (no `.github/workflows/`).
- Runs as a single process: `uvicorn app.main:app --host 0.0.0.0 --port 8000` (must be
  run from the repo root — `app/main.py` uses `from app.routes import router`).
- Configuration is loaded from a local `.env` file via `python-dotenv` (gitignored).
  Known variables: `OPENAI_API_KEY`, `DATABASE_URL`, `account_sid`, `auth_token`.
- Local persistent artifacts:
  - `chroma_db/` — Chroma vector store (relative path, sensitive to process working
    directory)
  - `data/sample_policy.txt` — source document ingested into Chroma via the `/ingest`
    endpoint
  - `graph.png` — LangGraph graph diagram, regenerated at **import time** in
    `app/graph.py` via a network call to `mermaid.ink`
- Database tables (`leads`, `demo_slots`, and the LangGraph checkpoint tables) are
  auto-created on app import/startup — there is no separate migration step.
- A prior, untracked `DEPLOYMENT.md` in this repo already documents one specific target
  deployment: single AWS EC2 instance + RDS PostgreSQL, no Docker, systemd + Nginx
  reverse proxy, GitHub Actions CI/CD — see that file for the step-by-step guide.

## Application structure

- `app/main.py` — FastAPI entrypoint, root health check (`GET /`)
- `app/routes.py` — `POST /message` (invokes the agent graph), `POST /ingest` (loads
  docs into Chroma)
- `app/graph.py` — LangGraph `StateGraph`: supervisor node + admission/faq/scheduling
  agent nodes; opens the Postgres checkpointer connection at import time
- `app/scheduling_agent.py`, `app/booking_tool.py`, `app/demo_slots.py` — demo booking
  agent and its Postgres-backed slot table
- `app/tools.py`, `app/fees.py` — fee lookup tool logic
- `app/leads.py` — Postgres-backed leads/CRM table, upserted on every inbound message
- `app/ingest.py` — loads and splits documents into the Chroma store
- `app/config.py` — env loading, LLM/embeddings client construction
- `data/` — source documents for RAG ingestion
- `tests/` — pytest suite

## External dependencies (must be reachable at runtime)

- **OpenAI API** — required for every LLM call and for embeddings; needs
  `OPENAI_API_KEY` and outbound internet access.
- **PostgreSQL** — required at process **startup**, not just at request time:
  `app/graph.py` connects and runs checkpointer setup at import time, so the app will
  not start if the database is unreachable.
- **mermaid.ink** — called at import time in `app/graph.py` to regenerate `graph.png`;
  an external, non-essential dependency that currently sits on the app's startup path.
- **WhatsApp Business Platform** — planned channel, not yet integrated into the code.

## Known items relevant to deployment planning

- `CHROMA_DIR = "chroma_db"` in `app/config.py` is a relative path — whatever directory
  the process starts from becomes its effective storage location.
- The `mermaid.ink` call at import time means app startup depends on an external
  service being reachable; a network/egress issue there currently blocks the whole app
  from starting.
- Secrets (`OPENAI_API_KEY`, `DATABASE_URL`, `account_sid`, `auth_token`) currently live
  only in a local, gitignored `.env` file — there is no secrets-manager integration yet.
- The root README's documented run command (`uvicorn main:app --reload`) is stale
  relative to the actual package layout (`app.main:app`, run from repo root).
