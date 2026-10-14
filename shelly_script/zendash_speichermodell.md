# zenDash-API + Watchdog – Speichermodell (v3.5.8)

Stand: 14.10.2026 · gilt für `zendash_watch` v3.5.8 mit **Debug aus**

Die Tabelle schätzt den Speicherbedarf des zenDash-Scripts auf dem Shelly. Sie zeigt, wie viel Reserve für welche Anzahl von SolarFlow-Geräten und Akkus bleibt.

## Kurzfassung

- **1–2 SolarFlow:** unkritisch, auch mit vielen Akkus
- **3 SolarFlow:** ok bis etwa 3–4 Akkus am Gerät mit den meisten Akkus
- **4 SolarFlow:** mit v3.5.8 **nicht unterstützt**, zu wenig Reserve

## Grundlagen

| Begriff | Bedeutung |
|---|---|
| Gesamtspeicher | ~25,2 kB pro Script (`mem_used` + `mem_free`) |
| Grundlast | `mem_used` im Ruhezustand zwischen zwei Polls |
| Spitze | höchster Speicherbedarf (`mem_peak`), entsteht beim Lesen eines Hub-Reports |
| Reserve | 25,2 kB − Spitze |

## Formeln

```
Grundlast ≈ 10,8 kB + 2,2 kB × Geräte
Spitze    ≈ 14,6 kB + 2,4 kB × Geräte + 0,65 kB × (max. Akkus je Gerät − 2)   [letzter Term nur bei > 2]
Reserve   = 25,2 kB − Spitze
```

**Bewertung:** ✅ Reserve ≥ 3 kB · ⚠️ 1,5–3 kB · ❌ < 1,5 kB

Die 1,5 kB Mindestreserve sind ein Puffer für Momente, in denen mehrere Dinge zusammenkommen: Nachrichtenversand, Startphase, gleichzeitige Dashboard-Abrufe, Schwankungen der Firmware.

## Tabelle

Annahme: Die Akkus sind gleichmäßig auf die Geräte verteilt.

| Geräte | Akkus | max. je Gerät | Grundlast | Spitze | Reserve | Bewertung | Quelle |
|---|---|---|---|---|---|---|---|
| 1 | 1 | 1 | 13,1 kB | **17,1 kB** | 8,1 kB | ✅ | **gemessen** |
| 1 | 2 | 2 | 13,0 kB | 17,0 kB | 8,2 kB | ✅ | Modell |
| 1 | 3 | 3 | 13,0 kB | 17,7 kB | 7,5 kB | ✅ | Modell |
| 2 | 2 | 1 | 15,2 kB | 19,4 kB | 5,8 kB | ✅ | Modell |
| 2 | 3 | 2 | 15,1 kB | **19,3 kB** | 5,9 kB | ✅ | **gemessen** |
| 2 | 4 | 2 | 15,2 kB | 19,4 kB | 5,8 kB | ✅ | Modell |
| 2 | 6 | 3 | 15,2 kB | 20,1 kB | 5,1 kB | ✅ | Modell |
| 3 | 3 | 1 | 17,4 kB | 21,8 kB | 3,4 kB | ✅ | Modell |
| 3 | 6 | 2 | 17,4 kB | 21,8 kB | 3,4 kB | ✅ | Modell |
| 3 | 8 | 3 | 17,5 kB | **22,5 kB** | 2,7 kB | ⚠️ | **gemessen** |
| 4 | 4 | 1 | 19,6 kB | 24,2 kB | 1,0 kB | ❌ | Modell |
| 4 | 8 | 2 | 19,6 kB | 24,2 kB | 1,0 kB | ❌ | Modell |

## Was Geräte und Akkus kosten

| | Grundlast | Spitze |
|---|---|---|
| je SolarFlow-Gerät | +2,2 kB | +2,4 kB |
| je Akku (allgemein) | 0 (seit v3.5.6) | 0 |
| je Akku über 2 **am Gerät mit den meisten Akkus** | 0 | +0,65 kB (geschätzt) |

Die Gesamtzahl der Akkus ist nicht entscheidend. Die Hub-Reports werden nacheinander gelesen, und der größte Report setzt die Spitze. Ein Report wächst mit der Zahl der Akkus am Gerät, weil `packData` einen Eintrag pro Akku enthält. Im RAM belegt ein Report etwa das Doppelte seiner Größe.

**Ungleiche Verteilung:** Bei 4 Geräten mit 8 Akkus in der Verteilung 5/1/1/1 kämen 3 × 0,65 kB dazu. Die Spitze läge dann bei etwa 26,2 kB, und das Script würde abstürzen.

## Messpunkte

| Anlage | Version | Grundlast | `mem_peak` |
|---|---|---|---|
| 1 SolarFlow (SF2400), 1 Akku | 3.5.8 | 13 062 | 17 066 |
| 2 SolarFlow (SF2400 + SF800), 3 Akkus | 3.5.8 | 15 106 | 19 320 |
| 3 SolarFlow (SF800 Pro), 8 Akkus | 3.5.8 | ~17 500 | 22 456 |

Alle Messungen mit Debug aus, aufgenommen mit `Shelly_Script_Status_poller.py`.

## Belastbarkeit

- **Gerätekosten (2,4 kB):** gut belegt. Die drei Messpunkte liegen auf ±0,1 kB genau auf der Formel.
- **Akkukosten (0,65 kB):** nur geschätzt, aus einem einzigen Messpunkt. Angenommen ist die Verteilung 3/3/2 beim 3-Geräte-System. Bei 4/2/2 wären es nur ~0,33 kB pro Akku. Die Tabelle ist also eher vorsichtig gerechnet.
- **Debug an:** etwa 0,3–0,5 kB mehr Spitze.
- **Andere Gerätetypen** mit anderer Report-Größe können abweichen.
- Kleinere Konfigurationsunterschiede wie Label-Längen oder Nachrichtentyp sind in den Messwerten enthalten.

**Für genauere Akkukosten:** ein Debug-Log einer Anlage mit mehr als 2 Akkus an einem Gerät (Zeilen `MEM Poll … Body … B`) und die Zahl der Akkus je Gerät.

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
| 3.5.8 | `config_api` zweistufig: KVS-Callback erst verlassen, dann Antwort bauen | ~1,5 kB weniger in `config_api` |

**Firmware-Verhalten:** Die Shelly-Firmware hält eine HTTP-Antwort im Speicher, bis der Callback zurückkehrt. `body = null` gibt vorher nichts frei. Wer danach noch viel Speicher braucht, verlässt den Callback zuerst per `Timer.set(0)`. Außerdem belegt der Programmcode selbst RAM, jede zusätzliche Funktion erhöht also die Grundlast.
