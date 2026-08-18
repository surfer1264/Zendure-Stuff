# Multi-Device-Controller Test-Harness

Führt das **unveränderte** Originalskript (nur CONFIG-IPs/gridSource auf den
Mock-Server umgebogen) unter Node.js gegen einen stateful Mock-Server aus –
geschlossener Regelkreis, echte Logik, keine Annahmen mehr über
`distributeDischarge`/`applyOutputs`.

## Dateien

- `zdmc_test.js` – dein Original-Skript, CONFIG gepatcht auf:
  - `devices[i].ip` → `localhost:3900/dev0`, `/dev1`, ...
  - `gridSource` → `"http_json"`, `gridSourceUrl` → Mock-Endpoint,
    `gridSourceField` → `"total_power"`
  - Alles andere (minSoc, maxOutput, Hysterese, dischargeAllowed, ...)
    bleibt exakt wie im Original
- `mock_server.js` – simuliert Netzzähler + beide Solarflows:
  - PV lädt den Akku autonom (DC-seitig), unabhängig vom Regler
  - reagiert auf `POST /devN/properties/write` (setzt acMode/outputLimit/
    inputLimit/smartMode/minSoc/socSet/gridReverse tatsächlich)
  - `socLimit` wird aus dem SOC + den vom Regler geschriebenen minSoc/socSet
    berechnet (nicht aus der CONFIG kopiert – testet also auch, ob
    `syncSocLimitsAll` korrekt schreibt)
  - `minSoc`/`socSet` wirken als **harte physikalische Grenzen** in der
    Akku-Simulation (wie echte Geräte-Firmware das auch tut) – kein
    Überschwingen unter/über die geschriebenen Grenzwerte
  - `GET /grid/properties/report` liefert `haushalt − Summe aktueller
    AC-Leistung beider Geräte` (echter geschlossener Kreis) und rückt dabei
    die simulierte Uhr um `STEP_MIN` Minuten weiter
- `shelly_shim.js` – stellt `Shelly.call` (HTTP.GET/HTTP.Request/KVS.*),
  `Timer.set/clear`, `print` bereit, damit das Skript 1:1 unter Node läuft.
  Beschleunigt über `SPEED_FACTOR` nur das **reale** Warten zwischen
  wiederkehrenden Zyklen, ohne die Hold-/Cooldown-Zähler-Logik im Skript
  zu berühren (siehe Abschnitt "Geschwindigkeit" unten)
- `run_test.js` – Runner: startet Mock + Skript, lässt N Zyklen laufen,
  schreibt `closed_loop_result.csv`
- `patch_for_mock.js` – patcht eine beliebige Version von
  `zerooutput_multi_kvs.js` automatisch auf die Mock-Verbindungsdaten
  (Details weiter unten)

## Ausführen

**Voraussetzung:** Node.js installiert (keine weiteren Pakete nötig – nur
eingebaute Node-Module). Falls `node` nicht gefunden wird: Node.js von
nodejs.org installieren, Terminal neu öffnen, mit `node -v` prüfen.

**Schritte:**

1. Alle Dateien (`zdmc_test.js`, `mock_server.js`, `shelly_shim.js`,
   `run_test.js`, `patch_for_mock.js`) in einen gemeinsamen Ordner legen
2. Terminal in diesem Ordner öffnen
3. Test starten:

**Mac/Linux:**
```bash
SPEED_FACTOR=150 STEP_MIN=0.05 CYCLES=28800 INTERVAL_MS=3000 START_SOC=50 LOAD_SCALE=1 node run_test.js
```

**PowerShell:**
```powershell
$env:SPEED_FACTOR=150; $env:STEP_MIN=0.05; $env:CYCLES=28800; $env:INTERVAL_MS=3000; $env:START_SOC=50; $env:LOAD_SCALE=1; node run_test.js
```

**Windows CMD:**
```cmd
set SPEED_FACTOR=150&&set STEP_MIN=0.05&&set CYCLES=28800&&set INTERVAL_MS=3000&&node run_test.js
```

**Alle Umgebungsvariablen im Überblick:**

| Variable | Steuert | Womit erreichst du das |
|---|---|---|
| `CYCLES` | Anzahl Regelzyklen | Wie lang der simulierte Zeitraum ist (`CYCLES × STEP_MIN` Minuten) |
| `STEP_MIN` | Simulierte Minuten pro Zyklus | Auflösung der Umgebung. Klein (0.05) = realitätstreue Hold-/Cooldown-Timer. Groß (15) = schneller grober Tagesüberblick, aber Timer-Verhalten verfälscht |
| `SPEED_FACTOR` | Reales Warten zwischen Zyklen | Beschleunigt nur die Wall-Clock-Geschwindigkeit, ohne die Zyklen-Zähler-Logik im Skript zu beeinflussen – macht lange `CYCLES`-Läufe in Minuten statt Stunden machbar |
| `START_MIN` | Start-Uhrzeit (Minute seit 00:00) | Gezielt in ein bestimmtes Fenster springen, z. B. `420` = 07:00, um nur die morgendliche Entladesperre zu testen, ohne die Nacht davor mitlaufen zu lassen |
| `START_SOC` | Start-SOC beider Geräte (%) | Szenarien wie "beide starten fast voll" simulieren, ohne erst stundenlang aufladen zu müssen |
| `LOAD_SCALE` | Skaliert die gesamte Haushaltslastkurve | Extremszenarien erzwingen – z. B. sehr niedrige Last (`0.05`–`0.2`), damit beide Akkus gleichzeitig 100 % erreichen und der `gridReverse`-Fleet-Lock auslöst |
| `INTERVAL_MS` | Muss zu `CONFIG.interval` in `zdmc_test.js` passen | Nur für die Laufzeit-Schätzung/Logging des Runners – steuert NICHT den echten Zyklus (der kommt aus der CONFIG selbst) |
| `MIN_REAL_MS` | Untergrenze für den realen Zyklusabstand | Schutz gegen Überlastung des Mock-Servers bei sehr hohem `SPEED_FACTOR` |
| `MAX_WAIT_MS` | Sicherheits-Obergrenze für die Gesamtlaufzeit | Verhindert endloses Warten, falls ein Zyklus hängt (z. B. Watchdog-Stall) – normalerweise nicht selbst setzen, hat sinnvollen Default |


**Die drei, die für unterschiedliche Testziele am wichtigsten sind:**
- **Realitätsnaher Tageslauf:** `STEP_MIN=0.05` + `CYCLES=28800` + `SPEED_FACTOR=150`
- **Schneller grober Überblick:** `STEP_MIN=15` + `CYCLES=96` (ohne `SPEED_FACTOR`, läuft in ~5 Min.)
- **Fleet-Lock (`gridReverse=2`) gezielt provozieren:** `LOAD_SCALE=0.05` + `START_SOC=85`, kombinierbar mit einem der beiden obigen
- **2-Stunden Test ab 08:00** 
`$env:SPEED_FACTOR=150; $env:STEP_MIN=0.05; $env:CYCLES=2400; $env:INTERVAL_MS=3000; $env:START_MIN=480; $env:START_SOC=50; $env:LOAD_SCALE=1; node run_test.js`


## Geschwindigkeit: läuft das in Echtzeit? Kann man beschleunigen?

Zwei getrennte "Uhren" laufen parallel:

1. **Der Regler selbst tickt real** – `Timer.set(CONFIG.interval, true, update)`.
   Hold-/Cooldown-Zähler (`holdCycles`, `reversalHoldCount`) sind reine
   **Zyklen-Zähler** im Skript, keine Zeitmessung – sie zählen unabhängig
   davon, wie schnell wir die Zyklen real feuern.
2. **Die Umgebung (Haushalt/PV/Uhrzeit im Mock) ist zeitgerafft** – rückt pro
   Zyklus um `STEP_MIN` simulierte Minuten vor.

**Ohne `SPEED_FACTOR`** entspricht 1 Zyklus = `INTERVAL_MS` reale
Millisekunden (Standard 3000ms) – 1 simulierter Tag dauert dann grob
`CYCLES × 3s` real (z. B. 96 Zyklen ≈ 5 Minuten).

**`SPEED_FACTOR`** verkürzt nur das reale Warten zwischen **wiederkehrenden**
Zyklen (z. B. Faktor 150 macht aus 3000ms nur noch 20ms real), lässt aber
einmalige Timer (Watchdog, `Timer.set(0,...)`, Banner-Verzögerungen)
unangetastet in echter Zeit – sonst würde der Watchdog fälschlich anschlagen,
bevor die (realen, aber sehr schnellen) HTTP-Roundtrips zum Mock fertig sind.

## Wichtig: STEP_MIN und Hold-Timer müssen zusammenpassen

Das Original-Skript berechnet einmal beim Start:
```
CONCENTRATE_HOLD_CYCLES = round(concentrateHoldMinutes * 60000 / CONFIG.interval)
```
Bei `interval: 3000` und `concentrateHoldMinutes: 3` sind das **60 Zyklen**.
Ist `STEP_MIN` zu groß, springt die simulierte Umgebung während dieser 60
Zyklen viel zu weit voran – Beispiel `STEP_MIN=15`: `60 × 15 = 900`
simulierte Minuten (15 Stunden!) vergehen, während der Regler intern
"3 Minuten" zählt. Die Hold-Timer reagieren dann auf eine unrealistisch
schnell wechselnde Welt statt auf die geplanten 3 Minuten.

**Kalibrierte Faustformel für Fidelity:**
```
STEP_MIN ≈ concentrateHoldMinutes / CONCENTRATE_HOLD_CYCLES
         = 3 / 60 = 0.05   (bei interval = 3000 ms)
CYCLES   = 1440 / STEP_MIN   (für einen kompletten simulierten Tag)
```
Das ergibt viele Zyklen (28800 für einen Tag) – dank `SPEED_FACTOR` bleibt
die reale Laufzeit trotzdem überschaubar:
`28800 × max(15ms, 3000/150) ≈ 28800 × 20ms ≈ 9,6 Minuten`.

**Wenn du bewusst grob/schnell nur den Tagesverlauf überfliegen willst** (Hold-
Timer-Feinheiten sind dann egal): größeres `STEP_MIN` (z. B. 15) ist weiterhin
legitim – nur wissen, dass Hold-/Cooldown-Verhalten dabei nicht realitätsnah
ist. Validiert (526 Zyklen, keine Watchdog-Fehlalarme): mit
`SPEED_FACTOR=150 STEP_MIN=0.05` läuft die Physik fein granular statt in
großen Sprüngen.

## Was ein Testlauf typischerweise zeigt

(Beispiel aus einem Lauf mit `STEP_MIN=15`, Standard-Lastprofil, `LOAD_SCALE=1`)

- Zero-Feed-in funktioniert im Normalbetrieb sehr gut (Netzsaldo ~0 W)
- **07:00–09:00**: beide Geräte erreichen `socLimit=2` (Entladesperre) kurz
  vor Sonnenaufgang → Regler kann nichts mehr tun → Netzbezug = Haushaltslast
  1:1 (im Chart deutlich sichtbar)
- **19:00–20:00**: gleiches Muster abends, bevor beide wieder aufgeladen sind
- SF800 Pro sättigt in diesem Lauf bei ~93 %, SF2400 bei ~96 % – **nicht**
  exakt 100 %, weil während der PV-Stunden zwischendurch trotzdem Haushalts-
  spitzen bedient werden. Der `gridReverse`-Fleet-Lock (beide gleichzeitig
  auf `socLimit=1`) wurde in diesem Lauf **nicht** ausgelöst.

## Um den gridReverse-Fleet-Lock gezielt zu triggern

In `mock_server.js` z. B. `householdLoad()` tagsüber absenken oder die
Start-SOC höher ansetzen, damit beide Geräte gleichzeitig 100 % erreichen.
Geht auch ohne Code-Änderung, direkt über die Env-Vars:

```bash
LOAD_SCALE=0.2 START_SOC=75 CYCLES=96 INTERVAL_MS=3000 STEP_MIN=15 node run_test.js
```

Getestet: Damit läuft SF2400 mehrere Stunden auf `socLimit=1`, SF800 Pro kam
mit 97 % knapp nicht ganz auf 100 % – solange noch irgendein Haushaltsbedarf
da ist, wechselt der Regler laufend das aktive Entlade-Gerät ("Ausgleich: ...
Prozentpunkte" im Log), was das jeweils führende Gerät immer wieder minimal
unter 100 % zieht. Für **exakt gleichzeitige** 100 %-Sättigung noch näher an
0 gehen, z. B. `LOAD_SCALE=0.05 START_SOC=85`. Bei Erfolg erscheint im Log:
`gridReverse=2 gesetzt` (auf beiden Geräten) bzw. `gridReverse=1` sobald
wieder Kapazität frei ist.

## Kann ich die Akkukapazität verändern?

Ja – in `mock_server.js`, bei der Geräte-Erzeugung (2. Parameter von
`makeDevice`):

```js
const dev0 = makeDevice("MOCKSN-SF800", 2.0, START_SOC, pv800);   // 2.0 = kWh
const dev1 = makeDevice("MOCKSN-SF2400", 4.0, START_SOC, pv2400); // 4.0 = kWh
```

**Wichtig:** Lade-/Entladeleistung (1000/800 W bzw. 2000/2000 W) und
`minSoc`/`maxSoc` stehen **nicht** im Mock, sondern in `zdmc_test.js` selbst
(`CONFIG.devices[i].maxInputPower`, `.maxOutput`, `.minSoc`, `.maxSoc`) –
die müsst ihr dort separat anpassen, falls die Kapazitätsänderung auch die
Leistungswerte betreffen soll.

**Gemessener Effekt einer Halbierung** (2.0/4.0 → 1.0/2.0 kWh, gleicher
Lastverlauf): der maximale SOC-Sprung pro Zyklus stieg von 14/17 %-Punkten
auf 19/27 %-Punkte. Logisch: `soc_gain = Leistung × Zeit / Kapazität` – bei
halber Kapazität doppelt so schnelle SOC-Änderung. **Faustregel:** `STEP_MIN`
proportional zur Kapazität mitsenken (halbe Kapazität → halbes `STEP_MIN`,
`CYCLES` entsprechend erhöhen), sonst wird die Simulation unrealistisch
grobkörnig.

## Kann ich mit jedem neuen Codestand testen?

Ja, mit zwei Einschränkungen:
- Die CONFIG muss wieder auf den Mock gepatcht werden (siehe unten) –
  **einmal pro Codestand**, nicht bei jedem `run_test.js`-Aufruf
- Nutzt der neue Code andere `Shelly.call`-Methoden (z. B. `Wifi.GetStatus`,
  MQTT, `gridSource:"local"` via `Shelly.getComponentStatus`) → muss der
  Shim (`shelly_shim.js`) dafür erweitert werden – aktuell nur
  HTTP.GET/HTTP.Request/KVS.* implementiert

**"Bei jeder neuen Version erneut nötig"** heißt konkret: eine neue
`zerooutput_multi_kvs.js` enthält wieder eure echten Produktions-Werte –
echte IP-Adressen, `gridSource: "local"` usw. Damit läuft der Test nicht
automatisch, weil das Original-Skript dann versucht, echte Hardware
anzusprechen statt den Mock-Server.

**Konkret betroffen sind genau diese 4 Stellen** (automatisch durch
`patch_for_mock.js`):

| Feld | Produktions-Wert (Beispiel) | Wird für Test |
|---|---|---|
| `devices[i].ip` (alle) | `"192.168.178.143"` | `"localhost:3900/dev0"`, `/dev1`, ... |
| `gridSource` | `"local"` | `"http_json"` |
| `gridSourceUrl` | (unbenutzt bei "local") | `"http://localhost:3900/grid/properties/report"` |
| `gridSourceField` | z. B. `"power"` | `"total_power"` (muss zum Mock-Antwortformat passen) |

**Alles andere** (minSoc, maxOutput, Hysterese, dischargeAllowed, interval,
...) bleibt unangetastet – das soll ja original getestet werden, nur die
Verbindung zu den Geräten wird umgeleitet.

**Workflow für jede neue Version:**
```bash
node patch_for_mock.js neue_version.js zdmc_test.js
node run_test.js
```
Kein manuelles Editieren mehr nötig. `zdmc_test.js` bleibt danach stabil –
`run_test.js` kannst du beliebig oft mit unterschiedlichen Env-Vars erneut
laufen lassen, ohne erneut zu patchen. Nur bei mehr als 2 Geräten oder neuen
`Shelly.call`-Methoden muss noch am Shim/Mock nachjustiert werden.

## Erzeugt die Simulation ein echtes Logfile?

```bash
node run_test.js > testlauf.log
```
Die Konsolen-Ausgabe **ja** – das sind 1:1 die `print()`-Zeilen des
unveränderten Skripts, genau wie auf der echten Shelly-Konsole.

## Brauche ich die closed_loop_result.csv für den Test?

Nein – sie ist nur ein Analyse-Export (in `mock_server.js` selbst gebaut),
kein Bestandteil des eigentlichen Tests. Der Test läuft komplett über die
Konsolen-Ausgabe. Die CSV ist praktisch, wenn danach geplottet/ausgewertet
werden soll – sonst ignorierbar.

## Struktureller Ablauf der Simulation

Alles läuft in **einem** Node-Prozess (`run_test.js`), in zwei getrennten
Rollen:

**1. Start-Reihenfolge**
```
run_test.js
 ├─ startet sofort: mock_server.js (http.createServer auf Port 3900)
 └─ nach 500ms: lädt zdmc_test.js in einer VM-Sandbox (shelly_shim.js)
```

**2. Die Sandbox (`shelly_shim.js`)**
Das Original-Skript läuft per `vm.runInContext` in einer isolierten Umgebung
mit drei globalen Objekten, die reine Weiterleitungen sind:
- `Shelly.call("HTTP.GET"/"HTTP.Request", ...)` → echter `http.request()` an `localhost:3900/...`
- `Timer.set/clear` → `setInterval`/`setTimeout` (Repeat-Timer via `SPEED_FACTOR` beschleunigt, Einmal-Timer unverändert real)
- `print` → `console.log`

Das Skript selbst merkt nichts von der Simulation – für den Code sieht es
aus wie ein Shelly mit HTTP-Geräten im Netz.

**3. Ein Regelzyklus (unverändert im Original-Skript)**
```
Timer.set(interval, true, update)
  → readGridPower()      GET /grid/properties/report
  → readAllDevices()     GET /dev0/.../report, GET /dev1/.../report (nacheinander)
  → calculate()          reine JS-Berechnung, synchron
  → applyOutputs()       ggf. POST /devN/properties/write
```

**4. Der Mock als Zustandsautomat**
Der Mock hält SOC, `acMode`/`outputLimit`/`inputLimit` je Gerät und eine
simulierte Uhrzeit. Die "Physik" rückt genau dann vor, wenn
`/grid/properties/report` gepollt wird – das passiert exakt einmal pro
Zyklus, als erstes. Dabei: PV lädt den Akku, das zuletzt geschriebene
AC-Kommando wirkt auf den SOC (begrenzt durch die vom Regler geschriebenen
minSoc/socSet), dann wird der Netzsaldo berechnet. Die Geräte-GETs danach
liefern den frisch aktualisierten Zustand.

**Der geschlossene Kreis:** Zyklus N schreibt ein Kommando → wirkt sich
zwischen N und N+1 auf den Akku aus → Zyklus N+1 liest den veränderten
Zustand → Regler reagiert erneut. Jede Entscheidung hat eine echte, im
nächsten Zyklus sichtbare Konsequenz – genau wie bei echter Hardware.

## Warum der Test zuverlässig ist – und wo nicht

"Zuverlässig" heißt hier **zuverlässig für Logik-Verhalten**, nicht "bildet
exakt ab, was am echten Gerät passiert".

✅ **Hohe Konfidenz bei:**
- Der kompletten Entscheidungslogik – läuft unverändert, keine Nachbildung
- Zustandsabhängigem Verhalten über Zeit: Hysterese, Richtungswechsel-
  Cooldown, Rebalancing, Ladesperre/Entladesperre-Übergänge (echte
  HTTP-Roundtrips, keine internen Funktionsaufrufe simuliert) – **sofern**
  `STEP_MIN` gemäß obiger Formel kalibriert ist
- Schnittstellen-Kompatibilität: liest/schreibt der Code die richtigen Felder?
- Regressionsvergleich zwischen Codeversionen: gleicher Mock, anderer Code
  → Unterschiede sind eindeutig dem Code zuzuordnen

⚠️ **Begrenzt bei:**
- Physikalischer Genauigkeit (kein Wirkungsgrad, keine Rampzeiten, keine
  echten PV-Input-Limits)
- Unkalibriertem `STEP_MIN` – zu groß gewählt, verwischt Hold-Timer-
  Verhalten (siehe Abschnitt oben)
- Fehlerfällen: Mock antwortet immer sofort korrekt – Timeout-/Fehlerpfade
  (`reportError`, Watchdog) werden dadurch **nicht** automatisch mitgetestet,
  nur wenn man das gezielt nachbaut (Mock könnte man leicht um künstliche
  Verzögerungen/Fehlerantworten erweitern)
- Nur die Shelly-Methoden, die der Shim kennt (HTTP.GET/Request, KVS.*) –
  neue APIs im Skript würden unbemerkt ignoriert

Kurz: Der Test ist stark für "verhält sich der Regler logisch korrekt über
die Zeit", schwach für "verhält sich exakt wie die echte Zendure-Hardware
bei Netzwerkfehlern".

## Woher kommen die Haushaltsdaten für den Testlauf?

**Keine externe Datei, kein CSV-Import.** Die Werte kommen aus einer reinen
Formel direkt in `mock_server.js` (`householdLoad()`), die bei jedem
`/grid/properties/report`-Aufruf live für die aktuelle simulierte Uhrzeit
(`simMinute`) neu berechnet wird.

**Aufbau der Formel:**
1. `dayW` – ein Sigmoid-Übergang, der zwischen Nacht (~0) und Tag (~1) weich
   blendet, Übergänge bei 06:00/22:00
2. `lower`/`upper` – Leistungsgrenzen, die zwischen Nacht (150–300 W) und
   Tag (300–3000 W) interpoliert werden
3. `base` – ein Sockel bei 30 % der Tagesspanne
4. `peaks` – drei Gauß-Glocken für Morgen (07:12), Mittag (12:30), Abend
   (19:00) – simulieren Frühstück/Kochen/Abendspitze
5. `LOAD_SCALE` – Skalierungsfaktor (Env-Var), multipliziert alles

**Wichtige Eigenschaften:**
- **Deterministisch** – bei gleichem `simMinute`/`LOAD_SCALE` kommt immer
  derselbe Wert raus (kein Zufall, kein Seed nötig) → Testläufe sind
  reproduzierbar
- **Unabhängig von der PV-/SOC-Simulation der Geräte** – reiner
  Funktionsaufruf, kein Zustand, keine Rückkopplung von den Batterien auf
  den Haushalt

Falls **reale Messdaten** (z. B. euer tatsächlicher Hausverbrauch als CSV)
statt der synthetischen Kurve gewünscht sind: `householdLoad()` lässt sich
leicht so umbauen, dass sie stattdessen Werte aus einer CSV-Datei
interpoliert.

## Bekannte Vereinfachungen des Mocks

- PV-Ladeleistung wird nicht durch ein separates Hardware-Limit gedeckelt
  (nur durch Batterie-Headroom) – reale Geräte könnten hier einen PV-Input-
  Cap haben, der nicht bekannt ist
- Kein Lade-/Entlade-Wirkungsgrad (100 % angenommen, real ~90–95 %)
- Keine Rampzeiten – `outputLimit`/`inputLimit` wirkt sofort und vollständig
- `directionChangeHoldCycles`/Hysterese-Skip werden vom Original-Skript
  selbst gehandhabt (nicht vom Mock) – das ist beabsichtigt, genau das soll
  ja mitgetestet werden
- Mock antwortet immer sofort fehlerfrei – keine simulierten Timeouts/Fehler

## Offene Erweiterungen (angeboten, noch nicht gebaut)

- **Mehr als 2 Geräte**: Mock ist aktuell hart auf `dev0`/`dev1` verdrahtet.
  Für eine generische Geräteliste (analog `CONFIG.devices` im Original)
  müsste `mock_server.js` umgebaut werden.
- **Reale Lastdaten statt Formel**: `householdLoad()` könnte aus einer CSV
  interpolieren statt synthetisch zu rechnen.
- **Künstliche Fehler/Timeouts im Mock**: um `reportError`/Watchdog-Pfade
  gezielt zu testen (aktuell nicht abgedeckt, siehe "Warum zuverlässig").

  ## Testdatenkurven
  
  <img width="1500" height="1125" alt="image" src="https://github.com/user-attachments/assets/cd95b21d-4481-4a06-a2aa-7ef8d5bf2098" />

  ### Einsatz von LOAD_SCALE
  <img width="1500" height="675" alt="image" src="https://github.com/user-attachments/assets/552e5a88-afd2-44c5-a442-2fcb4f93628f" />