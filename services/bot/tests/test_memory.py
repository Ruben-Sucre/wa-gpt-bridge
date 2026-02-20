import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.memory import ConversationMemory


@pytest.mark.asyncio
async def test_get_conversation_sin_datos_devuelve_lista_vacia(mocker):
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=None)
    mocker.patch("app.memory.Redis.from_url", return_value=redis_mock)

    memory = ConversationMemory("redis://localhost:6379/0")
    result = await memory.get_conversation("521111111111")

    assert result == []
    redis_mock.get.assert_awaited_once_with("conv:521111111111")


@pytest.mark.asyncio
async def test_get_conversation_trunca_a_max_messages(mocker):
    messages = [{"role": "user", "content": f"m{i}"} for i in range(30)]
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=json.dumps(messages))
    mocker.patch("app.memory.Redis.from_url", return_value=redis_mock)

    memory = ConversationMemory("redis://localhost:6379/0")
    result = await memory.get_conversation("521111111111", max_messages=20)

    assert len(result) == 20
    assert result[0]["content"] == "m10"
    assert result[-1]["content"] == "m29"


@pytest.mark.asyncio
async def test_get_conversation_json_invalido_devuelve_lista_vacia(mocker):
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value="{json invalido")
    mocker.patch("app.memory.Redis.from_url", return_value=redis_mock)

    memory = ConversationMemory("redis://localhost:6379/0")
    result = await memory.get_conversation("521111111111")

    assert result == []


@pytest.mark.asyncio
async def test_get_conversation_json_no_lista_lanza_excepcion(mocker):
    redis_mock = MagicMock()
    redis_mock.get = AsyncMock(return_value=json.dumps({"role": "user", "content": "hola"}))
    mocker.patch("app.memory.Redis.from_url", return_value=redis_mock)

    memory = ConversationMemory("redis://localhost:6379/0")

    with pytest.raises(TypeError, match="JSON list"):
        await memory.get_conversation("521111111111")
