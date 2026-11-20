# simplemon – einfacher Logger und Dashboard für einen Zendure-Speicher

> **Archiv – wird nicht weiterentwickelt.** simplemon ist ein früher, eigenständiger Vorläufer der Suite. Nachfolger sind das Shelly-Script `zendash_watch` (Daten und Watchdog), der Dashboard-Proxy und die Statistik-Auswertung unter [`shelly_script/`](../../../shelly_script/).

simplemon ist ein einzelnes Python-Script, das **einen** Zendure-Speicher regelmäßig ausliest, die Werte speichert und als Webseite mit Live-Werten, Verläufen und Tagesenergie anzeigt. Auf Wunsch schickt es Warnungen per Signal oder WhatsApp. Es **steuert nichts**: Es liest nur und schreibt nichts auf den Speicher.

Gedacht war es für einen Dauerläufer im Heimnetz, etwa ein NAS oder einen Raspberry Pi.

## Dateien

| Datei | Inhalt |
|---|---|
| `zendure_dashboard.py` | Das Programm: Abfrage, Speicherung, Warnungen, Webserver und Webseite in einer Datei |
| `config.py` | Alle Einstellungen. Nur diese Datei wird angepasst, das Programm lässt sich bei einem Update einfach ersetzen |

Es braucht nur Python 3 mit der Standardbibliothek, keine Zusatzpakete.

## Was es macht

1. **Abfrage:** Alle `POLL_INTERVAL` Sekunden (Standard 30) holt es den Report des Speichers über die lokale zenSDK-Schnittstelle (`GET /properties/report`).
   - Optional dazu die Netzleistung von einem **Shelly Pro 3EM** (`EM.GetStatus`, Feld `total_act_power`).
   - Optional die Leistung eines **weiteren Shellys**, z. B. an einer zusätzlichen Einspeisung. Erkannt werden `total_act_power`, `act_power` und `apower`.
   - Fällt einer der Shellys aus, läuft die Aufzeichnung des Speichers trotzdem weiter.
2. **Speichern:**
   - **SQLite** (`zendure_log.db`):
     - Tabelle `device` mit den wichtigsten Hub-Werten (SoC, PV, Ausgang, Akku laden/entladen, Grenzen, Temperatur, WLAN …).
     - Tabelle `packs` je Akkupack (SoC, Temperatur, Spannung, Zellspannung min/max …).
     - Temperaturen werden dabei von Zehntel-Kelvin in ganze °C umgerechnet.
   - **CSV** (`zendure_log.csv`, `zendure_packs.csv`) als unbegrenztes Archiv, abschaltbar mit `WRITE_CSV = False`.
   - **Aufräumen:** Einmal am Tag werden Rohdaten älter als `RETENTION_DAYS` (Standard 7) aus der Datenbank gelöscht. Vorher werden die Tageswerte in die Tabelle `energy_daily` übernommen, sie bleiben also dauerhaft erhalten.
3. **Tagesenergie:** Aus den Leistungswerten rechnet es je Tag die Energie in kWh für PV, Abgabe ans Haus, Laden aus dem Netz, Akku laden und Akku entladen. Lücken länger als zwei Abfrageintervalle (Ausfall, Neustart) werden nicht mitgezählt.
4. **Warnungen** (nur mit `USE_SIGNAL = True`, über den Dienst CallMeBot). Jede Warnung kommt einmal und erst wieder, wenn der Wert in den sicheren Bereich zurückgekehrt ist:
   - Akku voll ab `VOLL_SCHWELLE` %, erneut erst nach Unterschreiten von `ENTLADE_RESET` %.
   - Gerätetemperatur über `TEMP_WARN` °C, zurückgesetzt unter `TEMP_RESET` °C.
   - Zellspannung eines Packs unter `MIN_VOLT_WARN` V, zurückgesetzt über `MIN_VOLT_RESET` V.
   - Beim Start zusätzlich die Meldung „Zendure-Watchdog gestartet“.
5. **Webseite** unter `http://<Rechner-IP>:<WEB_PORT>`:
   - Leistungsverlauf (PV, Ausgang, Akku laden/entladen, SoC, Netz laut Smartmeter), Anzahl der Punkte umschaltbar (200 / 400 / 600)
   - Energiefluss live, mit optionaler Kachel für den weiteren Shelly
   - Arbeit heute und Tageswerte in kWh
   - Akkupacks als Tabelle und Verlauf der Zellspannungen je Pack

## Schnittstellen des Webservers

| Adresse | Liefert |
|---|---|
| `/` | die Webseite |
| `/data` | letzter Report des Speichers plus Smartmeter- und Shelly-Wert (JSON) |
| `/history?n=…` | Verlauf der Hub-Werte, höchstens `MAX_POINTS` Punkte |
| `/packhistory?n=…` | Verlauf von Zellspannung min/max je Pack |
| `/energy?days=…` | Tagesenergie in kWh, optional nur die letzten Tage |

## Einstellungen (`config.py`)

| Gruppe | Schlüssel |
|---|---|
| Gerät und Server | `DEVICE_URL` (Report-Adresse des Speichers), `POLL_INTERVAL`, `WEB_PORT`, `DEVICE_LABEL` |
| Dateien | `CSV_FILE`, `PACK_CSV_FILE`, `DB_FILE`, `WRITE_CSV` |
| Ausgabe und Speicherung | `QUIET`, `RETENTION_DAYS`, `MAX_POINTS` |
| Benachrichtigungen | `USE_SIGNAL`, `MESSENGER_TYP` (`SIGNAL` oder `WHATSAPP`), `SIGNAL_PHONE`, `SIGNAL_KEY` |
| Schwellen | `VOLL_SCHWELLE`, `ENTLADE_RESET`, `MIN_VOLT_WARN`, `MIN_VOLT_RESET`, `TEMP_WARN`, `TEMP_RESET` |
| Smartmeter | `USE_SMARTMETER`, `SMARTMETER_URL` |
| Weiterer Shelly | `USE_EXTRA_SHELLY`, `EXTRA_SHELLY_URL`, `EXTRA_SHELLY_LABEL` |

Fehlen in einer älteren `config.py` die Einträge für Smartmeter oder weiteren Shelly, läuft das Programm trotzdem; die Anzeige dafür bleibt dann aus.

## Start

```sh
python3 zendure_dashboard.py
```

`config.py` muss im selben Ordner liegen. Beenden mit Strg+C.

## Grenzen und Hinweise

- **Nur ein Speicher.** Mehrere Geräte, Regelung und Einstellungen über das Dashboard gibt es erst in der Suite.
- **Kein Zugangsschutz.** Der Webserver lauscht auf allen Netzwerkschnittstellen (`0.0.0.0`) ohne Passwort, also nur im Heimnetz betreiben.
- **Internet für die Diagramme:** Die Webseite lädt Chart.js von `cdn.jsdelivr.net`. Ohne Internet fehlen die Diagramme, die Zahlen erscheinen trotzdem.
- **Zugangsdaten:** Telefonnummer und CallMeBot-Schlüssel stehen im Klartext in `config.py` und werden in der Abfrage-URL an CallMeBot übertragen. Eine ausgefüllte `config.py` gehört nicht ins Repo.
- **Port:** Die Beschreibung am Anfang von `zendure_dashboard.py` nennt Port 8080. Maßgeblich ist `WEB_PORT` aus `config.py`, dort steht 8085.
- **Felder des Reports:** simplemon liest nur Felder, die auch in Report `version` 4 noch vorhanden sind (Stand 11/2026). Fehlt ein Feld, bleibt die Spalte leer.
