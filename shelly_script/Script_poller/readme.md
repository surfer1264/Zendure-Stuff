# 1.) Shelly Script-Status-Poller

Fragt periodisch `Script.GetStatus` von einem oder mehreren Shelly-Geräten/Script-IDs ab
und schreibt jede Messung als Zeile in eine Semikolon-CSV.

## Nutzung

```bash
python3 shelly_script_status_poller.py --config config.json
python3 shelly_script_status_poller.py --config config.json --once   # nur ein Testdurchlauf
```

Keine externen Abhängigkeiten (nur Python-Standardbibliothek).

## Konfiguration (`config.json`)

- `interval_seconds` – Abfrage-Takt (Standard: 10)
- `timeout_seconds` – HTTP-Timeout pro Anfrage (Standard: 5)
- `csv_file` – Zieldatei (wird angehängt, Header nur einmal geschrieben)
- `targets` – Liste aus `{ "host", "script_id", "label" }`, beliebig viele, auch verschiedene Hosts

## CSV-Spalten

`timestamp;host;script_id;label;running;cpu;mem_used;mem_peak;mem_free;error`

Bei Verbindungsfehlern bleiben die Status-Felder leer, `error` enthält die Meldung – der Poller läuft unbeeindruckt weiter.

## Bekannte Einschränkung

Geht von einem offenen, unauthentifizierten lokalen Netz aus – kein Basic/Digest-Auth-Support.

---


# 2) Shelly WebSocket Log Grabber

Diese Anleitung beschreibt, wie Sie den Live-Debug-Log-Stream eines Shelly-Geräts (Gen2+) per WebSocket abgreifen und in eine Log-Datei speichern.

---

## Vorbereitung & Installation

Das Skript benötigt das Python-Modul `websocket-client`. Installieren Sie dieses über das Terminal / die Eingabeaufforderung:

```bash
pip install websocket-client
```

---

## Konfiguration

Öffnen Sie die Datei `shelly_log_grabber.py` in einem Texteditor und passen Sie den Abschnitt **KONFIGURATION** am Anfang der Datei an:

```python
# ==============================================================================
# KONFIGURATION
# ==============================================================================
SHELLY_IP = "192.168.178.117"  # IP-Adresse Ihres Shelly
TARGET_SCRIPT_ID = 8           # Script-ID zum Filtern (None für ALLE Logs)
LOG_TO_FILE = True             # In Datei speichern? (True / False)
LOG_FILE_PATH = "shelly_debug.log"  # Ziel-Dateiname für das Log
AUTO_RECONNECT = True          # Bei Abbrüchen automatisch neu verbinden
RECONNECT_DELAY = 5            # Pause vor Wiederverbindung (in Sekunden)
# ==============================================================================
```

* **`SHELLY_IP`**: Die IPv4-Adresse des Shelly im lokalen Netz.
* **`TARGET_SCRIPT_ID`**: 
  * Geben Sie die ID ein (z. B. `8`), um nur Meldungen dieses einen Skripts anzuzeigen/zu speichern.
  * Tragen Sie `None` ein, um alle System- und Skript-Logs des Shelly zu erfassen.

---

## Skript ausführen

Starten Sie das Skript im Terminal:

```bash
python3 shelly_log_grabber.py
```

### Ausgabe-Beispiel:
```text
Starte Shelly Log Grabber für 192.168.178.117...
[2026-08-05 21:50:00] ERFOLGREICH VERBUNDEN mit ws://192.168.178.117/debug/log
  -> Filter aktiv: Nur Nachrichten von Script ID 8
------------------------------------------------------------
[2026-08-05 21:50:05] Shelly-Script #8: Power consumption updated to 42.5W
[2026-08-05 21:50:15] Shelly-Script #8: Loop cycle completed.
```

---

## Beenden

* Drücken Sie **`Strg + C`** im Terminal, um den Log-Grabber sauber zu beenden.
* Die gesammelten Logs finden Sie anschließend in der Datei **`shelly_debug.log`** im selben Verzeichnis
