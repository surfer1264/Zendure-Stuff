Zwei Scripte helfen einen Überblick zu erhalten, was mit und auf dem Shelly passiert

Der **Script-Status-Poller** schaut von außen drauf und misst im 15Sek-Takt CPU und freien Speicher)

Der **Websocket-Log-Grabber** holt das Script-Log aus dem Shelly raus, um über mehrere Stunden den Betrieb zu loggen. Dieses Log ist Grundlage für jegliche Analysen.

Grundvoraussetzung ist eine Python-Umgebung. Die existiert defacto auf jedem Computer und Betriebssystem oder lässt sich sehr einfach nachinstallieren.

Ladet Euch die Dateien hier in EIN Verzeichnis auf Eurem Computer
* passt die CMD-Files für Euch an (Windows-Nutzer)
* konfiguriert die `config.json` und die `shelly_log_grabber.py`

# 1.) Shelly Script-Status-Poller

Diese Anleitung beschreibt, wie Sie den Status zu einem Shelly-Script abgreifen und in eine Log-Datei speichern können.

Fragt periodisch `Script.GetStatus` von einem oder mehreren Shelly-Geräten/Script-IDs ab
und schreibt jede Messung als Zeile in eine Semikolon-CSV.

Relevante Dateien sind
`config.json` für die Konfiguration
und 
das eigentliche Script `shelly_script_status_poller.py`.


## Script ausführen

```bash
# in einer Kommandozeile aufrufen
python3 shelly_script_status_poller.py --config config.json
python3 shelly_script_status_poller.py --config config.json --once   # nur ein Testdurchlauf
```

Keine externen Abhängigkeiten (nur Python-Standardbibliothek).

## Konfiguration (`config.json`)

- `interval_seconds` – Abfrage-Takt (Standard: 10)
- `timeout_seconds` – HTTP-Timeout pro Anfrage (Standard: 5)
- `csv_file` – Zieldatei (wird angehängt, Header nur einmal geschrieben)
- `targets` – Liste aus `{ "host", "script_id", "label" }`, beliebig viele, auch verschiedene Hosts

### Beispiel

```json
{
  "interval_seconds": 15,
  "timeout_seconds": 5,
  "csv_file": "script_status.csv",

  "targets": [
    { "host": "192.168.178.117", "script_id": 8, "label": "Regler auf 3EM" },
    { "host": "192.168.178.117", "script_id": 6, "label": "Watchdog auf 3EM" }
  ]
}
```

## CSV-Spalten

`timestamp;host;script_id;label;running;cpu;mem_used;mem_peak;mem_free;error`

Bei Verbindungsfehlern bleiben die Status-Felder leer, `error` enthält die Meldung – der Poller läuft unbeeindruckt weiter. Kann man direkt z.B. in Excel öffnen.

### Beispiel

```csv
2026-08-06T12:36:34+02:00;192.168.178.117;8;Regler auf 3EM;False;0;;;18074;
2026-08-06T12:36:34+02:00;192.168.178.117;6;Watchdog auf 3EM;True;0;7112;13188;18074;
2026-08-06T12:36:49+02:00;192.168.178.117;8;Regler auf 3EM;False;0;;;18074;
2026-08-06T12:36:49+02:00;192.168.178.117;6;Watchdog auf 3EM;True;0;7112;13188;18074;
```

## Bekannte Einschränkung

Geht von einem offenen, unauthentifizierten lokalen Netz aus – kein Basic/Digest-Auth-Support.

---


# 2) Shelly WebSocket Log Grabber

Diese Anleitung beschreibt, wie Sie den Live-Debug-Log-Stream eines Shelly-Geräts (Gen2+) per WebSocket abgreifen und in eine Log-Datei speichern.

---

## Vorbereitung & Installation

Das Skript benötigt das Python-Modul `websocket-client`. Installieren Sie dieses über das Terminal / die Eingabeaufforderung in Ihrem Computer:

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
```

* **`SHELLY_IP`**: Die IPv4-Adresse des Shelly im lokalen Netz.
* **`TARGET_SCRIPT_ID`**: 
  * Geben Sie die eine oder mehrere IDs ein (z. B. `8`), um nur Meldungen dieses einen Skripts anzuzeigen/zu speichern.
  * Tragen Sie `None` ein, um alle System- und Skript-Logs des Shelly zu erfassen.

---

## Skript ausführen

Starten Sie das Skript im Terminal:

```bash
python3 shelly_log_grabber.py
```

### Ausgabe-Beispiel:
```text
[2026-08-06 13:43:27] [Script 8] Grid: 27.471 W | Summe Geraete: 0 W (netzladefaehig: 0 W) | Ziel Entladen: 18 W | Ziel Laden: 18 W
[2026-08-06 13:43:27] [Script 8]   SF2400: SOC 36% | socLimit 0 | Ist 0 W | Soll 0 W | acMode 1 (Import/Idle)
[2026-08-06 13:43:27] [Script 8]   Fatamorgana: SOC 36% | socLimit 0 | Ist 0 W | Soll 0 W | acMode 1 (Import/Idle) [DRYRUN - wird nicht geschrieben]
[2026-08-06 13:43:32] [Script 8] Grid: -30.516 W | Summe Geraete: 0 W (netzladefaehig: 0 W) | Ziel Entladen: -11 W | Ziel Laden: -11 W
[2026-08-06 13:43:32] [Script 8]   SF2400: SOC 36% | socLimit 0 | Ist 0 W | Soll 0 W | acMode 1 (Import/Idle)
[2026-08-06 13:43:32] [Script 8]   Fatamorgana: SOC 36% | socLimit 0 | Ist 0 W | Soll 0 W | acMode 1 (Import/Idle) [DRYRUN - wird nicht geschrieben]
[2026-08-06 13:43:35] [Script 8] Grid: 45.32 W | Summe Geraete: 0 W (netzladefaehig: 0 W) | Ziel Entladen: 22 W | Ziel Laden: 22 W
[2026-08-06 13:43:35] [Script 8]   SF2400: SOC 36% | socLimit 0 | Ist 0 W | Soll 0 W | acMode 1 (Import/Idle)
[2026-08-06 13:43:35] [Script 8]   Fatamorgana: SOC 36% | socLimit 0 | Ist 0 W | Soll 0 W | acMode 1 (Import/Idle) [DRYRUN - wird nicht geschrieben]
```

## Testen
unbedingt die geschriebenen Logfiles ansehen. Alle Shelly Versionen bringen so Ihre Eigenheiten mit sich.


---

## Beenden

* Drücken Sie **`Strg + C`** im Terminal, um den Log-Grabber sauber zu beenden.
* Die gesammelten Logs finden Sie anschließend in der Datei **`shelly_debug.log`** im selben Verzeichnis
