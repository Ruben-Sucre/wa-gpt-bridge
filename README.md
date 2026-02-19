# wa-gpt-bridge

WhatsApp ↔ OpenAI chatbot con orquestación n8n usando FastAPI, Redis y Docker.

> 📖 **Para deployment en producción, consulta la [Guía de Deployment](DEPLOYMENT.md)** con instrucciones detalladas de configuración, troubleshooting y monitoreo.

## Arquitectura

- **n8n**: Orquestador de workflows (puerto 5678)
- **bot**: Middleware FastAPI para procesamiento de mensajes (puerto 8000)
- **redis**: Almacenamiento de historial conversacional (puerto interno 6379)

## Flujo de Datos

```
Usuario WhatsApp → Meta WhatsApp Cloud API → ngrok
  → FastAPI Bot (valida, limpia, consulta Redis, llama Gemini/OpenAI, responde)
  → Meta WhatsApp Cloud API → Usuario WhatsApp
```

## Levantar el stack

### Comando único (recomendado)

```bash
./start.sh
```

Este script hace **en orden**:
1. `docker compose up -d` — levanta Redis y el Bot
2. `ngrok http 8000 --domain=...` — expone el bot con dominio fijo

> ⚠️ **Siempre usa `./start.sh`** en lugar de levantar docker y ngrok por separado.
> ngrok debe apuntar al bot (`8000`), no a n8n (`5678`).

### URL pública fija (no cambia)

```
https://agonisingly-unapprehended-vernice.ngrok-free.dev/webhook/whatsapp
```

Esta URL ya está configurada en Meta. No necesitas cambiarla nunca.

### Token de WhatsApp (expira cada 24h en modo prueba)

Cuando el bot deje de responder, renueva el token en Meta → WhatsApp → API Setup, actualiza `.env`:

```bash
# Edita .env y actualiza WHATSAPP_TOKEN=...
docker compose up -d bot   # recarga el token sin bajar redis
```

## Características

- ✅ System prompt cargado desde `services/bot/prompts/system_prompt.txt`
- ✅ Historial conversacional persistente en Redis (TTL 24h)
- ✅ **Límite de mensajes** - Solo últimos 20 mensajes para prevenir overflow de contexto
- ✅ **Rate limiting** - Protección anti-spam (10 mensajes/minuto por usuario)
- ✅ Validación de webhook de Meta (hub.challenge)
- ✅ Limpieza de texto y sanitización
- ✅ Autenticación con header `x-bot-secret`
- ✅ **Health check mejorado** - Verifica Redis y credenciales de WhatsApp
- ✅ Envío directo a WhatsApp Cloud API desde FastAPI
- ✅ Selector de LLM por variable de entorno (OpenAI o Gemini 2.0 Flash)

## Quick Start

### 1. Configurar variables de entorno

```bash
cp .env.example .env
# Edita .env y configura tus API keys
# LLM_PROVIDER=openai|gemini
# OPENAI_API_KEY=... (si usas OpenAI)
# OPENAI_MODEL=gpt-4o
# GOOGLE_API_KEY=... (si usas Gemini)
# GEMINI_MODEL=gemini-1.5-flash
```

### 2. Levantar servicios con Docker Compose

```bash
docker compose up --build -d
```

### 3. Verificar salud del bot

```bash
curl http://localhost:8000/health
```

### 4. Importar flujo n8n

1. Abre n8n en `http://localhost:5678` (usuario/contraseña en `.env`)
2. Import → Selecciona `n8n/flows/wa-gpt-openai.json`
3. Configura credenciales de WhatsApp en n8n
4. Activa el workflow

### 5. Configurar webhook en Meta

1. Ve a Meta Business Console → WhatsApp → Configuration → Webhooks
2. URL: `https://tu-dominio.com/webhook/whatsapp` (endpoint de n8n expuesto)
3. Verify Token: configura el mismo que uses en n8n
4. Suscribe a `messages`

## Estructura

```
wa-gpt-bridge/
├── docker-compose.yml          # Orquestación de servicios
├── .env.example                # Variables de entorno
├── n8n/
│   └── flows/
│       └── wa-gpt-openai.json  # Workflow n8n
└── services/
    └── bot/
        ├── Dockerfile
        ├── requirements.txt
        ├── app/
        │   ├── __init__.py
        │   ├── main.py           # FastAPI endpoints
        │   ├── validation.py     # Modelos Pydantic
        │   ├── cleaner.py        # Sanitización de texto
        │   ├── memory.py         # Redis client
        │   ├── openai_client.py  # Wrapper OpenAI
        │   └── whatsapp_client.py # Meta API client
        └── prompts/
            └── system_prompt.txt # Personalización del asistente
```

## API Endpoints

### `GET /health`
Health check del servicio con verificación de dependencias.

**Respuesta**:
```json
{
  "status": "ok",
  "llm_provider": "gemini",
  "checks": {
    "redis": "ok",
    "whatsapp_credentials": "ok"
  }
}
```

**Estados posibles**:
- `status`: `"ok"` (todo funcional) o `"degraded"` (Redis desconectado)
- `checks.redis`: `"ok"` o `"failed"`
- `checks.whatsapp_credentials`: `"ok"` o `"not_configured"`

### `POST /webhook/whatsapp`
Procesa mensajes de WhatsApp.

**Headers**:
- `x-bot-secret`: Token de autenticación (opcional, configurable en `.env`)

**Body**:
```json
{
  "from": "+1234567890",
  "text": "Hola, necesito ayuda"
}
```

**Respuesta**:
```json
{
  "delivered": true,
  "detail": null
}
```

## Personalización

### Modificar el System Prompt

Edita `services/bot/prompts/system_prompt.txt` para cambiar el comportamiento del asistente.

### Elegir proveedor LLM

- Define `LLM_PROVIDER=openai` o `LLM_PROVIDER=gemini` en `.env`.
- OpenAI usa `OPENAI_API_KEY` y `OPENAI_MODEL` (default: gpt-4o).
- Gemini usa `GOOGLE_API_KEY` y `GEMINI_MODEL` (default: gemini-1.5-flash).

### Ajustar parámetros de generación

En los clientes (`services/bot/app/openai_client.py` y `services/bot/app/gemini_client.py`):
- `temperature`: Creatividad (0.0-2.0, default: 0.2)
- `max_tokens`/`maxOutputTokens`: Longitud máxima de respuesta (default: 800)
- `model`: Modelo a usar según proveedor

### TTL de conversación

En `services/bot/app/memory.py`, el TTL por defecto es 24 horas (86400 segundos).

## Desarrollo Local (sin Docker)

```bash
cd services/bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Troubleshooting

**Error de conexión a Redis**: Verifica que el servicio Redis esté corriendo:
```bash
docker compose ps redis
```

**Bot no responde**: Revisa logs:
```bash
docker compose logs -f bot
```

**n8n no recibe webhooks**: Asegúrate de exponer n8n con túnel (ngrok/cloudflare) o servidor público para que Meta pueda alcanzarlo.

