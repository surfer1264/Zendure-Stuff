# Changelog 2.4.0

**Feature**: Hub-seitige GridReverse-Steuerung ("Bypass-Verhalten")

Die Solarflow-Firmware besitzt einen eigenen Schalter gridReverse (0/1/2) auf Hub-Ebene. Er steuert nicht das Laden vom Netz, sondern ob der Hub im Bypass-Betrieb (Akku voll, PV-Überschuss wird direkt durchgereicht) Energie ins Netz exportieren darf - betrifft also den Export-Zweig (outputLimit), unabhängig von der script-internen Ladeverteilung.

**Änderung**

- Neuer **CONFIG-Schalter** immerBypass (Default: false) steuert, ob das Feature aktiv genutzt wird:
  - **true**: gridReverse wird nur einmalig beim Start auf 1 (Export erlaubt) gesetzt, danach nie mehr verändert - kein Laufzeit-Effekt, geringstes Risiko.
  - **false** (Default): Script schaltet `gridReverse` aktiv zur Laufzeit zwischen 1 (Export erlaubt) und 2 (Export gesperrt) um.
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
