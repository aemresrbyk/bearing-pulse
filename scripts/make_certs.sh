#!/usr/bin/env bash
# Phase 5: self-signed CA + broker certificate + MQTT password file, all in .local/ (git-ignored).
# Usage: scripts/make_certs.sh [extra-ip]   e.g. the laptop's LAN IP, so the ESP32 can verify the broker
set -euo pipefail
cd "$(dirname "$0")/.."
D=.local/certs; mkdir -p "$D"
[ -f .env ] || { echo "MQTT_USER=node1" > .env; echo "MQTT_PASSWORD=$(openssl rand -hex 16)" >> .env; }
source .env
SAN="DNS:localhost,IP:127.0.0.1${1:+,IP:$1}"
openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -subj "/CN=bearing-pulse-ca" \
  -keyout "$D/ca.key" -out "$D/ca.crt" 2>/dev/null
openssl req -newkey rsa:2048 -nodes -subj "/CN=localhost" -keyout "$D/server.key" -out "$D/server.csr" 2>/dev/null
openssl x509 -req -in "$D/server.csr" -CA "$D/ca.crt" -CAkey "$D/ca.key" -CAcreateserial -days 825 \
  -extfile <(echo "subjectAltName=$SAN") -out "$D/server.crt" 2>/dev/null
rm -f "$D/passwd"; touch "$D/passwd"; chmod 600 "$D/passwd"
/opt/homebrew/bin/mosquitto_passwd -b "$D/passwd" "$MQTT_USER" "$MQTT_PASSWORD"
echo "certs + password file in $D (SAN: $SAN); credentials in .env"
