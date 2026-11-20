# simplemon – Logger für Zendure-Speicher

> **Archiv – wird nicht weiterentwickelt.** simplemon ist ein früher, eigenständiger Vorläufer der Suite. Nachfolger sind das Shelly-Script `zendash_watch` (Daten und Watchdog), der Dashboard-Proxy und die Statistik-Auswertung unter [`shelly_script/`](../../../shelly_script/).

simplemon ist ein einzelnes Python-Script, das einen oder mehrere Zendure-Speicher samt Akkupacks regelmäßig ausliest und die Werte in eine SQLite-Datenbank schreibt, auf Wunsch zusätzlich in CSV-Dateien. Es **steuert nichts**, zeigt nichts an und verschickt keine Nachrichten. Es liest nur und schreibt nichts auf die Speicher.

Gedacht ist es für einen Dauerläufer im Heimnetz, etwa ein NAS oder einen Raspberry Pi. Ausgewertet werden die Daten mit eigenen Werkzeugen, z. B. einem SQLite-Browser oder einer Tabellenkalkulation.

## Dateien

| Datei | Inhalt |
|---|---|
| `zendure_logger.py` | Das Programm: Abfrage und Speichern |
| `config.py` | Alle Einstellungen. Nur diese Datei wird angepasst, das Programm lässt sich bei einem Update einfach ersetzen |

Es braucht nur Python 3 mit der Standardbibliothek, keine Zusatzpakete.

## Was es macht

1. **Abfrage:** Alle `POLL_INTERVAL` Sekunden (Standard 30) holt es von jedem Speicher den Report über die lokale zenSDK-Schnittstelle (`GET /properties/report`).
   - Alle Speicher werden **gleichzeitig** abgefragt. Ein Speicher, der nicht antwortet, hält die anderen nicht auf. Er erscheint als Fehler in der Konsole, die übrigen werden normal geschrieben.
   - Optional dazu die Netzleistung von einem **Shelly Pro 3EM** (`EM.GetStatus`, Feld `total_act_power`), einmal je Runde.
   - Dauert eine Runde länger, verkürzt sich die Pause bis zur nächsten, damit der Takt gleich bleibt.
2. **Speichern in SQLite** (`DB_FILE`, Standard `zendure_log.db`):

   | Tabelle | Inhalt |
   |---|---|
   | `device` | je Runde und Speicher eine Zeile: Zeit, Name aus der Konfiguration, Seriennummer des Hubs, Zeit laut Gerät (`dev_ts`), SoC, PV (gesamt und je Eingang), Ausgang, Akku laden/entladen, Netzladung, Grenzen, Temperatur, Spannung, Betriebsart, WLAN, Fehlerkennung |
   | `packs` | je Runde und Akkupack eine Zeile: Zeit, Name und Seriennummer des Hubs, Nummer des Packs, Seriennummer des Packs, SoC, Zustand, Leistung, Temperatur, Spannung, Strom, Zellspannung max/min |
   | `site` | je Runde eine Zeile mit der Netzleistung vom Smartmeter (nur mit `USE_SMARTMETER = True`) |

   - Alle Zeilen einer Runde tragen dieselbe Zeit `ts`. So lassen sich Speicher, Packs und Smartmeter direkt verknüpfen, z. B. `SELECT … FROM device JOIN site USING (ts)`.
   - Temperaturen werden von Zehntel-Kelvin in ganze °C umgerechnet.
   - Eine Runde wird in einem Zug geschrieben: entweder ganz oder gar nicht.
3. **CSV (optional):** Mit `WRITE_CSV = True` schreibt es dieselben Werte zusätzlich in `zendure_log.csv`, `zendure_packs.csv` und, mit Smartmeter, `zendure_site.csv`. Die CSV-Dateien wachsen unbegrenzt.
4. **Aufräumen:** Beim Start und danach einmal am Tag löscht es Zeilen älter als `RETENTION_DAYS` (Standard 7) aus allen Tabellen. `RETENTION_DAYS = 0` löscht nie. Die CSV-Dateien bleiben unangetastet.

## Einstellungen (`config.py`)

| Schlüssel | Bedeutung | Standard |
|---|---|---|
| `DEVICES` | Liste der Speicher, je Eintrag `name` und `url` (siehe unten) | – |
| `DEVICE_URL` | nur ein Speicher, ältere Schreibweise. Wird ignoriert, wenn `DEVICES` gesetzt ist | – |
| `POLL_INTERVAL` | Sekunden zwischen zwei Runden | 30 |
| `DB_FILE` | Name der Datenbank | `zendure_log.db` |
| `WRITE_CSV` | zusätzlich CSV schreiben | `True` |
| `CSV_FILE`, `PACK_CSV_FILE`, `SITE_CSV_FILE` | Namen der CSV-Dateien | `zendure_log.csv`, `zendure_packs.csv`, `zendure_site.csv` |
| `QUIET` | `True` = nur Start- und Fehlermeldungen in der Konsole | `False` |
| `RETENTION_DAYS` | Zeilen in der Datenbank nach so vielen Tagen löschen, 0 = nie | 7 |
| `USE_SMARTMETER`, `SMARTMETER_URL` | Netzleistung vom Shelly Pro 3EM mitschreiben | `False` |

Mehrere Speicher:

```python
DEVICES = [
    {"name": "SF800 Pro", "url": "http://192.168.x.x/properties/report"},
    {"name": "SF800",     "url": "http://192.168.x.y/properties/report"},
]
```

Der Name erscheint in Datenbank und CSV und muss eindeutig sein. Ein doppelter oder leerer Name bricht den Start mit einer Fehlermeldung ab.

## Start

```sh
python3 zendure_logger.py
```

`config.py` muss im selben Ordner liegen. Beenden mit Strg+C.

## Umstieg von der Fassung für ein Gerät

Die Datenbank hat einen neuen Aufbau (Spalte `name`, Tabelle `site`, keine Tagesenergie mehr). Beim ersten Start mit dieser Fassung gilt:

- Eine **Datenbank im alten Aufbau wird gelöscht und neu angelegt.** Alte Daten werden nicht übernommen.
- **CSV-Dateien mit altem Kopf werden gelöscht** und neu angelegt.

Wer die alten Daten behalten will, kopiert die Dateien vorher weg oder trägt in `config.py` neue Dateinamen ein. Die Konsole meldet jedes Löschen. Bei späteren Starts bleibt die neue Datenbank erhalten.

## Hinweise

- **Felder des Reports:** simplemon liest nur Felder, die auch in Report `version` 4 noch vorhanden sind (Stand 11/2026). Fehlt ein Feld, bleibt die Spalte leer.
- **Datenbank im laufenden Betrieb:** Lesen ist jederzeit möglich. Sperrt ein anderes Programm die Datei, kann eine Runde scheitern; der Fehler erscheint in der Konsole, die nächste Runde wird normal geschrieben.
- **Zugangsdaten und Adressen:** Eine `config.py` mit echten IP-Adressen gehört nicht ins Repo.

## Frühere Fassungen

- Bis 11/2026 hieß das Programm `zendure_dashboard.py` und enthielt zusätzlich eine Webseite sowie Warnungen per Signal/WhatsApp mit Schwellwerten.
- Die erste Fassung von `zendure_logger.py` konnte nur einen Speicher, schrieb zusätzlich die Leistung eines weiteren Shellys und rechnete eine Tagesenergie (`energy_daily`).

Beides steht in der Git-Historie.
