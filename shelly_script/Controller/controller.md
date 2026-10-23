Dieses JavaScript-Skript ist ein Steuerungsskript (mJS) für **Shelly-Geräte** (wie den Shelly Pro 3EM oder Shelly Plus/Pro Serie). Es dient zur dynamischen Nulleinspeiseregelung und Lastverteilung von **mehreren Zendure-Balkonkraftwerk-Speichersystemen** (z. B. Zendure SolarFlow / Hyper / SF2400).

Eine gründliche Analyse der Architektur, Kernfunktionen und Steuerungslogik des Skripts zeigt Folgendes:

---

### 1. Hauptzweck und Funktionsweise

Das Skript bildet eine geschlossene Regelschleife:

1. **Grid-Power lesen:** Es fragt fortlaufend den aktuellen Netzsaldo (Import/Export in Watt) ab (entweder von einem lokalen/entfernten Shelly Pro 3EM oder einem anderen HTTP-JSON-Zähler/Zendure 3CT).
2. **Zielwert berechnen:** Es ermittelt, wie viel Leistung geladen oder entladen werden muss, um den Strombezug bzw. die Einspeisung am Netzverknüpfungspunkt auf nahe **0 Watt** (oder einen konfigurierbaren Sollwert `setpoint`) zu regeln.
3. **Auf Geräte verteilen:** Basierend auf Akkustand (SOC), Kapazität, Prioritäten und Schwellenwerten verteilt es die Lade- bzw. Entladeleistung dynamisch auf die konfigurierten Zendure-Geräte.
4. **Per HTTP-API steuern:** Die berechneten Sollwerte (`acMode`, `outputLimit`, `inputLimit`, `smartMode`) werden per lokalen HTTP-POST-Requests direkt an die Zendure-Geräte übertragen.

---

### 2. Kernfunktionen und Features

#### A. Intelligente Lastverteilung (Discharge & Charge)

* **Single vs. Spread Mode:**
* Bei geringem Leistungsbedarf (unter `concentrateBelow`, z. B. < 600 W) steuert das Skript bevorzugt **nur ein** Gerät an, um Wandlungsverluste zu minimieren und Geräte zu schonen.
* Erst bei höherem Bedarf (über `spreadAbove`, z. B. > 800 W) oder wenn ein Gerät an seine Leistungsgrenze stößt, wird die Last auf mehrere/alle Geräte aufgeteilt (Water-Fill-Algorithmus).


* **SOC-Balancing & Rebalancing:**
* Geräte mit höherem Akkustand entladen bevorzugt.
* Geräte mit niedrigerem Akkustand laden bevorzugt.
* Unterscheiden sich die SOC-Werte zweier Geräte um mehr als `rebalance.socMargin` (z. B. 5 %), wechselt das Skript das primäre Gerät im Single-Modus.



#### B. Regelungstechnik & Dämpfung

* **Asymmetrische Dämpfung (`dampingFactor` / `jumpFactor`):**
* Verhindert Überschwingen und Schwingungen im Regelkreis.
* Standardverstärkung liegt bei `0.65`.
* Bei plötzlichen Änderungen in Richtung weniger Einspeisung greift eine schnellere Flanke (`jumpFactor: 0.9`), sobald ein Schwellenwert (`JUMP_THRESHOLD`) überschritten wird, um Netzbezug oder ungewollte Einspeisung schnell abzufangen.


* **Hysterese und Totzonen:**
* Verhindert ständiges Nachregeln/Schreiben bei minimalen Schwankungen (`hysteresis: 12W`).
* Schutz vor Zyklen-Flattern an den Grenzen von `minSoc` und `maxSoc` über Hysteresewerte (`dischargeResetMargin` / `chargeResetMargin`).



#### C. Geräte- & System-Schutzmechanismen

* **Richtungswechsel-Sperre (`directionChangeHoldCycles`):**
* Erzwingt eine Pause (Standby) von einigen Zyklen beim Umschalten zwischen Laden und Entladen, um Relais und Leistungselektronik der Wechselrichter zu schonen.


* **Standby SmartMode Zero Delay:**
* Schaltet `smartMode` erst nach `15` aufeinanderfolgenden Standby-Zyklen auf `0`, um unnötige EEPROM/Flash-Schreibzugriffe bei kurzen Nulldurchgängen zu vermeiden.


* **Watchdog & Fehler-Handling:**
* Überwacht die Ausführungszeit eines Regeltakts. Bleibt ein Aufruf hängen, greift ein Watchdog-Timer, setzt den Zustand zurück und meldet den Fehler.
* Nach `errorThreshold` (6) aufeinanderfolgenden Fehlern werden Benachrichtigungen verschickt.


* **SafeCall Wrapper:**
* Fängt Fehler beim Shelly-eigenen Call-Pool ab ("Too many calls in progress") und verhindert das Einfrieren der Skript-Schleife.



#### D. Performance- und Speicheroptimierung (Shelly-Spezifisch)

* **Adaptive Polling / Sparmodus (`idleSkip`):**
* Bleibt die Netzsaldoregelung stabil innerhalb der Hysterese (`cyclesUnchanged: 4`), setzt das Skript das Abfragen der Zendure-Geräte für bis zu 44 Sekunden aus, um die Netzwerk- und HTTP-Last auf den Shelly und die Zendure-Hubs stark zu reduzieren.


* **Speichermanagement (Garbage Collection & RAM):**
* Banner-Texte, Initialisierungs- und Sync-Funktionen werden nach dem Skriptstart explizit im Speicher auf `null` gesetzt und freigegeben.
* JSON-Strings von HTTP-Antworten werden sofort nach dem Parsen verworfen (`res = null`), um RAM-Peaks auf dem Mikrocontroller zu vermeiden.


* **Echtzeit-Optimierung der Abfragereihenfolge (`buildPollOrder`):**
* Zuerst werden inaktive Geräte abgefragt, als letztes das aktuell regelnde Gerät direkt vor dem Smartmeter. Dadurch liegen Messwert des Speichers und Netzmesswert zeitlich extrem nah beieinander.



#### E. Schnittstellen & Integration

* **Live-Overrides über Shelly KVS (Key-Value-Store):**
* Parameter wie `setpoint`, `dischargeFixed`, `minSoc` oder `inputLimit` können zur Laufzeit über den Shelly KVS geändert werden, ohne das Skript neu starten zu müssen.
* Das Skript reagiert eventbasiert auf Änderungen der `kvs_rev`.


* **Benachrichtigungssystem (`signal`):**
* Unterstützt Alarmierungen über Webhooks (z. B. Home Assistant), Signal oder WhatsApp (via CallMeBot) bei Verbindungsabbrüchen oder Fehlerzuständen.



---

### 3. Stärken & Ausfallkonzept

| Feature | Umsetzung im Skript | Vorteil |
| --- | --- | --- |
| **Bypass-Korrektur** | `applyBypassExcessCorrection` | Wenn ein Akku voll ist (`socLimit = 1`) und PV-Strom durchleitet, wird dieser Überschuss erkannt und von den Entlade-Sollwerten der anderen Geräte abgezogen. |
| **Manuelles Laden** | `syncInputLimitDevice` | Erkennt manuelles AC-Laden aus der App/Dashboard und unterbricht die Automatik für das betreffende Gerät schadlos. |
| **Dry-Run Modus** | `dryRun: true` in Dev-Config | Erlaubt das Testen und Loggen aller Berechnungen, ohne tatsächlich Steuerbefehle an die Zendure-Geräte zu senden. |

### Fazit

Das Skript ist ein **außerordentlich ausgereifter, robuster und extrem speicheroptimierter Regler** für Shelly-Geräte. Es berücksichtigt vorallem die technischen Einschränkungen von Shelly mJS (begrenzter Arbeitsspeicher, Call-Pool-Limits) sowie die Hardware-Schonung der Zendure-Akkus/Inverter (EEPROM-Schreibschutz, Umschaltpausen, Hysterese).