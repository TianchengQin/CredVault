#!/bin/sh
set -eu

DATA_DIR=${DATA_DIR:-/data}
CERT_DIR=${CERT_DIR:-/certs}
CERT_FILE=$CERT_DIR/server.crt
KEY_FILE=$CERT_DIR/server.key
APP_USER=credvault

umask 077
mkdir -p "$DATA_DIR" "$CERT_DIR"

# ---- TLS: self-signed certificate on first boot (replace with your own in ./certs) ----
if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
  echo "Generating self-signed certificate..."
  openssl req -x509 -newkey rsa:3072 -nodes -sha256 \
    -keyout "$KEY_FILE" -out "$CERT_FILE" -days 825 \
    -subj "/CN=credvault.local" \
    -addext "subjectAltName=DNS:localhost,DNS:credvault.local,IP:127.0.0.1" \
    >/dev/null 2>&1
fi

# ---- SECRET_KEY: strong and persistent, never a known default ----
case "${SECRET_KEY:-}" in
  ""|dev-secret-change-me|change-me-to-a-long-random-string)
    if [ ! -s "$DATA_DIR/.secret_key" ]; then
      openssl rand -hex 32 > "$DATA_DIR/.secret_key"
    fi
    SECRET_KEY=$(cat "$DATA_DIR/.secret_key")
    export SECRET_KEY
    ;;
esac

# ---- ADMIN_PASSWORD: only used to create the first admin ----
case "${ADMIN_PASSWORD:-}" in
  ""|123sqwert|change-me-to-a-strong-password)
    if [ ! -s "$DATA_DIR/.admin_password" ]; then
      openssl rand -base64 18 | tr -d '=+/\n' > "$DATA_DIR/.admin_password"
      echo "Generated initial admin password -> stored in $DATA_DIR/.admin_password"
      echo "Read it with: docker compose exec credvault cat $DATA_DIR/.admin_password"
    fi
    ADMIN_PASSWORD=$(cat "$DATA_DIR/.admin_password")
    export ADMIN_PASSWORD
    ;;
esac

# ---- drop privileges ----
if [ "$(id -u)" = "0" ]; then
  chown -R "$APP_USER:$APP_USER" "$DATA_DIR" "$CERT_DIR"
  RUN_AS="setpriv --reuid=$APP_USER --regid=$APP_USER --init-groups"
else
  RUN_AS=""
fi

echo "Starting CredVault on https://0.0.0.0:8443"
# shellcheck disable=SC2086
exec $RUN_AS uvicorn app.main:app --host 0.0.0.0 --port 8443 \
  --proxy-headers --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}" \
  --ssl-keyfile "$KEY_FILE" --ssl-certfile "$CERT_FILE" \
  --no-server-header
