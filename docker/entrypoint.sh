#!/bin/sh
set -e

CERT_DIR=${CERT_DIR:-/certs}
CERT_FILE=$CERT_DIR/server.crt
KEY_FILE=$CERT_DIR/server.key

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
  echo "Generating self-signed certificate..."
  mkdir -p "$CERT_DIR"
  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -days 3650 \
    -subj "/CN=credvault.local" \
    -addext "subjectAltName=DNS:localhost,IP:0.0.0.0,IP:127.0.0.1" \
    >/dev/null 2>&1
fi

# Ensure a strong, persistent SECRET_KEY (never the insecure defaults).
DATA_DIR=${DATA_DIR:-/data}
mkdir -p "$DATA_DIR"
KEY_FILE_SECRET=$DATA_DIR/.secret_key
INSECURE_KEYS="dev-secret-change-me change-me-to-a-long-random-string"
if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "dev-secret-change-me" ] || [ "$SECRET_KEY" = "change-me-to-a-long-random-string" ]; then
  if [ -f "$KEY_FILE_SECRET" ]; then
    SECRET_KEY=$(cat "$KEY_FILE_SECRET")
  else
    SECRET_KEY=$(openssl rand -hex 32)
    umask 077
    printf '%s' "$SECRET_KEY" > "$KEY_FILE_SECRET"
  fi
  export SECRET_KEY
fi

# Ensure a strong admin password (never ship the old insecure default).
if [ -z "$ADMIN_PASSWORD" ] || [ "$ADMIN_PASSWORD" = "123sqwert" ]; then
  if [ -f "$DATA_DIR/.admin_password" ]; then
    ADMIN_PASSWORD=$(cat "$DATA_DIR/.admin_password")
  else
    ADMIN_PASSWORD=$(openssl rand -base64 12 | tr -d '=+/')
    umask 077
    printf '%s' "$ADMIN_PASSWORD" > "$DATA_DIR/.admin_password"
  fi
  export ADMIN_PASSWORD
  echo "Generated admin password -> $ADMIN_PASSWORD  (also stored in $DATA_DIR/.admin_password)"
fi

echo "Starting CredVault on https://0.0.0.0:8443"
exec uvicorn app.main:app --host 0.0.0.0 --port 8443 \
  --ssl-keyfile "$KEY_FILE" \
  --ssl-certfile "$CERT_FILE"
