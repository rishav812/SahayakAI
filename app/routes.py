from fastapi import APIRouter
from pydantic import BaseModel
from app.config import OPENAI_API_KEY, llm_with_tools

router = APIRouter()


class MessageRequest(BaseModel):
    course: str
    batch: str


@router.post("/message")
def handle_message(body: MessageRequest):
    resp = llm_with_tools.invoke("JEE 2 saal ki fees kitni hai?")
    print(resp.tool_calls)
    return {"reply": f"Fee lookup result: {resp}"}
