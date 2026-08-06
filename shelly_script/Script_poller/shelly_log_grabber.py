#!/usr/bin/env python3
"""
Shelly WebSocket Debug Log Grabber & Filter
============================================
Verbindet sich per WebSocket mit dem Live-Debug-Log eines Shelly (Gen2+)
über den Pfad ws://<HOST>/debug/log und filtert/schreibt die Logs.

Voraussetzung:
    pip install websocket-client
V2.0.0
"""

import json
import re
import sys
import time
from datetime import datetime
import websocket

# ==============================================================================
# KONFIGURATION
# ==============================================================================
SHELLY_IP = "192.168.178.117"  # IP-Adresse des Shelly

# Script-IDs zum Filtern. Beispiele:
#   [6]        -> nur Script 6
#   [6, 8, 12] -> Scripts 6, 8 und 12 (beliebig viele)
#   None       -> keine ID-Filterung, alle Skripte durchlassen
TARGET_SCRIPT_IDS = [6, 8]
ONLY_SCRIPT_LOGS = True        # True = Systemmeldungen ausblenden, NUR Skript-Logs zeigen

LOG_TO_FILE = True             # In Datei speichern? (True / False)
LOG_FILE_PATH = "shelly_debug.log"  # Dateiname, falls SEPARATE_LOG_FILES = False
SEPARATE_LOG_FILES = False     # True = eigene Datei je Script-ID (shelly_debug_script<ID>.log)
SHOW_SCRIPT_PREFIX = True      # True = "[Script 6]" vor jede Zeile schreiben (sinnvoll bei mehreren IDs)

AUTO_RECONNECT = True          # Bei Verbindungsabbruch automatisch neu verbinden?
RECONNECT_DELAY = 5            # Wartezeit vor Wiederverbindung in Sekunden

# Shelly kennzeichnet jede Log-Zeile mit einem "fd"-Feld. Systemmeldungen
# (auch solche, die *über* ein Skript berichten, z. B. CPU-Auslastung)
# laufen auf niedrigen fd-Werten. Echte print()/console.log()-Ausgaben
# eines Skripts laufen auf einem eigenen, höheren fd. Beobachtung: fd = 100 + Script-ID
# (bei dir z. B. Script 6 -> fd 106). Das ist nicht offiziell dokumentiert -
# bitte einmal mit SHOW_FD_DEBUG=True verifizieren, ob es auf deiner Firmware stimmt.
SCRIPT_FD_BASE = 100
SHOW_FD_DEBUG = False           # True = fd-Wert in der Ausgabe mitloggen (zum Verifizieren)
# ==============================================================================


def format_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def write_log_to_file(text, script_id=None):
    if not LOG_TO_FILE:
        return
    if SEPARATE_LOG_FILES and script_id is not None:
        base, dot, ext = LOG_FILE_PATH.rpartition(".")
        path = f"{base}_script{script_id}.{ext}" if dot else f"{LOG_FILE_PATH}_script{script_id}"
    else:
        path = LOG_FILE_PATH
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

    # fd-basierte Erkennung: fd >= SCRIPT_FD_BASE => Ausgabe eines laufenden
    # Skripts (print()/console.log()). Niedrigere fd-Werte sind interne
    # System-/Notification-Kanäle - auch wenn deren Text zufällig "script:N"
    # enthält (z. B. CPU-Auslastungsmeldungen).
    if detected_script_id is None and isinstance(fd, int) and fd >= SCRIPT_FD_BASE:
        detected_script_id = fd - SCRIPT_FD_BASE

    is_script_msg = detected_script_id is not None

    # Fallback nur falls kein fd im Datensatz vorhanden ist
    if fd is None and detected_script_id is None:
        match = re.search(r"script[:#](\d+)", log_text, re.IGNORECASE)
        if match:
            detected_script_id = int(match.group(1))
            is_script_msg = True

    # 1. Check: Nur Skript-Logs erlauben?
    if ONLY_SCRIPT_LOGS and not is_script_msg:
        return None, None  # Systemmeldung verworfen

    # 2. Check: Auf eine Menge von Script-IDs filtern?
    if TARGET_SCRIPT_IDS is not None:
        if detected_script_id is not None and int(detected_script_id) not in TARGET_SCRIPT_IDS:
            return None, None  # Gehört zu keinem der gewünschten Skripte

    if SHOW_FD_DEBUG:
        log_text = f"[fd={fd}] {log_text}"

    return log_text, detected_script_id


def on_message(ws, message):
    log_text, script_id = parse_and_filter(message)
    if log_text is None:
        return  # Gefiltert

    ts = format_timestamp()
    prefix = f"[Script {script_id}] " if (SHOW_SCRIPT_PREFIX and script_id is not None) else ""
    formatted_msg = f"[{ts}] {prefix}{log_text}"
    print(formatted_msg)
    write_log_to_file(formatted_msg, script_id)


def on_error(ws, error):
    print(f"[{format_timestamp()}] WebSocket-Fehler: {error}")


def on_close(ws, close_status_code, close_msg):
    print(f"[{format_timestamp()}] Verbindung geschlossen ({close_status_code}: {close_msg})")


def on_open(ws):
    print(f"[{format_timestamp()}] ERFOLGREICH VERBUNDEN mit ws://{SHELLY_IP}/debug/log")
    print(f"  -> Systemmeldungen ausblenden: {'JA' if ONLY_SCRIPT_LOGS else 'NEIN'}")
    if TARGET_SCRIPT_IDS is not None:
        ids = ", ".join(str(i) for i in TARGET_SCRIPT_IDS)
        print(f"  -> Filter aktiv: Nur Nachrichten von Script ID(s) {ids}")
    else:
        print("  -> Zeige Logs aller Skripte")
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