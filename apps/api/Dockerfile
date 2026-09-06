FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

RUN python -m venv /opt/venv

COPY requirements.prod.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.prod.txt

# Installation tools and their vendored dependencies are not part of the API runtime.
# Remove both virtualenv and base-image copies after installing runtime dependencies.
RUN python -m pip uninstall --yes pip setuptools wheel \
    && /usr/local/bin/python -m pip uninstall --yes pip setuptools wheel \
    && rm -rf /usr/local/lib/python3.12/ensurepip \
    && python -c "import fastapi, psycopg, sqlalchemy, uvicorn; import importlib.util; assert importlib.util.find_spec('pip') is None"

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3).read()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--timeout-graceful-shutdown", "25"]
