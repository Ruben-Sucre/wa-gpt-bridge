#!/bin/bash
# ─── Levanta todo el stack wa-gpt-bridge con validaciones estrictas ─────────
set -euo pipefail

DOMAIN="${DOMAIN:-agonisingly-unapprehended-vernice.ngrok-free.dev}"
N8N_PORT="${N8N_PORT:-5678}"
NGROK_API_URL="${NGROK_API_URL:-http://127.0.0.1:4040/api/tunnels}"
NGROK_READY_RETRIES="${NGROK_READY_RETRIES:-20}"
NGROK_READY_INTERVAL="${NGROK_READY_INTERVAL:-1}"
DIR="$(cd "$(dirname "$0")" && pwd)"
EXPECTED_BASE_URL="https://${DOMAIN}"

require_cmd() {
	local cmd="$1"
	if ! command -v "$cmd" >/dev/null 2>&1; then
		echo "❌ Falta dependencia requerida: $cmd"
		exit 1
	fi
}

get_active_ngrok_url() {
	curl -fsS "$NGROK_API_URL" | python3 -c 'import json,sys; data=json.load(sys.stdin); print(next((t.get("public_url", "") for t in data.get("tunnels", []) if t.get("proto") == "https"), ""))'
}

echo "▶ Validando dependencias..."
require_cmd docker
require_cmd ngrok
require_cmd curl
require_cmd python3

echo "▶ Iniciando contenedores..."
docker compose -f "$DIR/docker-compose.yml" up -d

echo "▶ Iniciando ngrok en dominio fijo..."
pkill -f "ngrok http" 2>/dev/null || true
sleep 1
nohup ngrok http "$N8N_PORT" --domain="$DOMAIN" --log=stdout > /tmp/ngrok.log 2>&1 &

echo "▶ Esperando que ngrok quede operativo..."
ACTIVE_BASE_URL=""
for ((attempt=1; attempt<=NGROK_READY_RETRIES; attempt++)); do
	if ACTIVE_BASE_URL="$(get_active_ngrok_url 2>/dev/null)" && [ -n "$ACTIVE_BASE_URL" ]; then
		break
	fi
	sleep "$NGROK_READY_INTERVAL"
done

if [ -z "$ACTIVE_BASE_URL" ]; then
	echo "❌ ngrok no quedó operativo. Revisa /tmp/ngrok.log"
	exit 1
fi

if [ "$ACTIVE_BASE_URL" != "$EXPECTED_BASE_URL" ]; then
	echo "❌ Dominio activo inesperado en ngrok"
	echo "   Esperado: $EXPECTED_BASE_URL"
	echo "   Activo:   $ACTIVE_BASE_URL"
	echo "   Revisa tu plan/reserva de dominio en ngrok"
	exit 1
fi

WEBHOOK_URL="${ACTIVE_BASE_URL}/webhook/whatsapp"
echo "✅ ngrok operativo: $ACTIVE_BASE_URL"

echo "▶ Verificando webhook al finalizar arranque..."
"$DIR/verificar_webhook.sh" "$WEBHOOK_URL"

echo ""
echo "✅ Stack listo"
echo ""
echo "   Bot:      http://localhost:8000/health"
echo "   n8n:      http://localhost:${N8N_PORT}"
echo "   Webhook:  ${WEBHOOK_URL}"
echo ""
echo "   ℹ️  Topología: Meta -> n8n (público) -> bot (interno con x-bot-secret)"
echo "   ⚠️  Si el token de WhatsApp expiró, actualiza WHATSAPP_TOKEN en .env"
echo "      y luego corre:  docker compose up -d bot"
