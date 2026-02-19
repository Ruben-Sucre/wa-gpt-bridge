"""
Fixtures compartidas para todos los tests del bot.
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient


# Variables de entorno mínimas para que la app arranque
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("LLM_PROVIDER", "gemini")
os.environ.setdefault("GOOGLE_API_KEY", "test-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.0-flash")
os.environ.setdefault("WHATSAPP_TOKEN", "test-token")
os.environ.setdefault("WHATSAPP_PHONE_ID", "123456789")
os.environ.setdefault("BOT_SECRET", "test-secret")


@pytest.fixture()
def app_client(mocker):
    """
    TestClient con todas las dependencias externas mockeadas:
    - Redis (memory, rate_limiter)
    - LLM (gemini/openai)
    - WhatsApp API
    """
    # Mockear Redis / memory
    mock_memory = MagicMock()
    mock_memory.ping = AsyncMock(return_value=True)
    mock_memory.get_conversation = AsyncMock(return_value=[])
    mock_memory.append_message = AsyncMock()
    mocker.patch("app.main.memory", mock_memory)

    # Mockear rate limiter — por defecto permite pasar
    mock_rl = MagicMock()
    mock_rl.check_rate_limit = AsyncMock(return_value=(True, 1, 10))
    mocker.patch("app.main.rate_limiter", mock_rl)

    # Mockear LLM
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value="Respuesta de prueba del bot.")
    mocker.patch("app.main.llm_client", mock_llm)

    # Mockear WhatsApp client
    mock_wa = MagicMock()
    mock_wa.send_text_message = AsyncMock(return_value={"messages": [{"id": "wamid.test"}]})
    mocker.patch("app.main.whatsapp_client", mock_wa)

    from app.main import app
    return TestClient(app)


# Payload estándar que envía Meta cuando llega un mensaje de texto
META_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [{
        "changes": [{
            "value": {
                "messages": [{
                    "from": "5215627698201",
                    "type": "text",
                    "text": {"body": "Hola bot"}
                }]
            }
        }]
    }]
}

# Payload que envía Meta para status updates (delivery receipts)
META_STATUS_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [{
        "changes": [{
            "value": {
                "statuses": [{
                    "id": "wamid.test",
                    "status": "delivered",
                    "recipient_id": "5215627698201"
                }]
            }
        }]
    }]
}
