# TxLens API service image.
# STATUS: full application code present (all 12 phases), but this image
# has never actually been built — no Docker available in the environment
# that generated this repo. Validate locally with:
#   docker build -f docker/api.Dockerfile -t txlens-api .
# NOTE: build context is the repo ROOT (not apps/api) as of Phase 4, since
# the API process now imports the risk-engine service and ml/ feature
# schema directly (see PYTHONPATH below) rather than calling them over
# the network — that's a known simplification for the MVP; splitting this
# into a real internal API call is worth revisiting once services/mcp-server
# and services/ai-analyst need the same data.

FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/requirements.txt apps/api/requirements.txt
RUN pip install --no-cache-dir -r apps/api/requirements.txt

COPY services/risk-engine/requirements.txt services/risk-engine/requirements.txt
RUN pip install --no-cache-dir -r services/risk-engine/requirements.txt

COPY services/ai-analyst/requirements.txt services/ai-analyst/requirements.txt
RUN pip install --no-cache-dir -r services/ai-analyst/requirements.txt

COPY apps/api apps/api
COPY ml ml
COPY services/risk-engine services/risk-engine
COPY services/ai-analyst services/ai-analyst

ENV PYTHONPATH=/app:/app/apps/api:/app/services/risk-engine:/app/services/ai-analyst
WORKDIR /app/apps/api

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
