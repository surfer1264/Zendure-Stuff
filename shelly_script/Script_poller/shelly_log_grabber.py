#!/usr/bin/env python3
"""
Shelly WebSocket Debug Log Grabber & Filter
============================================
Verbindet sich per WebSocket mit dem Live-Debug-Log eines Shelly (Gen2+)
über den Pfad ws://<HOST>/debug/log und filtert/schreibt die Logs.

Konfiguration erfolgt ueber eine JSON-Datei (Standard: config.json im
selben Verzeichnis), siehe shelly_log_grabber_config.json als Beispiel.

Aufruf:
    python3 shelly_log_grabber.py [--config PATH]

    --config PATH   Pfad zur Config-Datei (Standard: config.json)

Voraussetzung:
    pip install websocket-client
V2.1.0
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
import websocket

CONFIG = {}  # wird in main() per load_config() befuellt


def load_config(path):
    if not os.path.isfile(path):
        sys.exit(f"Config-Datei nicht gefunden: {path}")

    with open(path, "r", encoding="utf-8") as f:
        try:
            cfg = json.load(f)
        except json.JSONDecodeError as e:
            sys.exit(f"Config-Datei ist kein gueltiges JSON ({path}): {e}")

    if "shelly_ip" not in cfg:
        sys.exit("Config-Fehler: 'shelly_ip' fehlt.")

    # Defaults, falls in der Config nicht gesetzt (target_script_ids darf
    # bewusst "null" sein -> keine ID-Filterung, alle Skripte durchlassen)
    cfg.setdefault("target_script_ids", None)
    cfg.setdefault("only_script_logs", True)
    cfg.setdefault("log_to_file", True)
    cfg.setdefault("log_file_path", "shelly_debug.log")
    cfg.setdefault("separate_log_files", False)
    cfg.setdefault("show_script_prefix", True)
    cfg.setdefault("auto_reconnect", True)
    cfg.setdefault("reconnect_delay", 5)
    cfg.setdefault("script_fd_base", 100)
    cfg.setdefault("show_fd_debug", False)

    return cfg


def format_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def write_log_to_file(text, script_id=None):
    if not CONFIG["log_to_file"]:
        return
    log_file_path = CONFIG["log_file_path"]
    if CONFIG["separate_log_files"] and script_id is not None:
        base, dot, ext = log_file_path.rpartition(".")
        path = f"{base}_script{script_id}.{ext}" if dot else f"{log_file_path}_script{script_id}"
    else:
        path = log_file_path
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception as e:
        print(f"Fehler beim Schreiben in Logdatei: {e}")


def parse_and_filter(message):
    """Filtert eingehende Nachrichten nach System/Skript-Status und Script-ID.

    Rückgabe: (log_text, detected_script_id) oder (None, None) falls gefiltert.
    """
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        data = message

    log_text = ""
    fd = None
    detected_script_id = None

    if isinstance(data, dict):
        # Die eigentliche Nachricht steht im "data"-Feld (Shelly-Log-Format:
        # {"ts":..., "level":2, "data":"<message>", "fd":N}). "msg"/"text"
        # existieren in der Praxis nicht - das war der Grund, warum bisher
        # das komplette JSON-Objekt ausgegeben wurde.
        log_text = data.get("data") or data.get("msg") or data.get("text") \
            or json.dumps(data, ensure_ascii=False)
        fd = data.get("fd")
        detected_script_id = data.get("script_id") or data.get("sid")
    else:
        log_text = str(data)

    # fd-basierte Erkennung: fd >= script_fd_base => Ausgabe eines laufenden
    # Skripts (print()/console.log()). Niedrigere fd-Werte sind interne
    # System-/Notification-Kanäle - auch wenn deren Text zufällig "script:N"
    # enthält (z. B. CPU-Auslastungsmeldungen).
    if detected_script_id is None and isinstance(fd, int) and fd >= CONFIG["script_fd_base"]:
        detected_script_id = fd - CONFIG["script_fd_base"]

    is_script_msg = detected_script_id is not None

    # Fallback nur falls kein fd im Datensatz vorhanden ist
    if fd is None and detected_script_id is None:
        match = re.search(r"script[:#](\d+)", log_text, re.IGNORECASE)
        if match:
            detected_script_id = int(match.group(1))
            is_script_msg = True

    # 1. Check: Nur Skript-Logs erlauben?
    if CONFIG["only_script_logs"] and not is_script_msg:
        return None, None  # Systemmeldung verworfen

    # 2. Check: Auf eine Menge von Script-IDs filtern?
    target_script_ids = CONFIG["target_script_ids"]
    if target_script_ids is not None:
        if detected_script_id is not None and int(detected_script_id) not in target_script_ids:
            return None, None  # Gehört zu keinem der gewünschten Skripte

    if CONFIG["show_fd_debug"]:
        log_text = f"[fd={fd}] {log_text}"

    return log_text, detected_script_id


def on_message(ws, message):
    log_text, script_id = parse_and_filter(message)
    if log_text is None:
        return  # Gefiltert

    ts = format_timestamp()
    prefix = f"[Script {script_id}] " if (CONFIG["show_script_prefix"] and script_id is not None) else ""
    formatted_msg = f"[{ts}] {prefix}{log_text}"
    print(formatted_msg)
    write_log_to_file(formatted_msg, script_id)


def on_error(ws, error):
    print(f"[{format_timestamp()}] WebSocket-Fehler: {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"[{format_timestamp()}] Verbindung geschlossen ({close_status_code}: {close_msg})")


def on_open(ws):
    shelly_ip = CONFIG["shelly_ip"]
    print(f"[{format_timestamp()}] ERFOLGREICH VERBUNDEN mit ws://{shelly_ip}/debug/log")
    print(f"  -> Systemmeldungen ausblenden: {'JA' if CONFIG['only_script_logs'] else 'NEIN'}")
    target_script_ids = CONFIG["target_script_ids"]
    if target_script_ids is not None:
        ids = ", ".join(str(i) for i in target_script_ids)
        print(f"  -> Filter aktiv: Nur Nachrichten von Script ID(s) {ids}")
    else:
        print("  -> Zeige Logs aller Skripte")
    print("-" * 60)


def main():
    parser = argparse.ArgumentParser(description="Verbindet sich mit dem Shelly-Debug-Log per WebSocket und filtert/schreibt die Logs.")
    parser.add_argument("--config", default="config.json", help="Pfad zur Config-Datei (Standard: config.json)")
    args = parser.parse_args()

    global CONFIG
    CONFIG = load_config(args.config)

    shelly_ip = CONFIG["shelly_ip"]
    ws_url = f"ws://{shelly_ip}/debug/log"
    print(f"Starte Shelly Log Grabber für {shelly_ip}...")

    while True:
        try:
            ws = websocket.WebSocketApp(
                ws_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            ws.run_forever()
        except KeyboardInterrupt:
            print("\n[+] Beendet durch Benutzer (Strg+C).")
            sys.exit(0)
        except Exception as e:
            print(f"[{format_timestamp()}] Unerwarteter Fehler: {e}")

        if not CONFIG["auto_reconnect"]:
            break

        print(f"[{format_timestamp()}] Versuche Wiederverbindung in {CONFIG['reconnect_delay']} Sekunden...")
        time.sleep(CONFIG["reconnect_delay"])


if __name__ == "__main__":
    main()