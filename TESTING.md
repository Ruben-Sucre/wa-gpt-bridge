# Guía de Testing - WhatsApp GPT Bridge

Esta guía te ayudará a probar el pipeline completo desde cero hasta tener el bot respondiendo mensajes de WhatsApp.

## 🧪 Pre-requisitos de Testing

- Docker y Docker Compose instalados
- API key de Google Gemini (ya configurada en `.env`)
- Cuenta de Meta Business para WhatsApp Cloud API
- ngrok instalado para testing local

## 📝 Checklist de Testing

### Fase 1: Verificar Configuración Local

#### 1.1 Verificar Variables de Entorno

```bash
# Ver configuración actual (sin mostrar secretos completos)
grep -E "^(LLM_PROVIDER|GEMINI_MODEL|WHATSAPP_TOKEN|WHATSAPP_PHONE_ID)=" .env
```

**Esperado**:
- ✅ `LLM_PROVIDER=gemini`
- ✅ `GEMINI_MODEL=gemini-2.0-flash`
- ⚠️ `WHATSAPP_TOKEN` y `WHATSAPP_PHONE_ID` deben tener valores reales (no placeholders)

#### 1.2 Construir e Iniciar Servicios

```bash
# Construir imágenes
docker-compose build

# Iniciar todos los servicios en background
docker-compose up -d

# Verificar que todos están corriendo
docker-compose ps
```

**Esperado**: Tres servicios en estado `Up`:
- `redis`
- `bot`
- `n8n`

#### 1.3 Verificar Logs

```bash
# Ver logs del bot (buscar errores)
docker-compose logs bot

# Verificar que no hay errores de conexión a Redis
docker-compose logs bot | grep -i "redis\|error"
```

**Esperado**: 
- ✅ Sin errores de "Connection refused"
- ✅ Sin errores de "Invalid API key"

### Fase 2: Testing de Health Check

#### 2.1 Health Check Básico

```bash
curl -s http://localhost:8000/health | jq
```

**Esperado**:
```json
{
  "status": "ok",
  "llm_provider": "gemini",
  "checks": {
    "redis": "ok",
    "whatsapp_credentials": "not_configured"  // OK si aún no configuraste WhatsApp
  }
}
```

Si `whatsapp_credentials` es `"ok"`, significa que ya tienes las credenciales configuradas. ✅

#### 2.2 Verificar Conectividad con Redis

```bash
# Conectarse a Redis y verificar
docker-compose exec redis redis-cli ping
```

**Esperado**: `PONG`

### Fase 3: Testing de n8n

#### 3.1 Acceder a n8n UI

```bash
# Obtener contraseña de n8n desde .env
grep N8N_BASIC_AUTH_PASSWORD .env
```

1. Abre http://localhost:5678 en tu navegador
2. Usuario: `admin`
3. Contraseña: (valor de `N8N_BASIC_AUTH_PASSWORD`)
4. Verifica que el workflow "WhatsApp → OpenAI (FastAPI)" existe y está activo

#### 3.2 Verificar Webhook de n8n

```bash
# Probar el webhook de n8n (debe devolver error porque no hay datos)
curl -X POST http://localhost:5678/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Esperado**: Error por falta de datos (normal, confirma que n8n recibe peticiones)

### Fase 4: Testing del Bot (Sin WhatsApp)

#### 4.1 Test Directo al Bot (Simulación)

```bash
# Test sin autenticación (debe fallar)
curl -X POST http://localhost:8000/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{"from": "+1234567890", "text": "Hola"}' \
  -w "\n"
```

**Esperado**: `401 Unauthorized` (correcto, necesita `x-bot-secret`)

#### 4.2 Test con Autenticación

```bash
# Obtener BOT_SECRET
BOT_SECRET=$(grep BOT_SECRET .env | cut -d'=' -f2)

# Test con autenticación
curl -X POST http://localhost:8000/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -H "x-bot-secret: $BOT_SECRET" \
  -d '{"from": "+1234567890", "text": "Hola, cómo estás?"}' \
  -w "\n" | jq
```

**Esperado** (si WhatsApp NO está configurado):
```json
{
  "delivered": false,
  "detail": "LLM OK, WhatsApp send failed"
}
```

Esto es **CORRECTO** - significa que:
- ✅ Bot recibió el mensaje
- ✅ Limpió el texto
- ✅ Llamó a Gemini correctamente
- ✅ Guardó la conversación en Redis
- ❌ Falló al enviar a WhatsApp (porque no está configurado)

#### 4.3 Verificar Conversación en Redis

```bash
# Ver qué conversaciones existen
docker-compose exec redis redis-cli KEYS "conv:*"

# Ver historial de la conversación de prueba
docker-compose exec redis redis-cli GET "conv:+1234567890"
```

**Esperado**: JSON con mensajes del usuario y la respuesta del asistente

#### 4.4 Test de Rate Limiting

```bash
# Enviar 12 mensajes rápidos (límite es 10/minuto)
BOT_SECRET=$(grep BOT_SECRET .env | cut -d'=' -f2)

for i in {1..12}; do
  echo "Mensaje $i:"
  curl -s -X POST http://localhost:8000/webhook/whatsapp \
    -H "Content-Type: application/json" \
    -H "x-bot-secret: $BOT_SECRET" \
    -d "{\"from\": \"+test123\", \"text\": \"Mensaje $i\"}" | jq .delivered
done
```

**Esperado**:
- Primeros 10 mensajes: `true` (o `false` si WhatsApp no configurado, pero procesados)
- Mensajes 11-12: `false` con `detail: "rate limit exceeded"`

### Fase 5: Configurar WhatsApp Cloud API

#### 5.1 Obtener Credenciales

Sigue la [Guía de Deployment - Sección 1](DEPLOYMENT.md#1-obtener-credenciales-de-whatsapp-cloud-api)

#### 5.2 Actualizar .env

```bash
# Editar .env con tus credenciales reales
nano .env

# Actualizar estas líneas:
# WHATSAPP_TOKEN=EAABsbCS...tu-token-real
# WHATSAPP_PHONE_ID=123456789012345
```

#### 5.3 Reiniciar Bot

```bash
docker-compose restart bot

# Verificar que health check ahora muestra credenciales OK
curl -s http://localhost:8000/health | jq .checks.whatsapp_credentials
```

**Esperado**: `"ok"`

### Fase 6: Exponer Webhook Públicamente

#### 6.1 Iniciar ngrok

```bash
# En una nueva terminal
ngrok http 5678
```

**Esperado**: URL pública como `https://abc123.ngrok-free.app`

Copia esta URL (la usaremos como `NGROK_URL`)

#### 6.2 Configurar Webhook en Meta

1. Ve a [Meta for Developers](https://developers.facebook.com/apps)
2. Selecciona tu app → WhatsApp → Configuration (Configuración)
3. En la sección Webhooks, clic en "Configure" o "Edit"
4. **Callback URL**: `https://abc123.ngrok-free.app/webhook/whatsapp`
5. **Verify Token**: Déjalo vacío (n8n lo maneja automáticamente)
6. Clic en "Verify and Save"

**Esperado**: ✅ Verificación exitosa (marca verde)

#### 6.3 Suscribirse a Eventos

En la misma página de Webhooks:
1. Suscríbete a `messages`
2. (Opcional) Suscríbete a `message_status` para confirmaciones de lectura

### Fase 7: Test End-to-End

#### 7.1 Monitoreo de Logs

Antes de enviar el mensaje, abre 3 terminales para monitorear:

**Terminal 1 - Logs de n8n**:
```bash
docker-compose logs -f n8n
```

**Terminal 2 - Logs del bot**:
```bash
docker-compose logs -f bot
```

**Terminal 3 - ngrok Inspector**:
```
http://localhost:4040
```

#### 7.2 Enviar Mensaje de WhatsApp

Desde tu teléfono:
1. Abre WhatsApp
2. Envía un mensaje al número configurado en tu app de WhatsApp Business
3. Mensaje de prueba: "Hola, necesito información sobre tus servicios"

#### 7.3 Verificar Flujo Completo

**En logs de n8n** deberías ver:
```
Webhook received: POST /webhook/whatsapp
```

**En logs del bot** deberías ver:
```
Processing message from +52XXXXXXXXXX. Provider: gemini
Generated response for +52XXXXXXXXXX (XXX chars)
```

**En tu teléfono** deberías recibir:
```
¡Hola! 👋 Gracias por tu interés...
```

✅ **¡TEST EXITOSO!** El pipeline está funcionando end-to-end.

#### 7.4 Test de Conversación Multi-Turn

Envía varios mensajes seguidos para verificar que mantiene contexto:

1. "Hola, cómo estás?"
2. "Cuéntame sobre tus servicios"
3. "Qué precios manejan?"

**Verificar**: El bot debe recordar el contexto de mensajes anteriores.

### Fase 8: Tests de Robustez

#### 8.1 Test de Mensajes Largos

Envía un mensaje de >500 caracteres. El bot debería procesarlo correctamente.

#### 8.2 Test de Caracteres Especiales

Envía: "Hola 👋 ¿Cómo están? 🎉 #prueba"

**Esperado**: Procesamiento correcto con emojis preservados.

#### 8.3 Test de Recuperación de Redis

```bash
# Reiniciar Redis en medio de una conversación
docker-compose restart redis

# Enviar mensaje
# Esperado: Se pierde el historial (conversación nueva)
```

#### 8.4 Test de Timeout de LLM

Modificar temporalmente el timeout en `gemini_client.py` a 1 segundo y verificar manejo de errores.

## ✅ Checklist de Validación Final

Antes de considerar el sistema "production-ready":

- [ ] Health check retorna `status: "ok"` y `checks.redis: "ok"`
- [ ] Health check retorna `checks.whatsapp_credentials: "ok"`
- [ ] Mensajes de WhatsApp llegan al bot (logs muestran procesamiento)
- [ ] Bot responde correctamente en WhatsApp
- [ ] Conversación multi-turn mantiene contexto
- [ ] Rate limiting bloquea después de 10 mensajes/min
- [ ] Sistema recupera después de reinicio de Redis
- [ ] n8n workflow está activo y procesando webhooks
- [ ] ngrok o tunnel público está funcionando establemente
- [ ] Logs no muestran errores 500 o crashes

## 🐛 Troubleshooting Común

### Bot no responde

```bash
# Verificar orden de problemas:
# 1. ¿Llega el webhook a n8n?
docker-compose logs n8n | tail -20

# 2. ¿n8n envía al bot?
docker-compose logs bot | tail -20

# 3. ¿Bot puede llamar a Gemini?
curl "https://generativelanguage.googleapis.com/v1beta/models?key=$(grep GOOGLE_API_KEY .env | cut -d'=' -f2)"

# 4. ¿Redis está conectado?
docker-compose exec redis redis-cli ping
```

### Webhook no verifica

- Verifica que ngrok está corriendo y no expiró
- Revisa logs de n8n durante la verificación
- Prueba manualmente: `curl https://TU-NGROK-URL/webhook/whatsapp?hub.mode=subscribe&hub.challenge=test`
- Debería retornar: `"test"`

### Conversación pierde contexto

```bash
# Verificar que Redis guarda datos
docker-compose exec redis redis-cli KEYS "conv:*"

# Ver TTL de una conversación
docker-compose exec redis redis-cli TTL "conv:+52XXXXXXXXXX"
# Esperado: Número > 0 (segundos restantes)
```

## 📊 Métricas de Performance

Valores típicos esperados:

- **Latencia end-to-end**: 2-5 segundos (WhatsApp → Bot → Gemini → WhatsApp)
- **Latencia de Gemini**: 0.5-2 segundos
- **Uso de memoria del bot**: ~50-100 MB
- **Uso de Redis**: ~10-50 MB (depende de número de conversaciones activas)

## 🎯 Siguientes Pasos

Una vez que todos los tests pasen:

1. Configure alertas de monitoreo (Sentry, Datadog, etc.)
2. Configure backups automáticos de Redis
3. Agregue tests automatizados (pytest)
4. Configure CI/CD para deployments
5. Migre de ngrok a dominio permanente con SSL

---

**Nota**: Para deployment a producción completo, consulta [DEPLOYMENT.md](DEPLOYMENT.md)
