# Controller – Kernfunktionen

Der Controller ist ein Shelly-Script (JavaScript) für **Shelly Gen2/3/4-Geräte**. Er regelt den Netzbezug auf nahe 0 W (Nulleinspeisung) und verteilt die Lade- und Entladeleistung auf **einen oder mehrere Zendure-Speicher** mit zenSDK-Schnittstelle (SF800 und neuer, siehe [Kompatible Geräte](../kompatible_geraete.md)).

Diese Seite gibt einen Überblick. Alle Details stehen in der [Gesamtdokumentation](gesamtdoku.md).

---

## 1. Hauptzweck und Funktionsweise

Das Script bildet eine geschlossene Regelschleife:

1. **Netzsaldo lesen:** Es fragt fortlaufend den aktuellen Netzsaldo (Bezug/Export in Watt) ab – vom lokalen oder entfernten Shelly Pro 3EM oder von einem HTTP-JSON-Zähler wie dem Zendure Smart Meter 3CT ([Kapitel 5](gesamtdoku.md#5-smartmeter-anbindung---die-drei-grid-quellen-im-überblick)).
2. **Ziel berechnen:** Es ermittelt getrennt für Entladen und Laden, wie viel Leistung nötig ist, um den Netzpunkt auf den Sollwert `setpoint` (meist 0 W) zu bringen ([Kapitel 8.1](gesamtdoku.md#81-ablauf-eines-regelzyklus)).
3. **Auf Geräte verteilen:** Nach Ladestand (SOC), Gerätegrenzen (`maxOutput`/`maxInputPower`, `minSoc`/`maxSoc`) und den Schwellen `concentrateBelow`/`spreadAbove` verteilt es die Leistung auf die Zendure-Geräte. Feste Prioritäten gibt es nicht.
4. **Per HTTP-API steuern:** Die Sollwerte (`acMode`, `outputLimit`, `inputLimit`, `smartMode`) gehen per lokalem HTTP-POST direkt an die Geräte – ohne Cloud.

---

## 2. Kernfunktionen

### A. Lastverteilung beim Entladen und Laden

- **Ein Gerät oder alle** ([Kapitel 7](gesamtdoku.md#7-lastaufteilung--wie-wirken-concentratebelow-und-spreadabove)):
    - Bei kleinem Bedarf (unter `concentrateBelow`, Standard 600 W) arbeitet **nur ein** Gerät. Das spart Wandlungsverluste und Schreibzugriffe.
    - Bei größerem Bedarf (über `spreadAbove`, Standard 800 W) oder wenn das aktive Gerät an seine Leistungsgrenze stößt, wird auf alle verfügbaren Geräte verteilt („Wasserfüllung“).
- **Ausgleich der Ladestände** ([Kapitel 6c](gesamtdoku.md#6c-sanfter-ausgleich-rebalance)):
    - Beim Entladen tragen Geräte mit höherem SOC mehr bei, beim Laden Geräte mit mehr freiem Platz.
    - Hat ein anderes Gerät einen Vorsprung von mindestens `rebalance.socMargin` (Standard 5 Prozentpunkte), wechselt im Ein-Geräte-Betrieb das aktive Gerät.

### B. Regelung und Dämpfung

- **Asymmetrische Dämpfung** ([Kapitel 8.2](gesamtdoku.md#82-dämpfung-der-lade-entladesignale)):
    - Das Regelsignal folgt gedämpft mit `dampingFactor` (Standard 0,65). Das verhindert Überschwingen.
    - Nur bei einem Sprung größer `JUMP_THRESHOLD` in Richtung „weniger Export“ (z. B. Wasserkocher aus) greift die schnelle Flanke `jumpFactor` (Standard 0,9). So bleibt ungewollte Einspeisung kurz.
- **Hysterese** ([Kapitel 8.9](gesamtdoku.md#89-startstop-hysterese-laden--entladen)):
    - Geschrieben wird erst ab einer Änderung von `hysteresis` (Standard 12 W).
    - An den SoC-Grenzen verhindern `dischargeResetMargin` und `chargeResetMargin` das Flattern zwischen Standby und Betrieb.

### C. Schutz für Geräte und Script

- **Richtungswechsel-Bremse** (`directionChangeHoldCycles`, [Kapitel 8.10](gesamtdoku.md#810-richtungswechsel-bremse-beispiel)): Beim Wechsel zwischen Laden und Entladen hält das Gerät einige Zyklen Standby. Das verhindert schnelles Hin- und Herschalten.
- **`smartMode` 0 erst nach längerem Standby** (optional, [Kapitel 8.11](gesamtdoku.md#811-bedeutung-von-smartmode-0-vs-1)): Mit `standbySmartModeZero: true` schreibt das Script `smartMode: 0` erst nach 15 Standby-Zyklen in Folge. Kurze Nulldurchgänge lösen so keine Flash-Schreibvorgänge im Gerät aus. Standard ist `false`.
- **Watchdog** ([Kapitel 8.3](gesamtdoku.md#83-watchdog--timer)): Bleibt ein Regelzyklus hängen, gibt der Watchdog (`interval` × 2,5) die Zyklussperre frei und meldet den Fehler.
- **Fehlerzähler** ([Kapitel 8.4](gesamtdoku.md#84-fehlerzähler--benachrichtigung)): Nach `errorThreshold` (Standard 6) Fehlern in Folge wird eine Benachrichtigung verschickt.
- **`safeCall()`** ([Kapitel 10](gesamtdoku.md#10-hinweis-performance-grenzen-und-status-prüfung-des-shelly)): Ist der Call-Pool des Shelly voll („Too many calls in progress“), wird der Fehler abgefangen und der Zyklus endet sauber.

### D. Shelly-gerechte Performance und Speichernutzung

- **Sparmodus** (`idleSkip`, [Kapitel 8.12](gesamtdoku.md#812-adaptives-polling--sparmodus-idleskip)): Bleibt der berechnete Output `cyclesUnchanged` (Standard 4) Zyklen lang innerhalb der Hysterese, setzt das Script die Abfrage der Zendure-Geräte für bis zu `maxSkipSeconds` (Standard 44 s) aus. Die Netzmessung läuft in jedem Zyklus weiter.
- **Speicher** ([Kapitel 8.7](gesamtdoku.md#87-startprotokoll-banner)):
    - Banner-Texte und Start-Funktionen werden nach dem Start auf `null` gesetzt und freigegeben.
    - HTTP-Antworten werden direkt nach dem Parsen verworfen (`res = null`). Das senkt Speicherspitzen.
- **Abfragereihenfolge** (`buildPollOrder()`, [Kapitel 8.1](gesamtdoku.md#81-ablauf-eines-regelzyklus)): Zuerst werden die Geräte abgefragt, die gerade nicht regeln, zuletzt das regelnde Gerät, direkt vor dem Smartmeter. So passen Ist-Leistung und Netzwert zeitlich zusammen.

### E. Schnittstellen

- **Live-Einstellungen per KVS** ([Kapitel 13](gesamtdoku.md#13-live-override-der-regelparameter-per-kvs-z-b-home-assistant)):
    - Werte wie `setpoint`, `dischargeFixed`, `minSoc` oder `inputLimit` lassen sich im laufenden Betrieb ändern, ohne Neustart des Scripts.
    - Das Script reagiert ereignisgesteuert auf Änderungen von `kvs_rev`, statt den KVS zyklisch abzufragen.
- **Benachrichtigungen** (`signal`, [Kapitel 8.5](gesamtdoku.md#85-signal-benachrichtigung-callmebot--inkl-whatsapp)): per Signal oder WhatsApp (über CallMeBot) oder per Webhook (z. B. Home Assistant).

---

## 3. Weitere Funktionen

| Funktion | Umsetzung im Script | Wirkung |
| --- | --- | --- |
| **Bypass-Korrektur** | `applyBypassExcessCorrection()` | Liefert ein ladegesperrtes Gerät (`socLimit = 1`, PV-Durchleitung) mehr Leistung als zugeteilt, wird der Überschuss von den übrigen Geräten abgezogen ([Kapitel 6e](gesamtdoku.md#6e-bypass-überschuss-korrektur-soclimit--1)). |
| **Manuelles AC-Laden** | `syncInputLimitDevice()` | Ein per KVS gesetztes `inputLimit` erzwingt Laden aus dem Netz mit fester Leistung. Für dieses Gerät pausiert die Regelung so lange ([Kapitel 13.4](gesamtdoku.md#134-live-überschreibbare-werte)). |
| **Testmodus** | `dryRun: true` pro Gerät | Das Script liest und rechnet mit echten Daten, schreibt aber nichts an das Gerät ([Kapitel 4c](gesamtdoku.md#4c-testmodus-dryrun)). |

---

## Fazit

Der Controller ist auf die Grenzen der Shelly-Script-Engine ausgelegt (wenig Arbeitsspeicher, begrenzter Call-Pool). Gleichzeitig schont er die Zendure-Geräte: Hysterese, Richtungswechsel-Bremse und Sparmodus vermeiden unnötige Schreibzugriffe und Umschaltvorgänge.
