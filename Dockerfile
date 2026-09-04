# ---- build frontend ----
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- runtime ----
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    DATABASE_URL="sqlite:////data/credvault.db" \
    ADMIN_USERNAME="admin" \
    ADMIN_PASSWORD="123sqwert"

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app
COPY --from=frontend /app/dist ./static

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p /data /certs
VOLUME ["/data", "/certs"]

EXPOSE 8443

ENTRYPOINT ["/entrypoint.sh"]
