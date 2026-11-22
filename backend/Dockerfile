FROM python:3.13-slim

WORKDIR /app

# Install curl for health check probes
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root system user
RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -s /bin/sh -m appuser

# Copy requirements
COPY requirements.txt .

# Install CPU torch wheel and backend requirements
RUN pip install --no-cache-dir torch sentence-transformers --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

# Set up permissions, make entrypoint executable, and ensure writable directories exist
RUN chmod +x entrypoint.sh && \
    mkdir -p uploads/documents logs && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
