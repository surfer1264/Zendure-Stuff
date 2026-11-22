# Changelog simplemon (zendure_logger)

## 1.1.0

**Ziel:** Dieselben Smartmeter wie im Multi-Configurator.

- **Smartmeter-Typen** (`SMARTMETER_TYPE`): Shelly Pro 3EM (`pro3em`, mit `SMARTMETER_EM_ID`), Zendure Smart Meter 3CT (`zendure3ct`) und D0 (`zendured0`), everHome EcoTracker (`ecotracker`), Shelly 3EM Gen1 (`shelly3em`), Tasmota-Lesekopf (`tasmota`) und beliebiges JSON (`http_json` mit `SMARTMETER_URL`). Adresse über `SMARTMETER_IP`, Pfad und Feld kommen aus der Vorlage.
- **Feld frei wählbar** (`SMARTMETER_FIELD`), auch verschachtelt mit Punkten (`StatusSNS.DVS7420.power`) oder als Liste. Zahlen als Text (`"1234,5"`) werden umgewandelt.
- **Vorzeichen umkehren** (`SMARTMETER_INVERT`) wie im Configurator.
- **Prüfung beim Start:** unbekannter Typ, fehlende Adresse, Platzhalter (`192.168.x.z`, `<…>`) im Feld oder in der Adresse brechen mit Meldung ab. Fehlt das Feld zur Laufzeit in der Antwort, meldet die Konsole das; die Speicher werden trotzdem geschrieben.
- Eine Einstellung nur mit `SMARTMETER_URL` (Fassung 1.0.0) gilt weiter, Feld `total_act_power`.

Keine Änderung an Datenbank, CSV und ThingsBoard-Format.

## 1.0.0

**Ziel:** Eigenständiger Logger ohne Shelly: liest einen oder mehrere Zendure-Speicher samt Akkupacks direkt über die zenSDK-Schnittstelle und schreibt die Werte in SQLite, CSV und/oder an ThingsBoard.

- **Mehrere Speicher:** Liste `DEVICES` mit Name und Adresse. Alle Speicher und der Smartmeter (Shelly Pro 3EM, optional) werden gleichzeitig abgefragt; ein ausgefallenes Gerät hält die anderen nicht auf.
- **Fester Takt:** Standard jede Minute, jeweils 10 s vor der vollen Minute (`POLL_INTERVAL`, `POLL_ALIGN`, `POLL_LEAD`).
- **Drei Ausgaben, jede abschaltbar** (`WRITE_DB`, `WRITE_CSV`, `WRITE_TB`):
  - SQLite: Tabellen `device` (je Speicher), `packs` (je Akkupack), `site` (Smartmeter); alle Zeilen einer Runde mit derselben Zeit `ts`. Alte Zeilen werden nach `RETENTION_DAYS` gelöscht.
  - CSV: Semikolon als Trenner, Dezimalkomma, Einheit im Kopf der umgerechneten Spalten.
  - ThingsBoard: je Solarflow und je Akkupack ein Gerät mit eigenem Token, Akku über die Seriennummer, lesbarer Akku-Name als Attribut. Werte frei zuordenbar („Name im Report“ → „Name in ThingsBoard“). Standard mit denselben 15 Werten und Namen wie der Dashboard-Proxy (`ts_bridge`), einschließlich der berechneten `minVol`, `batteryPower` und `packTempLow`. Status-Werte nur bei Änderung.
- **Umrechnungen:** Temperaturen in ganze °C, Spannungen (`BatVolt`, `totalVol`, `maxVol`, `minVol`) in V, `socSet`/`minSoc` in %.
- **Testmodus `--once`:** einmal abfragen, die ThingsBoard-Daten in `tb_test.json` schreiben, nichts senden, keine Tokens in der Datei.
- **Alter Aufbau:** Passen Datenbank oder CSV nicht zur Fassung, werden sie mit Datum und Uhrzeit im Namen umbenannt und neu angelegt; es wird nichts gelöscht.
- **Konfiguration:** `config.py` ist die Vorlage mit Platzhaltern, eigene Werte (Adressen, Tokens) stehen in `config_local.py` (in `.gitignore`).
