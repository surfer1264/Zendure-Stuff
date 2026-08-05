#!/usr/bin/env python3
"""
Shelly WebSocket Debug Log Grabber & Filter
============================================
Verbindet sich per WebSocket mit dem Live-Debug-Log eines Shelly (Gen2+)
über den Pfad ws://<HOST>/debug/log und filtert/schreibt die Logs.

Voraussetzung:
    pip install websocket-client

Aufruf:
    python3 shelly_log_grabber.py
"""

import json
import os
import sys
import time
from datetime import datetime
import websocket

# ==============================================================================
# KONFIGURATION (Hier IP-Adresse und Script-ID anpassen)
# ==============================================================================
SHELLY_IP = "192.168.178.117"  # IP-Adresse des Shelly
TARGET_SCRIPT_ID = 8           # Script-ID zum Filtern (None setzen für ALLE Logs)

LOG_TO_FILE = True             # In Datei speichern? (True / False)
LOG_FILE_PATH = "shelly_debug.log"  # Dateiname für das Log
AUTO_RECONNECT = True          # Bei Verbindungsabbruch automatisch neu verbinden?
RECONNECT_DELAY = 5            # Wartezeit vor Wiederverbindung in Sekunden
# ==============================================================================


def format_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def write_log_to_file(text):
    if not LOG_TO_FILE:
        return
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(text + "\n")
    except Exception as e:
        print(f"Fehler beim Schreiben in Logdatei: {e}")


def on_message(ws, message):
    """Wird aufgerufen, wenn eine neue Log-Nachricht vom Shelly empfangen wird."""
    ts = format_timestamp()

    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        # Fallback, falls die Nachricht reiner Text/kein JSON ist
        log_line = f"[{ts}] {message}"
        print(log_line)
        write_log_to_file(log_line)
        return

    # Extraktion der Nachricht und der Script-ID aus dem JSON
    log_text = ""
    script_id = None

    if isinstance(data, dict):
        # Shelly Gen2/Gen3 liefert Logs meist in 'msg' oder 'text'
        log_text = data.get("msg") or data.get("text") or json.dumps(data, ensure_ascii=False)
        script_id = data.get("script_id") or data.get("sid")
    else:
        log_text = str(data)

    # Filterung nach Script-ID
    if TARGET_SCRIPT_ID is not None and script_id is not None:
        if str(script_id) != str(TARGET_SCRIPT_ID):
            return  # Ignorieren, wenn es von einem anderen Skript stammt

    formatted_msg = f"[{ts}] {log_text}"
    print(formatted_msg)
    write_log_to_file(formatted_msg)


def on_error(ws, error):
    print(f"[{format_timestamp()}] WebSocket-Fehler: {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"[{format_timestamp()}] Verbindung geschlossen ({close_status_code}: {close_msg})")


def on_open(ws):
    print(f"[{format_timestamp()}] ERFOLGREICH VERBUNDEN mit ws://{SHELLY_IP}/debug/log")
    if TARGET_SCRIPT_ID is not None:
        print(f"  -> Filter aktiv: Zeige nur Logs von Script ID {TARGET_SCRIPT_ID}")
    else:
        print("  -> Zeige ALLE System- & Script-Logs")
    print("-" * 60)


def main():
    ws_url = f"ws://{SHELLY_IP}/debug/log"
    print(f"Starte Shelly Log Grabber für {SHELLY_IP}...")

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

        if not AUTO_RECONNECT:
            break

        print(f"[{format_timestamp()}] Versuche Wiederverbindung in {RECONNECT_DELAY} Sekunden...")
        time.sleep(RECONNECT_DELAY)


if __name__ == "__main__":
    main()