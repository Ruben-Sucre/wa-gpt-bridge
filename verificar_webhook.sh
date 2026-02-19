#!/bin/bash
# Script para verificar que n8n webhook está respondiendo correctamente

echo "═══════════════════════════════════════════════════════════"
echo "  Verificando webhook de n8n..."
echo "═══════════════════════════════════════════════════════════"
echo ""

URL="https://agonisingly-unapprehended-vernice.ngrok-free.dev/webhook/whatsapp"

echo "1. Probando verificación de Meta (simulación)..."
RESPONSE=$(curl -s "${URL}?hub.mode=subscribe&hub.challenge=test123&hub.verify_token=test")

echo "   Respuesta: $RESPONSE"
echo ""

if [ "$RESPONSE" == "\"test123\"" ] || [ "$RESPONSE" == "test123" ]; then
    echo "✅ ¡PERFECTO! El webhook está respondiendo correctamente"
    echo ""
    echo "    Ahora puedes configurar el webhook en Meta:"
    echo "    URL: ${URL}"
    echo "    Verify Token: (déjalo vacío o cualquier valor)"
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    exit 0
else
    echo "❌ ERROR: El webhook NO está respondiendo correctamente"
    echo ""
    echo "Posibles causas:"
    echo "  1. El workflow no está importado en n8n"
    echo "  2. El workflow no está ACTIVO (toggle verde)"
    echo "  3. ngrok no está corriendo"
    echo ""
    echo "Soluciones:"
    echo "  • Ve a http://localhost:5678"
    echo "  • Importa el workflow: n8n/flows/wa-gpt-openai.json"
    echo "  • ACTIVA el workflow (toggle arriba a la derecha)"
    echo "  • Verifica que ngrok esté corriendo: ps aux | grep ngrok"
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    exit 1
fi
