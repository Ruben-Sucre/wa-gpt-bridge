import os
import logging
from pathlib import Path
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
# Prevent httpx from logging full URLs (which may contain credentials)
logging.getLogger("httpx").setLevel(logging.WARNING)

from .validation import IncomingWhatsApp
from .cleaner import clean_text
from .memory import ConversationMemory
from .openai_client import OpenAIClient
from .gemini_client import GeminiClient
from .whatsapp_client import WhatsAppClient
from .rate_limiter import RateLimiter

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
BOT_SECRET = os.getenv("BOT_SECRET")
WEBHOOK_VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN")
ALLOW_DIRECT_META_WEBHOOK = os.getenv("ALLOW_DIRECT_META_WEBHOOK", "false").lower() in {"1", "true", "yes", "on"}

# Load system prompt
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "system_prompt.txt"
SYSTEM_PROMPT = PROMPT_PATH.read_text(encoding="utf-8").strip() if PROMPT_PATH.exists() else ""

app = FastAPI(title="wa-gpt-bridge-bot")

memory = ConversationMemory(REDIS_URL)
rate_limiter = RateLimiter(REDIS_URL, max_requests=10, window_seconds=60)
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


def _mask_sender(sender: str) -> str:
    digits = "".join(char for char in sender if char.isdigit())
    if len(digits) <= 4:
        return "***"
    return f"***{digits[-4:]}"


@app.get("/health")
async def health():
    """
    Health check endpoint with dependency verification.
    Returns detailed status of critical components.
    """
    status = {
        "status": "ok",
        "llm_provider": LLM_PROVIDER,
        "checks": {}
    }
    
    # Check Redis connectivity
    redis_ok = await memory.ping()
    status["checks"]["redis"] = "ok" if redis_ok else "failed"
    
    # Check WhatsApp credentials configuration using already-loaded client
    wa_token = whatsapp_client.token or ""
    wa_phone = whatsapp_client.phone_id or ""
    whatsapp_configured = (
        bool(wa_token) and
        bool(wa_phone) and
        not wa_token.startswith("EAA_PEGA") and
        not wa_phone.startswith("TU_PHONE")
    )
    status["checks"]["whatsapp_credentials"] = "ok" if whatsapp_configured else "not_configured"
    
    # Overall health status
    if not redis_ok:
        status["status"] = "degraded"
    
    return status


@app.get("/webhook/whatsapp")
async def whatsapp_verify(request: Request):
    """Meta webhook verification (hub.challenge handshake)."""
    params = dict(request.query_params)
    mode = params.get("hub.mode")
    challenge = params.get("hub.challenge")
    token = params.get("hub.verify_token")
    logger.info(f"Webhook verification attempt: mode={mode}")
    if mode == "subscribe" and challenge:
        if WEBHOOK_VERIFY_TOKEN and token != WEBHOOK_VERIFY_TOKEN:
            logger.warning("Webhook verification rejected: invalid verify token")
            raise HTTPException(status_code=403, detail="Verification failed")
        return PlainTextResponse(content=challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook/whatsapp", response_model=WebhookResponse)
async def whatsapp_webhook(request: Request, x_bot_secret: str | None = Header(None)):
    if not BOT_SECRET:
        logger.error("BOT_SECRET is not configured")
        raise HTTPException(status_code=503, detail="service misconfigured")

    if x_bot_secret != BOT_SECRET:
        logger.warning("Unauthorized webhook access attempt")
        raise HTTPException(status_code=401, detail="invalid secret")

    # Parse raw body — Meta sends nested payload, internal callers send simple one
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON")

    # Detect Meta's native payload format
    if "object" in body and "entry" in body:
        if not ALLOW_DIRECT_META_WEBHOOK:
            logger.warning("Direct Meta webhook payload rejected by policy")
            raise HTTPException(status_code=403, detail="direct webhook disabled")
        try:
            msg = body["entry"][0]["changes"][0]["value"]["messages"][0]
            sender = msg["from"]
            msg_type = msg.get("type", "")
            if msg_type != "text":
                logger.info(f"Ignoring non-text message type: {msg_type}")
                return WebhookResponse(delivered=False, detail=f"unsupported type: {msg_type}")
            text_body = msg["text"]["body"]
        except (KeyError, IndexError, TypeError) as e:
            # Could be a status update (delivery receipt, etc.) — ignore silently
            logger.debug(f"Non-message webhook event ignored: {e}")
            return WebhookResponse(delivered=False, detail="not a message event")
    else:
        # Internal format from n8n or tests: {"from": "...", "text": "..."}
        try:
            payload = IncomingWhatsApp(**body)
            sender = payload.from_number
            text_body = payload.text
        except Exception:
            raise HTTPException(status_code=422, detail="invalid payload")

    text = clean_text(text_body)

    # Rate limiting check
    is_allowed, current_count, limit = await rate_limiter.check_rate_limit(sender)
    if not is_allowed:
        logger.warning(f"Rate limit exceeded for {_mask_sender(sender)}: {current_count}/{limit}")
        rate_limit_msg = (
            "Has alcanzado el límite de mensajes. "
            f"Por favor espera un momento antes de enviar más mensajes. (Límite: {limit} mensajes por minuto)"
        )
        try:
            await whatsapp_client.send_text_message(sender, rate_limit_msg)
        except Exception:
            pass  # Best effort notification
        return WebhookResponse(delivered=False, detail="rate limit exceeded")

    logger.info(f"Processing message from {_mask_sender(sender)}. Provider: {LLM_PROVIDER}")

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
        logger.info(f"Generated response for {_mask_sender(sender)} ({len(assistant_text)} chars)")

        # 5. Save assistant response
        await memory.append_message(sender, "assistant", assistant_text)

        # 6. Send directly via WhatsApp
        try:
            await whatsapp_client.send_text_message(sender, assistant_text)
        except Exception as send_err:
            logger.warning(f"Failed to send WhatsApp message to {_mask_sender(sender)}: {send_err}")
            return WebhookResponse(delivered=False, detail="LLM OK, WhatsApp send failed")
        
        return WebhookResponse(delivered=True)

    except Exception as e:
        logger.error(f"Error processing message for {_mask_sender(sender)}: {str(e)}", exc_info=True)
        return WebhookResponse(delivered=False, detail="processing failed")
