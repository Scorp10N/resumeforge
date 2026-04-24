FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential pkg-config curl \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
    libglib2.0-0 libpixman-1-0 libfontconfig1 libfreetype6 \
    libgdk-pixbuf-2.0-0 shared-mime-info \
    fonts-dejavu fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8080
CMD ["uv", "run", "uvicorn", "resumeforge.api.app:app", "--host", "0.0.0.0", "--port", "8080"]
