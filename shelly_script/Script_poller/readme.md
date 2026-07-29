# Shelly Script-Status-Poller

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