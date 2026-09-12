import requests
from fastapi import APIRouter, UploadFile, File, Form, Response, BackgroundTasks
from pydantic import BaseModel
from app.graph import admissions_agent
from app.ingest import ingest as run_ingest
from app.leads import upsert_lead
from app.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM
from twilio.rest import Client
import shutil, os
from xml.sax.saxutils import escape

router = APIRouter()


class MessageRequest(BaseModel):
    message: str
    thread_id: str
    name: str | None = None
    course_interest: str | None = None


def extract_ai_reply(messages: list) -> str:
    """
    Extracts the appropriate AI response from LangGraph's message history.
    
    Handles multi-turn conversations cleanly:
    1. Identifies the user's latest question (last HumanMessage without worker name).
    2. Collects replies from specialist worker agents (admission, faq, scheduling) for the current turn.
    3. Falls back to any AI response in current turn if worker names were omitted.
    4. Defaults to standard fallback message if current turn yielded no new worker reply (never leaks old turn history).
    """
    print("messages----->", messages)
    if not messages:
        return "Thank you for contacting SahayakAI. How can I assist you today?"

    # Step 1: Find where the user's latest query started (last HumanMessage without a worker name)
    last_human_index = -1
    for index in range(len(messages) - 1, -1, -1):
        msg = messages[index]
        msg_type = getattr(msg, "type", "")
        msg_class = msg.__class__.__name__
        msg_name = getattr(msg, "name", None)
        if (msg_type == "human" or msg_class == "HumanMessage") and not msg_name:
            last_human_index = index
            break

    # Get only the messages generated AFTER the user's latest query
    current_turn_messages = messages[last_human_index + 1:] if last_human_index != -1 else messages

    # Step 2: Collect specialist worker replies (messages with a 'name' attribute like admission, faq, scheduling)
    worker_replies = []
    for msg in current_turn_messages:
        name = getattr(msg, "name", None)
        content = getattr(msg, "content", "")
        if name and content and isinstance(content, str) and content.strip():
            worker_replies.append(content.strip())

    if worker_replies:
        return "\n\n".join(worker_replies)

    # Step 3: If no named worker replies, check for ANY AI response in the current turn
    ai_replies = []
    for msg in current_turn_messages:
        msg_type = getattr(msg, "type", "")
        msg_class = msg.__class__.__name__
        content = getattr(msg, "content", "")
        if (msg_type == "ai" or msg_class == "AIMessage") and content and isinstance(content, str) and content.strip():
            ai_replies.append(content.strip())

    if ai_replies:
        return "\n\n".join(ai_replies)

    # Step 4: Default fallback for current turn
    return "Thank you for contacting SahayakAI. How can I assist you today?"


def process_whatsapp_background(body: str, sender: str):
    """Executes multi-agent graph in background and pushes reply directly to WhatsApp via Twilio API."""
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            result = admissions_agent.invoke(
                {"messages": [{"role": "user", "content": body}]},
                config={"recursion_limit": 10, "configurable": {"thread_id": sender}},
            )

            reply = extract_ai_reply(result.get("messages", []))

            print(f"[WhatsApp Async] From: {sender} | Body: {body}")
            print(f"[WhatsApp Async Reply]: {reply}")

            upsert_lead(sender)

            if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
                resp = requests.post(
                    url,
                    data={
                        "From": TWILIO_WHATSAPP_FROM,
                        "To": sender,
                        "Body": reply,
                    },
                    auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
                    timeout=10,
                )
                if resp.status_code in (200, 201):
                    print(f"[WhatsApp Async Push] Sent reply to {sender}")
                else:
                    print(f"[WhatsApp Async Push Error]: {resp.status_code} - {resp.text}")

            break
        except Exception as e:
            if attempt < max_retries:
                print(f"[WhatsApp Async Warning] Attempt {attempt + 1} failed: {e}. Retrying...")
            else:
                print(f"[WhatsApp Async Error]: {e}")


@router.post("/message")
def handle_message(body: MessageRequest):
    result = admissions_agent.invoke(
        {"messages": [{"role": "user", "content": body.message}]},
        config={"recursion_limit": 10, "configurable": {"thread_id": body.thread_id}},
    )

    reply = extract_ai_reply(result.get("messages", []))
    print("reply>>>", reply)

    lead_fields = {}
    if body.name:
        lead_fields["name"] = body.name
    if body.course_interest:
        lead_fields["course_interest"] = body.course_interest
    upsert_lead(body.thread_id, **lead_fields)

    return {"reply": reply}


@router.post("/whatsapp")
def handle_whatsapp(background_tasks: BackgroundTasks, Body: str = Form(""), From: str = Form("")):
    background_tasks.add_task(process_whatsapp_background, Body, From)
    twiml = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
    return Response(content=twiml, media_type="application/xml")





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
