import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.gemini_client import GeminiClient


def test_constructor_sin_api_key_lanza_error(mocker):
    mocker.patch("app.gemini_client.os.getenv", return_value=None)
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        GeminiClient(api_key=None)


@pytest.mark.asyncio
async def test_chat_mapea_roles_y_system_instruction(mocker):
    response_mock = MagicMock()
    response_mock.raise_for_status = MagicMock()
    response_mock.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"text": "hola "}, {"text": "mundo"}]}}
        ]
    }

    post_mock = AsyncMock(return_value=response_mock)
    client_in_context = MagicMock(post=post_mock)
    async_client_cm = MagicMock()
    async_client_cm.__aenter__ = AsyncMock(return_value=client_in_context)
    async_client_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch("app.gemini_client.httpx.AsyncClient", return_value=async_client_cm)

    client = GeminiClient(api_key="g-test", model="gemini-2.0-flash")
    messages = [
        {"role": "system", "content": "Regla 1"},
        {"role": "system", "content": "Regla 2"},
        {"role": "user", "content": "hola"},
        {"role": "assistant", "content": "respuesta previa"},
        {"role": "user", "content": "   "},
    ]

    result = await client.chat(messages)

    assert result == "hola mundo"
    post_mock.assert_awaited_once()
    call = post_mock.await_args
    assert call.args[0] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    assert call.kwargs["headers"]["x-goog-api-key"] == "g-test"

    payload = call.kwargs["json"]
    assert payload["system_instruction"]["parts"][0]["text"] == "Regla 1\nRegla 2"
    assert payload["contents"] == [
        {"role": "user", "parts": [{"text": "hola"}]},
        {"role": "model", "parts": [{"text": "respuesta previa"}]},
    ]


@pytest.mark.asyncio
async def test_chat_respuesta_inesperada_devuelve_vacio(mocker):
    response_mock = MagicMock()
    response_mock.raise_for_status = MagicMock()
    response_mock.json.return_value = {"unexpected": True}

    post_mock = AsyncMock(return_value=response_mock)
    client_in_context = MagicMock(post=post_mock)
    async_client_cm = MagicMock()
    async_client_cm.__aenter__ = AsyncMock(return_value=client_in_context)
    async_client_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch("app.gemini_client.httpx.AsyncClient", return_value=async_client_cm)

    client = GeminiClient(api_key="g-test", model="gemini-2.0-flash")
    result = await client.chat([{"role": "user", "content": "hola"}])

    assert result == ""


@pytest.mark.asyncio
async def test_chat_candidates_sin_texto_devuelve_vacio(mocker):
    response_mock = MagicMock()
    response_mock.raise_for_status = MagicMock()
    response_mock.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"foo": "bar"}]}}
        ]
    }

    post_mock = AsyncMock(return_value=response_mock)
    client_in_context = MagicMock(post=post_mock)
    async_client_cm = MagicMock()
    async_client_cm.__aenter__ = AsyncMock(return_value=client_in_context)
    async_client_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch("app.gemini_client.httpx.AsyncClient", return_value=async_client_cm)

    client = GeminiClient(api_key="g-test", model="gemini-2.0-flash")
    result = await client.chat([{"role": "user", "content": "hola"}])

    assert result == ""


@pytest.mark.asyncio
async def test_chat_error_http_se_propaga(mocker):
    request = httpx.Request("POST", "https://generativelanguage.googleapis.com")
    response = httpx.Response(500, request=request)
    http_error = httpx.HTTPStatusError("server error", request=request, response=response)

    response_mock = MagicMock()
    response_mock.raise_for_status = MagicMock(side_effect=http_error)
    response_mock.json.return_value = {}

    post_mock = AsyncMock(return_value=response_mock)
    client_in_context = MagicMock(post=post_mock)
    async_client_cm = MagicMock()
    async_client_cm.__aenter__ = AsyncMock(return_value=client_in_context)
    async_client_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch("app.gemini_client.httpx.AsyncClient", return_value=async_client_cm)

    client = GeminiClient(api_key="g-test", model="gemini-2.0-flash")

    with pytest.raises(httpx.HTTPStatusError):
        await client.chat([{"role": "user", "content": "hola"}])
