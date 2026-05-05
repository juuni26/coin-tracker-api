FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python deps first so the layer caches between code changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy app + migrations + tests (tests are useful inside the container for
# `docker compose run --rm app pytest`).
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY tests/ ./tests/
COPY alembic.ini pytest.ini ./

EXPOSE 8000

# Apply migrations, then boot uvicorn. Same semantics as the Railway Procfile.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
