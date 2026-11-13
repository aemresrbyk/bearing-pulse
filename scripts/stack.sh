#!/usr/bin/env bash
# Start/stop the local stack: Mosquitto, InfluxDB 3, Grafana, MQTT->Influx bridge.
# Data and logs live in .local/ (git-ignored). Install once: brew install mosquitto influxdb grafana
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
L=$ROOT/.local
mkdir -p "$L"/{influx,grafana,logs,pids}

start() {
  /opt/homebrew/sbin/mosquitto -c services/mosquitto.conf >"$L/logs/mosquitto.log" 2>&1 &
  echo $! >"$L/pids/mosquitto"
  # without-auth only on localhost for development; Phase 5 adds auth
  influxdb3 serve --node-id local --object-store file --data-dir "$L/influx" \
    --http-bind 127.0.0.1:8181 --without-auth >"$L/logs/influx.log" 2>&1 &
  echo $! >"$L/pids/influx"
  GF=/opt/homebrew/opt/grafana/share/grafana
  GF_PATHS_PROVISIONING=$ROOT/grafana/provisioning GF_PATHS_DATA=$L/grafana GF_PATHS_LOGS=$L/logs \
  GF_AUTH_ANONYMOUS_ENABLED=true GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer BP_DASHBOARDS=$ROOT/grafana/dashboards \
    grafana server --homepath "$GF" >"$L/logs/grafana.log" 2>&1 &
  echo $! >"$L/pids/grafana"
  for _ in $(seq 30); do curl -sf http://127.0.0.1:8181/health >/dev/null && break; sleep 0.5; done
  .venv/bin/python bridge/mqtt_to_influx.py >"$L/logs/bridge.log" 2>&1 &
  echo $! >"$L/pids/bridge"
  echo "up: MQTT :1883 · InfluxDB :8181 · Grafana http://localhost:3000"
}

stop() {
  for p in "$L"/pids/*; do [ -f "$p" ] && kill "$(cat "$p")" 2>/dev/null; rm -f "$p"; done
  echo "stopped"
}

"${1:-start}"
