#!/bin/bash
# ─── Corre la suite de tests del bot ───────────────────────────
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "▶ Construyendo imagen de tests..."
docker build -t wa-gpt-bridge-test --target test "$DIR/services/bot" -q

echo "▶ Ejecutando tests..."
docker run --rm \
  -e REDIS_URL=redis://localhost:6379/0 \
  -e LLM_PROVIDER=gemini \
  -e GOOGLE_API_KEY=test-key \
  -e GEMINI_MODEL=gemini-2.0-flash \
  -e WHATSAPP_TOKEN=test-token \
  -e WHATSAPP_PHONE_ID=123456789 \
  -e BOT_SECRET=test-secret \
  wa-gpt-bridge-test \
  python -m pytest tests/ -v
