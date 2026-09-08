# TxLens MCP server image.
# STATUS: not built/verified in this environment (no Docker, no network to
# install the `mcp` package). Validate locally with:
#   docker build -f docker/mcp-server.Dockerfile -t txlens-mcp-server services/mcp-server

FROM python:3.12-slim AS base

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV TXLENS_API_URL=http://api:8000
EXPOSE 8765

CMD ["python", "-m", "mcp_server.server"]
