# simplemon – Logger für Zendure-Speicher

> **Eigenständiges Werkzeug neben der Suite.** simplemon braucht keinen Shelly und kein Script der Suite. Es liest die Speicher direkt über die zenSDK-Schnittstelle. Für Regelung, Dashboard und Meldungen gibt es die [Suite](../readme.md) mit dem Shelly-Script `zendash_watch`, dem Dashboard-Proxy und der [Statistik-Auswertung](../stat/auswertung/readme.md).

simplemon ist ein einzelnes Python-Script, das einen oder mehrere Zendure-Speicher samt Akkupacks regelmäßig ausliest und die Werte in eine SQLite-Datenbank, in CSV-Dateien und/oder an ThingsBoard schreibt. Jede der drei Ausgaben lässt sich einzeln abschalten. Es **steuert nichts**, zeigt nichts an und verschickt keine Nachrichten. Es liest nur und schreibt nichts auf die Speicher.

Gedacht ist es für einen Dauerläufer im Heimnetz, etwa ein NAS oder einen Raspberry Pi. Ausgewertet werden die Daten mit eigenen Werkzeugen, z. B. einem SQLite-Browser oder einer Tabellenkalkulation.

Version: **1.1.0** (steht als `VERSION` in `zendure_logger.py` und in der Startmeldung). Änderungen: [CHANGELOG](CHANGELOG.md).

## Dateien

| Datei | Inhalt |
|---|---|
| `zendure_logger.py` | Das Programm: Abfrage und Speichern |
| `config.py` | Vorlage der Einstellungen mit Platzhaltern. Liegt im Repo, wird nicht angepasst |
| `CHANGELOG.md` | Änderungen je Version |
| `config_local.py` | Deine Einstellungen mit echten Adressen. Legst du selbst an (Kopie von `config.py`), steht in `.gitignore` und kommt nie ins Repo |

Gibt es `config_local.py`, liest das Programm nur diese Datei, sonst `config.py`. Die Startmeldung nennt die verwendete Datei. Das Programm lässt sich bei einem Update einfach ersetzen, deine Einstellungen bleiben erhalten.

Es braucht nur Python 3 mit der Standardbibliothek, keine Zusatzpakete.

## Was es macht

1. **Abfrage:** Alle `POLL_INTERVAL` Sekunden (Standard 60) holt es von jedem Speicher den Report über die lokale zenSDK-Schnittstelle (`GET /properties/report`).
   - Alle Speicher werden **gleichzeitig** abgefragt. Ein Speicher, der nicht antwortet, hält die anderen nicht auf. Er erscheint als Fehler in der Konsole, die übrigen werden normal geschrieben.
   - Optional dazu die Netzleistung von einem **Smartmeter**, einmal je Runde. Unterstützt werden dieselben Geräte wie im Multi-Configurator (Shelly Pro 3EM, Zendure Smart Meter 3CT/D0, everHome EcoTracker, Shelly 3EM, Tasmota-Lesekopf, beliebiges JSON), siehe [Smartmeter](#smartmeter).
   - **Fester Takt am Raster** (`POLL_ALIGN = True`, Standard): Abgefragt wird jeweils `POLL_LEAD` Sekunden (Standard 10) vor einem Vielfachen von `POLL_INTERVAL`, bei 60 also immer um hh:mm:50. Die erste Abfrage nach dem Start läuft sofort. So hat der ThingsBoard-Versand zur vollen Minute einen rund 10 s alten Stand, wie im Dashboard-Proxy.
   - Mit `POLL_ALIGN = False` wird ab dem Start im festen Abstand abgefragt, ohne Raster. Dauert eine Runde länger, verkürzt sich die Pause bis zur nächsten.
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
   - Umgerechnete Spalten tragen die Einheit im Kopf, z. B. `BatVolt (V)`, `hyperTmp (Grad C)`, `socSet (%)`. In der Datenbank heißen die Spalten wie im Report.
   - In der Datenbank sind die Werte echte Zahlen, dort gibt es kein Dezimalkomma.
4. **ThingsBoard (optional):** Mit `WRITE_TB = True` gehen die Werte zusätzlich an ThingsBoard, siehe [Versand an ThingsBoard](#versand-an-thingsboard).
5. **Aufräumen** (nur mit Datenbank): Beim Start und danach einmal am Tag löscht es Zeilen älter als `RETENTION_DAYS` (Standard 7) aus allen Tabellen. `RETENTION_DAYS = 0` löscht nie. Die CSV-Dateien bleiben unangetastet.

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
| `BatVolt` (Hub), `totalVol` (Pack), `maxVol`, `minVol` (Zellspannung) | 0,01 V | V mit 2 Nachkommastellen, z. B. 49,13 bzw. 3,27 |
| `minSoc`, `socSet` | Zehntel-Prozent | %, z. B. 40 bzw. 40,5 |

Alle anderen Werte bleiben in der Einheit des Reports, z. B. Leistungen in W und Ladestände in %.

## Einstellungen (`config_local.py`)

| Schlüssel | Bedeutung | Standard |
|---|---|---|
| `DEVICES` | Liste der Speicher, je Eintrag `name` und `url` (siehe unten) | – |
| `DEVICE_URL` | nur ein Speicher, ältere Schreibweise. Wird ignoriert, wenn `DEVICES` gesetzt ist | – |
| `POLL_INTERVAL` | Sekunden zwischen zwei Runden | 60 |
| `POLL_ALIGN` | Abfrage am Raster ausrichten (siehe oben) | `True` |
| `POLL_LEAD` | Sekunden vor dem Raster, höchstens das halbe Intervall | 10 |
| `WRITE_DB` | in die SQLite-Datenbank schreiben | `True` |
| `WRITE_CSV` | in CSV-Dateien schreiben | `True` |
| `WRITE_TB` | an ThingsBoard senden, Einstellungen `TB_…` siehe [Versand an ThingsBoard](#versand-an-thingsboard) | `False` |
| `DB_FILE` | Name der Datenbank | `zendure_log.db` |
| `CSV_FILE`, `PACK_CSV_FILE`, `SITE_CSV_FILE` | Namen der CSV-Dateien | `zendure_log.csv`, `zendure_packs.csv`, `zendure_site.csv` |
| `QUIET` | `True` = nur Start- und Fehlermeldungen in der Konsole | `False` |
| `RETENTION_DAYS` | Zeilen in der Datenbank nach so vielen Tagen löschen, 0 = nie | 7 |
| `USE_SMARTMETER` | Netzleistung vom Smartmeter mitschreiben, Einstellungen `SMARTMETER_…` siehe [Smartmeter](#smartmeter) | `False` |

Mehrere Speicher:

```python
DEVICES = [
    {"name": "SF800 Pro", "url": "http://192.168.x.x/properties/report"},
    {"name": "SF800",     "url": "http://192.168.x.y/properties/report"},
]
```

Der Name erscheint in Datenbank und CSV und muss eindeutig sein. Ein doppelter oder leerer Name bricht den Start mit einer Fehlermeldung ab, ebenso wenn `WRITE_DB`, `WRITE_CSV` und `WRITE_TB` alle `False` sind.

Smartmeter: siehe eigener Abschnitt [Smartmeter](#smartmeter).

## Start

```sh
python3 zendure_logger.py
```

Beim ersten Mal `config.py` als `config_local.py` kopieren und dort die eigenen Adressen eintragen. Beide liegen im selben Ordner wie das Programm. Beenden mit Strg+C.

Testmodus für ThingsBoard, siehe [Testmodus `--once`](#testmodus---once):

```sh
python3 zendure_logger.py --once
```

## Umstieg von einer früheren Fassung

Ändert sich der Aufbau von Datenbank oder CSV (zuletzt: alle Spannungen in V, Einheit im CSV-Kopf), passen vorhandene Dateien nicht mehr. Beim ersten Start mit der neuen Fassung gilt:

- Die Datenbank und die CSV-Dateien im alten Aufbau werden **umbenannt**, mit Datum und Uhrzeit im Namen, z. B. `zendure_log.db` → `zendure_log_alt_20261121-153000.db`. Gibt es den Namen schon, wird `_2`, `_3` … angehängt.
- **Es wird nichts gelöscht und nicht nachgefragt.** Das funktioniert auch als Hintergrunddienst.
- Danach legt das Programm neue Dateien an. Die alten Daten bleiben in den umbenannten Dateien, werden aber nicht übernommen.
- Lässt sich eine Datei nicht umbenennen, weil sie z. B. in Excel oder einem SQLite-Browser geöffnet ist, beendet sich das Programm mit einem Hinweis. Datei schließen und neu starten.

Dateien im aktuellen Aufbau bleiben unverändert.

## Smartmeter

Mit `USE_SMARTMETER = True` liest simplemon je Runde die Netzleistung in W (positiv = Bezug). Sie landet in der Tabelle `site`, in `zendure_site.csv` und bei ThingsBoard im Gerät „Netz“. Die Typen entsprechen der Smartmeter-Auswahl im Multi-Configurator.

### Übersicht

| `SMARTMETER_TYPE` | Gerät | nötige Einstellungen |
|---|---|---|
| `pro3em` | Shelly Pro 3EM | `SMARTMETER_IP`, `SMARTMETER_EM_ID` |
| `zendure3ct` | Zendure Smart Meter 3CT | `SMARTMETER_IP` |
| `zendured0` | Zendure Smart Meter D0 | `SMARTMETER_IP` |
| `ecotracker` | everHome EcoTracker | `SMARTMETER_IP` |
| `shelly3em` | Shelly 3EM (Gen1, nicht Pro) | `SMARTMETER_IP` |
| `tasmota` | Tasmota-Lesekopf | `SMARTMETER_IP`, `SMARTMETER_FIELD` |
| `http_json` | beliebiges Gerät mit JSON-Antwort | `SMARTMETER_URL`, `SMARTMETER_FIELD` |

Aus Typ und IP baut simplemon die Adresse selbst:

| `SMARTMETER_TYPE` | Adresse (URL-Muster) | gelesenes Feld |
|---|---|---|
| `pro3em` | `http://<IP>/rpc/EM.GetStatus?id=<EM_ID>` | `total_act_power` |
| `zendure3ct` | `http://<IP>/properties/report` | `total_power` |
| `zendured0` | `http://<IP>/properties/report` | `total_power` |
| `ecotracker` | `http://<IP>/v1/json` | `power` |
| `shelly3em` | `http://<IP>/status` | `total_power` |
| `tasmota` | `http://<IP>/cm?cmnd=STATUS%2010` | `SMARTMETER_FIELD`, z. B. `StatusSNS.<Zähler>.power` |
| `http_json` | `SMARTMETER_URL` | `SMARTMETER_FIELD` |

Tipp: Die Adresse einmal im Browser öffnen. Dann sieht man die Antwort und das Feld mit der Netzleistung.

### Beispiele

Jeweils: Einstellung in `config_local.py` → daraus gebaute Adresse → typische Antwort (gekürzt), das gelesene Feld ist markiert.

**Shelly Pro 3EM**

```python
USE_SMARTMETER = True
SMARTMETER_TYPE = "pro3em"
SMARTMETER_IP = "192.168.x.z"
SMARTMETER_EM_ID = 0
```

Adresse: `http://192.168.x.z/rpc/EM.GetStatus?id=0`

```text
{"id": 0, "a_act_power": 120.4, "b_act_power": 80.1, "c_act_power": 145.0,
 "total_act_power": 345.5}                     ← gelesen: 345.5 W
```

**Zendure Smart Meter 3CT** (D0 genauso mit `"zendured0"`)

```python
USE_SMARTMETER = True
SMARTMETER_TYPE = "zendure3ct"
SMARTMETER_IP = "192.168.x.z"
```

Adresse: `http://192.168.x.z/properties/report`

```text
{"a_aprt_power": 40, "b_aprt_power": -90, "c_aprt_power": -70,
 "total_power": -120}                          ← gelesen: -120 W (Einspeisung)
```

**everHome EcoTracker**

```python
USE_SMARTMETER = True
SMARTMETER_TYPE = "ecotracker"
SMARTMETER_IP = "192.168.x.z"
```

Adresse: `http://192.168.x.z/v1/json`

```text
{"power": 512, "powerAvg": 500, "powerPhase1": 170, "powerPhase2": 172, "powerPhase3": 170,
 "energyCounterIn": 1234567, "energyCounterOut": 89012}
   ↑ gelesen: power = 512 W
```

**Shelly 3EM (Gen1, nicht Pro)**

```python
USE_SMARTMETER = True
SMARTMETER_TYPE = "shelly3em"
SMARTMETER_IP = "192.168.x.z"
```

Adresse: `http://192.168.x.z/status`

```text
{"emeters": [{"power": 30.2}, {"power": 25.1}, {"power": 22.2}],
 "total_power": 77.5}                          ← gelesen: 77.5 W
```

**Tasmota-Lesekopf**

```python
USE_SMARTMETER = True
SMARTMETER_TYPE = "tasmota"
SMARTMETER_IP = "192.168.x.z"
SMARTMETER_FIELD = "StatusSNS.DVS7420.power"   # mittleren Namen aus der Antwort übernehmen
```

Adresse: `http://192.168.x.z/cm?cmnd=STATUS%2010`

```text
{"StatusSNS": {"Time": "2026-11-22T10:00:00",
               "DVS7420": {"energy": 20302, "power": 353}}}
                                     ↑ gelesen: StatusSNS → DVS7420 → power = 353 W
```

Der mittlere Name (hier `DVS7420`) hängt vom Zähler bzw. vom Tasmota-Script ab, z. B. auch `SML`, `MT681` oder `eBZ`. Deshalb die Antwort einmal im Browser ansehen.

**Beliebiges Gerät mit JSON (`http_json`)**

```python
USE_SMARTMETER = True
SMARTMETER_TYPE = "http_json"
SMARTMETER_URL = "http://192.168.x.z/api/werte"
SMARTMETER_FIELD = "daten.netz"                # verschachtelt mit Punkten
SMARTMETER_INVERT = True                       # Gerät liefert Bezug negativ
```

Adresse: genau `SMARTMETER_URL`

```text
{"daten": {"netz": "-1234,5", "pv": "0"}}
   ↑ gelesen: daten → netz = "-1234,5" → -1234.5 → umgekehrt: 1234.5 W Bezug
```

### Einzelheiten

- **`SMARTMETER_FIELD`:** Feld mit der gesamten Netzleistung. Bei den Vorlagen ist es schon gesetzt, das Feld dann leer lassen. Verschachtelte Namen mit Punkten verbinden oder als Liste angeben: `["StatusSNS", "DVS7420", "power"]`.
- **`SMARTMETER_INVERT = True`**, wenn der Wert bei Netzbezug negativ ist. Das ist wie „Vorzeichen umkehren“ im Configurator. Prüfen: Bei Bezug aus dem Netz muss der Wert positiv sein.
- **`SMARTMETER_EM_ID`** (nur `pro3em`): Nummer des Messkanals, fast immer 0.
- Liefert das Gerät die Zahl als Text, z. B. `"1234,5"`, wird sie umgewandelt.
- **Beim Start geprüft:** bekannter Typ, Adresse vorhanden und kein Platzhalter (`192.168.x.z`), Feld ohne `<…>`. Sonst bricht der Start mit Meldung ab.
- **Im Betrieb:** Ist der Smartmeter nicht erreichbar oder fehlt das Feld in der Antwort, meldet die Konsole das, z. B. „Feld daten.netz nicht in der Antwort“. Die Speicher werden trotzdem geschrieben, der Netzwert bleibt in dieser Runde leer.
- **Ältere Einstellung:** Steht in `config_local.py` nur `SMARTMETER_URL` ohne `SMARTMETER_TYPE` (Fassung 1.0.0), wird diese Adresse wie bisher mit dem Feld `total_act_power` gelesen.
- Mit dem [Testmodus `--once`](#testmodus---once) lässt sich der gelesene Wert prüfen, ohne etwas zu schreiben: Er steht in `tb_test.json` beim Gerät „Netz“.

## Hinweise

- **Felder des Reports:** simplemon liest nur Felder, die auch in Report `version` 4 noch vorhanden sind (Stand 11/2026). Fehlt ein Feld, bleibt die Spalte leer.
- **Datenbank im laufenden Betrieb:** Lesen ist jederzeit möglich. Sperrt ein anderes Programm die Datei, kann eine Runde scheitern; der Fehler erscheint in der Konsole, die nächste Runde wird normal geschrieben.
- **Zugangsdaten und Adressen:** Echte IP-Adressen gehören nur in `config_local.py`, nie in `config.py`. Das gilt ebenso für ThingsBoard-Tokens. Datenbanken (`*.db`) und CSV-Dateien sind über `.gitignore` ausgeschlossen, weil sie Seriennummern enthalten.

## Versand an ThingsBoard

Mit `WRITE_TB = True` sendet simplemon die Werte an [ThingsBoard](https://thingsboard.io), zusätzlich zu oder statt Datenbank und CSV. Das Vorbild ist die ThingsBoard-Anbindung des Dashboard-Proxys ([`ts_bridge.py`](../zendash_watch_API_ZenSDK/ts_bridge.py)).

### Geräte und Tokens

**Jeder Solarflow und jeder Akkupack ist in ThingsBoard ein eigenes Gerät mit eigenem Access Token.** Die Geräte legst du in ThingsBoard selbst an, kopierst je Gerät das Access Token und trägst es in `config_local.py` ein:

| Gerät | Name in ThingsBoard (Empfehlung) | Token in `config_local.py` |
|---|---|---|
| Solarflow | Name wie in `DEVICES`, z. B. „SF800 Pro“ | `TB_HUB_TOKENS = {"SF800 Pro": "<TOKEN>"}` |
| Akkupack | **Seriennummer** des Packs | `TB_PACK_TOKENS = {"<SERIENNUMMER>": "<TOKEN>"}` |
| Netz (Smartmeter) | „Netz“ | `TB_GRID_TOKEN = "<TOKEN>"`, Wertname `TB_GRID_KEY` (Standard `gridPower`) |

- Die Seriennummern der Packs stehen in der Datenbank bzw. CSV (Spalte `sn`). Findet simplemon einen Pack ohne Token, meldet es das einmal in der Konsole, mit Seriennummer und Position („SF800 Akku 2“).
- Ein Akku wird über seine Seriennummer zugeordnet, nicht über seine Position. Ändert sich die Reihenfolge im Report, landen die Werte trotzdem beim richtigen Gerät.
- Ein Solarflow oder Akku ohne Token wird nicht gesendet. Die anderen laufen normal weiter.

### Welche Werte gesendet werden

Alles ist in `config_local.py` einstellbar. Jede Liste ordnet einem **Namen im Report** einen **selbst gewählten Namen in ThingsBoard** zu:

```python
TB_HUB_FIELDS  = {"electricLevel": "soc", "solarInputPower": "pv", "minSoc": "reserve"}
TB_PACK_FIELDS = {"socLevel": "soc", "minVol": "zelleMin", "maxTemp": "temp"}
```

| Einstellung | Inhalt | Art in ThingsBoard |
|---|---|---|
| `TB_HUB_FIELDS` | Messwerte je Solarflow. Standard: dieselben 15 Werte und Namen wie der Dashboard-Proxy (`ts_bridge`) | Telemetrie, bei jedem Senden |
| `TB_PACK_FIELDS` | Messwerte je Akkupack | Telemetrie, bei jedem Senden |
| `TB_ON_CHANGE` | Reportnamen, die nur **bei Änderung** gesendet werden, dazu einmal am Tag und nach einem Neustart (Standard: `socLimit`, `socStatus`, `socSet`, `minSoc`, `heatState`, `gridOffMode`, `chargeMaxLimit`, `inverseMaxPower`, `gridReverse`). Wirkt nur für Werte, die in `TB_HUB_FIELDS`/`TB_PACK_FIELDS` stehen | Telemetrie |
| `TB_HUB_ATTRIBUTES` | feste Angaben je Solarflow (Standard: `product`, `version`, `sn` als `hub_sn`, `packNum`) | Attribute, beim Start, bei Änderung und einmal am Tag |
| `TB_PACK_ATTRIBUTES` | feste Angaben je Akkupack (Standard: `sn`, `packType`, `softVersion`) | Attribute, ebenso |
| `TB_PACK_NAME_ATTRIBUTE`, `TB_PACK_NAME_FORMAT` | lesbarer **Name des Akkus als Attribut**, Standard `name` = „{hub} Akku {nr}“, z. B. „SF800 Akku 1“. Platzhalter `{hub}`, `{nr}`, `{sn}`. Leerer Attributname = kein Namens-Attribut | Attribut |

- Umgerechnet wird wie in Datenbank und CSV: Temperatur in °C, Spannungen in V, `socSet`/`minSoc` in %.
- **Berechnete Werte je Solarflow**, in `TB_HUB_FIELDS` wie Reportnamen verwendbar und genau wie in `ts_bridge` gerechnet:

  | Name | Bedeutung |
  |---|---|
  | `minVol` | kleinste Zellspannung aller Packs des Solarflows in V. Packs mit 0 (schlafend) zählen nicht |
  | `batteryPower` | `packInputPower − outputPackPower` in W: + = Akku entlädt, − = Akku lädt |
  | `packTempLow` | kühlstes Pack (kleinstes `maxTemp`) in ganzen °C. Packs mit 0 zählen nicht |
- Werte, die ein Gerät nicht liefert, werden weggelassen.
- Jeder Wert kostet Datenpunkte in ThingsBoard. Beispiel: 2 Solarflows mit je 11 laufenden Werten und 3 Akkupacks mit je 7 Werten ergeben 43 Werte je Minute, rund 62 000 am Tag. Die vier Status-Werte (`socLimit`, `socSet`, `minSoc`, `heatState`) zählen dank `TB_ON_CHANGE` kaum. Die genaue Zahl für die eigene Anlage zeigt der [Testmodus `--once`](#testmodus---once).

### Senden

| Einstellung | Bedeutung | Standard |
|---|---|---|
| `TB_HOST` | Adresse des ThingsBoard-Servers, auch ein eigener Server im Heimnetz | `https://eu.thingsboard.cloud` |
| `TB_INTERVAL` | Sekunden zwischen zwei Sendungen, ab 10. Bei 60 wird zu jeder vollen Minute gesendet | 60 |

- Gesendet wird zu jedem Vielfachen von `TB_INTERVAL` der **letzte Stand der Abfrage**, mit diesem Zeitpunkt als Zeitstempel. Mit den Standardwerten (`POLL_INTERVAL = 60`, `POLL_ALIGN = True`, `POLL_LEAD = 10`, `TB_INTERVAL = 60`) wird um hh:mm:50 abgefragt und zur vollen Minute gesendet. Der Stand ist dann rund 10 s alt, wie im Dashboard-Proxy.
- `POLL_INTERVAL` und `TB_INTERVAL` sind unabhängig: Man kann z. B. alle 30 s in die Datenbank schreiben und jede Minute an ThingsBoard senden. Damit der gesendete Stand frisch ist, sollte `TB_INTERVAL` ein Vielfaches von `POLL_INTERVAL` sein.
- Das Senden läuft in einem **eigenen Thread**. Ein langsames oder nicht erreichbares ThingsBoard bremst weder die Abfrage noch Datenbank und CSV.
- Scheitert eine Sendung, folgt nach 5 s **ein Wiederholversuch**. Scheitert auch der, wird der Wert verworfen und in der Konsole gemeldet. Nachgesendet wird nicht, die Daten liegen ja in Datenbank bzw. CSV.
- Ist ein Solarflow offline, sendet er in dieser Runde nichts, ebenso seine Akkus.
- Ist der letzte Stand älter als zwei Abfrageintervalle bzw. ein Sendeintervall, wird in dieser Runde nichts gesendet.

### Prüfungen

- **Beim Start, ohne Verbindung:** Form der Einstellungen. Tokens dürfen nur erlaubte Zeichen enthalten, `TB_HUB_TOKENS` darf nur Namen aus `DEVICES` enthalten, die Listen müssen Zuordnungen „Report → ThingsBoard“ sein. Bei einem Fehler bricht der Start mit Meldung ab.
- **Beim Start, mit Verbindung:** Jedes Token sendet einmal das Test-Attribut `simplemonStart`. Lehnt ThingsBoard ein Token ab (HTTP 401), meldet die Konsole das, und dieses Token wird bis zum nächsten Neustart nicht mehr verwendet. Die übrigen Geräte laufen weiter.

### Testmodus `--once`

Bevor etwas an ThingsBoard geht, lässt sich ansehen, was gesendet würde:

```sh
python3 zendure_logger.py --once
```

- Fragt alle Speicher und den Smartmeter **einmal** ab, baut die Daten genau wie beim Senden (Zuordnung, Umrechnung, Akku-Namen, Attribute) und schreibt sie in die Datei `TB_TEST_FILE` (Standard `tb_test.json`). Danach endet das Programm.
- **Es wird nichts gesendet**, Datenbank und CSV werden nicht angefasst, es wird nichts umbenannt.
- Funktioniert auch mit `WRITE_TB = False` und mit Platzhaltern statt Tokens. Geprüft wird nur der Aufbau der Listen.
- **Tokens stehen nie in der Datei.** Je Gerät steht dort nur „eingetragen“ oder „fehlt – wird nicht gesendet“, die Adresse mit `<TOKEN>`.
- Geräte ohne Token erscheinen trotzdem, Akkus mit Seriennummer und Position. So findet man die Seriennummern für `TB_PACK_TOKENS`.
- Am Ende der Datei und in der Konsole: nicht erreichte Solarflows, Geräte ohne Token und die Zahl der Datenpunkte (erste Sendung, jede weitere Sendung, ungefähr je Tag).

Die Datei enthält Seriennummern. Sie steht deshalb in `.gitignore` (`tb_test*.json`) und sollte nicht weitergegeben werden.

### Sicherheit

Tokens sind Zugangsdaten. Sie gehören nur in `config_local.py`, die nicht ins Repo kommt, nie in `config.py`.

## Frühere Fassungen

- Bis 11/2026 lag simplemon im Archiv unter `archiv/ha/simplemon/`.

- Bis 11/2026 hieß das Programm `zendure_dashboard.py` und enthielt zusätzlich eine Webseite sowie Warnungen per Signal/WhatsApp mit Schwellwerten.
- Die erste Fassung von `zendure_logger.py` konnte nur einen Speicher, schrieb zusätzlich die Leistung eines weiteren Shellys und rechnete eine Tagesenergie (`energy_daily`).

Beides steht in der Git-Historie.
