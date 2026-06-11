FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install uv (fast Python package manager)
RUN pip install --no-cache-dir uv==0.4.0

# Copy project metadata first for layer caching
COPY pyproject.toml ./
COPY src/ ./src/

RUN uv pip install --system .

EXPOSE 8000

CMD ["uvicorn", "anant.main:app", "--host", "0.0.0.0", "--port", "8000"]
