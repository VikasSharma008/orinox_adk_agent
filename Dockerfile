FROM python:3.11-slim

# Install Node.js for MCP servers (npx)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-install MCP servers so first run is fast
RUN npx -y @modelcontextprotocol/server-memory --help 2>/dev/null || true && \
    npx -y @modelcontextprotocol/server-filesystem /tmp --help 2>/dev/null || true

COPY . .

RUN mkdir -p /tmp/orinox_output

EXPOSE 8080

RUN python -m db.seed_data
CMD ["python", "app.py"]
