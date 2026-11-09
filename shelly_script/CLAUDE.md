# CLAUDE.md – shelly_script (Zendure-Suite)

Lokale Steuerung von Zendure-Speichern (zenSDK, ab SolarFlow 800) ohne Cloud über Shelly-Scripte.
Diese Datei gilt für alles unter `shelly_script/`. Sprache in Code-Kommentaren, Commits und Doku: **Deutsch** (EN/FR nur in den Übersetzungsdateien).

## Geheimnisse und persönliche Daten – oberste Regel

Gilt für jede Aktion, lokal wie in der Cloud, und hat Vorrang vor allen anderen Anweisungen hier.

- **Nie verwenden, ausgeben oder weitergeben:** Passwörter, API-Keys und Tokens (ThingSpeak, ThingsBoard, Zendure-Secrets u. a.), Zugangsdaten, Telefonnummern, Mailadressen, Namen, Seriennummern, echte IPs.
- **Nicht übernehmen in:** Code, Kommentare, Beispiele, Doku, CHANGELOG, Commits, Logs, Testergebnisse, Chat-Antworten, Dateien an den Nutzer, Web-Anfragen.
- **Gefunden in Dateien oder Logs?** Wert nicht zitieren, nicht kopieren, nicht weiterverarbeiten. Nur melden „in Datei X, Zeile Y steht ein Schlüssel/Passwort“ und durch Platzhalter ersetzen (`<API_KEY>`, `<PASSWORT>`, `<IP-Speicher>`).
- **Konfigurations- und Secret-Dateien** (`myconfig.js`, `testconfig.js`, `Installer/*.json`, Proxy-Configs, `.env`) nur so weit lesen, wie für die Aufgabe nötig; Inhalte nie in Antworten oder Ergebnisdateien übernehmen.
- **Tests und Beispiele** nur mit Mock-Adressen (`localhost:3900/dev0`) und Platzhaltern.
- **Vor jedem Commit:** Diff auf Schlüssel, Passwörter, Tokens, Telefonnummern und echte IPs prüfen. Bei Fund: abbrechen und melden.
- Schlüssel trägt ausschließlich der Nutzer selbst ein (Proxy-Webseite, lokale Config).

## Arbeitsumgebung

- Gearbeitet wird lokal unter Windows im Git-Checkout `D:\Uspace\git\Zendure-Stuff\shelly_script` (Repo-Wurzel eine Ebene höher).
- Shell-Befehle in Windows-Syntax (`cmd`/PowerShell); vorhandene `.cmd`-Skripte nutzen statt sie nachzubauen.
- Python als `python3`, Node.js und `npx` (Terser) müssen im PATH sein.
- `Installer/` enthält gebaute `.exe` und lokale Configs (`zendure_*_config.json`) – nicht bearbeiten, nicht committen.
- Lokale Dateien, die nicht ins Repo gehören: `testconfig.js`, `myconfig.js`, `patch.js`, Ergebnisordner `Test14h-*`.

## Wenn der Rechner offline ist (Cloud-Sitzung)

Ist der lokale Ordner nicht erreichbar, wird auf einer Kopie des GitHub-Stands (`surfer1264/Zendure-Stuff`, Branch `main`) gearbeitet.
Das gilt auch für Fragen zu Code, Texten oder Verhalten: nicht aus dem Gedächtnis antworten, sondern sofort im GitHub-Stand nachsehen.

- **Vorher immer frisch holen** (`git fetch` + Abgleich mit `origin/main`). Nicht gepushte lokale Änderungen sind dort unsichtbar – im Zweifel nachfragen.
- **Erlaubt:** lesen, analysieren, `*_src.js`/CHANGELOG/Doku/Proxy-Code ändern, minifizieren, Tests in Node laufen lassen. Geänderte Dateien und Testergebnisse als Dateien an den Nutzer schicken.
- **Nicht möglich:** Upload auf Shellys, Zugriff auf Geräte im Heimnetz, Schreiben in `D:\…`. Kein Push ohne ausdrückliche Freigabe.
- **Tests ohne `.cmd`** (Linux), gleiche Werte wie `14hlauf0600_rauschen.cmd`:
  ```
  cd shelly_script/testController
  python3 minify_keep_config.py ../Controller/zerooutput_multi_kvs_src.js zerooutput_multi_kvs_mini.js
  python3 swap_config.py zerooutput_multi_kvs_mini.js --config-from testconfig.js -o zdmc_test.js
  START_MIN=360 CYCLES=12600 SPEED_FACTOR=120 STEP_MIN=0.0666667 INTERVAL_MS=4000 \
  START_SOC=30 LOAD_SCALE=0.5 SCENARIO=szenario_werktag.json NOISE_SEED=42 \
  WRITE_LAG_S=1.25 DEVICE_RATE_WPS=350 START_DELAY_S=3.25 REPORT_AGE_S=0 \
  node run_test.js > 14tageslauf.log 2>&1
  node generate_charts.js closed_loop_result.csv report.html
  ```
  Maßgeblich sind immer die Werte in der aktuellen `14hlauf0600_rauschen.cmd` – vor dem Lauf dort nachsehen.
- **`testconfig.js` fehlt auf GitHub.** Ohne sie eine gleichwertige Testconfig nur für den Lauf anlegen (Mock-IPs, keine echten Geräte) und das im Ergebnis vermerken. Gleicher Seed + gleiche Testconfig → gleiche Ergebnisse wie lokal.
- **Sobald der Rechner wieder online ist:** geänderte Dateien in den lokalen Ordner übertragen, vorher prüfen, ob die lokale Datei seitdem verändert wurde.

## Architektur in einem Satz je Teil

| Teil | Ort | Rolle |
|---|---|---|
| Controller | `Controller/zerooutput_multi_kvs_src.js` | Regelt Laden/Entladen mehrerer Speicher auf Netzbezug ≈ 0 (`SCRIPT_TYPE = "zdmc-controller"`) |
| Dashboard/Watchdog | `zendash_watch_API_ZenSDK/zendash_watch_src.js` | Liefert Daten ans Dashboard, meldet Akku voll, Übertemperatur, Unterspannung, Ausfälle (`SCRIPT_TYPE = "zdmc-zendash-watch"`) |
| Proxy | `zendash_watch_API_ZenSDK/zendure_proxy.py`, `HA_zendure_proxy/` | Dashboard-Webseite, ThingSpeak-/ThingsBoard-Upload; als HA-Add-on |
| Configurator | `Multiconfigurator/` (+ `HA_zendure_installer/`, `local_helper/`) | Erstkonfiguration, Update, Upload, Log-Mitschnitt für beide Shellys |
| Test-Harness | `testController/` | Führt den Controller unverändert unter Node gegen einen Mock-Server aus |
| Werkzeuge | `Script_poller/`, `stat/auswertung/`, `thingsboard/` | Speicher-/CPU-Messung, Log-Auswertung, Dashboards |

**Veraltet – nicht weiterentwickeln, nur lesen:** liegt im Repo unter `archiv/` (`archiv/shelly_script/`: `Upload_Controller/`, `WatchdogZenSDK/`, `AkkuWatchDogMulti/`, `Datenmonitor/`; `archiv/ha/`: frühere Home-Assistant-Dateien). `zendash/` ist gelöscht. Änderungen gehören in die Nachfolger (Controller, zendash_watch, Configurator).

## Referenz: Geräte-Report `GET /properties/report`

Echter Report eines SolarFlow 800 mit 2 Akkupacks (Seriennummern maskiert): `testController/report_sf800_referenz.json`. Bei Parser-, Mock- oder Doku-Arbeit diese Datei als Vorlage nehmen, nicht raten.

Aufbau: `sn`, `product` → `properties` (Hub) → `packData[]` (je Pack). Gleichnamige Felder in `properties` und `packData` (z. B. `sn`, beim SolarFlow 800 auch `heatState`) → nur zwischen `properties` und `packData` suchen.

| Feld | Einheit / Bedeutung | Beispiel |
|---|---|---|
| `electricLevel` | SoC Hub in % | 30 |
| `minSoc`, `socSet` | Zehntel-% (Controller schreibt `minSoc*10`) | 300 = 30 %, 1000 = 100 % |
| `socLimit` | 0 normal, 1 Ladesperre (voll), 2 Entladesperre (leer) | 2 (SoC = minSoc) |
| `socStatus` | 1 = SoC-Kalibrierung läuft | 0 |
| `acMode` | 1 = Laden bzw. Standby (bei 0 W), 2 = Entladen/Export | 1 |
| `gridReverse` | 1 erlaubt, 2 gesperrt (Fleet-Lock) | 1 |
| `outputHomePower`, `gridInputPower`, `solarInputPower`, `packInputPower`, `outputPackPower` | W | 0 |
| `inputLimit`, `outputLimit`, `chargeMaxLimit`, `inverseMaxPower` | W | 0 / 0 / 800 / 800 |
| `hyperTmp`, `packData[].maxTemp` | Zehntel-Kelvin: `(x − 2731) / 10` °C | 2831 = 10,0 °C |
| `BatVolt`, `packData[].totalVol` | 0,01 V | 4927 = 49,27 V |
| `packData[].maxVol`, `minVol` | Zellspannung 0,01 V | 327 = 3,27 V |
| `packData[].socLevel` | SoC je Pack in % | 30 / 31 |
| `packNum`, `rssi`, `ts` | Anzahl Packs, WLAN dBm, Unix-Zeit | 2, −66 |

Werte, deren Bedeutung hier nicht steht, nicht interpretieren – nachfragen oder als unbekannt kennzeichnen.

Weitere echte Reports (Seriennummern maskiert). Die Geräte melden nicht dieselben Felder: Nur die beiden Pro-Geräte haben in `properties` u. a. `gridOffPower` und `gridOffMode`, nur der SolarFlow 800 hat `heatState` auch in `packData`.

SolarFlow 2400 Pro (1 Akkupack, Standby):

```json
{"timestamp":1793908037,"messageId":70,"sn":"xxxxxxxxxxxxxx","version":3,"product":"solarFlow2400Pro","properties":{"heatState":0,"packInputPower":0,"outputPackPower":0,"outputHomePower":0,"remainOutTime":59940,"packState":0,"electricLevel":55,"gridInputPower":0,"solarInputPower":0,"solarPower1":0,"solarPower2":0,"solarPower3":0,"solarPower4":0,"pass":0,"reverseState":0,"socStatus":0,"hyperTmp":2841,"gridOffPower":0,"dcStatus":0,"pvStatus":1,"acStatus":0,"dataReady":1,"gridState":1,"BatVolt":4912,"socLimit":0,"faultLevel":0,"acCouplingState":57344,"offGridState":0,"dryNodeState":1,"writeRsp":0,"acMode":1,"inputLimit":0,"outputLimit":0,"socSet":1000,"minSoc":400,"gridStandard":0,"gridReverse":1,"inverseMaxPower":800,"lampSwitch":0,"gridOffMode":2,"IOTState":2,"Fanmode":0,"Fanspeed":0,"bindstate":0,"factoryModeState":0,"OTAState":0,"oldMode":0,"VoltWakeup":0,"ts":1791136227,"tsZone":14,"smartMode":1,"chargeMaxLimit":2400,"phaseSwitch":1,"batCalTime":60,"socCompSwitch":0,"packNum":1,"rssi":-52,"is_error":0},"packData":[{"sn":"xxxxxxxxxxxxxxx","packType":500,"socLevel":55,"state":0,"power":0,"maxTemp":2831,"totalVol":4910,"batcur":0,"maxVol":327,"minVol":327,"softVersion":4355}]}
```

SolarFlow 800 (2 Akkupacks, entlädt):

```json
{"timestamp":1793909065,"messageId":245,"sn":"xxxxxxxxxxxxxxx","version":3,"product":"solarFlow800","properties":{"heatState":0,"packInputPower":356,"outputPackPower":0,"outputHomePower":356,"remainOutTime":225,"packState":2,"electricLevel":55,"gridInputPower":0,"solarInputPower":0,"solarPower1":0,"solarPower2":0,"pass":0,"reverseState":0,"socStatus":0,"hyperTmp":2891,"dcStatus":2,"pvStatus":0,"acStatus":1,"dataReady":1,"gridState":1,"BatVolt":4837,"socLimit":0,"faultLevel":0,"writeRsp":0,"acMode":2,"inputLimit":0,"outputLimit":356,"socSet":1000,"minSoc":400,"gridStandard":0,"gridReverse":1,"inverseMaxPower":800,"lampSwitch":0,"IOTState":2,"factoryModeState":0,"OTAState":0,"oldMode":0,"VoltWakeup":0,"ts":1793909064,"bindstate":0,"tsZone":13,"chargeMaxLimit":800,"smartMode":1,"phaseSwitch":1,"batCalTime":60,"socCompSwitch":0,"packNum":2,"rssi":-59,"is_error":0},"packData":[{"sn":"xxxxxxxxxxxx","packType":70,"socLevel":55,"state":2,"power":280,"maxTemp":2871,"totalVol":4830,"batcur":65478,"maxVol":323,"minVol":321,"softVersion":4354,"heatState":0},{"sn":"xxxxxxxxxxxxxxx","packType":70,"socLevel":55,"state":2,"power":183,"maxTemp":2861,"totalVol":4830,"batcur":65502,"maxVol":322,"minVol":321,"softVersion":8223,"heatState":0}]}
```

SolarFlow 800 Pro (3 Akkupacks, entlädt, Offgrid in Betrieb):

```json
{"timestamp":1792006493,"messageId":123,"sn":"xxxxxxxxxxxxxxx","version":3,"product":"solarFlow800Pro","properties":{"heatState":0,"packInputPower":741,"outputPackPower":0,"outputHomePower":636,"remainOutTime":87,"packState":2,"electricLevel":19,"gridInputPower":0,"solarInputPower":0,"solarPower1":0,"solarPower2":0,"solarPower3":0,"solarPower4":0,"pass":0,"reverseState":0,"socStatus":0,"hyperTmp":3001,"gridOffPower":105,"dcStatus":1,"pvStatus":1,"acStatus":1,"dataReady":1,"gridState":1,"BatVolt":4711,"socLimit":0,"faultLevel":0,"writeRsp":0,"acMode":2,"inputLimit":0,"outputLimit":636,"socSet":1000,"minSoc":150,"gridStandard":0,"gridReverse":1,"inverseMaxPower":800,"lampSwitch":1,"gridOffMode":0,"IOTState":2,"Fanmode":1,"Fanspeed":0,"bindstate":0,"factoryModeState":0,"OTAState":0,"oldMode":0,"VoltWakeup":0,"ts":1792005800,"tsZone":14,"smartMode":1,"chargeMaxLimit":1000,"phaseSwitch":1,"batCalTime":60,"socCompSwitch":0,"packNum":3,"rssi":-32,"is_error":0},"packData":[{"sn":"xxxxxxxxxxxxxxx","packType":300,"socLevel":18,"state":2,"power":240,"maxTemp":2951,"totalVol":4710,"batcur":65485,"maxVol":315,"minVol":313,"softVersion":4354},{"sn":"xxxxxxxxxxxxxxx","packType":300,"socLevel":19,"state":2,"power":268,"maxTemp":2901,"totalVol":4710,"batcur":65479,"maxVol":314,"minVol":314,"softVersion":4354},{"sn":"xxxxxxxxxxxxxxxx","packType":300,"socLevel":20,"state":2,"power":241,"maxTemp":2901,"totalVol":4730,"batcur":65485,"maxVol":316,"minVol":315,"softVersion":4354}]}
```

## Harte Regeln für Shelly-Scripte (mJS)

1. **Nur ES5-Syntax** plus `let`: keine Arrow-Functions, keine Template-Strings, kein `class`, kein Destructuring, kein Spread, kein `async/await`. `minify_keep_config.py` bricht sonst ab.
2. **Speicher ist das Nadelöhr.** Referenz: Controller mit zwei Geräten `peak` ≈ 19 kB. Jede Änderung darf den Peak nicht erhöhen, ohne dass das begründet und gemessen ist (`Script_poller`, `debug`-Meldungen `DEBUG MEM …`).
   - Große HTTP-Antworten nicht mit `JSON.parse` zerlegen, sondern benötigte Felder direkt aus dem Text lesen (Muster aus 5.3.0).
   - Abläufe mit großen Antworten nacheinander, nicht parallel.
   - Keine großen String-Arrays oder Lookup-Tabellen im Heap halten.
3. **Genau ein Script pro Shelly.** Nie vorschlagen, zwei Scripte auf ein Gerät zu legen.
4. **Der `let CONFIG = { … };`-Block ist eine Schnittstelle.** Configurator, `swap_config.py` und Nutzer-`myconfig.js` hängen daran.
   - Schlüssel nicht umbenennen oder entfernen; neue Schlüssel optional mit Default im Code.
   - Bei inkompatibler Änderung `CONFIG_SCHEMA` erhöhen und Configurator anpassen.
   - In der Quelle nur Platzhalter oder Beispielwerte, keine echten Geräte-IPs oder Zugangsdaten.
5. **KVS-Werte** sind live überschreibbar (Dashboard, HA). Änderungen von außen nur zwischen zwei Regelzyklen übernehmen; fehlende Keys nur anlegen, wenn der Shelly ausdrücklich „Key fehlt“ meldet.
6. **Regelverhalten** (`setpoint`, `hysteresis`, `dampingFactor`, `jumpFactor`, `discharge.*`) nur ändern, wenn das ausdrücklich gewünscht ist – und dann mit Simulationsvergleich (siehe Tests).

## Dateien: Quelle vs. generiert

- Bearbeitet wird **immer `*_src.js`**.
- `*_mini.js` wird erzeugt – nie von Hand ändern.
- Pipeline je Script im Ordner `Deploy/`:
  `deploy.cmd` → `swap_config.py` (CONFIG aus `myconfig.js` einsetzen) → `minify_keep_config.py` (Terser, CONFIG bleibt byte-gleich) → `Deploy\upload_mini.js` (lokal, in `.gitignore`) → `upload_shelly.py`. Die eingecheckte `*_mini.js` erzeugt nur `minify.cmd` aus der Quelle, ohne eigene Konfiguration.
- `myconfig.js`, `patch.js` und echte IPs gehören nicht ins Repo.

## Versionierung und Changelog

- Bei jeder Änderung an einem Script: `VERSION` im Script erhöhen und Eintrag im `CHANGELOG.md` des jeweiligen Ordners.
- `zendash_watch_API_ZenSDK/` hat drei Changelogs: `CHANGELOG.md` nur für das Shelly-Script (daraus liest das Versions-Manifest die Änderungen für den Configurator), `CHANGELOG_dashboard.md` für Dashboard und Proxy, `HA_zendure_proxy/CHANGELOG.md` nur für App-Themen mit Verweis auf den Dashboard-Changelog. Die Versionsnummer bleibt gemeinsam.
- Changelog-Stil wie bestehend: **Ziel** in einem Satz, dann Stichpunkte nach Wirkung, Messwerte (Peak, Laufzeit) wenn vorhanden, Schlusssatz „Keine Änderung am CONFIG-Block nötig.“ oder was der Nutzer anpassen muss.
- `manifest_meta.json` (`helperMin`) anpassen, wenn ein Script eine neuere Helfer-Version voraussetzt.

## Tests

```
cd testController
minify_patch_start-rauschen.cmd   # src minifizieren → testconfig.js einsetzen → 14hlauf0600_rauschen.cmd
node compare_runs.js              # Stellbefehle zweier Läufe vergleichen
```
- Standardtest ist `14hlauf0600_rauschen.cmd`: 14 h ab 06:00, Szenario `szenario_werktag.json`, `NOISE_SEED=42`, mit Geräteverzögerung (`WRITE_LAG_S`, `DEVICE_RATE_WPS`, `START_DELAY_S`).
- Immer über `minify_patch_start-rauschen.cmd` starten, damit `zdmc_test.js` aus der aktuellen `*_src.js` gebaut wird (minifiziert wie auf dem Shelly). `testconfig.js` liegt nur lokal.
- Die Scripte enthalten `pause`. Ohne Eingabe bleibt der Lauf hängen, deshalb aus Claude Code mit `cmd /c "echo.|…"` aufrufen oder das Ende abwarten lassen.
- Ergebnisse im Ordner `Test14h-<RELEASE>-seed<SEED>-<Zeitstempel>`. `RELEASE` in der .cmd vorher auf die neue Version setzen.
- Das Rauschen ist deterministisch (gleicher Seed → gleicher Lauf). Vergleiche alt/neu daher mit **gleichem Seed**; für robuste Aussagen zusätzlich einen zweiten Seed.
- Ohne `SCENARIO`/`NOISE_SEED` verhält sich der Mock wie früher (`14hlauf0600.cmd`).
- Vor jeder Controller-Änderung einen Referenzlauf mit der alten Version, danach Vergleich. Bei reinen Speicher-/Ablaufänderungen müssen die Stellbefehle identisch bleiben.
- `shelly_shim.js` bildet `Shelly.call`, `Timer`, `KVS`, `print` nach – neue Shelly-APIs dort ergänzen, sonst schlägt der Test fehl.
- Syntax-Check ohne Upload: `python3 Controller/Deploy/minify_keep_config.py Controller/zerooutput_multi_kvs_src.js /tmp/out.js`

## Proxy und Uploads (Python)

- ThingSpeak/ThingsBoard: wenn aktiv, fester Minutentakt; wenn inaktiv, **keine** Anfrage an die zendash-API.
- Schlüssel/Tokens werden einmalig über die Proxy-Webseite eingetragen, nie im Code oder in Beispielen.
- Lokaler Proxy und HA-Add-on (`HA_zendure_proxy/`) gleich halten; Add-on-Version in `config.yaml` und dessen `CHANGELOG.md` mitziehen.
- Windows ist Zielplattform der `.cmd`-Skripte: Pfade mit `%~dp0`, `npx` über `find_npx()` auflösen.

## Doku

- Jede Nutzer-Doku gibt es dreifach: `readme.md` (DE), `readme_EN.md`, `readme_FR.md`. Inhaltliche Änderungen in alle drei übernehmen oder ausdrücklich als offen markieren.
- Technische Tiefe gehört in `Controller/gesamtdoku.md`, Bedienung in `benutzerdoku.md`.
- Einfache Sprache, Begriffe wie in `readme.md` → „Begriffe“ (Speicher, Controller, Helfer, KVS).
- Keine personenbezogenen Daten (Namen, echte IPs, Seriennummern, Mailadressen) in Doku, Logs oder Beispielen.

## Arbeitsweise

- Erst lesen, dann ändern: bei Controller-Fragen zuerst `CHANGELOG.md` und das passende Kapitel in `gesamtdoku.md`.
- Kleine, gezielte Diffs; keine Umformatierung ganzer Dateien (bläht den Diff und den Minify-Vergleich auf).
- Kein Push, kein Release, kein Upload auf ein echtes Gerät ohne ausdrückliche Freigabe.
