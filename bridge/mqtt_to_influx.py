"""MQTT -> InfluxDB 3 bridge. Subscribes to bearingpulse/<node>/<kind> and writes line protocol.

    raw       {"t0": ns, "fs": Hz, "x": [...]}   -> one point per sample in measurement "raw"
    features  {"t": ns, "rms": .., ...}          -> one point per window in measurement "features"
    model     same as features + "label", "confidence"
"""
import json
import os
import threading
import time
import urllib.request

import paho.mqtt.client as mqtt

INFLUX = os.environ.get("INFLUX_URL", "http://127.0.0.1:8181")
DB = os.environ.get("INFLUX_DB", "bearingpulse")
WRITE_URL = f"{INFLUX}/api/v3/write_lp?db={DB}&precision=nanosecond"
FLUSH_S = 1.0   # each write waits ~0.5 s for InfluxDB's WAL, so one write per message can't keep up

pending, lock = [], threading.Lock()


def to_lines(node, kind, msg):
    """Convert one MQTT message into InfluxDB line protocol."""
    tags = f"node={node}"
    if "truth" in msg:
        tags += f",truth={msg['truth']}"
    if kind == "raw":
        dt = int(1e9 / msg["fs"])
        return [f"raw,{tags} x={v} {msg['t0'] + i * dt}" for i, v in enumerate(msg["x"])]
    fields = []
    for k, v in msg.items():
        if k in ("t", "truth"):
            continue
        fields.append(f'{k}="{v}"' if isinstance(v, str) else f"{k}={float(v)}")
    return [f"{kind},{tags} {','.join(fields)} {msg['t']}"]


def write(lines):
    req = urllib.request.Request(WRITE_URL, data="\n".join(lines).encode(), method="POST")
    urllib.request.urlopen(req, timeout=5).read()


def on_message(client, userdata, m):
    _, node, kind = m.topic.split("/")
    try:
        lines = to_lines(node, kind, json.loads(m.payload))
    except Exception as e:      # a malformed message must not kill the bridge
        print(f"bad message on {m.topic}: {e}")
        return
    with lock:
        pending.extend(lines)


def flush_forever():
    global pending
    while True:
        time.sleep(FLUSH_S)
        with lock:
            batch, pending = pending, []
        if not batch:
            continue
        try:
            write(batch)
        except Exception as e:  # DB down: put the batch back and retry next round
            print(f"write failed ({len(batch)} lines), retrying: {e}")
            with lock:
                pending = batch + pending


if __name__ == "__main__":
    c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="bridge")
    c.on_message = on_message
    c.on_connect = lambda cl, *a: cl.subscribe("bearingpulse/+/+")   # re-subscribe after reconnect
    c.connect(os.environ.get("MQTT_HOST", "127.0.0.1"), 1883)
    c.loop_start()              # MQTT runs in its own thread, the main thread flushes to InfluxDB
    flush_forever()
