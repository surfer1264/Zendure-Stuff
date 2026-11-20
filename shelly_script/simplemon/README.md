# simplemon – Logger für Zendure-Speicher

> **Eigenständiges Werkzeug neben der Suite.** simplemon braucht keinen Shelly und kein Script der Suite. Es liest die Speicher direkt über die zenSDK-Schnittstelle. Für Regelung, Dashboard und Meldungen gibt es die [Suite](../readme.md) mit dem Shelly-Script `zendash_watch`, dem Dashboard-Proxy und der [Statistik-Auswertung](../stat/auswertung/readme.md).

simplemon ist ein einzelnes Python-Script, das einen oder mehrere Zendure-Speicher samt Akkupacks regelmäßig ausliest und die Werte in eine SQLite-Datenbank und/oder in CSV-Dateien schreibt. Beides lässt sich einzeln abschalten. Es **steuert nichts**, zeigt nichts an und verschickt keine Nachrichten. Es liest nur und schreibt nichts auf die Speicher.

Gedacht ist es für einen Dauerläufer im Heimnetz, etwa ein NAS oder einen Raspberry Pi. Ausgewertet werden die Daten mit eigenen Werkzeugen, z. B. einem SQLite-Browser oder einer Tabellenkalkulation.

## Dateien

| Datei | Inhalt |
|---|---|
| `zendure_logger.py` | Das Programm: Abfrage und Speichern |
| `config.py` | Vorlage der Einstellungen mit Platzhaltern. Liegt im Repo, wird nicht angepasst |
| `config_local.py` | Deine Einstellungen mit echten Adressen. Legst du selbst an (Kopie von `config.py`), steht in `.gitignore` und kommt nie ins Repo |

Gibt es `config_local.py`, liest das Programm nur diese Datei, sonst `config.py`. Die Startmeldung nennt die verwendete Datei. Das Programm lässt sich bei einem Update einfach ersetzen, deine Einstellungen bleiben erhalten.

Es braucht nur Python 3 mit der Standardbibliothek, keine Zusatzpakete.

## Was es macht

1. **Abfrage:** Alle `POLL_INTERVAL` Sekunden (Standard 30) holt es von jedem Speicher den Report über die lokale zenSDK-Schnittstelle (`GET /properties/report`).
   - Alle Speicher werden **gleichzeitig** abgefragt. Ein Speicher, der nicht antwortet, hält die anderen nicht auf. Er erscheint als Fehler in der Konsole, die übrigen werden normal geschrieben.
   - Optional dazu die Netzleistung von einem **Shelly Pro 3EM** (`EM.GetStatus`, Feld `total_act_power`), einmal je Runde.
   - Dauert eine Runde länger, verkürzt sich die Pause bis zur nächsten, damit der Takt gleich bleibt.
2. **Speichern in SQLite (optional)** mit `WRITE_DB = True` (Standard) in `DB_FILE`, Standard `zendure_log.db`:

   | Tabelle | Inhalt |
   |---|---|
   | `device` | je Runde und Speicher eine Zeile, Felder siehe unten |
   | `packs` | je Runde und Akkupack eine Zeile, Felder siehe unten |
   | `site` | je Runde eine Zeile mit der Netzleistung vom Smartmeter (nur mit `USE_SMARTMETER = True`) |

   - Alle Zeilen einer Runde tragen dieselbe Zeit `ts`. So lassen sich Speicher, Packs und Smartmeter direkt verknüpfen, z. B. `SELECT … FROM device JOIN site USING (ts)`.
   - Eine Runde wird in einem Zug geschrieben: entweder ganz oder gar nicht.
3. **CSV (optional):** Mit `WRITE_CSV = True` schreibt es dieselben Werte zusätzlich in `zendure_log.csv`, `zendure_packs.csv` und, mit Smartmeter, `zendure_site.csv`. Die CSV-Dateien wachsen unbegrenzt.
   - Format für Excel mit deutschen Einstellungen: Spalten getrennt mit **Semikolon**, Dezimalzahlen mit **Komma** (`3,27`). Kommazahlen ohne Nachkommaanteil stehen als ganze Zahl (`100` statt `100,0`).
   - In der Datenbank sind die Werte echte Zahlen, dort gibt es kein Dezimalkomma.
4. **Aufräumen** (nur mit Datenbank): Beim Start und danach einmal am Tag löscht es Zeilen älter als `RETENTION_DAYS` (Standard 7) aus allen Tabellen. `RETENTION_DAYS = 0` löscht nie. Die CSV-Dateien bleiben unangetastet.

## Gespeicherte Felder

Gespeichert wird eine Auswahl aus dem Report, nicht der ganze Report. Felder, die ein Modell nicht liefert (z. B. Offgrid beim SolarFlow 800), bleiben leer.

| Tabelle | Felder |
|---|---|
| `device` | `ts`, `dt`, `name`, `hub_sn`, `dev_ts` (Zeit laut Gerät), `product`, `version` (Report-Version) und aus `properties`: `electricLevel`, `packInputPower`, `outputPackPower`, `outputHomePower`, `gridInputPower`, `solarInputPower`, `solarPower1`–`4`, `packState`, `packNum`, `hyperTmp`, `heatState`, `BatVolt`, `outputLimit`, `inputLimit`, `socSet`, `minSoc`, `socLimit`, `socStatus`, `acMode`, `gridReverse`, `chargeMaxLimit`, `inverseMaxPower`, `gridOffPower`, `gridOffMode`, `faultLevel`, `rssi`, `is_error` |
| `packs` | `ts`, `dt`, `name`, `hub_sn`, `packIndex` und aus `packData`: `sn`, `packType`, `softVersion`, `socLevel`, `state`, `power`, `maxTemp`, `totalVol`, `batcur`, `maxVol`, `minVol` |
| `site` | `ts`, `dt`, `gridMeterPower` |

Umgerechnet wird vor dem Speichern, gleich für Datenbank und CSV:

| Felder | Report | gespeichert |
|---|---|---|
| `hyperTmp`, `maxTemp` | Zehntel-Kelvin | ganze °C, gerundet |
| `maxVol`, `minVol` (Zellspannung) | 0,01 V | V mit 2 Nachkommastellen, z. B. 3,27 |
| `minSoc`, `socSet` | Zehntel-Prozent | %, z. B. 40 bzw. 40,5 |

Alle anderen Werte bleiben in der Einheit des Reports, z. B. `BatVolt` und `totalVol` in 0,01 V (4913 = 49,13 V), Leistungen in W.

## Einstellungen (`config_local.py`)

| Schlüssel | Bedeutung | Standard |
|---|---|---|
| `DEVICES` | Liste der Speicher, je Eintrag `name` und `url` (siehe unten) | – |
| `DEVICE_URL` | nur ein Speicher, ältere Schreibweise. Wird ignoriert, wenn `DEVICES` gesetzt ist | – |
| `POLL_INTERVAL` | Sekunden zwischen zwei Runden | 30 |
| `WRITE_DB` | in die SQLite-Datenbank schreiben | `True` |
| `WRITE_CSV` | in CSV-Dateien schreiben | `True` |
| `DB_FILE` | Name der Datenbank | `zendure_log.db` |
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

Der Name erscheint in Datenbank und CSV und muss eindeutig sein. Ein doppelter oder leerer Name bricht den Start mit einer Fehlermeldung ab, ebenso `WRITE_DB = False` zusammen mit `WRITE_CSV = False`.

## Start

```sh
python3 zendure_logger.py
```

Beim ersten Mal `config.py` als `config_local.py` kopieren und dort die eigenen Adressen eintragen. Beide liegen im selben Ordner wie das Programm. Beenden mit Strg+C.

## Umstieg von einer früheren Fassung

Ändert sich der Aufbau von Datenbank oder CSV (zuletzt: mehrere Geräte, zusätzliche Felder, Umrechnungen, Semikolon und Dezimalkomma in der CSV), gilt beim ersten Start mit der neuen Fassung:

- Das Programm listet die Datenbank und die CSV-Dateien im alten Aufbau auf und **fragt nach**: „Löschen und neu anlegen? Alte Daten gehen verloren. [j/N]“
- **Nur „j“ oder „ja“ löscht** die aufgelisteten Dateien; sie werden danach neu angelegt. Alte Daten werden nicht übernommen.
- **Jede andere Antwort**, auch nur Enter, bricht ab. Es wird nichts gelöscht, das Programm beendet sich mit einem Hinweis.
- **Ohne Konsole** (z. B. als Hintergrunddienst oder per Aufgabenplaner) kann niemand antworten: Es wird nichts gelöscht, das Programm beendet sich. Nach einem Update daher einmal von Hand in einer Konsole starten.

Wer die alten Daten behalten will, kopiert die Dateien vorher weg oder trägt in `config_local.py` neue Dateinamen ein (`DB_FILE`, `CSV_FILE`, `PACK_CSV_FILE`, `SITE_CSV_FILE`). Bei späteren Starts bleiben die neuen Dateien erhalten, eine Rückfrage kommt nur bei einem alten Aufbau.

## Hinweise

- **Felder des Reports:** simplemon liest nur Felder, die auch in Report `version` 4 noch vorhanden sind (Stand 11/2026). Fehlt ein Feld, bleibt die Spalte leer.
- **Datenbank im laufenden Betrieb:** Lesen ist jederzeit möglich. Sperrt ein anderes Programm die Datei, kann eine Runde scheitern; der Fehler erscheint in der Konsole, die nächste Runde wird normal geschrieben.
- **Zugangsdaten und Adressen:** Echte IP-Adressen gehören nur in `config_local.py`, nie in `config.py`. Datenbanken (`*.db`) und CSV-Dateien sind über `.gitignore` ausgeschlossen, weil sie Seriennummern enthalten.

## Mögliche Erweiterung: Versand an ThingsBoard

> **Nur ein Konzept, nicht umgesetzt.** Es orientiert sich an der ThingsBoard-Anbindung des Dashboard-Proxys ([`ts_bridge.py`](../zendash_watch_API_ZenSDK/ts_bridge.py)). Die offenen Fragen am Ende sind noch zu entscheiden.

### Ziel

Neben Datenbank und CSV als **dritte, abschaltbare Ausgabe** die Werte an ThingsBoard senden. Jeder Solarflow ist dort ein eigenes Gerät, jeder Akkupack ebenfalls.

```python
WRITE_TB = True        # WRITE_DB / WRITE_CSV / WRITE_TB – mindestens eins True
TB_HOST  = "https://eu.thingsboard.cloud"
```

### Was von `ts_bridge` übernommen wird

- **Geräte-Schnittstelle von ThingsBoard:** `POST {host}/api/v1/{token}/telemetry` für Messwerte und `…/attributes` für selten wechselnde Werte. Erfolg ist HTTP 200.
- **Fester Sendetakt:** zu jeder vollen Minute, Zeitstempel = volle Minute.
- **Ein Wiederholversuch** nach 5 s. Scheitert auch der, wird der Wert verworfen und protokolliert.
- **Status-Werte nur bei Änderung**, dazu einmal am Tag und nach einem Neustart. Das spart Datenpunkte.
- **Fehlende Werte werden weggelassen.** Ein Gerät, das offline ist, sendet in dieser Minute nichts.
- **Smartmeter als eigenes Gerät „Netz“** mit dem Wert `gridPower`.
- **Prüfung der Tokens:** Im Logger gibt es keine Einstellungsseite, deshalb wird beim Start je Token ein Test-Attribut gesendet. Ist ein Token falsch, kommt eine klare Fehlermeldung.

### Geräte in ThingsBoard

| Gerät | Beispielname | Inhalt |
|---|---|---|
| je Solarflow | „SF2400Pro“ (Name aus `DEVICES`) | Messwerte und Status des Hubs |
| je Akkupack | „SF2400Pro Akku 1“ | Messwerte des Packs |
| Netz | „Netz“ | Netzleistung vom Smartmeter, nur wenn eingerichtet |

Ein Solarflow mit zwei Akkupacks ergibt also drei Geräte.

### Welche Werte wie gesendet werden

Die Werte sind dieselben wie in Datenbank und CSV, mit denselben Umrechnungen (°C, V, %).

| Art | Solarflow | Akkupack |
|---|---|---|
| **Messwerte** (Telemetrie, jede Minute) | `electricLevel`, `solarInputPower`, `outputHomePower`, `gridInputPower`, `packInputPower`, `outputPackPower`, `hyperTmp` … | `socLevel`, `power`, `maxTemp`, `totalVol`, `maxVol`, `minVol`, `batcur` |
| **Status und Grenzen** (Telemetrie, nur bei Änderung) | `socLimit`, `socStatus`, `socSet`, `minSoc`, `heatState`, `gridOffMode`, `chargeMaxLimit`, `inverseMaxPower`, `gridReverse` | – |
| **Feste Angaben** (Attribute, beim Start und bei Änderung) | `product`, `version`, `hub_sn`, `packNum` | `sn`, `packType`, `softVersion` |

### Ablauf

- Das Senden läuft in einem **eigenen Thread**. Ein langsames oder nicht erreichbares ThingsBoard bremst weder die Abfrage noch das Schreiben in Datenbank und CSV.
- Der Sendetakt ist unabhängig vom Abfragetakt: Gesendet wird zur vollen Minute der jeweils letzte Stand.

### Offene Fragen (mit Empfehlung)

1. **Ein Token je Gerät oder ein Gateway?**
   - Wie in `ts_bridge` je Gerät ein Token: Bei Akkupacks wird das mühsam. Jeder Pack muss in ThingsBoard von Hand angelegt werden, und nach einem Tausch braucht es ein neues Gerät mit neuem Token.
   - Alternative: die **Gateway-Schnittstelle von ThingsBoard**. Ein einziges Gerät „Gateway“ mit einem Token (`…/gateway/telemetry`, `…/gateway/attributes`). ThingsBoard legt Solarflow-, Akku- und Netz-Geräte anhand des Namens **selbst an**.
   - **Empfehlung: Gateway.**
2. **Name der Akku-Geräte:**
   - Nach Position („SF800 Akku 1“): gut lesbar, aber die Nummer kann sich verschieben, wenn sich die Reihenfolge im Report ändert.
   - Nach Seriennummer („SF800 Akku <sn>“): stabil, aber schlechter lesbar.
   - **Empfehlung:** Position im Namen, Seriennummer als Attribut.
3. **Sendetakt:** bei jeder Abfrage oder jede volle Minute? **Empfehlung: jede Minute** (`TB_INTERVAL = 60`), auch wenn alle 30 s abgefragt wird.
4. **Auswahl der Werte:**
   - Fest vorgegeben, oder in `config_local.py` als Liste einstellbar (`TB_HUB_FIELDS`, `TB_PACK_FIELDS`) mit Standardwerten?
   - **Empfehlung: einstellbar.** Jeder Wert kostet Datenpunkte in ThingsBoard. Beispiel: 2 Solarflows mit je 10 Werten und 4 Akkupacks mit je 5 Werten ergeben 40 Werte pro Minute, rund 58 000 am Tag.
5. **ThingsBoard nicht erreichbar:** verwerfen wie in `ts_bridge` (die Daten liegen ja in Datenbank bzw. CSV) oder zwischenspeichern und später nachsenden? **Empfehlung: verwerfen.**
6. **Smartmeter als Gerät „Netz“:** **Empfehlung: ja**, wie in `ts_bridge`.

### Sicherheit

Das Token (bzw. die Tokens) stünde in `config_local.py`, nie in `config.py`. Damit wird die Datei noch schützenswerter.

## Frühere Fassungen

- Bis 11/2026 lag simplemon im Archiv unter `archiv/ha/simplemon/`.

- Bis 11/2026 hieß das Programm `zendure_dashboard.py` und enthielt zusätzlich eine Webseite sowie Warnungen per Signal/WhatsApp mit Schwellwerten.
- Die erste Fassung von `zendure_logger.py` konnte nur einen Speicher, schrieb zusätzlich die Leistung eines weiteren Shellys und rechnete eine Tagesenergie (`energy_daily`).

Beides steht in der Git-Historie.
