# ---- build frontend ----
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- runtime ----
FROM python:3.12-slim
WORKDIR /app

# No credentials are baked into the image: the entrypoint generates and persists
# SECRET_KEY / ADMIN_PASSWORD under /data when they aren't supplied.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL="sqlite:////data/credvault.db" \
    STATIC_DIR=/app/static

RUN apt-get update \
 && apt-get install -y --no-install-recommends openssl \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system credvault \
 && useradd --system --gid credvault --home-dir /app --shell /usr/sbin/nologin credvault

COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/app ./app
COPY --from=frontend /app/dist ./static
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod 0755 /entrypoint.sh && mkdir -p /data /certs

VOLUME ["/data", "/certs"]
EXPOSE 8443

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import ssl,urllib.request;urllib.request.urlopen('https://127.0.0.1:8443/api/health',context=ssl._create_unverified_context())" || exit 1

# The entrypoint fixes volume ownership, then drops to the unprivileged user.
ENTRYPOINT ["/entrypoint.sh"]
