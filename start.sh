#!/bin/bash
# ─── Levanta todo el stack wa-gpt-bridge ───────────────────────
set -e

DOMAIN="agonisingly-unapprehended-vernice.ngrok-free.dev"
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "▶ Iniciando contenedores..."
docker compose -f "$DIR/docker-compose.yml" up -d

echo "▶ Iniciando ngrok en dominio fijo..."
pkill -f "ngrok http" 2>/dev/null || true
sleep 1
nohup ngrok http 8000 --domain="$DOMAIN" --log=stdout > /tmp/ngrok.log 2>&1 &

sleep 3
echo ""
echo "✅ Stack listo"
echo ""
echo "   Bot:      http://localhost:8000/health"
echo "   n8n:      http://localhost:5678"
echo "   Webhook:  https://$DOMAIN/webhook/whatsapp"
echo ""
echo "   ⚠️  Si el token de WhatsApp expiró, actualiza WHATSAPP_TOKEN en .env"
echo "      y luego corre:  docker compose up -d bot"
