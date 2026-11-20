# simplemon – Logger für einen Zendure-Speicher

> **Archiv – wird nicht weiterentwickelt.** simplemon ist ein früher, eigenständiger Vorläufer der Suite. Nachfolger sind das Shelly-Script `zendash_watch` (Daten und Watchdog), der Dashboard-Proxy und die Statistik-Auswertung unter [`shelly_script/`](../../../shelly_script/).

simplemon ist ein einzelnes Python-Script, das **einen** Zendure-Speicher regelmäßig ausliest und die Werte in eine SQLite-Datenbank schreibt, auf Wunsch zusätzlich in CSV-Dateien. Es **steuert nichts**, zeigt nichts an und verschickt keine Nachrichten. Es liest nur und schreibt nichts auf den Speicher.

Gedacht ist es für einen Dauerläufer im Heimnetz, etwa ein NAS oder einen Raspberry Pi. Ausgewertet werden die Daten mit eigenen Werkzeugen, z. B. einem SQLite-Browser oder einer Tabellenkalkulation.

## Dateien

| Datei | Inhalt |
|---|---|
| `zendure_logger.py` | Das Programm: Abfrage und Speichern |
| `config.py` | Alle Einstellungen. Nur diese Datei wird angepasst, das Programm lässt sich bei einem Update einfach ersetzen |

Es braucht nur Python 3 mit der Standardbibliothek, keine Zusatzpakete.

## Was es macht

1. **Abfrage:** Alle `POLL_INTERVAL` Sekunden (Standard 30) holt es den Report des Speichers über die lokale zenSDK-Schnittstelle (`GET /properties/report`).
   - Optional dazu die Netzleistung von einem **Shelly Pro 3EM** (`EM.GetStatus`, Feld `total_act_power`).
   - Optional die Leistung eines **weiteren Shellys**, z. B. an einer zusätzlichen Einspeisung. Erkannt werden `total_act_power`, `act_power` und `apower`.
   - Fällt einer der Shellys aus, läuft die Aufzeichnung des Speichers trotzdem weiter; der Wert bleibt dann leer.
2. **Speichern in SQLite** (`DB_FILE`, Standard `zendure_log.db`):

   | Tabelle | Inhalt |
   |---|---|
   | `device` | je Abfrage eine Zeile: Zeit, Seriennummer des Hubs, Smartmeter- und Shelly-Wert, SoC, PV (gesamt und je Eingang), Ausgang, Akku laden/entladen, Netzladung, Grenzen, Temperatur, Spannung, Betriebsart, WLAN, Fehlerkennung |
   | `packs` | je Abfrage und Akkupack eine Zeile: Seriennummer, SoC, Zustand, Leistung, Temperatur, Spannung, Strom, Zellspannung max/min |
   | `energy_daily` | je Tag die Energie in kWh: PV, Abgabe ans Haus, Laden aus dem Netz, Akku laden, Akku entladen |

   Temperaturen werden von Zehntel-Kelvin in ganze °C umgerechnet. Kommen in einer neuen Version Spalten dazu, ergänzt das Programm sie in einer vorhandenen Datenbank selbst.
3. **CSV (optional):** Mit `WRITE_CSV = True` schreibt es dieselben Werte zusätzlich in `zendure_log.csv` und `zendure_packs.csv`. Die CSV-Dateien wachsen unbegrenzt und dienen als Archiv.
4. **Aufräumen:** Einmal am Tag rechnet es die Tagesenergie aus den Rohdaten und schreibt sie in `energy_daily`. Danach löscht es Rohdaten älter als `RETENTION_DAYS` (Standard 7) aus `device` und `packs`. Die Tagesenergie und die CSV-Dateien bleiben erhalten. `RETENTION_DAYS = 0` löscht nie.
   - Für die Tagesenergie zählen nur Abstände bis zu zwei Abfrageintervallen; längere Lücken (Ausfall, Neustart) werden nicht hochgerechnet.

## Einstellungen (`config.py`)

| Schlüssel | Bedeutung | Standard |
|---|---|---|
| `DEVICE_URL` | Report-Adresse des Speichers, z. B. `http://192.168.x.x/properties/report` | – |
| `POLL_INTERVAL` | Sekunden zwischen zwei Abfragen | 30 |
| `DB_FILE` | Name der Datenbank | `zendure_log.db` |
| `WRITE_CSV` | zusätzlich CSV schreiben | `True` |
| `CSV_FILE`, `PACK_CSV_FILE` | Namen der CSV-Dateien | `zendure_log.csv`, `zendure_packs.csv` |
| `QUIET` | `True` = nur Start- und Fehlermeldungen in der Konsole | `False` |
| `RETENTION_DAYS` | Rohdaten in der Datenbank nach so vielen Tagen löschen, 0 = nie | 7 |
| `USE_SMARTMETER`, `SMARTMETER_URL` | Netzleistung vom Shelly Pro 3EM mitschreiben | – |
| `USE_EXTRA_SHELLY`, `EXTRA_SHELLY_URL` | Leistung eines weiteren Shellys mitschreiben | – |

Fehlen die Einträge für Smartmeter oder weiteren Shelly, bleiben diese Quellen aus. Eine ältere `config.py` mit Einträgen für Webseite, Nachrichten oder Schwellwerte funktioniert weiter; diese Einträge werden ignoriert.

## Start

```sh
python3 zendure_logger.py
```

`config.py` muss im selben Ordner liegen. Beenden mit Strg+C.

## Hinweise

- **Nur ein Speicher.** Für mehrere Geräte das Programm mehrfach in eigenen Ordnern starten, jeweils mit eigener `config.py`.
- **Felder des Reports:** simplemon liest nur Felder, die auch in Report `version` 4 noch vorhanden sind (Stand 11/2026). Fehlt ein Feld, bleibt die Spalte leer.
- **Datenbank im laufenden Betrieb:** Lesen ist jederzeit möglich. Ein Programm, das die Datei sperrt, kann einzelne Schreibvorgänge scheitern lassen; der Fehler erscheint in der Konsole, die nächste Abfrage wird normal geschrieben.

## Frühere Fassung

Bis 11/2026 hieß das Programm `zendure_dashboard.py` und enthielt zusätzlich eine Webseite (Live-Werte, Verläufe, Energiefluss) sowie Warnungen per Signal/WhatsApp mit Schwellwerten. Beides ist entfallen; die Fassung steht in der Git-Historie.
