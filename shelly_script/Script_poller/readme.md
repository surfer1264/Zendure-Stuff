Zwei Scripte helfen einen Überblick zu erhalten, was mit und auf dem Shelly passiert

Der **Script-Status-Poller** schaut von außen drauf und misst im 15Sek-Takt CPU und freien Speicher)

Der **Websocket-Log-Grabber** holt das Script-Log aus dem Shelly raus, um über mehrere Stunden den Betrieb zu loggen. Dieses Log ist Grundlage für jegliche Analysen.

Grundvoraussetzung ist eine Python-Umgebung. Die existiert defacto auf jedem Computer und Betriebssystem oder lässt sich sehr einfach nachinstallieren.

Ladet Euch die Dateien hier in EIN Verzeichnis auf Eurem Computer
* passt die CMD-Files für Euch an (Windows-Nutzer)
* konfiguriert die beiden Config-Dateien (siehe unten) – ein Bearbeiten der `.py`-Dateien ist **nicht** nötig

> **Wichtig:** Beide Scripte erwarten standardmäßig eine Datei namens `config.json` im selben Verzeichnis. Da hier beide Scripte gemeinsam in einem Ordner liegen, würden sich die Configs sonst gegenseitig überschreiben bzw. das jeweils falsche Script liest die falsche Datei. Deshalb bekommt jede Config in dieser Anleitung einen eigenen, eindeutigen Namen (`config_status_poller.json` bzw. `config_log_grabber.json`) und wird dem jeweiligen Script explizit per `--config` übergeben.

# 1.) Shelly Script-Status-Poller

Diese Anleitung beschreibt, wie Sie den Status zu einem Shelly-Script abgreifen und in eine Log-Datei speichern können.

Fragt periodisch `Script.GetStatus` von einem oder mehreren Shelly-Geräten/Script-IDs ab
und schreibt jede Messung als Zeile in eine Semikolon-CSV.

Relevante Dateien sind
`config_status_poller.json` für die Konfiguration
und
das eigentliche Script `shelly_script_status_poller.py`.


## Script ausführen

```bash
# in einer Kommandozeile aufrufen
python3 shelly_script_status_poller.py --config config_status_poller.json
python3 shelly_script_status_poller.py --config config_status_poller.json --once   # nur ein Testdurchlauf
```

Keine externen Abhängigkeiten (nur Python-Standardbibliothek).

## Konfiguration (`config_status_poller.json`)

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

Die Konfiguration erfolgt über eine JSON-Datei (hier: `config_log_grabber.json`), die im selben Verzeichnis wie das Script liegt. Ein Bearbeiten der Datei `shelly_log_grabber.py` selbst ist nicht mehr nötig – alle Einstellungen stehen in der JSON-Datei:

```json
{
  "shelly_ip": "192.168.178.117",

  "target_script_ids": [6, 8],
  "only_script_logs": true,

  "log_to_file": true,
  "log_file_path": "shelly_debug.log",
  "separate_log_files": false,
  "daily_log_rotation": true,
  "show_script_prefix": true,

  "auto_reconnect": true,
  "reconnect_delay": 5,

  "script_fd_base": 100,
  "show_fd_debug": false
}
```

* **`shelly_ip`**: Die IPv4-Adresse des Shelly im lokalen Netz.
* **`target_script_ids`**:
  * Liste mit einer oder mehreren Script-IDs (z. B. `[8]` oder `[6, 8, 12]`), um nur Meldungen dieser Skripte anzuzeigen/zu speichern.
  * `null` eintragen, um alle System- und Skript-Logs des Shelly zu erfassen.
* **`only_script_logs`**: `true` = Systemmeldungen ausblenden, nur echte Skript-Logs zeigen.
* **`log_to_file`**: `true`/`false` – ob überhaupt in eine Datei geschrieben wird.
* **`log_file_path`**: Zieldatei fürs Log (Standard: `shelly_debug.log`).
* **`separate_log_files`**: `true` = eigene Datei je Script-ID (`shelly_debug_script<ID>.log`), sonst eine gemeinsame Datei. Bei aktiver `daily_log_rotation` (Standard) kommt zusaetzlich das Datum dazu, siehe unten.
* **`daily_log_rotation`**: `true` (Standard) = haengt automatisch das aktuelle Datum als `_YYMMDD` an den Dateinamen (vor die Endung), z. B. `shelly_debug_260823.log`. Beim Wechsel auf einen neuen Tag entsteht dadurch von selbst eine neue Datei, ohne dass das Script neu gestartet werden muss. `false` = alte Namensgebung ohne Datum (`log_file_path` wird 1:1 genutzt, bzw. mit `_script<ID>` bei `separate_log_files`).
* **`show_script_prefix`**: `true` = schreibt `[Script 6]` vor jede Zeile (sinnvoll bei mehreren IDs).
* **`auto_reconnect`** / **`reconnect_delay`**: Automatische Wiederverbindung bei Verbindungsabbruch und Wartezeit in Sekunden.
* **`script_fd_base`** / **`show_fd_debug`**: Interne Erkennung, welche fd-Werte zu Skript-Ausgaben gehören (Standard `100`, siehe Hinweis unten). Nur bei Bedarf ändern.

> **Hinweis zur fd-Erkennung:** Shelly kennzeichnet jede Log-Zeile mit einem `fd`-Feld. Systemmeldungen (auch solche, die *über* ein Skript berichten, z. B. CPU-Auslastung) laufen auf niedrigen fd-Werten. Echte `print()`/`console.log()`-Ausgaben eines Skripts laufen auf einem eigenen, höheren fd. Beobachtung: `fd = script_fd_base + Script-ID` (z. B. Script 6 → fd 106). Das ist nicht offiziell dokumentiert – bitte einmal mit `"show_fd_debug": true` verifizieren, ob es auf Eurer Firmware stimmt.

---

## Skript ausführen

Starten Sie das Skript im Terminal:

```bash
python3 shelly_log_grabber.py --config config_log_grabber.json
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
* Die gesammelten Logs finden Sie anschließend im selben Verzeichnis, im Namen basierend auf `log_file_path` aus `config_log_grabber.json` (Standard: `shelly_debug.log`). Solange `daily_log_rotation` aktiv ist (Standard), heißt die Datei tatsächlich `shelly_debug_YYMMDD.log` mit dem jeweiligen Tagesdatum (z. B. `shelly_debug_260823.log`) – pro Tag entsteht so automatisch eine neue Datei. Der aktuell aktive Dateiname wird beim Start des Scripts auch im Terminal angezeigt.