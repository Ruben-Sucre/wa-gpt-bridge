# wa-gpt-bridge

WhatsApp ↔ OpenAI chatbot con orquestación n8n usando FastAPI, Redis y Docker.

## Arquitectura

- **n8n**: Orquestador de workflows (puerto 5678)
- **bot**: Middleware FastAPI para procesamiento de mensajes (puerto 8000)
- **redis**: Almacenamiento de historial conversacional (puerto interno 6379)

## Flujo de Datos

```
Usuario WhatsApp → Meta WhatsApp Cloud API → n8n Webhook
  → FastAPI Bot (valida, limpia, consulta Redis, llama OpenAI, guarda respuesta)
  → Meta WhatsApp Cloud API → Usuario WhatsApp
```

## Características

- ✅ System prompt cargado desde `services/bot/prompts/system_prompt.txt`
- ✅ Historial conversacional persistente en Redis (TTL 24h)
- ✅ Validación de webhook de Meta (hub.challenge)
- ✅ Limpieza de texto y sanitización
- ✅ Autenticación con header `x-bot-secret`
- ✅ Envío directo a WhatsApp Cloud API desde FastAPI

## Quick Start

### 1. Configurar variables de entorno

```bash
cp .env.example .env
# Edita .env y configura tus API keys
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
Health check del servicio.

**Respuesta**: `{"status": "ok"}`

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

### Ajustar parámetros de OpenAI

En `services/bot/app/openai_client.py`:
- `temperature`: Creatividad (0.0-2.0, default: 0.2)
- `max_tokens`: Longitud máxima de respuesta (default: 800)
- `model`: Modelo a usar (configurable en `.env`, default: gpt-4o)

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

