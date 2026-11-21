# simplemon – Logger für Zendure-Speicher

> **Eigenständiges Werkzeug neben der Suite.** simplemon braucht keinen Shelly und kein Script der Suite. Es liest die Speicher direkt über die zenSDK-Schnittstelle. Für Regelung, Dashboard und Meldungen gibt es die [Suite](../readme.md) mit dem Shelly-Script `zendash_watch`, dem Dashboard-Proxy und der [Statistik-Auswertung](../stat/auswertung/readme.md).

simplemon ist ein einzelnes Python-Script, das einen oder mehrere Zendure-Speicher samt Akkupacks regelmäßig ausliest und die Werte in eine SQLite-Datenbank, in CSV-Dateien und/oder an ThingsBoard schreibt. Jede der drei Ausgaben lässt sich einzeln abschalten. Es **steuert nichts**, zeigt nichts an und verschickt keine Nachrichten. Es liest nur und schreibt nichts auf die Speicher.

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

1. **Abfrage:** Alle `POLL_INTERVAL` Sekunden (Standard 60) holt es von jedem Speicher den Report über die lokale zenSDK-Schnittstelle (`GET /properties/report`).
   - Alle Speicher werden **gleichzeitig** abgefragt. Ein Speicher, der nicht antwortet, hält die anderen nicht auf. Er erscheint als Fehler in der Konsole, die übrigen werden normal geschrieben.
   - Optional dazu die Netzleistung von einem **Shelly Pro 3EM** (`EM.GetStatus`, Feld `total_act_power`), einmal je Runde.
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
| `USE_SMARTMETER`, `SMARTMETER_URL` | Netzleistung vom Shelly Pro 3EM mitschreiben | `False` |

Mehrere Speicher:

```python
DEVICES = [
    {"name": "SF800 Pro", "url": "http://192.168.x.x/properties/report"},
    {"name": "SF800",     "url": "http://192.168.x.y/properties/report"},
]
```

Der Name erscheint in Datenbank und CSV und muss eindeutig sein. Ein doppelter oder leerer Name bricht den Start mit einer Fehlermeldung ab, ebenso wenn `WRITE_DB`, `WRITE_CSV` und `WRITE_TB` alle `False` sind.

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
| `TB_HUB_FIELDS` | Messwerte je Solarflow. Standard: dieselben 15 Werte und Namen wie der Dashboard-Proxy (`ts_bridge`), siehe [Umstieg von `ts_bridge`](#umstieg-von-ts_bridge) | Telemetrie, bei jedem Senden |
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

### Umstieg von `ts_bridge`

Wer bisher den ThingsBoard-Versand des Dashboard-Proxys (`ts_bridge`) nutzt, kann auf simplemon umsteigen und **seine ThingsBoard-Geräte und Verläufe weiterverwenden**.

**Was gleich ist**

| | `ts_bridge` | simplemon |
|---|---|---|
| Gerät je Solarflow | ja | ja, dasselbe Gerät mit demselben Token |
| Werte je Solarflow | 15 wählbare Werte | dieselben 15 Werte mit denselben Namen, im Standard alle aktiv |
| Berechnete Werte | `minVol`, `batteryPower`, `packTempLow` | gleich gerechnet |
| Einheiten | V, °C, % | gleich |
| Nur bei Änderung | `socLimit`, `socSet`, `minSoc`, `heatState` | dieselben, plus weitere Status-Werte, falls ausgewählt |
| Gerät „Netz“ | `gridPower`, + = Bezug | `gridPower`, + = Bezug (Quelle: Shelly Pro 3EM, `USE_SMARTMETER`) |
| Zeitpunkt | jede volle Minute | jede volle Minute (`TB_INTERVAL = 60`) |
| Alter des Stands | Abfrage 14 s vor der vollen Minute, höchstens ca. 8 s alt | Abfrage 10 s vor der vollen Minute (`POLL_LEAD`), ca. 10 s alt |
| Hub offline | in dieser Minute nichts | gleich |

**Was neu dazukommt**
- ein **Gerät je Akkupack** (`TB_PACK_TOKENS`) mit eigenen Messwerten,
- **Attribute** je Solarflow und Akku (`product`, `hub_sn`, Akku-Name …) sowie beim Start das Test-Attribut `simplemonStart`,
- in `ts_bridge` abgeschaltete Werte (z. B. `batteryPower`, `temp`) sind im Standard von simplemon **an**. Wer genau die bisherige Auswahl behalten will, entfernt die überzähligen Zeilen aus `TB_HUB_FIELDS`.

**So geht der Umstieg**
1. Die Access Tokens der Solarflows und des Netzes in ThingsBoard holen: beim jeweiligen Gerät unter „Zugangsdaten“ kopieren. Die Proxy-Seite `/thingsboard` zeigt sie nur gekürzt an, hilft aber bei der Zuordnung, welches Gerät zu welchem Hub gehört.
2. In `config_local.py` eintragen:
   - Solarflow: das Token beim **Namen** aus `DEVICES` in `TB_HUB_TOKENS`. `ts_bridge` ordnet nach Hub-Nummer, simplemon nach Namen, also auf die richtige Zuordnung achten.
   - Netz: das Token in `TB_GRID_TOKEN`, dazu `USE_SMARTMETER = True` mit der Adresse des Shelly Pro 3EM.
   - Für die Akkupacks in ThingsBoard neue Geräte anlegen und ihre Tokens in `TB_PACK_TOKENS` eintragen.
3. Mit `python3 zendure_logger.py --once` prüfen, was gesendet würde.
4. **Auf der Proxy-Seite `/thingsboard` den ThingsBoard-Versand abschalten.** Sonst kommt jeder Wert zweimal an, von `ts_bridge` und von simplemon.
5. `WRITE_TB = True` setzen und simplemon starten.

Gleiche Namen und gleiche Geräte bedeuten: In ThingsBoard laufen Verläufe, Dashboards und Regeln ohne Änderung weiter.

### Sicherheit

Tokens sind Zugangsdaten. Sie gehören nur in `config_local.py`, die nicht ins Repo kommt, nie in `config.py`.

## Frühere Fassungen

- Bis 11/2026 lag simplemon im Archiv unter `archiv/ha/simplemon/`.

- Bis 11/2026 hieß das Programm `zendure_dashboard.py` und enthielt zusätzlich eine Webseite sowie Warnungen per Signal/WhatsApp mit Schwellwerten.
- Die erste Fassung von `zendure_logger.py` konnte nur einen Speicher, schrieb zusätzlich die Leistung eines weiteren Shellys und rechnete eine Tagesenergie (`energy_daily`).

Beides steht in der Git-Historie.
