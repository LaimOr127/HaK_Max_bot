FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    PATH="/home/app/.local/bin:${PATH}"

WORKDIR /app

RUN useradd --create-home --shell /usr/sbin/nologin app

COPY pyproject.toml alembic.ini ./
COPY migrations ./migrations
COPY scripts ./scripts
COPY data ./data
COPY src ./src
COPY certs/russian-trusted-root-ca.crt /usr/local/share/ca-certificates/russian-trusted-root-ca.crt

RUN update-ca-certificates \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

USER app

CMD ["python", "-m", "navigator.bootstrap", "--worker-placeholder"]
