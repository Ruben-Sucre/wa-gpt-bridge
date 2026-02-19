# Guía de Deployment - WhatsApp GPT Bridge

Esta guía cubre la configuración y deployment del pipeline WhatsApp → n8n → FastAPI Bot → LLM (Gemini/OpenAI).

## 📋 Prerequisitos

- Docker y Docker Compose instalados
- Cuenta de Meta Business para WhatsApp Cloud API
- API key de Google Gemini o OpenAI
- (Para desarrollo local) ngrok o cloudflared para exponer webhooks públicamente

## 🔧 Configuración Paso a Paso

### 1. Obtener Credenciales de WhatsApp Cloud API

#### A. Crear/Configurar App de WhatsApp Business

1. Accede a [Meta for Developers](https://developers.facebook.com/apps)
2. Crea una nueva app o selecciona una existente
3. Agrega el producto **WhatsApp** si no lo tiene
4. Completa el proceso de verificación del negocio (puede tomar días si es primera vez)

#### B. Obtener Phone Number ID

1. En el panel de la app, ve a **WhatsApp** → **API Setup** (o Configuración de API)
2. Copia el **Phone Number ID** (empieza con números, ej: `123456789012345`)
3. Pégalo en `.env`:
   ```bash
   WHATSAPP_PHONE_ID=123456789012345
   ```

#### C. Generar Token Permanente

**Opción 1: Token Temporal (24h) - Solo para Testing**
1. En WhatsApp → API Setup, copia el token temporal
2. ⚠️ Expira en 24 horas, solo para pruebas

**Opción 2: Token Permanente - Recomendado para Producción**
1. Ve a **Configuración del negocio** → **Usuarios** → **Usuarios del sistema**
2. Crea un nuevo usuario del sistema con rol "Administrador"
3. Genera un token seleccionando tu app y los permisos:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
4. Copia el token (empieza con `EAA...`)
5. Pégalo en `.env`:
   ```bash
   WHATSAPP_TOKEN=EAABsbCS1234...tu-token-completo
   ```

### 2. Configurar Variables de Entorno

Edita el archivo `.env` y verifica/actualiza:

```bash
# ── LLM Provider (gemini u openai) ───────────────────────────
LLM_PROVIDER=gemini

# ── Google Gemini ─────────────────────────────────────────────
GOOGLE_API_KEY=AIzaSy...  # Obtener en https://aistudio.google.com/app/apikey
GEMINI_MODEL=gemini-2.0-flash

# ── OpenAI (alternativa) ──────────────────────────────────────
OPENAI_API_KEY=sk-...  # Obtener en https://platform.openai.com/api-keys
OPENAI_MODEL=gpt-4o

# ── WhatsApp Cloud API ────────────────────────────────────────
WHATSAPP_TOKEN=EAABsbCS...  # Token permanente de Meta
WHATSAPP_PHONE_ID=123456789012345  # Phone Number ID de WhatsApp

# ── Seguridad ─────────────────────────────────────────────────
BOT_SECRET=<generado-automaticamente>  # No modificar
N8N_BASIC_AUTH_PASSWORD=<generado-automaticamente>  # No modificar
```

### 3. Exponer Webhook Públicamente

#### Opción A: Desarrollo Local con ngrok

```bash
# Instalar ngrok
brew install ngrok  # macOS
# o descargar de https://ngrok.com/download

# Iniciar servicios
docker-compose up -d

# Exponer n8n públicamente
ngrok http 5678

# Copiar la URL (ej: https://abc123.ngrok-free.app)
```

#### Opción B: Desarrollo Local con Cloudflare Tunnel

```bash
# Instalar cloudflared
brew install cloudflared  # macOS
# o descargar de https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/

# Iniciar servicios
docker-compose up -d

# Crear túnel
cloudflared tunnel --url http://localhost:5678

# Copiar la URL (ej: https://xyz.trycloudflare.com)
```

#### Opción C: Producción con Dominio Propio

1. Configura un servidor con IP pública y dominio (ej: `webhook.tudominio.com`)
2. Instala Nginx y configura reverse proxy a puerto 5678
3. Configura certificado SSL con Let's Encrypt:
   ```bash
   sudo certbot --nginx -d webhook.tudominio.com
   ```
4. Asegúrate de que el firewall permite tráfico en puerto 443

### 4. Registrar Webhook en Meta WhatsApp

1. En el panel de WhatsApp, ve a **Configuración** (Configuration) → **Webhooks**
   - O directamente a: https://developers.facebook.com/apps/TU_APP_ID/whatsapp-business/wa-settings/
2. Haz clic en **Configurar webhooks** (Configure webhooks) o **Edit**
3. Introduce:
   - **URL de devolución de llamada**: `https://TU-URL-PUBLICA/webhook/whatsapp`
     - Ejemplo ngrok: `https://abc123.ngrok-free.app/webhook/whatsapp`
     - Ejemplo dominio: `https://webhook.tudominio.com/webhook/whatsapp`
   - **Token de verificación**: Deja en blanco o cualquier valor (n8n lo maneja automáticamente)
4. Haz clic en **Verificar y guardar**
5. Meta enviará una petición GET con `hub.mode=subscribe` - n8n responderá automáticamente
6. Una vez verificado, suscríbete a los campos:
   - `messages` (obligatorio)
   - `message_status` (opcional, para confirmaciones de entrega)

### 5. Iniciar Servicios

```bash
# Iniciar todos los servicios
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f bot
docker-compose logs -f n8n

# Verificar que los servicios están funcionando
docker-compose ps
```

### 6. Validar Configuración

#### A. Health Check del Bot

```bash
curl http://localhost:8000/health
```

Respuesta esperada:
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

Si `whatsapp_credentials` es `"not_configured"`, revisa las variables de entorno.

#### B. Verificar n8n

1. Accede a http://localhost:5678
2. Usuario: `admin`
3. Contraseña: Valor de `N8N_BASIC_AUTH_PASSWORD` en `.env`
4. Verifica que el workflow "WhatsApp → OpenAI (FastAPI)" esté activo

#### C. Probar Flujo Completo

1. Envía un mensaje de WhatsApp al número configurado
2. Verifica en los logs que se procesa:
   ```bash
   docker-compose logs -f bot
   ```
3. Deberías recibir una respuesta generada por el LLM
4. Envía un segundo mensaje para verificar que la conversación mantiene contexto

## 🔒 Seguridad en Producción

### Secretos Sensibles

- ✅ `BOT_SECRET` generado automáticamente (32+ caracteres)
- ✅ `N8N_BASIC_AUTH_PASSWORD` generado automáticamente
- ⚠️ NO commitear `.env` a Git (ya está en `.gitignore`)
- ⚠️ Rotar tokens de WhatsApp cada 60-90 días

### Rate Limiting

- **Límite actual**: 10 mensajes por minuto por usuario
- Para ajustar, modifica en `main.py`:
  ```python
  rate_limiter = RateLimiter(REDIS_URL, max_requests=10, window_seconds=60)
  ```

### Límite de Mensajes en Conversación

- **Límite actual**: 20 mensajes (10 pares user-assistant)
- Previene exceder context window del LLM y reduce costos
- Para ajustar, modifica el parámetro `max_messages` en `memory.py`:
  ```python
  async def get_conversation(self, conv_id: str, max_messages: int = 20):
  ```

## 📊 Monitoreo

### Logs

```bash
# Logs del bot (mensajes procesados, errores)
docker-compose logs -f bot | grep -i error

# Logs de n8n (webhooks recibidos)
docker-compose logs -f n8n

# Logs de Redis
docker-compose logs -f redis
```

### Métricas Importantes

- **Latencia de respuesta**: Tiempo desde mensaje recibido hasta enviado
- **Tasa de error**: Errores 500 o `delivered=False`
- **Uso de Redis**: Conexiones activas, memoria utilizada
- **Rate limiting**: Usuarios bloqueados por exceso de mensajes

### Alertas Recomendadas

- Redis desconectado (`health.checks.redis != "ok"`)
- WhatsApp credentials no configuradas
- Tasa de error > 5%
- Latencia > 10 segundos

## 🔄 Actualización de Modelos LLM

### Cambiar de Gemini a OpenAI

1. Asegúrate de tener `OPENAI_API_KEY` configurado en `.env`
2. Cambia `LLM_PROVIDER=openai` en `.env`
3. Reinicia el bot:
   ```bash
   docker-compose restart bot
   ```

### Actualizar Modelo de Gemini

1. Modifica `GEMINI_MODEL` en `.env` (ej: `gemini-2.0-flash-exp`)
2. Reinicia el bot:
   ```bash
   docker-compose restart bot
   ```

Modelos Gemini disponibles:
- `gemini-2.0-flash` - Rápido, económico (recomendado)
- `gemini-1.5-pro` - Más potente, más caro
- `gemini-1.5-flash` - Balance costo/rendimiento

### Actualizar Modelo de OpenAI

1. Modifica `OPENAI_MODEL` en `.env` (ej: `gpt-4-turbo`)
2. Reinicia el bot

Modelos OpenAI disponibles:
- `gpt-4o` - Optimizado multimodal (recomendado)
- `gpt-4-turbo` - Más rápido que GPT-4 original
- `gpt-3.5-turbo` - Económico, menor calidad

## 🐛 Troubleshooting

### Webhook No Recibe Mensajes

**Problema**: Meta no envía webhooks al servidor

**Soluciones**:
1. Verifica que la URL pública sea accesible:
   ```bash
   curl https://TU-URL-PUBLICA/webhook/whatsapp
   ```
2. Revisa que el webhook esté verificado en Meta (marca verde)
3. Verifica logs de n8n:
   ```bash
   docker-compose logs -f n8n | grep webhook
   ```
4. Si usas ngrok, verifica que no haya expirado (túneles gratis expiran)
5. Asegúrate de que n8n está en ejecución:
   ```bash
   docker-compose ps n8n
   ```

### Bot No Responde

**Problema**: Webhook llega pero no hay respuesta

**Soluciones**:
1. Verifica health check:
   ```bash
   curl http://localhost:8000/health
   ```
2. Revisa logs del bot:
   ```bash
   docker-compose logs -f bot
   ```
3. Verifica que `BOT_SECRET` coincida entre `.env` y n8n
4. Verifica conectividad con LLM:
   ```bash
   # Para Gemini
   curl "https://generativelanguage.googleapis.com/v1beta/models?key=TU_API_KEY"
   
   # Para OpenAI
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer TU_API_KEY"
   ```

### Redis Desconectado

**Problema**: `health.checks.redis = "failed"`

**Soluciones**:
1. Verifica que Redis está en ejecución:
   ```bash
   docker-compose ps redis
   ```
2. Reinicia Redis:
   ```bash
   docker-compose restart redis
   ```
3. Verifica logs de Redis:
   ```bash
   docker-compose logs redis
   ```

### Rate Limit Bloqueando Usuarios Legítimos

**Problema**: Usuarios reales reciben mensaje de límite

**Soluciones**:
1. Aumenta el límite en `main.py` (ej: 20 mensajes por minuto)
2. Resetea el rate limit manualmente en Redis:
   ```bash
   docker-compose exec redis redis-cli
   > DEL ratelimit:+1234567890
   ```

### Conversación Pierde Contexto

**Problema**: El bot no recuerda mensajes anteriores

**Soluciones**:
1. Verifica que Redis está persistiendo datos:
   ```bash
   docker-compose exec redis redis-cli
   > KEYS conv:*
   > GET conv:+1234567890
   ```
2. Aumenta `max_messages` en `memory.py` si necesitas más contexto
3. Verifica que el TTL de 24h no haya expirado

### Errores de LLM API

**Problema**: `delivered=False` por fallo de LLM

**Soluciones**:
1. Verifica que la API key es válida
2. Revisa logs para ver el error específico:
   ```bash
   docker-compose logs -f bot | grep -i error
   ```
3. Verifica cuota/créditos disponibles:
   - Gemini: https://aistudio.google.com/app/apikey
   - OpenAI: https://platform.openai.com/usage
4. Verifica límites de rate de la API del proveedor

## 📈 Escalamiento

### Aumentar Capacidad

Para manejar más usuarios simultáneos:

1. **Escalar replicas del bot**:
   ```yaml
   # En docker-compose.yml
   bot:
     deploy:
       replicas: 3
   ```

2. **Usar Redis Cluster** para mayor disponibilidad

3. **Agregar balanceador de carga** (Nginx) frente a múltiples instancias

### Migrar a Kubernetes

Consideraciones:
- Crear ConfigMaps para configuración no sensible
- Usar Secrets para API keys
- Configurar HPA (Horizontal Pod Autoscaler) basado en CPU/requests
- Usar Redis gestionado (Google Cloud Memorystore, AWS ElastiCache)

## 🔐 Rotación de Secretos

### Rotar BOT_SECRET

```bash
# Generar nuevo secreto
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Actualizar en .env
# Actualizar variable de entorno BOT_SECRET en n8n workflow
# Reiniciar servicios
docker-compose restart
```

### Rotar WhatsApp Token

1. Genera nuevo token en Meta Business Console
2. Actualiza `WHATSAPP_TOKEN` en `.env`
3. Reinicia el bot:
   ```bash
   docker-compose restart bot
   ```

### Rotar API Keys de LLM

1. Genera nueva key en el panel del proveedor
2. Actualiza `GOOGLE_API_KEY` o `OPENAI_API_KEY` en `.env`
3. Reinicia el bot:
   ```bash
   docker-compose restart bot
   ```
4. Revoca la key antigua en el panel del proveedor

## 📝 Mantenimiento

### Backup de Conversaciones

```bash
# Backup de Redis (conversaciones)
docker-compose exec redis redis-cli BGSAVE

# Copiar dump.rdb desde el contenedor
docker cp $(docker-compose ps -q redis):/data/dump.rdb ./backup-redis-$(date +%Y%m%d).rdb
```

### Limpieza de Logs

```bash
# Vaciar logs de Docker
docker-compose logs --tail=0 -f &  # Reinicia logging
docker system prune -a --volumes  # Limpia volúmenes viejos (CUIDADO: Borra datos)
```

### Updates de Dependencias

```bash
# Actualizar imágenes de Docker
docker-compose pull

# Reconstruir el bot con nuevas dependencias
cd services/bot
pip install -r requirements.txt --upgrade
cd ../..
docker-compose build bot
docker-compose up -d bot
```

## 🆘 Soporte

Para problemas adicionales:
1. Revisa los logs completos: `docker-compose logs > debug.log`
2. Verifica la documentación oficial:
   - [WhatsApp Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api)
   - [Google Gemini](https://ai.google.dev/docs)
   - [OpenAI API](https://platform.openai.com/docs)
   - [n8n Workflows](https://docs.n8n.io/)
3. Consulta el archivo `README.md` del proyecto

---

**Última actualización**: Febrero 2026
