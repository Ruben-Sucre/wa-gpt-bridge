import os
import httpx
import logging

logger = logging.getLogger(__name__)


WHATSAPP_API_VERSION = "v21.0"


class WhatsAppClient:
    def __init__(self, token: str | None = None, phone_id: str | None = None):
        self.token = token or os.getenv("WHATSAPP_TOKEN")
        self.phone_id = phone_id or os.getenv("WHATSAPP_PHONE_ID")
        self.base = "https://graph.facebook.com"

    async def send_text_message(self, to: str, text: str) -> dict:
        if not self.token or not self.phone_id:
            raise RuntimeError("WhatsApp credentials not configured")
        url = f"{self.base}/{WHATSAPP_API_VERSION}/{self.phone_id}/messages"
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, json=payload, headers=headers)
            if not r.is_success:
                logger.error(f"WhatsApp API error {r.status_code}: {r.text}")
            r.raise_for_status()
            return r.json()
