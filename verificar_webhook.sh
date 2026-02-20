#!/bin/bash
# Script para verificar que n8n webhook está respondiendo correctamente

set -euo pipefail

DOMAIN="${DOMAIN:-agonisingly-unapprehended-vernice.ngrok-free.dev}"
URL="${1:-https://${DOMAIN}/webhook/whatsapp}"
VERIFY_TOKEN="${WEBHOOK_VERIFY_TOKEN:-test}"
CHALLENGE="${WEBHOOK_CHALLENGE:-test123}"
RETRIES="${WEBHOOK_VERIFY_RETRIES:-10}"
INTERVAL="${WEBHOOK_VERIFY_INTERVAL:-2}"
TIMEOUT="${WEBHOOK_VERIFY_TIMEOUT:-10}"

echo "═══════════════════════════════════════════════════════════"
echo "  Verificando webhook de n8n..."
echo "═══════════════════════════════════════════════════════════"
echo ""

echo "URL objetivo: ${URL}"
echo "1. Probando verificación de Meta (simulación)..."

SUCCESS=0
LAST_STATUS="000"
LAST_BODY=""
DISPLAY_BODY=""

for ((attempt=1; attempt<=RETRIES; attempt++)); do
    RESPONSE_WITH_STATUS="$(
        curl -sS --max-time "$TIMEOUT" -w $'\n%{http_code}' \
            "${URL}?hub.mode=subscribe&hub.challenge=${CHALLENGE}&hub.verify_token=${VERIFY_TOKEN}" \
            || true
    )"

    LAST_STATUS="$(printf '%s' "$RESPONSE_WITH_STATUS" | tail -n1)"
    LAST_BODY="$(printf '%s' "$RESPONSE_WITH_STATUS" | sed '$d')"
    DISPLAY_BODY="$(printf '%s' "$LAST_BODY" | tr '\n' ' ' | tr '\r' ' ' | cut -c1-220)"

    if [ "$LAST_STATUS" = "200" ] && { [ "$LAST_BODY" = "\"${CHALLENGE}\"" ] || [ "$LAST_BODY" = "${CHALLENGE}" ]; }; then
        SUCCESS=1
        break
    fi

    echo "   Intento ${attempt}/${RETRIES} fallido (HTTP ${LAST_STATUS})"
    sleep "$INTERVAL"
done

echo "   Respuesta final (HTTP ${LAST_STATUS}): ${DISPLAY_BODY}"
echo ""

if [ "$SUCCESS" -eq 1 ]; then
    echo "✅ ¡PERFECTO! El webhook está respondiendo correctamente"
    echo ""
    echo "    Callback URL: ${URL}"
    echo "    Verify Token: usa el mismo valor configurado en Meta/n8n"
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    exit 0
fi

echo "❌ ERROR: El webhook NO está respondiendo correctamente"
echo ""
echo "Posibles causas:"
echo "  1. El workflow no está importado en n8n"
echo "  2. El workflow no está ACTIVO (toggle verde)"
echo "  3. ngrok no está corriendo o dominio no coincide"
echo "  4. Verify Token no coincide entre Meta/n8n"
echo ""
echo "Soluciones:"
echo "  • Ve a http://localhost:5678"
echo "  • Importa el workflow: n8n/flows/wa-gpt-openai.json"
echo "  • ACTIVA el workflow (toggle arriba a la derecha)"
echo "  • Verifica que ngrok esté corriendo: ps aux | grep ngrok"
echo "  • Verifica WEBHOOK_VERIFY_TOKEN en .env y en Meta"
echo ""
echo "═══════════════════════════════════════════════════════════"
exit 1
