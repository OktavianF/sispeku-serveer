# ── Stage 1: Build dependencies ──
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build essentials for compiled packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install PyTorch CPU-only first (saves ~1.5GB vs full torch with CUDA)
RUN pip install --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt


# ── Stage 2: Production image ──
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY main.py .
COPY app/ ./app/

# Copy model file
COPY model/ ./model/

# Default environment variables (overridden by Railway dashboard)
ENV MODEL_PATH=./model/model.pkl
ENV PORT=8000

# Expose the port
EXPOSE ${PORT}

# Run uvicorn — Railway injects PORT env var automatically
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
