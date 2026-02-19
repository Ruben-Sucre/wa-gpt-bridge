FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY app /app/app

# ── Test stage ────────────────────────────────────────────────
FROM base AS test
COPY tests /app/tests
COPY pytest.ini /app/pytest.ini

# ── Production stage ──────────────────────────────────────────
FROM base AS production
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
