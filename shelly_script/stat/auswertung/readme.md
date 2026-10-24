# Auswertung Zendure-Speicher (Multi-Device-Controller)

Statistische Auswertung der Debug-Logs des Multi-Device-Controllers.
Standard: alle Logs `shelly_debug_*.log` im Ordner über `auswertung` (einstellbar, siehe Einstellungen).

## Dateien

| Datei | Inhalt |
|---|---|
| `analyse.py` | Liest alle Logs neu ein und schreibt die drei CSV-Dateien. Einzige Rechenquelle; alle Einstellungen stehen oben im Block `EINSTELLUNGEN`. |
| `verlauf_15min.csv` | 15-Minuten-Mittel: Netzsaldo, Speicher-Ausgang (Summe), SOC und Ausgang je Gerät |
| `tage.csv` | Pro Tag: Energie (kWh), Aktivzeit (h), SOC-Min/-Max, Regelgüte, Stellbefehle, Störungen, Sparmodus-Takte |
| `geraete.csv` | Die ausgewerteten Geräte (Name wie im Log, Spaltenschlüssel). Schreibt `analyse.py`, liest `bericht.py`. |
| `tagesprofil.csv` | Pro Uhrzeit-Stunde: mittlerer Netzsaldo und Speicher-Ausgang; je Gerät SOC-Min/-Max und Perzentile 10/25/50/75/90 |
| `bericht.py` | Erzeugt `bericht.html` aus den CSV-Dateien. Wird am Ende von `analyse.py` automatisch aufgerufen, geht aber auch einzeln (`python bericht.py`). Hat keine eigenen Einstellungen. |
| `bericht.html` | **Bericht** zum Öffnen im Browser, eine einzelne Datei ohne Internetverbindung (Daten, Schriften und Zeichen-Skript eingebettet). Design wie Dashboard/Konfigurator mit Tag/Nacht-Umschalter. Zeitlicher Zoom, Werte beim Darüberfahren. |
| `zendure_fonts.css` | IBM-Plex-Schriften aus dem Dashboard; `bericht.py` bettet sie ein. Fehlt die Datei, nimmt der Bericht die Systemschrift. |
| `dashboard_seite.html` | Quelltext der Online-Dashboard-Seite (Grafiken, Berechnungen `kpi` und `fritzbox`). Eigenständig, von den Skripten nicht berührt. |

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

1. Neue Logs in den Log-Ordner legen (Standard: der Ordner über `auswertung`, also `../`).
2. `python <Pfad zu>/auswertung/analyse.py` ausführen – geht aus jedem Verzeichnis.
   Liegen die Logs woanders: `LOG_ORDNER` setzen oder den Ordner mitgeben
   (`python analyse.py <logordner>`).
   Das schreibt die CSV-Dateien neu und erzeugt danach `bericht.html`.
3. Nichts nachzupflegen: Mit `ZEITRAUM_BIS = None` geht die Auswertung bis zum Ende der Logs,
   Tageswerte und Tagesprofil nehmen automatisch nur volle Tage.
4. Für das Dashboard: Claude bitten, „die Speicher-Statistik mit den neuen Logs fortzuschreiben“.
   Claude lädt dann die drei CSV als neue Dateien ins Dashboard und trägt sie bei den Quellen
   `verlauf`, `tage` und `profil` ein. Die Seite selbst muss dafür nicht geändert werden.

## Bericht bedienen

- **Zeitraum-Leiste** (bleibt beim Scrollen oben): `Alles`, `7 T`, `3 T`, `1 T`; `−`/`+` zoomen heraus/hinein,
  `‹`/`›` verschieben um einen halben Ausschnitt. Kleinster Ausschnitt: 2 Stunden.
- **Verlauf-Grafiken**: mit der Maus einen Bereich aufziehen = hineinzoomen, Doppelklick = alles.
- **Tages-Grafiken**: Klick auf einen Tag zoomt auf diesen Tag.
- Der Zeitraum gilt für Kennzahlen, Verlauf und Tageswerte (alle vollen Tage, die den Ausschnitt berühren).
  Das Tagesprofil zeigt immer alle vollen Tage.
- **☾ / ☀** oben rechts schaltet Tag/Nacht um; die Wahl merkt sich der Browser, sonst gilt die Systemeinstellung.

## Einstellungen (Block `EINSTELLUNGEN` oben in `analyse.py`)

| Variable | Standard | Bedeutung |
|---|---|---|
| `LOG_ORDNER` | `None` | Ordner mit den Logs; `None` = Ordner über dem Skript. Ein Aufrufparameter hat Vorrang. |
| `LOG_MUSTER` | `shelly_debug_*.log` | Muster der Logdateinamen (`*` = beliebige Zeichen, `?` = ein Zeichen) |
| `ZEITRAUM_VON` | `2026-10-06` | Beginn der Auswertung (einschließlich); `None` = ab erstem Log. Der Einzeltag 20.09. bleibt so außen vor. |
| `ZEITRAUM_BIS` | `None` | Ende der Auswertung (einschließlich); `None` = bis zum Ende der Logs |
| `GERAETE` | `None` | `None` = alle Geräte aus dem Log, in der Reihenfolge ihres ersten Auftretens. Oder eine Liste wie `["SF2400", "SF800"]`: nur diese, in dieser Reihenfolge. Ein, zwei, drei oder mehr Geräte. |
| `TAKT_S` | 4 | übliche Taktlänge in Sekunden |
| `MAX_LUECKE_S` | 30 | Lücken darüber zählen nicht als Energie |
| `VOLLER_TAG_H` | 22 | ab so vielen erfassten Stunden gilt ein Tag als voll |
| `LEER_SCHWELLE_W` | 30 | Ist-Summe darunter = Speicher liefert nichts |
| `SATT_SCHWELLE_W` | 1500 | Ist-Summe ab hier = Speicher am Limit |
| `BAND_W` | 25 | Regelgüte: Takt gilt als gut bei \|Netzsaldo\| bis zu diesem Wert |
| `SOC_PERZENTILE` | 10, 25, 50, 75, 90 | Perzentile der SOC-Verteilung je Stunde im Tagesprofil. Der Bericht zeichnet 10/25/50/75/90 – diese fünf drin lassen, weitere nur ergänzen. |
| `AKTIV_SCHWELLE_W` | 10 | Gerät gilt als aktiv, wenn es mindestens so viel ins Haus abgibt |

`bericht.py` liest diese Werte für Titel und Beschriftungen mit. Der Bericht zeigt bei Tageswerten,
Kennzahlen und Tagesprofil alle vollen Tage im Zeitraum.

## Mehrere oder einzelne Geräte

Der Bericht passt sich der Anzahl der Geräte an: Farben je Gerät (vier eigene, danach wiederholt),
eine SOC-Verteilung je Gerät, und die Texte stehen in Einzahl oder Mehrzahl („aus dem Speicher“ /
„aus den Speichern“). Bei nur einem Gerät entfallen „Mindestens ein Gerät“ und „(Summe)“.
Netzsaldo und Ist-Summe kommen aus der Summenzeile des Logs; sie enthalten also alle Geräte, die der
Controller regelt, auch wenn `GERAETE` nur einen Teil davon auswählt.

## Definitionen

Zahlen in Klammern sind die Standardwerte aus dem Block `EINSTELLUNGEN`.

- **Takt**: eine Zeile `Netzsaldo: …` im Log, etwa alle `TAKT_S` (4 s, ca. 21.600 pro Tag).
- **Energie**: Leistung × Zeit bis zum nächsten Takt; Lücken über `MAX_LUECKE_S` (30 s) zählen nicht.
- **Netzbezug / Einspeisung**: Netzsaldo > 0 bzw. < 0. Setpoint ist 0 W.
- **Entladung je Gerät**: positiver `Ist`-Wert des Geräts. Netzladen: negativer `Ist`-Wert.
  PV-Ladung steht nicht im Log, sie zeigt sich nur am SOC-Anstieg.
- **Bezug bei leerem Speicher**: Netzsaldo > 0, während die Ist-Summe aller Geräte unter `LEER_SCHWELLE_W` (30 W) liegt.
- **Aktivzeit**: Stunden pro Tag, in denen ein Gerät mindestens `AKTIV_SCHWELLE_W` (10 W) ins Haus abgibt
  (positiver `Ist`-Wert; ein eigenes Feld `outputHomePower` steht nicht im Log). „Mindestens ein Gerät“
  nutzt die Ist-Summe und zählt gleichzeitige Abgabe nur einmal. Lücken über `MAX_LUECKE_S` zählen nicht.
- **Deckung**: Entladung ÷ (Entladung + Netzbezug).
- **Regelgüte**: Anteil der Takte mit |Netzsaldo| ≤ `BAND_W` (25 W), solange die Ist-Summe zwischen `LEER_SCHWELLE_W` und `SATT_SCHWELLE_W` (30 bis 1500 W) liegt.
- **Voller Tag**: mindestens `VOLLER_TAG_H` (22 h) erfasst. Nur volle Tage gehen in Tageswerte, Kennzahlen und Tagesprofil des Berichts ein.
- **Takt ohne Geräteabfrage (Sparmodus)**: Nach `Sparmodus an: 12 Zyklen ohne Geraete-Poll`
  zählen die nächsten 12 Takte als eingespart, außer `Sparmodus aus` / `beendet` / Neustart kommt vorher.
  Ältere Logs (bis 08.10.) melden das als `setze Polling fuer 12 Zyklen aus`.
  Wie viele Einzelanfragen an die Geräte das spart, lässt sich aus dem Log nicht ablesen.

## Festlegungen

- SOC nach Uhrzeit wird als Verteilung je Gerät dargestellt: Median als Linie, Bänder für 25–75 % und 10–90 %.
  Grundlage sind alle Takte der jeweiligen Stunde an allen vollen Tagen. Min/Max stehen nur noch im Hinweis beim Darüberfahren.
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
  Fritzbox-Markierung und Vorher/Nachher-Vergleich aus dem Bericht entfernt. README angepasst.
- 24.10.2026: Aktivzeit pro Tag ergänzt (Spalten `aktiv_<gerät>_h`, `aktiv_gesamt_h` in `tage.csv`,
  gruppierte Balkengrafik im Bericht), Einstellung `AKTIV_SCHWELLE_W`.
- 24.10.2026: Bericht im Design von Dashboard/Konfigurator (Titel „ZENDURE // TAGESSTATISTIK“, Geräte darunter,
  Tag/Nacht-Umschalter, IBM Plex über `zendure_fonts.css`). Zeitlicher Zoom für Verlauf, Kennzahlen und Tageswerte;
  die Grafiken zeichnet jetzt ein eingebettetes Skript.
- 24.10.2026: „SOC nach Uhrzeit“ als Verteilung (Median + Bänder 25–75 % und 10–90 %) je Gerät statt Min/Max;
  `tagesprofil.csv` um Perzentil-Spalten `soc_p10_<gerät>` … `soc_p90_<gerät>` erweitert, Einstellung `SOC_PERZENTILE`.
  „Störungen pro Tag“ in die Gruppe „Pro Tag“ verschoben.
- 24.10.2026: Beliebig viele Geräte: `GERAETE = None` erkennt sie automatisch (Namen nicht mehr auf `SF…` beschränkt),
  `geraete.csv` neu, Texte im Bericht in Einzahl/Mehrzahl, zwei weitere Gerätefarben.
