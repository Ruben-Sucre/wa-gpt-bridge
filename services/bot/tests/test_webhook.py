"""
Tests del endpoint GET /webhook/whatsapp — verificación de Meta.
"""
import pytest
from tests.conftest import META_PAYLOAD


class TestWebhookVerification:

    def test_challenge_respondido_correctamente(self, app_client):
        """Meta llama GET con hub.challenge y debe recibir exactamente ese valor."""
        r = app_client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test-verify-token",
                "hub.challenge": "ABC123"
            }
        )
        assert r.status_code == 200
        assert r.text == "ABC123"

    def test_verify_token_invalido_devuelve_403(self, app_client):
        """Con verify token incorrecto el bot rechaza la verificación."""
        r = app_client.get(
            "/webhook/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "invalido",
                "hub.challenge": "ABC123"
            }
        )
        assert r.status_code == 403

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

    def test_mensaje_meta_directo_bloqueado(self, app_client):
        """Payload directo de Meta se bloquea cuando el bot es interno-only."""
        r = app_client.post(
            "/webhook/whatsapp",
            json=META_PAYLOAD,
            headers={"x-bot-secret": "test-secret"}
        )
        assert r.status_code == 403

    def test_mensaje_interno_llama_llm(self, app_client, mocker):
        """Verifica que el LLM se llama para payload interno autorizado."""
        from app.main import llm_client
        app_client.post(
            "/webhook/whatsapp",
            json={"from": "521111111111", "text": "hola"},
            headers={"x-bot-secret": "test-secret"}
        )
        llm_client.chat.assert_awaited_once()

    def test_mensaje_interno_envia_por_whatsapp(self, app_client, mocker):
        """Verifica que se intenta enviar la respuesta por WhatsApp."""
        from app.main import whatsapp_client
        app_client.post(
            "/webhook/whatsapp",
            json={"from": "521111111111", "text": "hola"},
            headers={"x-bot-secret": "test-secret"}
        )
        whatsapp_client.send_text_message.assert_awaited_once()

    def test_json_invalido_devuelve_400(self, app_client):
        """Body que no es JSON devuelve 400."""
        r = app_client.post(
            "/webhook/whatsapp",
            content=b"no soy json",
            headers={
                "Content-Type": "application/json",
                "x-bot-secret": "test-secret",
            }
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

        r = app_client.post(
            "/webhook/whatsapp",
            json={"from": "521111111111", "text": "hola"},
            headers={"x-bot-secret": "test-secret"}
        )
        assert r.status_code == 200
        assert r.json()["delivered"] is False
        assert "rate limit" in r.json()["detail"]

    def test_rate_limit_excedido_no_llama_llm(self, app_client, mocker):
        """Con rate limit excedido no se debe llamar al proveedor LLM."""
        from app.main import rate_limiter, llm_client
        from unittest.mock import AsyncMock
        rate_limiter.check_rate_limit = AsyncMock(return_value=(False, 11, 10))

        r = app_client.post(
            "/webhook/whatsapp",
            json={"from": "521111111111", "text": "hola"},
            headers={"x-bot-secret": "test-secret"}
        )

        assert r.status_code == 200
        assert r.json()["delivered"] is False
        llm_client.chat.assert_not_awaited()


class TestErrorSanitization:

    def test_error_no_filtra_detalle_interno(self, app_client, mocker):
        """Errores de procesamiento no deben filtrar detalles sensibles al cliente."""
        from app.main import llm_client
        from unittest.mock import AsyncMock
        llm_client.chat = AsyncMock(side_effect=RuntimeError("openai key sk-test filtrada"))

        r = app_client.post(
            "/webhook/whatsapp",
            json={"from": "521111111111", "text": "hola"},
            headers={"x-bot-secret": "test-secret"}
        )
        assert r.status_code == 200
        assert r.json()["delivered"] is False
        assert r.json()["detail"] == "processing failed"


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
