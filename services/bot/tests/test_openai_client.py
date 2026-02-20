import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.openai_client import OpenAIClient


@pytest.mark.asyncio
async def test_chat_envia_payload_y_headers_correctos(mocker):
    response_mock = MagicMock()
    response_mock.raise_for_status = MagicMock()
    response_mock.json.return_value = {
        "choices": [{"message": {"content": "respuesta openai"}}]
    }

    post_mock = AsyncMock(return_value=response_mock)
    client_in_context = MagicMock(post=post_mock)
    async_client_cm = MagicMock()
    async_client_cm.__aenter__ = AsyncMock(return_value=client_in_context)
    async_client_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch("app.openai_client.httpx.AsyncClient", return_value=async_client_cm)

    client = OpenAIClient(api_key="sk-test", model="gpt-4o")
    messages = [{"role": "user", "content": "hola"}]

    result = await client.chat(messages)

    assert result == "respuesta openai"
    post_mock.assert_awaited_once()
    call = post_mock.await_args
    assert call.args[0] == "https://api.openai.com/v1/chat/completions"
    assert call.kwargs["headers"]["Authorization"] == "Bearer sk-test"
    assert call.kwargs["json"]["model"] == "gpt-4o"
    assert call.kwargs["json"]["messages"] == messages


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
    mocker.patch("app.openai_client.httpx.AsyncClient", return_value=async_client_cm)

    client = OpenAIClient(api_key="sk-test", model="gpt-4o")
    result = await client.chat([{"role": "user", "content": "hola"}])

    assert result == ""


@pytest.mark.asyncio
async def test_chat_content_vacio_devuelve_vacio(mocker):
    response_mock = MagicMock()
    response_mock.raise_for_status = MagicMock()
    response_mock.json.return_value = {
        "choices": [{"message": {"content": ""}}]
    }

    post_mock = AsyncMock(return_value=response_mock)
    client_in_context = MagicMock(post=post_mock)
    async_client_cm = MagicMock()
    async_client_cm.__aenter__ = AsyncMock(return_value=client_in_context)
    async_client_cm.__aexit__ = AsyncMock(return_value=None)
    mocker.patch("app.openai_client.httpx.AsyncClient", return_value=async_client_cm)

    client = OpenAIClient(api_key="sk-test", model="gpt-4o")
    result = await client.chat([{"role": "user", "content": "hola"}])

    assert result == ""


@pytest.mark.asyncio
async def test_chat_error_http_se_propaga(mocker):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
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
    mocker.patch("app.openai_client.httpx.AsyncClient", return_value=async_client_cm)

    client = OpenAIClient(api_key="sk-test", model="gpt-4o")

    with pytest.raises(httpx.HTTPStatusError):
        await client.chat([{"role": "user", "content": "hola"}])
