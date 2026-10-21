Dieser Report ist generiert aus den Tageslogfiles des Shelly Controllers und vergleicht zwei 24h Profile

# Analyse Multi-Device-Controller – 20.10.2026 im Vergleich zum 07.10.2026

Analysierte Logs: `…20.10.2026_00-00`, `…08-00`, `…16-00` (Rohdaten Controller, zusammen 84.899 Zeilen) und `…16-00_ereignisse.txt`.
Zeitraum: 20.10.2026, 00:00:10 bis 23:59:58 (24 h). Regelzyklen: **19.116** (07.10.: 19.054).
Geräte (wie am 07.10.): **ZSF800P1**, **ZSF800P2** (SF800 Pro), **ZSF2400P1** (SF2400 Pro).

## Fazit

- **Regelgüte:** Im Band ±13 W lagen 66,3 % der nicht gesättigten Zyklen (07.10.: 53,2 %), über 50 W nur noch 6,7 % (07.10.: 17,8 %). Über alle Zyklen lagen 63,7 % im Band (07.10.: 24,2 %).
- **Sättigung** 3,9 % (07.10.: 54,5 %). Am 20.10. gab es keine Phase, in der alle Geräte per Einstellung auf Soll 0 W standen. Die Sättigung entstand nur durch die Entladesperre bei 40 % (12:50–13:05 und ab 23:14).
- **Median der Regelabweichung: −1 W** (07.10.: 288 W).
- **Netzbezug ** 1,02 kWh am ganzen Tag (07.10.: 11,07 kWh). In den nicht gesättigten Zyklen: 0,40 kWh Bezug und 0,29 kWh Einspeisung (07.10.: 0,82 kWh und 0,46 kWh).
- **Soll und Ist stimmen eng überein** (Median 0–1 W, wie am 07.10.).
- **Sparmodus:** 40,9 % ohne Geräte-Poll (07.10.: 52,7 %). Schreibvorgänge: 5.758 (07.10.: 3.731).
- **Verbindungsfehler:** 18 (07.10.: 2), jeweils höchstens 2 in Folge. Übersprungene Takte: 66 (07.10.: 122).
- **Neue Version 5.2.0** (07.10.: 5.1.5) mit zusätzlicher Dämpfung 0,9 bei Sprüngen über 36 W in Richtung „weniger Export".
- **gridReverse dynamic:** eine Umschaltung, 02:35 Uhr von 2 auf 1 (ZSF800P1 bei 89 %).

---

## 1) Grundinformationen und Konfiguration

| Parameter | 20.10. | 07.10. |
|---|---|---|
| Version | **5.2.0** | 5.1.5 |
| Zählerquelle | local | local |
| Intervall / Watchdog | 4.500 / 11.250 ms | gleich |
| Setpoint | 0 W | 0 W |
| Hysterese (Config) | 12 W pro Gerät | gleich |
| Dämpfung | **0,65; bei Sprung > 36 W Richtung weniger Export: 0,9** | 0,65 |
| Einzelgerät / Verteilen | unter 600 W / über 800 W | gleich |
| Konzentrieren-Haltezeit | 3 min (40 Zyklen) | gleich |
| SoC-Ausgleich | ab 5 Prozentpunkten | gleich |
| Start/Stop Laden und Entladen | 35 W / 15 W | gleich |
| Richtungswechsel-Bremse | 4 Takte | gleich |
| Sparmodus | ab 4 gleichen Zyklen, max. 10 Zyklen / 44 s | gleich |
| gridReverseMode | dynamic | dynamic |
| minSoc (per KVS) | **40 % alle Geräte**, ganztägig | 15 %, zeitweise geändert |
| Skript-Starts | 00:00, 08:00, 16:00 | 00:00, 08:00, 16:00, 18:05 |

Gerätewerte (CONFIG) unverändert: ZSF800P1/P2 je 800 W Ausgang, 1.000 W Eingang; ZSF2400P1 2.400 W Ausgang, 3.200 W Eingang; maxSoc 100 %.

---

## 2.1) Regelgüte-Reporting

Regelabweichung = Netzsaldo − Setpoint (0 W).

![Regelabweichung 20.10.](chart_regelabweichung_20.10.png)

| Kennzahl | 20.10. alle | 20.10. ohne gesättigte | 07.10. alle | 07.10. ohne gesättigte |
|---|---|---|---|---|
| Median Regelabweichung | **−1 W** | – | 288 W | – |
| Anzahl Zyklen | 19.116 | 18.369 | 19.054 | 8.678 |
| Ausgelassene Zyklen | 66 | – | 122 | – |
| Im Hystereseband (≤ 13 W) | 12.183 (63,7 %) | **66,3 %** | 4.615 (24,2 %) | 53,2 % |
| > 13 W und ≤ 50 W | 4.951 (25,9 %) | 27,0 % | 2.539 (13,3 %) | 29,0 % |
| > 50 W | 1.982 (10,4 %) | **6,7 %** | 11.900 (62,5 %) | 17,8 % |
| **Sättigungsanteil** | **747 Zyklen (3,9 %)** | | **10.376 Zyklen (54,5 %)** | |

Sättigung am 20.10.: ZSF2400P1 in Entladesperre bei 40 %, beide SF800 am Maximum 800 W (12:50–12:58 und 13:03–13:05, 140 Zyklen); alle drei Geräte in Entladesperre bei 40 % (23:14–24:00, 604 Zyklen).

**Legende:**
- *Median:* mittlerer Wert der Regelabweichung; nahe 0 W = gut.
- *Ausgelassene Zyklen:* Takte, die übersprungen wurden, weil der vorige Zyklus noch lief.
- *Toleranzbänder:* Betrag der Regelabweichung je Zyklus.
- *Gesättigte Zyklen:* Netzbezug bzw. Einspeisung über 13 W, obwohl kein Gerät mehr liefern bzw. laden konnte oder durfte (Gerätegrenze, SoC-Sperre, minSoc oder Sperre per Einstellung). Diese Abweichung kann die Regelung nicht beheben.
- *Sättigungsanteil:* Anteil dieser Zyklen an allen Zyklen.

### Energie

| Bereich | 20.10. Bezug | 20.10. Einspeisung | 07.10. Bezug | 07.10. Einspeisung |
|---|---|---|---|---|
| nicht gesättigte Zyklen | **0,40 kWh** | **0,29 kWh** | 0,82 kWh | 0,46 kWh |
| gesättigte Zyklen | 0,62 kWh | 0,00 kWh | 10,24 kWh | 0,00 kWh |
| gesamt | 1,02 kWh | 0,29 kWh | 11,07 kWh | 0,46 kWh |
| Haushaltsverbrauch (Netz + Speicher) | 16,5 kWh | | 19,6 kWh | |

Berechnet aus Netzsaldo je Zyklus mal Zeit bis zum nächsten Zyklus (Lücken über 10 s mit 4,5 s gerechnet).

## 2.2) SOLL/IST-Vergleich je Gerät

![Soll/Ist je Gerät 20.10.](chart_soll_ist_20.10.png)

**Bedeutung:** SOLL ist die Leistung, die der Controller dem Gerät vorgibt. IST ist die Leistung, die das Gerät tatsächlich meldet.

**Gründe für Abweichungen:** Das Gerät braucht Zeit, um eine neue Vorgabe umzusetzen, und meldet Werte nur in festen Abständen. Außerdem können Gerätegrenzen (max. Leistung, SoC-Sperren), der Richtungswechsel-Schutz oder Verbindungsfehler die Umsetzung verhindern.

| Gerät | Median abs(Soll − Ist) 20.10. | 90 %-Wert 20.10. | Median 07.10. | 90 %-Wert 07.10. |
|---|---|---|---|---|
| ZSF800P1 | 0 W | 9 W | 0 W | 9 W |
| ZSF800P2 | 1 W | 9 W | 0 W | 12 W |
| ZSF2400P1 | 0 W | 6 W | 0 W | 6 W |

Am 20.10. gab es keine längeren Abschnitte mit großer Abweichung. Die längsten dauerten unter 1 min (z. B. 10:24–10:25 bei allen Geräten).

---

## 3) Regelgröße je Gerät

![Regelgröße je Gerät 20.10.](chart_regelgroesse_20.10.png)

| Gerät | Zyklen Entladen 20.10. | Median / Max 20.10. | Zyklen Entladen 07.10. | Median / Max 07.10. |
|---|---|---|---|---|
| ZSF800P1 | 9.332 | 349 W / 800 W | 4.488 | 456 W / 800 W |
| ZSF800P2 | 13.335 | 391 W / 801 W | 5.515 | 491 W / 801 W |
| ZSF2400P1 | 5.719 | 232 W / 1.868 W | 2.540 | 1.372 W / 2.403 W |

Laden: am 20.10. **kein Gerät** (Ist nie negativ). Am 07.10. luden ZSF800P1 (695 Zyklen) und ZSF2400P1 (1.036 Zyklen).
Das bevorzugte Gerät wechselte am 20.10. 11-mal durch den SoC-Ausgleich (07.10.: 8-mal).

---

## 4) SoC-Verlauf je Gerät

![SoC-Verlauf je Gerät 20.10.](chart_soc_20.10.png)

| Gerät | Start → Ende 20.10. | Min (Zeit) 20.10. | Start → Ende 07.10. | Min 07.10. |
|---|---|---|---|---|
| ZSF800P1 | 97 % → 40 % | 40 % (23:14) | 71 % → 60 % | 60 % |
| ZSF800P2 | 100 % → 40 % | 40 % (23:02) | 67 % → 63 % | 63 % |
| ZSF2400P1 | 99 % → 40 % | 40 % (12:50) | 64 % → 22 % | 22 % |

| Gerät | socLimit | von – bis (20.10.) | SoC |
|---|---|---|---|
| ZSF800P2 | 1 | 00:00 – 00:13 | 100 % → 98 % |
| ZSF2400P1 | 1 | 00:00 – 00:52 | 99 % → 98 % |
| ZSF2400P1 | 2 | 12:50 – 12:52 | 40 % → 41 % |
| ZSF2400P1 | 2 | 13:03 – 13:05 | 40 % → 41 % |
| ZSF2400P1 | 2 | 21:20 – Ende | 40 % |
| ZSF800P2 | 2 | 23:02 – Ende | 40 % |
| ZSF800P1 | 2 | 23:14 – Ende | 40 % |

Kein socLimit 3 am 20.10. (07.10.: ZSF800P1 14:41–16:12).

---

## 7) Skips in den Intervallen

| Abstand zwischen zwei Zyklen | 20.10. | 07.10. |
|---|---|---|
| ≤ 2 s | 0,3 % | 1,2 % |
| 3–6 s (Soll 4,5 s) | 99,1 % | 97,2 % |
| 7–9 s | 0,6 % | 1,6 % |
| > 9 s | 7-mal (max. 25 s beim Start 00:00) | 14-mal (max. 35 s) |

Übersprungene Takte: **66** (07.10.: 122), davon 32 zwischen 10 und 12 Uhr.

| Sparmodus | 20.10. | 07.10. |
|---|---|---|
| Sparmodus gestartet | 1.253-mal | 1.255-mal |
| Vorzeitig beendet | 801-mal | 413-mal |
| Zyklen ohne Geräte-Poll | 7.817 (**40,9 %**) | 10.035 (52,7 %) |
| Zyklen mit Geräte-Poll | 11.299 (59,1 %) | 9.019 (47,3 %) |
| Schreibvorgänge (Leistung gesetzt) | 5.758 | 3.731 |

---

## 9) Fehler im Log

| Fehler | 20.10. | 07.10. |
|---|---|---|
| Verbindungsfehler ZSF800P1 | 7 (04:49, 05:57, 10:27, 10:42 ×2, 10:48 ×2) | 0 |
| Verbindungsfehler ZSF800P2 | 10 (01:10, 02:03, 02:46, 05:00, 07:46, 10:06, 10:08, 10:26, 13:09, 13:16) | 0 |
| Verbindungsfehler ZSF2400P1 | 1 (01:07) | 2 |
| Höchste Fehlerfolge | 2 | 1 |
| Takt übersprungen | 66 | 122 |
| Watchdog-Timeout | 0 | 0 |
| Schreibvorgang fehlgeschlagen | 0 | 0 |

Die Regelung lief nach jedem Fehler selbständig weiter. Die Ereignisdatei meldet ein Ende per SIGTERM um 00:00:03 (21.10.), das ist das Ende des Aufzeichnungsfensters.

---

## 14) gridReverseMode

- Eingestellt: **dynamic** (wie am 07.10.).

| Uhrzeit | gridReverse | Auslöser | SoC ZSF800P1 / ZSF800P2 / ZSF2400P1 |
|---|---|---|---|
| 00:00 (Logbeginn) | **2** bei allen Geräten | Zustand vom Vortag übernommen | 97 % / 100 % / 99 % |
| 02:35:25–26 | 2 → **1** (alle Geräte) | ZSF800P1 unter 90 % (maxSoc − 10) | 89 % / 94 % / 92 % |

Danach blieb gridReverse bis Logende auf 1. Eine Umschaltung auf 2 gab es am 20.10. nicht, weil nie alle Geräte gleichzeitig socLimit 1 hatten.
Am 07.10.: 14:11 auf 2 (alle bei 100 %), 14:37 zurück auf 1 (ZSF2400P1 bei 89 %).
