# Chamglog 3.0.1
## 1. dryRun-Feature komplett entfernt

**Hintergrund**: Seicher zur Laufzeit sparen

Kein **dryRun-Feld** mehr in der Geräte-Konfiguration
applyOutputs(): Der komplette DRYRUN-Zweig ist weg – vorher wurde bei cfg.dryRun === true nur simuliert (ds.acMode/ds.outputLimit intern aktualisiert, aber kein HTTP-Write ausgeführt). Jetzt landet jedes Gerät ohne Ausnahme in toWrite und wird tatsächlich geschrieben.
syncSocLimitsDevice(): Der DRYRUN-Skip beim SoC-Grenzwert-Sync ist ebenfalls weg – minSoc/maxSoc werden jetzt beim Start immer ans Gerät geschrieben.
Print-Ausgaben: „[DRYRUN - wird nicht geschrieben]" (Vorschau) und „[DRYRUN]" (Banner-Zeile) sind entfernt.

➡️ Praktisch heißt das: Es gibt in 3.0.1 keine Möglichkeit mehr, den Regler im reinen Simulationsmodus laufen zu lassen, ohne dass tatsächlich ans Gerät geschrieben wird. Wer testen will, muss das jetzt anders absichern (z. B. übers Netzwerk isolieren oder Geräte-IP auf etwas Ungefährliches zeigen lassen).

Sonst keine Logikänderungen

# ChangeLog 2.3.0
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

**Kurz zusammengefasst:** Die wichtigste inhaltliche Änderung ist, dass 2.3.0 dem Gerät selbst vertraut (`socLimit`), statt SOC-Grenzen rein lokal zu berechnen, und dass der Richtungswechsel-Schutz von einer zeitbasierten "letzte-Richtung-halten"-Logik auf eine zyklenbasierte "erzwungener Standby"-Logik umgestellt wurde. Dazu kommt der neue `standbySmartModeZero`-Schalter und der Wegfall der Live-Überschreibbarkeit von `hysteresis`/`dampingFactor` per KVS.

# 2.2.0 Initiale Version