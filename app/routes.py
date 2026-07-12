from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from app.graph import admissions_agent
from app.ingest import ingest as run_ingest
from app.leads import upsert_lead
import shutil, os

router = APIRouter()


class MessageRequest(BaseModel):
    message: str
    thread_id: str
    name: str | None = None
    course_interest: str | None = None


@router.post("/message")
def handle_message(body: MessageRequest):
    result = admissions_agent.invoke(
        {"messages": [{"role": "user", "content": body.message}]},
        config={"recursion_limit": 10, "configurable": {"thread_id": body.thread_id}},
    )

    worker_replies = []
    for msg in reversed(result["messages"]):
        if getattr(msg, "name", None):
            worker_replies.append(msg.content)
        else:
            break
    worker_replies.reverse()

    reply = "\n\n".join(worker_replies)
    print("reply>>>",reply)

    lead_fields = {}
    if body.name:
        lead_fields["name"] = body.name
    if body.course_interest:
        lead_fields["course_interest"] = body.course_interest
    upsert_lead(body.thread_id, **lead_fields)

    return {"reply": reply}


@router.post("/ingest", tags=["Ingest"])
def ingest_route():
    try:
        chunks = run_ingest()
        return {
            "status": "success",
            "message": f"Successfully loaded and split documents into {len(chunks)} chunks."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
