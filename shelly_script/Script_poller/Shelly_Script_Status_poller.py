#!/usr/bin/env python3
"""
Shelly Script-Status-Poller
============================
Fragt fuer beliebig viele Shelly-Geraete/Script-IDs periodisch den
Script-Status ab (RPC: Script.GetStatus) und schreibt jede Messung als
Zeile in eine Semikolon-getrennte CSV-Datei.

Verwendet die einfache GET-Variante der Shelly-Gen2+-RPC-Schnittstelle:
    GET http://<host>/rpc/Script.GetStatus?id=<script_id>

Konfiguration erfolgt ausschliesslich ueber eine JSON-Datei (Standard:
config.json im selben Verzeichnis), siehe config.json als Beispiel.

Aufruf:
    python3 shelly_script_status_poller.py [--config PATH] [--once]

    --config PATH   Pfad zur Config-Datei (Standard: config.json)
    --once          Nur einen einzigen Durchlauf ausfuehren und beenden
                     (zum Testen der Konfiguration, ohne Dauerlauf)
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

CSV_FIELDS = [
    "timestamp",
    "host",
    "script_id",
    "label",
    "running",
    "cpu",
    "mem_used",
    "mem_peak",
    "mem_free",
    "error",
]


def load_config(path):
    if not os.path.isfile(path):
        sys.exit(f"Config-Datei nicht gefunden: {path}")

    with open(path, "r", encoding="utf-8") as f:
        try:
            cfg = json.load(f)
        except json.JSONDecodeError as e:
            sys.exit(f"Config-Datei ist kein gueltiges JSON ({path}): {e}")

    if "targets" not in cfg or not isinstance(cfg["targets"], list) or not cfg["targets"]:
        sys.exit("Config-Fehler: 'targets' muss eine nicht-leere Liste sein.")

    for i, t in enumerate(cfg["targets"]):
        if "host" not in t or "script_id" not in t:
            sys.exit(f"Config-Fehler: targets[{i}] braucht mindestens 'host' und 'script_id'.")
        t.setdefault("label", f"{t['host']}#{t['script_id']}")

    cfg.setdefault("interval_seconds", 10)
    cfg.setdefault("timeout_seconds", 5)
    cfg.setdefault("csv_file", "script_status.csv")

    return cfg


def fetch_script_status(host, script_id, timeout):
    """Ruft Script.GetStatus per einfachem HTTP-GET ab.
    Gibt (status_dict, error_string) zurueck - genau einer der beiden ist None."""
    url = f"http://{host}/rpc/Script.GetStatus?id={script_id}"

    try:
        with urlopen(url, timeout=timeout) as resp:
            if resp.status != 200:
                return None, f"HTTP {resp.status}"
            body = resp.read().decode("utf-8", errors="replace")
    except HTTPError as e:
        return None, f"HTTP-Fehler {e.code}: {e.reason}"
    except URLError as e:
        return None, f"Verbindungsfehler: {e.reason}"
    except TimeoutError:
        return None, "Timeout"
    except Exception as e:  # bewusst breit - jeder Fehler soll eine CSV-Zeile ergeben, nie den Poller stoppen
        return None, f"Unerwarteter Fehler: {e}"

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None, "Antwort ist kein gueltiges JSON"

    if "error" in data:
        # Shelly-RPC-Fehlerantwort, z.B. {"code":-105,"message":"Bad id=5"}
        return None, f"RPC-Fehler: {data['error'].get('message', data['error'])}"

    return data, None


def poll_once(targets, timeout, csv_writer, csv_file_handle):
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    for t in targets:
        status, error = fetch_script_status(t["host"], t["script_id"], timeout)

        row = {
            "timestamp": ts,
            "host": t["host"],
            "script_id": t["script_id"],
            "label": t["label"],
            "running": "",
            "cpu": "",
            "mem_used": "",
            "mem_peak": "",
            "mem_free": "",
            "error": "",
        }

        if error:
            row["error"] = error
            print(f"[{ts}] {t['label']} ({t['host']}): FEHLER - {error}")
        else:
            row["running"] = status.get("running")
            row["cpu"] = status.get("cpu")
            row["mem_used"] = status.get("mem_used")
            row["mem_peak"] = status.get("mem_peak")
            row["mem_free"] = status.get("mem_free")
            print(
                f"[{ts}] {t['label']} ({t['host']}): running={row['running']} "
                f"cpu={row['cpu']} mem_used={row['mem_used']} mem_peak={row['mem_peak']} mem_free={row['mem_free']}"
            )

        csv_writer.writerow(row)

    csv_file_handle.flush()


def main():
    parser = argparse.ArgumentParser(description="Pollt den Shelly Script-Status mehrerer Ziele in eine CSV.")
    parser.add_argument("--config", default="config.json", help="Pfad zur Config-Datei (Standard: config.json)")
    parser.add_argument("--once", action="store_true", help="Nur einen Durchlauf ausfuehren, dann beenden")
    args = parser.parse_args()

    cfg = load_config(args.config)
    targets = cfg["targets"]
    interval = cfg["interval_seconds"]
    timeout = cfg["timeout_seconds"]
    csv_path = cfg["csv_file"]

    write_header = not os.path.isfile(csv_path) or os.path.getsize(csv_path) == 0

    print(f"Ziele: {len(targets)} | Intervall: {interval}s | CSV: {csv_path}")
    for t in targets:
        print(f"  - {t['label']}: {t['host']} (script_id={t['script_id']})")

    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, delimiter=";")
        if write_header:
            writer.writeheader()
            f.flush()

        if args.once:
            poll_once(targets, timeout, writer, f)
            return

        next_run = time.monotonic()
        try:
            while True:
                poll_once(targets, timeout, writer, f)

                # Drift-korrigiertes Intervall: haengt vom festen Startzeitpunkt ab,
                # nicht von "Dauer des letzten Durchlaufs + interval" - verhindert,
                # dass sich der Takt bei langer Laufzeit langsam verschiebt.
                next_run += interval
                sleep_for = next_run - time.monotonic()

                if sleep_for > 0:
                    time.sleep(sleep_for)
                else:
                    # Durchlauf hat laenger als das Intervall gedauert - sofort weiter,
                    # Takt auf "jetzt" resynchronisieren statt Sleep-Schulden aufzubauen.
                    next_run = time.monotonic()

        except KeyboardInterrupt:
            print("\nBeendet (Strg+C).")


if __name__ == "__main__":
    main()