# Skalierungsmodell - Wieviel Solarflows

Stand: 15.10.2026 · gilt für `zendash_watch` v3.5.8 mit **Debug aus** · 5 Messpunkte

Die Tabelle schätzt den Speicherbedarf des zenDash-Scripts auf dem Shelly. Sie zeigt, wie viel Reserve für welche Anzahl von SolarFlow-Geräten und Akkus bleibt.

## Kurzfassung

- **1–2 SolarFlow:** unkritisch, auch mit vielen Akkus
- **3 SolarFlow:** ✅ bis 3 Akkus am Gerät mit den meisten Akkus, ⚠️ bei 4–7, ❌ ab 8
- **4 SolarFlow:** mit v3.5.8 **nicht unterstützt**, zu wenig Reserve

**Fazit für 4 Geräte:** Der Regler kommt ab 5.3.5 mit 4 Geräten und wenigen Akkus je Gerät aus (bis A = 1 ✅, bis A = 4 ⚠️). Begrenzend bleibt das zenDash-Script (oben: 4 Geräte ❌).

## Grundlagen

| Begriff | Bedeutung |
|---|---|
| Gesamtspeicher | ~25,2 kB pro Script (`mem_used` + `mem_free` = 25 186 Byte, bei allen Messungen gleich) |
| Grundlast | `mem_used` im Ruhezustand zwischen zwei Polls |
| Spitze | höchster Speicherbedarf (`mem_peak`), entsteht beim Lesen eines Hub-Reports |
| Reserve | 25,2 kB − Spitze |

## Watchdog-Script

### Formel

Eingaben:

- **G** = Anzahl SolarFlow-Geräte
- **A** = Akkus am Gerät mit den **meisten** Akkus. Bei Pro-Modellen zählt der integrierte Akku mit.

```
Spitze    ≈ 14,6 + 2,4 × G + 0,35 × max(0, A − 2)    [kB]
Reserve   = 25,2 − Spitze                            [kB]
Grundlast ≈ 10,8 + 2,2 × G                           [kB]   (optional)
```

**Bewertung:** ✅ Reserve ≥ 3 kB · ⚠️ 1,5–3 kB · ❌ < 1,5 kB

Die 1,5 kB Mindestreserve sind ein Puffer für Momente, in denen mehrere Dinge zusammenkommen: Nachrichtenversand, Startphase, gleichzeitige Dashboard-Abrufe, Schwankungen der Firmware.

**Beispiel:** 3 Geräte mit 4 / 2 / 1 Akkus, also G = 3 und A = 4

```
Spitze  = 14,6 + 2,4 × 3 + 0,35 × (4 − 2) = 14,6 + 7,2 + 0,7 = 22,5 kB
Reserve = 25,2 − 22,5 = 2,7 kB  →  ⚠️
```

**Als Excel-Formel**, mit G in A2, A in B2, Spitze in C2 und Reserve in D2:

```
Spitze:    =14,6+2,4*A2+0,35*MAX(0;B2-2)
Reserve:   =25,2-C2
Bewertung: =WENN(D2>=3;"✅";WENN(D2>=1,5;"⚠️";"❌"))
```

### Tabelle

Für die Modellzeilen ist angenommen, dass die Akkus gleichmäßig auf die Geräte verteilt sind.

| Geräte | Akkus | Verteilung | A | Spitze | Reserve | Bewertung | Quelle |
|---|---|---|---|---|---|---|---|
| 1 | 1 | 1 | 1 | **17,1 kB** | 8,1 kB | ✅ | **gemessen** |
| 1 | 2 | 2 | 2 | 17,0 kB | 8,2 kB | ✅ | Modell |
| 1 | 3 | 3 | 3 | 17,4 kB | 7,8 kB | ✅ | Modell |
| 2 | 2 | 1/1 | 1 | 19,4 kB | 5,8 kB | ✅ | Modell |
| 2 | 3 | 2/1 | 2 | **19,3 kB** | 5,9 kB | ✅ | **gemessen** |
| 2 | 4 | 2/2 | 2 | 19,4 kB | 5,8 kB | ✅ | Modell |
| 2 | 6 | 3/3 | 3 | 19,8 kB | 5,4 kB | ✅ | Modell |
| 2 | 7 | 4/3 | 4 | **20,2 kB** | 5,0 kB | ✅ | **gemessen** |
| 3 | 3 | 1/1/1 | 1 | 21,8 kB | 3,4 kB | ✅ | Modell |
| 3 | 6 | 2/2/2 | 2 | 21,8 kB | 3,4 kB | ✅ | Modell |
| 3 | 7 | 3/3/1 | 3 | **21,6 kB** | 3,6 kB | ✅ | **gemessen** |
| 3 | 8 | 1/3/4 | 4 | **22,5 kB** | 2,7 kB | ⚠️ | **gemessen** |
| 3 | 9 | 2/3/4 | 4 | 22,5 kB | 2,7 kB | ⚠️ | Modell |
| 3 | 12 | 4/4/4 | 4 | 22,5 kB | 2,7 kB | ⚠️ | Modell |
| 4 | 4 | 1/1/1/1 | 1 | 24,2 kB | 1,0 kB | ❌ | Modell |
| 4 | 8 | 2/2/2/2 | 2 | 24,2 kB | 1,0 kB | ❌ | Modell |

**Ungleiche Verteilung:** Bei 4 Geräten mit 8 Akkus in der Verteilung 5/1/1/1 kämen 3 × 0,35 kB dazu. Die Spitze läge dann bei etwa 25,3 kB, und das Script würde abstürzen.

### Was Geräte und Akkus kosten

| | Grundlast | Spitze |
|---|---|---|
| je SolarFlow-Gerät | +2,2 kB | +2,4 kB |
| je Akku (allgemein) | 0 (seit v3.5.6) | 0 |
| je Akku über 2 **am Gerät mit den meisten Akkus** | 0 | +0,35 kB |

Die Gesamtzahl der Akkus ist nicht entscheidend. Die Hub-Reports werden nacheinander gelesen, und der größte Report setzt die Spitze. Ein Report wächst mit der Zahl der Akkus am Gerät, weil `packData` einen Eintrag pro Akku enthält. Im RAM belegt ein Report etwa das Doppelte seiner Größe.

### Messpunkte

| Anlage | Geräte | Grundlast | `mem_peak` | Modell | Abweichung |
|---|---|---|---|---|---|
| A | 1× SF2400 (1 Akku) | 13 062 | 17 066 | 17,0 kB | −0,1 kB |
| A | SF2400 (1) + SF800 (2) | 15 106 | 19 320 | 19,4 kB | +0,1 kB |
| B | 3× SF800 Pro, 8 Akkus (1/3/4) | ~17 500 | 22 456 | 22,5 kB | ±0 |
| C | 2× SF800 Pro (je 3) + SF2400 Pro (1) | 16 870 | 21 560 | 22,2 kB | +0,6 kB |
| D | SF2400 Pro (4) + SF800 Pro (3), jeweils inkl. integriertem Akku | 15 442 | 20 216 | 20,1 kB | −0,1 kB |

Alle Messungen mit v3.5.8 und Debug aus. Das Modell trifft alle Messwerte auf −0,1 bis +0,6 kB genau und rechnet damit eher vorsichtig.

**Herleitung des Akku-Zuschlags:** Verglichen wird jeweils die Spitze über Grundlast mit einer Anlage ohne Zuschlag (höchstens 2 Akkus je Gerät):

| Anlage | Spitze über Grundlast | Vergleichswert | Differenz | Akkus über 2 | je Akku |
|---|---|---|---|---|---|
| C (3 Geräte, A = 3) | 4 690 | ~4 400 | ~290 | 1 | ~0,29 kB |
| D (2 Geräte, A = 4) | 4 774 | 4 214 (Anlage A, 2 Geräte) | 560 | 2 | 0,28 kB |
| B (3 Geräte, A = 4) | 4 956 | ~4 400 | ~560 | 2 | ~0,28 kB |

Drei Anlagen ergeben unabhängig voneinander ~0,28–0,29 kB pro Akku. Das Modell setzt 0,35 kB an und hat damit einen kleinen Sicherheitszuschlag.

### Belastbarkeit

- **Gerätekosten (2,4 kB):** gut belegt durch 5 Messpunkte an 4 Anlagen.
- **Akkukosten (0,35 kB):** bestätigt durch drei Anlagen mit bekannter Verteilung (B, C, D), die jeweils ~0,28–0,29 kB ergeben.
- **Integrierter Akku:** Bei Pro-Modellen mitzählen. Ohne ihn würde Anlage D um 0,45 kB unterschätzt.
- **Gerätetypen:** SF2400, SF800, SF800 Pro und SF2400 Pro liefern unterschiedlich große Reports. Daraus ergeben sich Abweichungen von bis zu ±0,6 kB.
- **`mem_peak`** zählt nur seit dem letzten Script-Start. Lief das Script erst kurz oder wurde noch kein Dashboard geladen, kann der echte Wert etwas höher liegen.
- **Debug an:** etwa 0,3–0,5 kB mehr Spitze.
- Kleinere Konfigurationsunterschiede wie Label-Längen oder Nachrichtentyp sind in den Messwerten enthalten.

**Noch offen:** Messpunkte mit 5 oder mehr Akkus an einem Gerät und mit 4 Geräten.

## Regler-Script (Controller)

Stand: 27.10.2026 · gilt für das Regler-Script `zerooutput_multi_kvs` **v5.3.5** mit **Debug aus** · 4 Messpunkte an 2 Anlagen, Rest abgeleitet

Das Regler-Script läuft auf einem eigenen Shelly mit eigener Grenze von ~25,2 kB. Es folgt demselben Muster: Die Geräte werden nacheinander abgefragt, und der größte Report setzt die Spitze. Seit 5.3.0 zerlegt der Regler den Report nicht mehr mit `JSON.parse`. Die Akkus kosten deshalb nur noch über die Größe des Reports Speicher, nicht über geparste Objekte.

### Formel

Gleiche Eingaben wie oben: **G** = Anzahl SolarFlow-Geräte, **A** = Akkus am Gerät mit den meisten Akkus (bei Pro-Modellen mit integriertem Akku).

```
Spitze    ≈ 15,3 + 1,55 × G + 0,5 × A    [kB]
Reserve   = 25,2 − Spitze                [kB]
Grundlast ≈ 12,3 + 1,55 × G              [kB]   (optional)
```

Bewertung wie oben: ✅ Reserve ≥ 3 kB · ⚠️ 1,5–3 kB · ❌ < 1,5 kB

**Herleitung:**

- **Report im Speicher:** Ein Report von B Byte belegt beim Empfang kurzzeitig etwa 2,9 × B (Antworttext, Header, Antwortobjekt und Zuschlag beim Empfang; aus den Debug-Messpunkten von 5.3.3).
- **Größe eines Reports:** etwa 0,87 kB (SF800) bzw. 1,02 kB (SF2400 Pro) plus 0,17 kB je Akku in `packData`.
- **Akku-Zuschlag:** 0,5 kB je Akku = 2,9 × 0,17 kB. Gerechnet ist mit dem größeren SF2400-Pro-Report, das Modell schätzt also eher zu hoch.
- **Kosten je Gerät:** Die 1,55 kB stammen aus dem Vergleich von 2 und 3 eingetragenen Geräten.

### Tabelle

| Geräte | A = 1 | A = 2 | A = 4 | A = 6 |
|---|---|---|---|---|
| 1 | 17,4 kB · 7,8 ✅ | 17,9 · 7,3 ✅ | 18,9 · 6,3 ✅ | 19,9 · 5,3 ✅ |
| 2 | 18,9 kB · 6,3 ✅ | **19,4 · 5,8 ✅** (gemessen) | 20,4 · 4,8 ✅ | 21,4 · 3,8 ✅ |
| 3 | 20,4 kB · 4,8 ✅ | **21,0 · 4,2 ✅** (gemessen) | 22,0 · 3,2 ✅ | 23,0 · 2,2 ⚠️ |
| 4 | 22,0 kB · 3,2 ✅ | 22,5 · 2,7 ⚠️ | 23,5 · 1,7 ⚠️ | 24,5 · 0,7 ❌ |

Angaben: Spitze · Reserve (kB) · Bewertung.

### Messpunkte

| Anlage | Geräte | Grundlast | `mem_peak` | Modell |
|---|---|---|---|---|
| A | SF2400 Pro (1) + SF800 (2), A = 2 | ~15 300 | 18 844 – 19 068 | 19,4 kB |
| A | wie oben + drittes Gerät nur eingetragen (`dryRun`, nicht erreichbar) | ~16 400 | 20 440 | 21,0 kB |
| A | SF2400 Pro (1) + SF800 (2), manuelles Laden gestartet und beendet | ~15 050 | 19 474 | 19,4 kB + KVS-Übernahme |
| E | 3 Geräte, 7 Akkus (3/3/1), A = 3 · Shelly Pro 3EM, Firmware 2.1.0 | 16 184 (kurz bis 16 870) | 20 608 nach Neustart · ~20 790 nach 8 h | 21,5 kB |

**Anlage E** ist der erste Messpunkt mit 3 echten Geräten und mehr als 2 Akkus an einem Gerät. Gemessen wurde 20 Minuten lang alle 30 s per `Script.GetStatus`, nach einem Neustart und mit gestopptem zweitem Script. `mem_peak` war nach etwa 38 s (Startphase) erreicht und blieb danach konstant. Nach 8 h Normalbetrieb lag er bei ~20 790, also nur ~0,2 kB höher. Das Modell liegt bei der Spitze 0,7–0,8 kB und bei der Grundlast ~0,8 kB über den Messwerten, rechnet also vorsichtig. Reserve gemessen: 25 186 − 20 608 = 4,6 kB (Modell 3,7 kB) → ✅.

Beim manuellen Laden schreibt das Dashboard drei KVS-Keys. Der Regler übernimmt sie mit einem `KVS.GetMany` zwischen zwei Regelzyklen. Das hob `mem_peak` um etwa 0,45 kB (19 026 → 19 474). Mit 5.3.3, als die Übernahme noch parallel zum Zyklus lief, waren es +2,4 kB bis 21 126.

Bei Anlage A ist A = 2, weil der SF800 zwei Akkus hat. Das Modell liegt dort 0,3–0,6 kB über den Messwerten.

Das dritte Gerät im zweiten Messpunkt liefert keinen Report. Es zeigt deshalb nur die Kosten eines weiteren Geräts, nicht die eines weiteren Reports. Für die Spitze ist das unerheblich, weil der größte Report gleich bleibt.

### Belastbarkeit

- **Kosten je Gerät (1,55 kB):** aus zwei Messpunkten an Anlage A; Anlage E (3 echte Geräte) bestätigt sie, das Modell liegt dort 0,7–0,8 kB zu hoch.
- **Akku-Zuschlag (0,5 kB):** abgeleitet aus der Report-Größe. Einzeln nicht gemessen; Anlage E (A = 3) liegt unter dem Modell, der Zuschlag ist also eher zu hoch als zu niedrig.
- **`mem_free`** gilt für alle Scripte auf dem Shelly gemeinsam. Läuft ein zweites Script, ist `mem_free` entsprechend kleiner. Für das Modell zählt `mem_peak` des Regler-Scripts.
- **Noch offen:** Messpunkte mit 4 oder mehr Akkus an einem Gerät und mit 4 echten Geräten.
- **Weitere Spitze beim Übernehmen von KVS-Änderungen:** Pro Key kostet sie etwa 0,21 kB, und es gibt 3 + 4 × G Keys. Bei 4 Geräten sind das etwa 4 kB über der Grundlast, ungefähr so viel wie ein Report. Seit 5.3.5 laufen beide nie gleichzeitig, weil KVS-Änderungen nur zwischen zwei Regelzyklen übernommen werden.

### Änderungen, die den Speicher betreffen

| Version | Änderung | Wirkung |
|---|---|---|
| 3.5.5 | Nachbearbeitung und Auto-Stop per `Timer.set(0)` auf frischem Stack | behebt „Too much recursion“ (Stack, nicht Heap) |
| 3.5.6 | `minVolSn`/`minVolSoc` entfernt, `lowVoltMsgSent` nur noch für Packs im Alarm | ~0,3 kB weniger Grundlast (2 Geräte) |
| 3.5.7 | `KVS_TMP` | ohne Wirkung, in 3.5.8 wieder entfernt |
| 3.5.8 | `config_api` zweistufig: KVS-Callback erst verlassen, dann Antwort bauen | ~1,5 kB weniger in `config_api`; bei 3 Geräten ~1,7 kB weniger `mem_peak` |

**Firmware-Verhalten:** Die Shelly-Firmware hält eine HTTP-Antwort im Speicher, bis der Callback zurückkehrt. `body = null` gibt vorher nichts frei. Wer danach noch viel Speicher braucht, verlässt den Callback zuerst per `Timer.set(0)`. Außerdem belegt der Programmcode selbst RAM, jede zusätzliche Funktion erhöht also die Grundlast.
