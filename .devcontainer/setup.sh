#!/bin/bash
set -e

echo "🚀 Configurando wa-gpt-bridge en Codespaces..."

# Crear .env si no existe
if [ ! -f .env ]; then
  cp .env.example .env
  echo "✅ .env creado desde .env.example"
  echo "⚠️  IMPORTANTE: Abre el archivo .env y completa tus credenciales reales antes de continuar."
fi

# Calcular la URL pública de n8n en Codespaces
if [ -n "$CODESPACE_NAME" ]; then
  N8N_PUBLIC_URL="https://${CODESPACE_NAME}-5678.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
  echo "🌐 URL pública de n8n: $N8N_PUBLIC_URL"

  # Escribir/actualizar N8N_WEBHOOK_URL en .env
  if grep -q "^N8N_WEBHOOK_URL=" .env; then
    sed -i "s|^N8N_WEBHOOK_URL=.*|N8N_WEBHOOK_URL=$N8N_PUBLIC_URL|" .env
  else
    echo "N8N_WEBHOOK_URL=$N8N_PUBLIC_URL" >> .env
  fi
  echo "✅ N8N_WEBHOOK_URL actualizado en .env"
fi

echo ""
echo "📋 Próximos pasos:"
echo "   1. Edita tu .env y pon tus credenciales reales (GOOGLE_API_KEY, BOT_SECRET, etc.)"
echo "   2. Corre: docker compose up --build -d"
echo "   3. Abre n8n en la pestaña Ports → puerto 5678 (asegúrate de que sea Public)"
echo "   4. Importa el flujo n8n/flows/wa-gpt-openai.json"
echo "   5. Configura el webhook en Meta Developer con la URL pública de n8n"
