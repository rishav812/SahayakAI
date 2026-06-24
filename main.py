from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class MessageRequest(BaseModel):
    message: str


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/message")
def handle_message(body: MessageRequest):
    return {"reply": f"Hello! This is a hardcoded reply. You said: {body.message}"}
