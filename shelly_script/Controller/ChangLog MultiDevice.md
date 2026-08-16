# Changelog *Major Change*
ab hier beginnt eigene Releasestrecke für den Controller

Codebase: https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Controller/zerooutput_multi_kvs_mini

Eine Weiterentwicklung kann nur erfolgen unter Nutzung von **Minify**, da die Script-Engine nur js-Scripte bis 50kB zulässt.
Mit einem **Terser** werden alle unnötigen Leerzeichen, Zeilenumbrüche und Kommentare aus dem Code entfernt. Dies kann auch ein Python-Script erledigen.
siehe: https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/minify_keep_config.py
Die Kürzungen sind erheblich Einsparungen bis zu 50% sind möglich.


# Changelog 3.1.1

Bezugnahme ist 
* https://github.com/surfer1264/Zendure-Stuff/issues/80
* https://github.com/surfer1264/Zendure-Stuff/issues/81


Der Konfigurationsparamteer `revers: true/false`steuert die AC-Ladefähigkeit der Solarflow im Controller.

Der Geräteparameter `gridRevers`steuert die Fähigkeit des Solarflow den Export von Überschussenergie zu erlauben oder zu verbieten.

Beide Parameter haben inhaltlich keine Berührungspunkte, waren im Code aber in einer Abhängigkeit verbunden. Die wurde aufgelöst.

**Problem:** Ein Gerät mit `reverse: false` hätte zwar Energie exportieren können, wurde aber von der Steuerung mit `gridReveers`ausgeschlossen.  


### Entfernt: `excessSocLimit1`-Korrekturterm

Solarflows folgen den Vorgaben des Controllers im Bypass Fall nicht ....
Es wird nicht nur die Entladeleistung gliefert sondern der gesamte PV-Überschuss, der zum Laden eines AC-ladefähigen Hubs dienen kann.

**Problem:** Der Überschusswert wurde defacto "doppelt" angerechnet. Ein AC-ladefähiges Gerät bekam damit im Zweifel den doppelten Ladebefehl. Je nach Gerätekonstellation konnte das sogar zu extra Netzbezug führen.


### Neu: Zustandserkennung beim Start

**Problem:** In einem Testfall war `gridRevers: 2` (Exportsperre aktiv). Nach Scriptstart wurde die Sperre nicht aufgehoben, obwohl alle Voraussetzungen erfüllt waren.
- In `syncSocLimitsDevice()` (einmalig beim Boot) wird jetzt geprüft: `if (data.properties && data.properties.gridReverse === 2) state.allMaxedLogged = true;`
- Damit erkennt der Controller nach einem Neustart sofort, wenn ein Gerät bereits mit `gridReverse: 2` (Netzexport verboten) läuft, statt diesen Zustand erst nach einer vollen Regelrunde (Stunden später) neu herzuleiten.
- Defacto wird die Prüfung durch Setzen des Status `state.allMaxedLogged = true` quasi erzwungen.

## Fazit

v3.1.1 ist im Kern ein **Bugfix-Release**: Die Kopplung von `reverse` (Geräteeigenschaft: darf vom Netz laden) an die fleet-weite `gridReverse`-Steuerung (Geräteeigenschaft: darf bei Ladesperre noch Netzexport machen) wurde entfernt. Beide Mechanismen laufen jetzt, wie beschrieben, komplett unabhängig voneinander – `socLimit` bestimmt allein, wann fleet-weit gesperrt/freigegeben wird, `reverse` bestimmt weiterhin ausschließlich, wie die Ladeleistung auf die Geräte verteilt wird.



# Changelog 3.0.3
Update Logging, siehe Kapitel 12 Gesamtdoku

Codebase: https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Controller/zerooutput_multi_kvs.js

# Changelog 3.0.2
Bei Neustart des Scriptes wird die Reinitialisierung des Status von GridR auf den Wert 1 (Export erlaubt) forciert.

**Hintergrund:** externe Zugriffe auf die Konfiguration des Solatflows (durch HA oder durch die Zendure App) korrumpieren ggf. den Zustand
Ein Neustart kann das beheben.

**Wichtig** Im laufenden Betrieb des Controllers findet KEINE Synchronisation von Einstellugnen statt mit dem Solarflow statt.

Bezugnahme ist 
* https://github.com/surfer1264/Zendure-Stuff/issues/80

Es is kein Fix im eigentlichen Sinne, der Zustand bildet sich im Controller automatisch über die Zeit korrekt ab.

# Changelog 3.0.1

**Sperren** (gridReverse: 2, bei allMaxed) bleibt in computeChargeWeights() – läuft weiterhin im Charge-Kontext, wo der Übergang zuverlässig erkannt wird.

**Freigeben** (gridReverse: 1, bei clearlyBelow) wurde von computeChargeWeights() nach distributeDischarge() verschoben.

**Grund:** Die Freigabe hing zuvor an chargeTarget < 0 – bei aktiver Export-Sperre wird jedoch im Zweifel kein Ladebefehl mehr ausgelöst (nur durch starkes Überschwingen an der Regelung), wodurch dieser Zweig nicht deterministisch erreicht wird, sondern eher zufällig. Der Discharge-Zweig läuft dagegen zuverlässig, solange Haushaltslast gedeckt wird. Beide Zweige behalten ihren Flankenschutz (state.allMaxedLogged).

Fixed:
* https://github.com/surfer1264/Zendure-Stuff/issues/79

httpTimeOut: 3 (vorher 5)

# Changelog 3.0.0
Dokumentation aktualisiert

# Changelog 2.4.5
`gridReverse` wird ins Log aufgenommen
`gridReverse` aktiv zur Laufzeit zwischen `1 (Export erlaubt)` und `2 (Export gesperrt)`

Logzeile:

`  SF2400: SOC 45% | socL 0 | gridR 2 | Ist 195 W | Soll 195 W | acMode 2 (Export)`

Zweck: `grid_Reverse` ist eine Geräte-Property, die steuert, ob das Zendure-Gerät (Überschuss-)Energie exportieren darf.

Werte, die der Controller selbst setzt:

- Wert 1:	Export erlaubt/aktiviert	
  - a) beim initialen SoC-Sync, wenn immerBypass: true (Zeile ~1593), dauerhaft freigegeben, danach nie wieder verändert.
  - b) wenn nach einer Vollsperre (allMaxed) mind. ein Gerät wieder klar unter seinem maxSoc − chargeResetMargin liegt (clearlyBelow) – nur bei `immerBypass: false`
- Wert 2:	Export gesperrt	wenn alle Geräte ihren maxSoc erreicht haben (allMaxed) – nur bei `immerBypass: false`, um unnötigen Export zu verhindern.

Wenn `immerBypass: true` findet kein aktives Schreiben oder Initalisieren dieses Wertes statt.




# Changelog 2.4.4

- CONFIG.httpTimeout als Parameter entfernt (wird im Code hhtpGet und httpPost als fester Wert mitgegeben)) 
- CONFIG.watchdog wird als abgeleiteter Wert von intervall (Faktor 2.5) definiert und ist nicht mehr veränderbar

# Changelog 2.4.3
Feature Toggle `compensateSocLimitExcess`entfernt...keine Funktionsänderung


# Changelog 2.4.2

**Geändert (Defaults)**
* `compensateSocLimitExcess`: Default von false auf true geändert.
* `hysteresis`: Default von 10 auf 12 W erhöht.
* `dampingFactor`: Default von 0.6 auf 0.65 erhöht.
* Grid-Log gerundet: Die Log-Zeile Grid: ... W gibt state.gridPower jetzt gerundet aus (Math.round(...)) statt mit Nachkommastellen.

**Neu hinzugefügt**
* Neue Banner-Zeile beim Start: Bypass immer erlauben: aktiviert/deaktiviert.


# Changelog 2.4.0

**Feature**: Hub-seitige GridReverse-Steuerung ("Bypass-Verhalten")

Die Solarflow-Firmware besitzt einen eigenen Schalter `gridReverse` (0/1/2) auf Hub-Ebene. Er steuert nicht das Laden vom Netz, sondern ob der Hub im Bypass-Betrieb (Akku voll, PV-Überschuss wird direkt durchgereicht) Energie ins Netz exportieren darf - betrifft also den Export-Zweig (outputLimit), unabhängig von der script-internen Ladeverteilung.

**Änderung**

- Neuer **CONFIG-Schalter** immerBypass (Default: false) steuert, ob das Feature aktiv genutzt wird:
  - **true**: gridReverse wird nur einmalig beim Start auf 1 (Export erlaubt) gesetzt, danach nie mehr verändert - kein Laufzeit-Effekt, geringstes Risiko.
  - **false** (Default): Script schaltet `gridReverse` aktiv zur Laufzeit zwischen `1 (Export erlaubt)` und `2 (Export gesperrt)` um.
- Neuer CONFIG-Parameter chargeResetMargin (Default: 5 Prozentpunkte) - Hysterese-Abstand unterhalb maxSoc, den mindestens ein Gerät unterschreiten muss, bevor eine gesetzte Sperre wieder aufgehoben wird.

**Codeänderung**
computeChargeWeights() erweitert: erkennt, wenn kein reverse:true-Gerät mehr Lade-Kapazität hat (allMaxed, d. h. Bypass-Betrieb droht) und löst darüber gridReverse=2 (Export gesperrt) aus; erkennt zusätzlich, wenn mindestens ein Gerät klar unter die Reset-Marge gefallen ist (clearlyBelow) und setzt gridReverse=1 (Export erlaubt) zurück. Beide Übergänge sind flankengetriggert (state.allMaxedLogged) - kein wiederholtes Schreiben pro Zyklus, schont den Flash-Speicher der Hubs.
Neue Funktionen setGridReverseDevice()/setGridReverseAll() kapseln den properties/write-Aufruf; nur Geräte mit reverse:true werden angefasst, dryRun-Geräte werden übersprungen.
syncSocLimitsDevice(): Bei immerBypass:true wird gridReverse:1 direkt in denselben properties/write-Aufruf wie minSoc/socSet gepackt (ein Request statt zwei separater Schreibvorgänge beim Start).
state.devices[i].gridReverse (zuletzt geschriebener Wert) und state.allMaxedLogged (Flankenerkennung) neu ergänzt.
Debug-Diagnose bei fehlgeschlagenem Schreibvorgang (DEBUG [Label]/gridReverse - res: ... | error_code: ... | error_message: ...), analog zu den bestehenden Schreibvorgängen (writeDevice, syncSocLimitsDevice).

Nicht per KVS live-überschreibbar: immerBypass/chargeResetMargin sind reine CONFIG-Werte, aktuell ohne Live-Override-Key.

# Changelog 2.3.3

**Problem**: Wenn in einer MultiDevice-Konfig ein Gerät bereits auf 100% (Bypass) stand, wurde der Überschuss genau dieses Gerätes nicht mehr aktiv auf die verbleibenden Geräte aufgeteilt

**Änderung** Feature-Toggle compensateSocLimitExcess (neuer CONFIG-Schalter, Default: true). 
Kompensiert beim Laden (rawCharge) die Leistung von Geräten, die socLimit === 1 melden und ein outputLimit gesetzt haben: der Überschuss (zenPower - outputLimit, wenn > 0) wird über alle betroffenen Geräte aufsummiert (excessSocLimit1) und von rawCharge abgezogen.
Alt: rawCharge = round((gridPower - setpoint) + sumZenReverse)
Neu: rawCharge = round((gridPower - setpoint) + sumZenReverse - excessSocLimit1)
kann deaktiviert werden, der FIx wird dadurch deaktiviert


# Changelog 2.3.2

## Konstellationen mit ≥2 reverse:true-Geräten (mit eigener PV)

**Problem**
- keine Überschussverarbeitung in PV-enabled Geräten
- Betrifft Konstellationen mit ≥2 `reverse:true`-Geräten, bei denen mindestens eines direkt angeschlossene PV-Module hat.
- `sumZenReverse` schloss Geräte mit `socLimit === 1` (Laden vom Netz gesperrt) bisher nicht aus. Dadurch konnte die unsteuerbare, PV-erzwungene Weiterausspeisung eines an seiner SOC-Grenze blockierten Speichers einen echten Ladebedarf bei anderen, noch ladefähigen Geräten maskieren – der Regler berechnete fälschlich weiter einen positiven Entlade-Zielwert, statt Laden auszulösen.


**Änderung**
- `calculate()`: `sumZenReverse` prüft zusätzlich `state.devices[i].socLimit !== 1`, analog zur bereits bestehenden Filterung in `computeChargeWeights()`.
- Fetaure Toggle `compensateSocLimitExcess`

**Adressierte Bugs:**
* https://github.com/surfer1264/Zendure-Stuff/issues/69


# Changelog 2.3.1
## Konstellationen Mischung aus reverse:true- und reverse:false Geräten (keine Überschussannahme)

**Effekt:** Ein netzladefähiges Gerät (`reverse:true`) kann jetzt im selben Zyklus laden, während andere Geräte (`reverse:false`, z.B. PV-gekoppelte Entlader) unverändert weiter exportieren – vorher hat der jeweils "verlierende" Zweig alle Geräte per `zeroOutputs()` auf 0 gezwungen.

**Sonst nichts geändert:** `concentrateBelow`/`spreadAbove`, SOC-Balancing, Cooldown, socLimit-Handling, KVS-Logik – alles 1:1 wie in 2.3.0. Bei einer reinen "alle Geräte `reverse:true`"-Flotte ist `sumZenReverse === sumZen`, also verhält sich 2.3.1 dort exakt wie 2.3.0 (kein Regressionsrisiko).

**Adressierte Bugs:**
* https://github.com/surfer1264/Zendure-Stuff/issues/56
* https://github.com/surfer1264/Zendure-Stuff/issues/52


1. **Neue Variable `sumZenReverse`** – zählt beim Einlesen der Geräte zusätzlich zur bisherigen `sumZen` (alle Geräte) eine zweite Summe **nur** für Geräte mit `reverse:true`.

2. **Zwei getrennte Zielsignale statt einem:**
   ```js
   dischargeTarget = gridPower + sumZen          // wie bisher, unveraendert
   chargeTarget     = gridPower + sumZenReverse   // NEU
   ```
   Dazu eine zweite, eigene Glättung (`state.smoothedCharge` statt nur `state.smoothedOutput`).

3. **`calculate()` berechnet jetzt beide Pools im selben Zyklus** statt sich per `if/else` für genau eine Richtung zu entscheiden:
   - Lade-Pool zuerst (`distributeCharge(chargeTarget)`), Geräte die dabei laden landen in `chargeExclude`
   - Entlade-Pool danach (`distributeDischarge(dischargeTarget, chargeExclude)`) – **mit** dem neuen zweiten Parameter, der die gerade ladenden Geräte ausschließt
   - Ergebnis wird gemerged: `output[i] = chargeOutput[i] || dischargeOutput[i]`

4. **`computeDischargeWeights()` und `distributeDischarge()`** bekommen dafür einen neuen optionalen `exclude`-Parameter.


# Changelog 3.0.1 (VERWORFEN)
## 1. dryRun-Feature komplett entfernt

**Hintergrund**: Seicher zur Laufzeit sparen

Lasttests zeigen aber Lauffähigkeit auf 
* Shelly 3EM Pro
* Shelly 3EM-63
* Shelly 1PM Gen4
* Shelly Plus1PM (Gen2?)

3.0.1 entspricht ansonsten inhaltlich der 2.3.0

# ChangeLog 2.3.0
**Kurz zusammengefasst:** Die wichtigste inhaltliche Änderung ist, dass 2.3.0 dem Gerät selbst vertraut (`socLimit`), statt SOC-Grenzen rein lokal zu berechnen, und dass der Richtungswechsel-Schutz von einer zeitbasierten "letzte-Richtung-halten"-Logik auf eine zyklenbasierte "erzwungener Standby"-Logik umgestellt wurde. Dazu kommt der neue `standbySmartModeZero`-Schalter und der Wegfall der Live-Überschreibbarkeit von `hysteresis`/`dampingFactor` per KVS.

## 1. SOC-Sperre kommt jetzt vom Gerät (`socLimit`) statt lokal berechnet
- **Alt:** `ds.atMaxSoc = (ds.soc >= cfg.maxSoc)` – lokal aus dem konfigurierten `maxSoc` berechnet.
- **Neu:** Liest `data.properties.socLimit` direkt vom Zendure-Gerät (0 = frei, 1 = Laden gesperrt, 2 = Entladen gesperrt), loggt Änderungen und nutzt es aktiv:
  - `computeDischargeWeights()`: Entladen wird zusätzlich blockiert, wenn `socLimit === 2`
  - `computeChargeWeights()`: Laden wird zusätzlich blockiert, wenn `socLimit === 1`
  - Das ist eine echte Verhaltensänderung – vorher zählte nur der lokal konfigurierte `maxSoc`, jetzt zählt auch, was das Gerät selbst meldet.

## 2. Richtungswechsel-Schutz komplett umgebaut
- **Alt:** `directionChangeCooldown` (Millisekunden, zeitbasiert). Bei Richtungswechsel wurde einfach der letzte `acMode` beibehalten und die Leistung auf 0 gesetzt, bis die Cooldown-Zeit abgelaufen war.
- **Neu:** `directionChangeHoldCycles` (Anzahl Regelzyklen statt Zeit). Es gibt jetzt `realDirection` (nur bei tatsächlich geschriebener Leistung ≠ 0 aktualisiert) und `reversalHoldCount`. Bei Richtungswechsel wird das Gerät für N Zyklen in einen expliziten **Standby-Plan** gezwungen (`acMode:1, outputLimit:0, inputLimit:0`), nicht mehr in die alte Richtung.
- Die Sanity-Checks am Anfang wurden entsprechend ersetzt (Clamp auf 0–20 Zyklen statt der alten ms-Clamps).

## 3. Neuer Parameter `standbySmartModeZero`
- Steuert, welcher `smartMode` (0 oder 1) beim Schreiben von 0 W (Standby) verwendet wird. Vorher war `smartMode` beim Schreiben **immer fest auf 1** gesetzt.
- `planWrite()` liefert jetzt auch `smartMode` als Teil des Plans zurück (vorher nur `acMode`/`outputLimit`/`inputLimit`).
- Erzwingt das Standby bei einigen Geräten (2400AC), die mit `smartmode: 1` partout nicht in den Standby gehen

## 4. KVS-Live-Override für `hysteresis` und `dampingFactor` entfernt
- In 2.2.0 konnten `zdmc_hysteresis` und `zdmc_dampingFactor` per KVS live überschrieben werden (inkl. Seeding der Default-Werte).
- In 2.3.0 sind diese beiden Blöcke sowohl aus `readKvsOverrides()` als auch aus `seedKvsDefaults()` entfernt. Nur noch `setpoint` sowie `dev{n}_dischargeAllowed`/`dev{n}_reverse` sind live überschreibbar.

## 5. `applyOutputs()` / `writeDevice()` refactored
- **Alt:** `writeDevice()` hat `planWrite()` und `enforceDirectionCooldown()` beim eigentlichen Schreiben **erneut** ausgeführt (mit frischem `Date.now()`), losgelöst von der Vorschau in `applyOutputs()`.
- **Neu:** Der Plan wird einmal in `applyOutputs()` berechnet, in einem `plans`-Array zwischengespeichert und an `writeDevice()`/`writeAllDevices()` durchgereicht – Vorschau und tatsächlicher Schreibvorgang benutzen garantiert denselben Plan.
- Die Hysterese-Skip-Bedingung ist strenger geworden: Ein Schreibvorgang wird jetzt auch dann ausgelöst, wenn sich `acMode` oder `smartMode` ändern, selbst wenn sich die Leistung kaum ändert (vorher wurde nur die Leistungsdifferenz gegen `CONFIG.hysteresis` geprüft).

## 6. `state.devices[i]`-Struktur geändert
- Entfernt: `atMaxSoc`, `acModeChangedAt`
- Neu: `socLimit`, `smartMode`, `realDirection`, `reversalHoldCount`

## 7. Banner-Ausgabe passend angepasst
- „Richtungswechsel-Cooldown: X s" → „Richtungswechsel-Bremse: X Takt(e)"
- KVS-Zeile nennt nur noch `setpoint`/`dev{n}_dischargeAllowed`/`dev{n}_reverse` (kein `hysteresis`/`dampingFactor` mehr)

---


# 2.2.0 Initiale Version
