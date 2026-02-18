import os
import logging
from pathlib import Path
from fastapi import FastAPI, Request, Header, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()

from .validation import IncomingWhatsApp
from .cleaner import clean_text
from .memory import ConversationMemory
from .openai_client import OpenAIClient
from .gemini_client import GeminiClient
from .whatsapp_client import WhatsAppClient

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()

# Load system prompt
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8").strip() if PROMPT_PATH.exists() else ""

app = FastAPI(title="wa-gpt-bridge-bot")

memory = ConversationMemory(REDIS_URL)
whatsapp_client = WhatsAppClient(token=os.getenv("WHATSAPP_TOKEN"), phone_id=os.getenv("WHATSAPP_PHONE_ID"))

if LLM_PROVIDER == "gemini":
    llm_client = GeminiClient(api_key=os.getenv("GOOGLE_API_KEY"), model=GEMINI_MODEL)
elif LLM_PROVIDER == "openai":
    llm_client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"), model=OPENAI_MODEL)
else:
    raise ValueError("Unsupported LLM_PROVIDER; use 'openai' or 'gemini'")


class WebhookResponse(BaseModel):
    delivered: bool = True
    detail: str | None = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/webhook/whatsapp", response_model=WebhookResponse)
async def whatsapp_webhook(payload: IncomingWhatsApp, x_bot_secret: str | None = Header(None)):
    secret = os.getenv("BOT_SECRET")
    if secret and x_bot_secret != secret:
        logger.warning(f"Unauthorized access attempt from {payload.from_number}")
        raise HTTPException(status_code=401, detail="invalid secret")

    sender = payload.from_number
    text = clean_text(payload.text)

    logger.info(f"Processing message from {sender}. Provider: {LLM_PROVIDER}")

    try:
        # 1. Assemble context
        history = await memory.get_conversation(sender)

        # 2. Save user message to Redis
        await memory.append_message(sender, "user", text)

        # 3. Build messages payload
        messages = []
        if SYSTEM_PROMPT:
            messages.append({"role": "system", "content": SYSTEM_PROMPT})
        
        messages.extend(history)
        messages.append({"role": "user", "content": text})

        # 4. Call LLM
        logger.debug(f"Sending {len(messages)} messages to {LLM_PROVIDER}...")
        resp = await llm_client.chat(messages)
        assistant_text = resp.strip()
        logger.info(f"Generated response for {sender} ({len(assistant_text)} chars)")

        # 5. Save assistant response
        await memory.append_message(sender, "assistant", assistant_text)

        # 6. Send directly via WhatsApp
        try:
            await whatsapp_client.send_text_message(sender, assistant_text)
        except Exception as send_err:
            logger.warning(f"Failed to send WhatsApp message to {sender}: {send_err}")
            return WebhookResponse(delivered=False, detail="LLM OK, WhatsApp send failed")
        
        return WebhookResponse(delivered=True)

    except Exception as e:
        logger.error(f"Error processing message for {sender}: {str(e)}", exc_info=True)
        # Return partial failure so n8n or the caller knows it failed but doesn't crash 500
        return WebhookResponse(delivered=False, detail=f"Processing failed: {str(e)}")
