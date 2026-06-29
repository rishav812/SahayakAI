from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from app.graph import admissions_agent
from app.ingest import ingest as run_ingest
import shutil, os

router = APIRouter()


class MessageRequest(BaseModel):
    message: str


@router.post("/message")
def handle_message(body: MessageRequest):
    result = admissions_agent.invoke(
        {"messages": [{"role": "user", "content": body.message}]},
        config={"recursion_limit": 10},
    )
    reply = result["messages"][-1].content
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
