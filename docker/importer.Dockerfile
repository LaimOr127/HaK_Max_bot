FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/app/.local/bin:${PATH}"

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin app

COPY pyproject.toml alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts
COPY data ./data
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

USER app

CMD ["python", "-m", "navigator.bootstrap", "--importer-placeholder"]
