# Build stage — compilers present, discarded after
FROM python:3.12-slim AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config \
    libcairo2-dev libpango1.0-dev libglib2.0-dev \
    libpixman-1-dev libfontconfig1-dev libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

# Runtime stage — no compilers, non-root user
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
    libglib2.0-0 libpixman-1-0 libfontconfig1 libfreetype6 \
    libgdk-pixbuf-2.0-0 shared-mime-info \
    fonts-dejavu fonts-liberation \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip && \
    python -m pip uninstall pip setuptools wheel -y 2>/dev/null || true
RUN useradd -m -u 1000 appuser
COPY --from=builder /app /app
WORKDIR /app
USER appuser
EXPOSE 8080
CMD ["/app/.venv/bin/uvicorn", "resumeforge.api.app:app", "--host", "0.0.0.0", "--port", "8080"]
