# Auswertung Speicher SF2400 + SF800

Statistische Auswertung der Debug-Logs des Multi-Device-Controllers (`../shelly_debug_*.log`).



## Dateien

| Datei | Inhalt |
|---|---|
| `analyse.py` | Liest alle Logs neu ein und schreibt die drei CSV-Dateien. Einzige Rechenquelle; alle Einstellungen stehen oben im Block `EINSTELLUNGEN`. |
| `verlauf_15min.csv` | 15-Minuten-Mittel: Netzsaldo, Speicher-Ausgang (Summe), SOC und Ausgang je Gerät |
| `tage.csv` | Pro Tag: Energie (kWh), SOC-Min/-Max, Regelgüte, Stellbefehle, Störungen, Sparmodus-Takte |
| `tagesprofil.csv` | Pro Uhrzeit-Stunde: mittlerer Netzsaldo und Speicher-Ausgang, SOC-Min/-Max je Gerät |
| `bericht.py` | Erzeugt `bericht.html` aus den CSV-Dateien. Wird am Ende von `analyse.py` automatisch aufgerufen, geht aber auch einzeln (`python bericht.py`). Hat keine eigenen Einstellungen. |
| `bericht.html` | **Statischer Bericht** zum Öffnen im Browser: alle Grafiken als fertige SVG, kein JavaScript, keine Internetverbindung nötig. Werte erscheinen beim Darüberfahren über Punkte und Balken. |
| `dashboard_seite.html` | Quelltext der Online-Dashboard-Seite (Grafiken, Berechnungen `kpi` und `fritzbox`) |

## Einmalig: pandas installieren

Das Skript braucht Python 3.9+ und das Paket `pandas`. Fehlt es, bricht es ab mit
`ModuleNotFoundError: No module named 'pandas'`. Installation in cmd oder PowerShell:

```
py -m pip install pandas
```

Wird `py` nicht gefunden:

```
python -m pip install pandas
```

Kommt der Fehler danach weiterhin, gehören `pip` und `python` zu verschiedenen
Python-Installationen. `py -0p` listet alle installierten Versionen mit Pfad.

## Fortschreiben

1. Neue Logs wie bisher in `D:\Uspace\git\stat` ablegen.
2. `python D:\Uspace\git\stat\auswertung\analyse.py` ausführen.
   Das schreibt die CSV-Dateien neu und erzeugt danach `bericht.html`.
3. Nichts nachzupflegen: Mit `ZEITRAUM_BIS = None` geht die Auswertung bis zum Ende der Logs,
   Tageswerte und Tagesprofil nehmen automatisch nur volle Tage.
4. Für das Dashboard: Claude bitten, „die Speicher-Statistik mit den neuen Logs fortzuschreiben“.
   Claude lädt dann die drei CSV als neue Dateien ins Dashboard und trägt sie bei den Quellen
   `verlauf`, `tage` und `profil` ein. Die Seite selbst muss dafür nicht geändert werden.

## Definitionen

- **Takt**: eine Zeile `Netzsaldo: …` im Log, etwa alle 4 s (ca. 21.600 pro Tag).
- **Energie**: Leistung × Zeit bis zum nächsten Takt; Lücken über 30 s zählen nicht.
- **Netzbezug / Einspeisung**: Netzsaldo > 0 bzw. < 0. Setpoint ist 0 W.
- **Entladung je Gerät**: positiver `Ist`-Wert des Geräts. Netzladen: negativer `Ist`-Wert.
  PV-Ladung steht nicht im Log, sie zeigt sich nur am SOC-Anstieg.
- **Bezug bei leerem Speicher**: Netzsaldo > 0, während die Ist-Summe beider Geräte unter 30 W liegt.
- **Deckung**: Entladung ÷ (Entladung + Netzbezug).
- **Regelgüte**: Anteil der Takte mit |Netzsaldo| ≤ 25 W, solange die Ist-Summe zwischen 30 und 1500 W liegt.
- **Voller Tag**: mindestens 22 h erfasst.
- **Takt ohne Geräteabfrage (Sparmodus)**: Nach `Sparmodus an: 12 Zyklen ohne Geraete-Poll`
  zählen die nächsten 12 Takte als eingespart, außer `Sparmodus aus` / `beendet` / Neustart kommt vorher.
  Ältere Logs (bis 08.10.) melden das als `setze Polling fuer 12 Zyklen aus`.
  Wie viele Einzelanfragen an die Geräte das spart, lässt sich aus dem Log nicht ablesen.

## Einstellungen (Block `EINSTELLUNGEN` oben in `analyse.py`)

| Variable | Standard | Bedeutung |
|---|---|---|
| `LOG_ORDNER` | `None` | Ordner mit den Logs; `None` = Ordner über dem Skript. Ein Aufrufparameter hat Vorrang. |
| `LOG_MUSTER` | `shelly_debug_*.log` | Muster der Logdateinamen (`*` = beliebige Zeichen, `?` = ein Zeichen) |
| `ZEITRAUM_VON` | `2026-10-06` | Beginn der Auswertung (einschließlich); `None` = ab erstem Log. Der Einzeltag 20.09. bleibt so außen vor. |
| `ZEITRAUM_BIS` | `None` | Ende der Auswertung (einschließlich); `None` = bis zum Ende der Logs |
| `GERAETE` | `SF2400`, `SF800` | Gerätenamen wie im Log; Reihenfolge = Reihenfolge im Bericht |
| `TAKT_S` | 4 | übliche Taktlänge in Sekunden |
| `MAX_LUECKE_S` | 30 | Lücken darüber zählen nicht als Energie |
| `VOLLER_TAG_H` | 22 | ab so vielen erfassten Stunden gilt ein Tag als voll |
| `LEER_SCHWELLE_W` | 30 | Ist-Summe darunter = Speicher liefert nichts |
| `SATT_SCHWELLE_W` | 1500 | Ist-Summe ab hier = Speicher am Limit |
| `BAND_W` | 25 | Regelgüte: Takt gilt als gut bei \|Netzsaldo\| bis zu diesem Wert |

`bericht.py` liest diese Werte für Titel und Beschriftungen mit. Der Bericht zeigt bei Tageswerten,
Kennzahlen und Tagesprofil alle vollen Tage im Zeitraum.

## Festlegungen

- SOC nach Uhrzeit wird als Min/Max dargestellt, nicht als Mittel.
- Energie pro Tag als gestapelte Balken: Entladung je Gerät,
  Bezug bei leerem Speicher, übriger Bezug.

## Ergebnisse bis 23.10.2026

- Regelung: rund 94 % der Takte im ±25-W-Band, typische Abweichung 4–6 W.
- Rund 90 % des Netzbezugs fallen bei leerem Speicher an (Kapazität/PV-Ertrag, nicht Regelung).
- Morgens 7–9 Uhr höchster Bezug bei niedrigstem SOC.
- Sparmodus: 65–80 % der Takte ohne Geräteabfrage, am meisten an ruhigen Tagen.

## Änderungsprotokoll

- 24.10.2026: Erstfassung. Spaltenvertauschung im 15-Minuten-Export korrigiert
  (SOC SF800 zeigte zuvor die Ausgangsleistung des SF2400). Energie als gestapelte Balken,
  SOC-Profil als Min/Max, Fritzbox-Vergleich und Sparmodus ergänzt.
- 24.10.2026: Abschnitt zur Installation von pandas ergänzt.
- 24.10.2026: `bericht.py` ergänzt; `analyse.py` erzeugt jetzt zusätzlich den statischen `bericht.html`.
- 24.10.2026: Einstellungen gesammelt und dokumentiert in `analyse.py` (Block `EINSTELLUNGEN`).
  Ein Zeitraum `ZEITRAUM_VON`/`ZEITRAUM_BIS` statt `VERLAUF_AB`/`PROFIL_VON`/`PROFIL_BIS`;
  Tagesprofil über alle vollen Tage. Logdateimuster einstellbar (`LOG_MUSTER`).
  `bericht.py` ohne eigene Einstellungen, Geräte und Schwellwerte aus `analyse.py`.
  Fritzbox-Markierung und Vorher/Nachher-Vergleich entfernt.
