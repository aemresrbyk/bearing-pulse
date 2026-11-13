"""Fake sensor node: plays CWRU recordings over MQTT as if an ESP32 + ADXL345 were measuring them.

Stands in for the real node until the hardware arrives. The message format is the same one the
firmware will send, so the bridge, database and dashboard don't change when the ESP32 replaces it.

    python sim/node_sim.py --condition inner          # raw samples (Phase 2)
    python sim/node_sim.py --mode features            # features only (Phase 3)
    python sim/node_sim.py --mode model --cycle       # on-device prediction (Phase 4)
    python sim/node_sim.py --mode model --tls         # over TLS + password like the real node (Phase 5)
"""
import argparse
import json
import sys
import time
from pathlib import Path

import paho.mqtt.client as mqtt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import bearing  # noqa: E402
import edge  # noqa: E402  (features and model run through the firmware C code)

FS = edge.FS
BATCH = 256          # samples per raw MQTT message (80 ms)
# 1 HP recordings. The device model was trained on all loads, so these are in-sample: fine for a
# dashboard demo, not an accuracy measurement (that is src/train_edge.py's leave-one-load-out).
RECORDING = {"normal": 98, "inner": 106, "ball": 119, "outer": 131}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", choices=list(RECORDING), default="normal")
    ap.add_argument("--cycle", action="store_true", help="go through all conditions")
    ap.add_argument("--period", type=float, default=20, help="seconds per condition with --cycle")
    ap.add_argument("--mode", choices=["raw", "features", "model"], default="raw")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--node", default="node1")
    ap.add_argument("--seconds", type=float, default=float("inf"))
    ap.add_argument("--tls", action="store_true", help="port 8883 with TLS + password from .env (Phase 5)")
    args = ap.parse_args()

    signals = {c: edge.adxl345(bearing.load(n)[0]) for c, n in RECORDING.items()}

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sim-{args.node}")
    port = 1883
    if args.tls:   # connect the way the ESP32 will: port 8883, verify the broker with our CA, log in
        root = Path(__file__).resolve().parent.parent
        env = dict(l.strip().split("=", 1) for l in open(root / ".env") if "=" in l)
        client.tls_set(ca_certs=str(root / ".local/certs/ca.crt"))
        client.username_pw_set(env["MQTT_USER"], env["MQTT_PASSWORD"])
        port = 8883
    client.connect(args.host, port)
    client.loop_start()

    order = list(RECORDING) if args.cycle else [args.condition]
    step = BATCH if args.mode == "raw" else edge.WINDOW
    start, sent_bytes, k = time.time(), 0, 0
    while time.time() - start < args.seconds:
        cond = order[int((time.time() - start) // args.period) % len(order)]
        x = signals[cond]
        i = (k * step) % (len(x) - step)              # loop the recording
        chunk = x[i:i + step]
        t0 = time.time_ns()
        if args.mode == "raw":
            msg = {"t0": t0, "fs": FS, "x": [round(v, 4) for v in chunk]}
        else:
            msg = {"t": t0, **edge.features_dict(chunk)}
            if args.mode == "model":
                msg.update(edge.predict(chunk))
        msg["truth"] = cond                           # simulator only: lets the dashboard show ground truth
        payload = json.dumps(msg)
        client.publish(f"bearingpulse/{args.node}/{args.mode}", payload, qos=0)
        sent_bytes += len(payload)
        k += 1
        time.sleep(max(0, start + k * step / FS - time.time()))   # real-time pacing
    rate = sent_bytes / (time.time() - start)
    print(f"{args.mode}: {k} messages, {rate / 1000:.1f} kB/s")
    client.loop_stop()
    client.disconnect()


if __name__ == "__main__":
    main()
