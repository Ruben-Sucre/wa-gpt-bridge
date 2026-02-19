"""
Tests del endpoint GET /webhook/whatsapp — verificación de Meta.
"""
import pytest
from tests.conftest import META_PAYLOAD, META_STATUS_PAYLOAD


class TestWebhookVerification:

    def test_challenge_respondido_correctamente(self, app_client):
        """Meta llama GET con hub.challenge y debe recibir exactamente ese valor."""
        r = app_client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "cualquier-cosa",
                "hub.challenge": "ABC123"
            }
        )
        assert r.status_code == 200
        assert r.text == "ABC123"

    def test_sin_hub_mode_devuelve_403(self, app_client):
        """Sin hub.mode el bot debe rechazar la verificación."""
        r = app_client.get("/webhook/whatsapp")
        assert r.status_code == 403

    def test_sin_challenge_devuelve_403(self, app_client):
        """Sin hub.challenge el bot no tiene nada que devolver."""
        r = app_client.get(
            "/webhook/whatsapp",
            params={"hub.mode": "subscribe"}
        )
        assert r.status_code == 403


class TestWebhookMensajeEntrante:

    def test_mensaje_meta_procesado_correctamente(self, app_client):
        """Payload nativo de Meta → bot lo procesa y responde 200 delivered=True."""
        r = app_client.post("/webhook/whatsapp", json=META_PAYLOAD)
        assert r.status_code == 200
        assert r.json()["delivered"] is True

    def test_mensaje_meta_llama_llm(self, app_client, mocker):
        """Verifica que el LLM se llama cuando llega un mensaje."""
        from app.main import llm_client
        app_client.post("/webhook/whatsapp", json=META_PAYLOAD)
        llm_client.chat.assert_awaited_once()

    def test_mensaje_meta_envia_por_whatsapp(self, app_client, mocker):
        """Verifica que se intenta enviar la respuesta por WhatsApp."""
        from app.main import whatsapp_client
        app_client.post("/webhook/whatsapp", json=META_PAYLOAD)
        whatsapp_client.send_text_message.assert_awaited_once()

    def test_status_update_ignorado_sin_error(self, app_client):
        """Delivery receipts de Meta no deben causar error — se ignoran silenciosamente."""
        r = app_client.post("/webhook/whatsapp", json=META_STATUS_PAYLOAD)
        assert r.status_code == 200
        assert r.json()["delivered"] is False
        assert "not a message event" in r.json()["detail"]

    def test_mensaje_tipo_imagen_ignorado(self, app_client):
        """Mensajes no-texto (imágenes, audio) se ignoran con mensaje claro."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{"changes": [{"value": {"messages": [{
                "from": "5215627698201",
                "type": "image",
                "image": {"id": "img123"}
            }]}}]}]
        }
        r = app_client.post("/webhook/whatsapp", json=payload)
        assert r.status_code == 200
        assert r.json()["delivered"] is False
        assert "image" in r.json()["detail"]

    def test_json_invalido_devuelve_400(self, app_client):
        """Body que no es JSON devuelve 400."""
        r = app_client.post(
            "/webhook/whatsapp",
            content=b"no soy json",
            headers={"Content-Type": "application/json"}
        )
        assert r.status_code == 400

    def test_formato_interno_requiere_secret(self, app_client):
        """Payload interno (n8n) sin el secret correcto devuelve 401."""
        r = app_client.post(
            "/webhook/whatsapp",
            json={"from": "521111111111", "text": "hola"},
            headers={"x-bot-secret": "secreto-incorrecto"}
        )
        assert r.status_code == 401

    def test_formato_interno_con_secret_correcto(self, app_client):
        """Payload interno con secret correcto se procesa."""
        r = app_client.post(
            "/webhook/whatsapp",
            json={"from": "521111111111", "text": "hola"},
            headers={"x-bot-secret": "test-secret"}
        )
        assert r.status_code == 200
        assert r.json()["delivered"] is True


class TestRateLimiting:

    def test_rate_limit_excedido_devuelve_delivered_false(self, app_client, mocker):
        """Cuando rate limit se excede, bot responde pero no procesa."""
        from app.main import rate_limiter
        from unittest.mock import AsyncMock
        rate_limiter.check_rate_limit = AsyncMock(return_value=(False, 11, 10))

        r = app_client.post("/webhook/whatsapp", json=META_PAYLOAD)
        assert r.status_code == 200
        assert r.json()["delivered"] is False
        assert "rate limit" in r.json()["detail"]


class TestHealth:

    def test_health_ok(self, app_client):
        """Health endpoint devuelve status ok cuando Redis funciona."""
        r = app_client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["checks"]["redis"] == "ok"
        assert data["checks"]["whatsapp_credentials"] == "ok"

    def test_health_degraded_sin_redis(self, app_client, mocker):
        """Health devuelve degraded cuando Redis no responde."""
        from app.main import memory
        from unittest.mock import AsyncMock
        memory.ping = AsyncMock(return_value=False)

        r = app_client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "degraded"
        assert r.json()["checks"]["redis"] == "failed"
