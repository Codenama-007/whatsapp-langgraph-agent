import os
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Form, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from twilio.request_validator import RequestValidator
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

from agent import get_agent_response

load_dotenv()

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
# Twilio sandbox default is "whatsapp:+14155238886"
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")
# Your public URL, e.g. https://abcd.ngrok-free.app (no trailing slash)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

# true  -> reply instantly with empty TwiML, send the answer later via REST API
#          (use this if your local model takes more than ~10 seconds)
# false -> reply directly in the webhook response (simplest)
ASYNC_REPLY = os.getenv("ASYNC_REPLY", "false").lower() == "true"
# Set to false only while testing locally without PUBLIC_BASE_URL
VALIDATE_SIGNATURE = os.getenv("VALIDATE_SIGNATURE", "true").lower() == "true"

MAX_WA_CHARS = 1500  # WhatsApp/Twilio hard limit is 1600 per message

validator = RequestValidator(TWILIO_AUTH_TOKEN or "")
twilio_client = (
    Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN
    else None
)

app = FastAPI()


def split_message(text: str, limit: int = MAX_WA_CHARS) -> list[str]:
    text = text.strip() or "Sorry, I couldn't come up with a reply."
    return [text[i:i + limit] for i in range(0, len(text), limit)]


def generate_reply(user_text: str, thread_id: str) -> str:
    try:
        return get_agent_response(user_text, thread_id=thread_id)
    except Exception as e:
        print(f"Agent error: {e}")
        return "Sorry, something went wrong. Please try again."


def send_reply_via_api(to_number: str, user_text: str):
    reply = generate_reply(user_text, thread_id=to_number)
    for part in split_message(reply):
        twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER, to=to_number, body=part
        )


@app.get("/")
def home_route():
    return {"message": "WhatsApp AI agent is running"}


@app.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    From: str = Form(...),
    Body: str = Form(""),
):
    # 1. Verify the request really came from Twilio
    if VALIDATE_SIGNATURE:
        form = await request.form()
        signature = request.headers.get("X-Twilio-Signature", "")
        url = f"{PUBLIC_BASE_URL}/whatsapp" if PUBLIC_BASE_URL else str(request.url)
        if not validator.validate(url, dict(form), signature):
            raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    resp = MessagingResponse()
    user_text = Body.strip()

    # 2. Handle empty messages (e.g. images/voice notes)
    if not user_text:
        resp.message("I can only read text messages for now.")
        return Response(content=str(resp), media_type="application/xml")

    # 3a. Async mode: acknowledge now, answer when the model is done
    if ASYNC_REPLY:
        if twilio_client is None:
            raise HTTPException(500, "Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
        background_tasks.add_task(send_reply_via_api, From, user_text)
        return Response(content=str(resp), media_type="application/xml")

    # 3b. Sync mode: answer inside the webhook (Twilio waits ~15s max)
    reply = await run_in_threadpool(generate_reply, user_text, From)
    for part in split_message(reply):
        resp.message(part)
    return Response(content=str(resp), media_type="application/xml")