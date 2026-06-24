# SahayakAI — WhatsApp Multi-Agent Ops Assistant for Coaching Institutes

A WhatsApp-first assistant for coaching institutes that answers parent and student queries in Hindi, books demo classes, sends fee and demo reminders, and hands off to a human counsellor when needed — built on a multi-agent architecture with a supervisor routing to specialist agents.

---

## Problem

Small coaching institutes (JEE/NEET/foundation centres across Tier-2/3 India) run admissions and student communication almost entirely over WhatsApp, in Hindi. Counsellors spend hours daily on repetitive work: answering the same fee/batch questions, chasing cold leads, and sending reminders. After office hours, this work simply doesn't happen — leads leak and fees slip.

---

## What it does

| Agent | Responsibility |
|---|---|
| **Supervisor** | Classifies intent and routes each message to the right specialist |
| **Admissions agent** | Answers fees/batch/eligibility, qualifies leads, nudges toward a demo |
| **Scheduling agent** | Books demo classes; sends fee-due and demo reminders |
| **Doubt / FAQ agent** | Answers syllabus and policy questions; escalates when unsure |
| **Human handoff** | Notifies a counsellor with full transcript on escalation |

---

## Tech stack

- **Backend:** FastAPI (Python)
- **Orchestration:** LangGraph
- **LLM:** Claude / Sarvam APIs (for Indic-language support)
- **Retrieval:** Chroma (RAG over policy/syllabus docs)
- **Database:** PostgreSQL (CRM, conversation state, fee/batch tables)
- **Channel:** WhatsApp Business Platform (Meta)

---

## Build phases

| Phase | Goal |
|---|---|
| 0 | Setup — repo, venv, FastAPI, README ✅ |
| 1 | Walking skeleton — API returns a hardcoded reply ✅ |
| 2 | One smart agent (LLM with fake institute data) |
| 3 | Grounding — table lookups + RAG + coverage gate |
| 4 | Supervisor + multi-agent via LangGraph |
| 5 | Persistent per-user conversation state |
| 6 | Real WhatsApp channel |
| 7 | Polish — handoff, proactive reminders, analytics |

---

## How to run

```bash
# 1. Activate the virtual environment
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
uvicorn main:app --reload
```

Server runs at `http://127.0.0.1:8000`.

**Test the health check:**
```bash
curl http://127.0.0.1:8000/
```

**Test the message endpoint:**
```bash
curl -X POST http://127.0.0.1:8000/message \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"hi\"}"
```
