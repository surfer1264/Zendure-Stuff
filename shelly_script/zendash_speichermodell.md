# zenDash-API + Watchdog – Speichermodell (v3.5.8)

Stand: 15.10.2026 · gilt für `zendash_watch` v3.5.8 mit **Debug aus** · 5 Messpunkte

Die Tabelle schätzt den Speicherbedarf des zenDash-Scripts auf dem Shelly. Sie zeigt, wie viel Reserve für welche Anzahl von SolarFlow-Geräten und Akkus bleibt.

## Kurzfassung

- **1–2 SolarFlow:** unkritisch, auch mit vielen Akkus
- **3 SolarFlow:** ✅ bis 3 Akkus am Gerät mit den meisten Akkus, ⚠️ bei 4–7, ❌ ab 8
- **4 SolarFlow:** mit v3.5.8 **nicht unterstützt**, zu wenig Reserve

## Grundlagen

| Begriff | Bedeutung |
|---|---|
| Gesamtspeicher | ~25,2 kB pro Script (`mem_used` + `mem_free` = 25 186 Byte, bei allen Messungen gleich) |
| Grundlast | `mem_used` im Ruhezustand zwischen zwei Polls |
| Spitze | höchster Speicherbedarf (`mem_peak`), entsteht beim Lesen eines Hub-Reports |
| Reserve | 25,2 kB − Spitze |

## Formel

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

## Tabelle

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

## Was Geräte und Akkus kosten

| | Grundlast | Spitze |
|---|---|---|
| je SolarFlow-Gerät | +2,2 kB | +2,4 kB |
| je Akku (allgemein) | 0 (seit v3.5.6) | 0 |
| je Akku über 2 **am Gerät mit den meisten Akkus** | 0 | +0,35 kB |

Die Gesamtzahl der Akkus ist nicht entscheidend. Die Hub-Reports werden nacheinander gelesen, und der größte Report setzt die Spitze. Ein Report wächst mit der Zahl der Akkus am Gerät, weil `packData` einen Eintrag pro Akku enthält. Im RAM belegt ein Report etwa das Doppelte seiner Größe.

## Messpunkte

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

## Belastbarkeit

- **Gerätekosten (2,4 kB):** gut belegt durch 5 Messpunkte an 4 Anlagen.
- **Akkukosten (0,35 kB):** bestätigt durch drei Anlagen mit bekannter Verteilung (B, C, D), die jeweils ~0,28–0,29 kB ergeben.
- **Integrierter Akku:** Bei Pro-Modellen mitzählen. Ohne ihn würde Anlage D um 0,45 kB unterschätzt.
- **Gerätetypen:** SF2400, SF800, SF800 Pro und SF2400 Pro liefern unterschiedlich große Reports. Daraus ergeben sich Abweichungen von bis zu ±0,6 kB.
- **`mem_peak`** zählt nur seit dem letzten Script-Start. Lief das Script erst kurz oder wurde noch kein Dashboard geladen, kann der echte Wert etwas höher liegen.
- **Debug an:** etwa 0,3–0,5 kB mehr Spitze.
- Kleinere Konfigurationsunterschiede wie Label-Längen oder Nachrichtentyp sind in den Messwerten enthalten.

**Noch offen:** Messpunkte mit 5 oder mehr Akkus an einem Gerät und mit 4 Geräten.

## Hinweis Regler-Script

Das Regler-Script zeigt dasselbe Muster mit eigener Grenze von ~25,2 kB:

| Geräte | Regler `mem_peak` |
|---|---|
| 1 | 17 934 |
| 2 | 19 642 |
| 3 | 22 372 |

Für 4 Geräte müssten **beide** Scripts sparsamer werden.

## Änderungen, die den Speicher betreffen

| Version | Änderung | Wirkung |
|---|---|---|
| 3.5.5 | Nachbearbeitung und Auto-Stop per `Timer.set(0)` auf frischem Stack | behebt „Too much recursion“ (Stack, nicht Heap) |
| 3.5.6 | `minVolSn`/`minVolSoc` entfernt, `lowVoltMsgSent` nur noch für Packs im Alarm | ~0,3 kB weniger Grundlast (2 Geräte) |
| 3.5.7 | `KVS_TMP` | ohne Wirkung, in 3.5.8 wieder entfernt |
| 3.5.8 | `config_api` zweistufig: KVS-Callback erst verlassen, dann Antwort bauen | ~1,5 kB weniger in `config_api`; bei 3 Geräten ~1,7 kB weniger `mem_peak` |

**Firmware-Verhalten:** Die Shelly-Firmware hält eine HTTP-Antwort im Speicher, bis der Callback zurückkehrt. `body = null` gibt vorher nichts frei. Wer danach noch viel Speicher braucht, verlässt den Callback zuerst per `Timer.set(0)`. Außerdem belegt der Programmcode selbst RAM, jede zusätzliche Funktion erhöht also die Grundlast.
