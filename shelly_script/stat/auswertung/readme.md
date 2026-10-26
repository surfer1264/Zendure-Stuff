# Auswertung Zendure-Speicher

Statistische Auswertung der Debug-Logs des Multi-Device-Controllers (Shelly-Skript) für einen
oder mehrere Zendure-Speicher. `analyse.py` liest die Logs ein und schreibt CSV-Dateien,
`bericht.py` erzeugt daraus einen Bericht zum Öffnen im Browser.

Version: **1.4.0** (steht als `VERSION` in `analyse.py` und erscheint in der Ausgabe und unten im Bericht).

## Download

Die Dateien liegen im Repository [surfer1264/Zendure-Stuff](https://github.com/surfer1264/Zendure-Stuff)
im Ordner [`shelly_script/stat/auswertung`](https://github.com/surfer1264/Zendure-Stuff/tree/main/shelly_script/stat/auswertung).

Benötigt werden `analyse.py`, `bericht.py` und `zendure_fonts.css`, unter Windows optional `analyse.cmd`.

- **Einzelne Dateien:** Datei im Ordner anklicken, dann oben rechts „Download raw file“.
- **Ganzes Repository als ZIP:** [main.zip](https://github.com/surfer1264/Zendure-Stuff/archive/refs/heads/main.zip)
  herunterladen und den Ordner `shelly_script/stat/auswertung` entpacken.
- **Mit Git, nur dieser Ordner:**

  ```
  git clone --depth 1 --filter=blob:none --sparse https://github.com/surfer1264/Zendure-Stuff
  cd Zendure-Stuff
  git sparse-checkout set shelly_script/stat/auswertung
  ```

## Installation

Benötigt werden Python 3.9 oder neuer und das Paket `pandas`. Installation in cmd oder PowerShell:

```
py -m pip install pandas
```

Wird `py` nicht gefunden:

```
python -m pip install pandas
```

Meldet das Skript danach weiterhin `ModuleNotFoundError: No module named 'pandas'`, gehören `pip`
und `python` zu verschiedenen Python-Installationen. `py -0p` listet alle installierten Versionen mit Pfad.

Die Dateien `analyse.py`, `bericht.py` und `zendure_fonts.css` liegen gemeinsam in einem Ordner
(hier `auswertung`). Standardmäßig erwartet das Skript die Logs im Ordner darüber.

## Benutzung

1. Logs des Multi-Device-Controllers in den Log-Ordner legen (Standard: der Ordner über `auswertung`).
2. Auswertung starten – geht aus jedem Verzeichnis:

   ```
   python <Pfad zu>/auswertung/analyse.py
   ```

   Liegen die Logs woanders, entweder `LOG_ORDNER` setzen oder den Ordner mitgeben:

   ```
   python analyse.py <logordner>
   ```

   Unter Windows geht das auch per Doppelklick auf `analyse.cmd`.
3. `bericht.html` im Browser öffnen.

Bei neuen Logs einfach erneut starten. Solange `ZEITRAUM_BIS = None` ist, muss nichts angepasst werden:
Die Auswertung reicht bis zum Ende der Logs, Tageswerte nutzen automatisch nur volle Tage.
`bericht.py` lässt sich auch einzeln starten (`python bericht.py`); es nutzt dann die vorhandenen CSV-Dateien.

### Zwischenspeicher und gepackte Logs

- Jedes Log (ein Tag) wird nur einmal ausgewertet. Das Ergebnis liegt im Ordner `cache/` neben dem Skript
  (eine kleine Datei je Log). Spätere Läufe lesen nur neue oder geänderte Logs, meist nur das heutige.
- Ändern sich Einstellungen, die das Ergebnis beeinflussen, oder die Version, rechnet das Skript
  automatisch alles neu. Von Hand: `python analyse.py --neu` verwirft den Zwischenspeicher.
- Mit `LOGS_PACKEN = True` werden abgeschlossene Logs nach der Auswertung gepackt
  (`….log` → `….log.gz`, etwa 25-mal kleiner). Das Original wird erst gelöscht, nachdem der Inhalt
  der gepackten Datei geprüft ist. Das jüngste Log bleibt ungepackt, ebenso Logs, die vor weniger als
  10 Minuten noch geändert wurden.
- Gepackte Logs werden genauso gelesen wie ungepackte; eine Neuberechnung ist jederzeit möglich.
  Liegt ein Log gepackt und ungepackt vor, gilt das ungepackte.
- Der Ordner `cache/` lässt sich jederzeit löschen; er wird beim nächsten Lauf neu aufgebaut.

### Bericht bedienen

- **Zeitraum-Leiste** (bleibt beim Scrollen oben): `Alles`, `7 T`, `3 T`; `−`/`+` zoomen heraus
  bzw. hinein, `‹`/`›` verschieben um einen halben Ausschnitt. Kleinster Ausschnitt: 2 Stunden.
- **Verlauf-Grafiken**: mit der Maus einen Bereich aufziehen = hineinzoomen, Doppelklick = alles.
  Auf Handy/Tablet zeigt Antippen die Werte; gezoomt wird dort über die Knöpfe der Leiste.
- **Tages-Grafiken**: Klick auf einen Tag zoomt auf diesen Tag.
- Der gewählte Zeitraum gilt für Kennzahlen, Verlauf und Tageswerte (alle vollen Tage, die den
  Ausschnitt berühren). Das Tagesprofil zeigt immer alle vollen Tage.
- **☾ / ☀** oben rechts schaltet Tag/Nacht um. Die Wahl merkt sich der Browser, sonst gilt die Systemeinstellung.
- Werte zu Punkten, Balken und Stunden erscheinen beim Darüberfahren.

## Einstellungen

Die Standardwerte stehen im Block `EINSTELLUNGEN` oben in `analyse.py`. `bericht.py` hat keine
eigenen Einstellungen; es übernimmt Schwellwerte und Taktlänge für seine Beschriftungen von dort
und die Geräte aus `geraete.csv`.

### Eigene Einstellungen: `analyse_config.json`

Damit eigene Werte ein Update überstehen, gehören sie nicht in `analyse.py`, sondern in die Datei
`analyse_config.json` neben dem Skript. Sie wird nicht ins Git übernommen und bei einem Update
nicht überschrieben.

- Gibt es die Datei, gelten ihre Werte; alles, was darin fehlt, behält den Standardwert.
- Gibt es sie nicht, gelten die Standardwerte aus `analyse.py`.
- Schlüssel wie die Variablen in der Tabelle unten. JSON-Schreibweise: `null` statt `None`,
  `true`/`false` statt `True`/`False`, Texte in doppelten Anführungszeichen, Listen in `[ ]`.
  Kommentare sind in JSON nicht erlaubt.
- Unbekannte Schlüssel (z. B. Tippfehler) meldet das Skript als Warnung und ignoriert sie.

Beispiel:

```json
{
  "ZEITRAUM_VON": "2026-10-06",
  "ZEITRAUM_BIS": null,
  "GERAETE": ["SF2400", "SF800"],
  "BAND_W": 25,
  "LOGS_PACKEN": true
}
```

| Variable | Bedeutung |
|---|---|
| `LOG_ORDNER` | Ordner mit den Logs; `None` = Ordner über dem Skript. Ein Aufrufparameter hat Vorrang. |
| `LOG_MUSTER` | Muster der Logdateinamen, z. B. `shelly_debug_*.log` (`*` = beliebige Zeichen, `?` = ein Zeichen). Gepackte Logs (Muster + `.gz`) werden mitgelesen. |
| `LOGS_PACKEN` | `True` = abgeschlossene Logs nach der Auswertung packen (`.log` → `.log.gz`); `False` = Logs unverändert lassen. |
| `ZEITRAUM_VON` | Beginn der Auswertung als `JJJJ-MM-TT` (einschließlich); `None` = ab erstem Log. |
| `ZEITRAUM_BIS` | Ende der Auswertung (einschließlich); `None` = bis zum Ende der Logs. |
| `GERAETE` | `None` = alle Geräte aus dem Log, in der Reihenfolge ihres ersten Auftretens. Oder eine Liste wie `["SF2400", "SF800"]`: nur diese, in dieser Reihenfolge. Namen genau wie im Log schreiben; Leerzeichen und Umlaute sind erlaubt (`["Keller Süd", "SF800"]`). |
| `TAKT_S` | Taktlänge in Sekunden; `None` = automatisch aus dem Log (Median der Abstände). |
| `MAX_LUECKE_S` | Lücken zwischen zwei Takten über diesem Wert zählen nicht als Energie bzw. Aktivzeit. |
| `VOLLER_TAG_H` | Ab so vielen erfassten Stunden gilt ein Tag als voll. |
| `LEER_SCHWELLE_W` | Ist-Summe darunter = kein Speicher liefert. |
| `SATT_SCHWELLE_W` | Ist-Summe ab hier = Speicher am Limit; solche Takte zählen nicht für die Regelgüte. |
| `BAND_W` | Regelgüte: Ein Takt gilt als gut bei \|Netzsaldo\| bis zu diesem Wert. |
| `PROFIL_PERZENTILE` | Perzentile der Verteilung je Stunde im Tagesprofil (SOC, Netzsaldo, Speicher-Ausgang). Der Bericht zeichnet 10/25/50/75/90 – diese fünf drin lassen, weitere nur ergänzen. |
| `AKTIV_SCHWELLE_W` | Ein Gerät gilt als aktiv, solange es mindestens so viel ins Haus abgibt. |
| `SOLLWERT_START_W` | Sollwert, solange das Log noch keinen gemeldet hat (nur am Anfang des ersten Logs relevant). Danach gilt der Wert aus dem Log. |
| `NEUSTART_ABSTAND_S` | Startzeilen des Controllers, die näher als dieser Abstand beieinander liegen, zählen als ein Neustart. |

## Erklärung

### Dateien

| Datei | Inhalt |
|---|---|
| `analyse.py` | Wertet die Logs aus (mit Zwischenspeicher), schreibt die CSV-Dateien, packt abgeschlossene Logs und ruft danach `bericht.py` auf. Einzige Rechenquelle. |
| `analyse.cmd` | Startet `analyse.py` per Doppelklick (Windows). |
| `bericht.py` | Erzeugt `bericht.html` aus den CSV-Dateien. |
| `zendure_fonts.css` | IBM-Plex-Schriften; werden in den Bericht eingebettet. Fehlt die Datei, nutzt der Bericht die Systemschrift. |
| `verlauf_15min.csv` | 15-Minuten-Mittel: Netzsaldo, Speicher-Ausgang (Summe), SOC und Ausgang je Gerät. |
| `tage.csv` | Pro Tag: Energie, Aktivzeit, SOC-Min/-Max, Regelgüte (gegen den gültigen Sollwert), Sollwert (`sollwert_min_w`, `sollwert_max_w`), Versatz (`regel_versatz_w`), Stellbefehle, Störungen, Sparmodus-Takte, Zyklusdauer (`zyklus_avg_ms`, `zyklus_max_ms`, `zyklus_interval_ms`, ab Controller 5.2.6, sonst leer), Kennzeichen „voller Tag“. |
| `tagesprofil.csv` | Pro Uhrzeit-Stunde über alle vollen Tage: Netzsaldo und Speicher-Ausgang (Mittel und Perzentile über die Tage, Anzahl Tage); je Gerät SOC-Min/-Max und Perzentile. |
| `geraete.csv` | Die ausgewerteten Geräte: Name wie im Log und Spaltenschlüssel (z. B. `Keller Süd` → `keller_sued`). |
| `cache/` | Zwischenspeicher: Auswertung je Log. Kann gelöscht werden, wird neu aufgebaut. |
| `bericht.html` | Der Bericht: eine einzelne Datei, die ohne Internetverbindung funktioniert (Daten, Schriften und Zeichen-Skript eingebettet). |

### Inhalt des Berichts

- **Kennzahlen** für den gewählten Zeitraum: Entladung, Netzbezug, Deckung, Regelgüte, Aktivzeit, Sparmodus.
- **Verlauf über die Zeit**: SOC je Gerät, Netzsaldo und Speicher-Ausgang (15-Minuten-Mittel).
- **Pro Tag**: Energie nach Herkunft (gestapelt), Aktivzeit je Gerät, Deckung, Regelgüte,
  Stellbefehle je Gerät, Störungen, Zyklusdauer (Ø, max und Intervall; nur mit Logs ab Controller 5.2.6).
- **Sparmodus**: Takte mit und ohne Geräteabfrage, Anteil eingesparter Takte.
- **Typischer Tagesverlauf**: Netzsaldo, Speicher-Ausgang und SOC je Gerät nach Uhrzeit, jeweils als Verteilung
  über die vollen Tage (Linie = Median, Bänder = 25–75 % und 10–90 %).

### Ein oder mehrere Geräte

Gerätename ist alles, was im Log vor `: SOC …` steht, also auch mit Leerzeichen oder Umlauten
(`  Keller Süd: SOC 45% | …`). Für die Spalten der CSV-Dateien bildet das Skript daraus einen Schlüssel:
klein geschrieben, Umlaute umschrieben, alle anderen Zeichen als `_` – aus „Keller Süd“ wird `keller_sued`,
die Spalten heißen dann z. B. `soc_keller_sued` und `entladung_keller_sued_kwh`. Ergäben zwei Namen denselben
Schlüssel, bekommt der zweite eine Nummer (`_2`). Im Bericht steht immer der Name wie im Log.

Der Bericht passt sich der Anzahl der Geräte an: eigene Farbe je Gerät (vier Farben, danach wiederholt),
eine SOC-Verteilung je Gerät, Texte in Einzahl oder Mehrzahl. Bei nur einem Gerät entfallen
„Mindestens ein Gerät“ und „(Summe)“. Netzsaldo und Ist-Summe stammen aus der Summenzeile des Logs;
sie enthalten alle Geräte, die der Controller regelt, auch wenn `GERAETE` nur einen Teil auswählt.

### Definitionen

- **Takt**: eine Zeile `Netzsaldo: …` im Log.
- **Energie**: Leistung × Zeit bis zum nächsten Takt; Lücken über `MAX_LUECKE_S` zählen nicht.
  Der letzte Takt eines Logs zählt mit der Taktlänge `TAKT_S`.
- **Netzbezug / Einspeisung**: Netzsaldo > 0 bzw. < 0. Der Netzsaldo im Log ist der tatsächliche Wert am
  Netzanschluss; Energie, Bezug und Einspeisung hängen nicht am Sollwert.
- **Sollwert**: der Wert, auf den der Controller regelt. Das Skript liest ihn aus dem Startblock
  (`Setpoint   : 0 W`) und aus jeder Änderung `KVS zdmc_setpoint: Wert uebernommen (a -> b)`; ab dort gilt er
  für jeden folgenden Takt, auch über Mitternacht ins nächste Log. Der Controller übernimmt den KVS-Wert vor
  „Starte Regelbetrieb“, es gibt also keine Regeltakte mit dem vorläufigen Wert aus dem Startblock.
- **Entladung je Gerät**: positiver `Ist`-Wert des Geräts. **Netzladen**: negativer `Ist`-Wert.
  PV-Ladung steht nicht im Log, sie zeigt sich nur am SOC-Anstieg.
- **Netzbezug bei leerem Speicher** (bei mehreren Geräten: „bei leeren Speichern“): Netzsaldo > 0,
  während die Ist-Summe unter `LEER_SCHWELLE_W` liegt.
- **Deckung**: Entladung ÷ (Entladung + Netzbezug).
- **Regelgüte**: Anteil der Takte mit |Netzsaldo − Sollwert| ≤ `BAND_W`, solange die Ist-Summe zwischen
  `LEER_SCHWELLE_W` und `SATT_SCHWELLE_W` liegt. Tage ohne solche Takte haben keinen Wert (Lücke statt 0 %).
  `regel_median_abw_w` ist der Median von |Netzsaldo − Sollwert| in diesen Takten.
- **Versatz** (`regel_versatz_w`): Median von Netzsaldo − Sollwert im Regelbetrieb, mit Vorzeichen. Er sollte
  nahe 0 liegen. Weicht er an einem Tag um mehr als `BAND_W`/2 ab, meldet das Skript einen Hinweis:
  Dann ist womöglich eine Sollwert-Änderung im Log verschluckt worden.
- **Aktivzeit**: Summe der Takte pro Tag, in denen ein Gerät mindestens `AKTIV_SCHWELLE_W` ins Haus abgibt
  (positiver `Ist`-Wert), in Stunden. Jeder Takt zählt mit seiner Dauer bis zum nächsten Takt; Lücken über
  `MAX_LUECKE_S` zählen nicht. „Mindestens ein Gerät“: Takte, in denen wenigstens ein Gerät selbst die Schwelle
  erreicht – gleichzeitige Abgabe mehrerer Geräte zählt nur einmal.
- **Voller Tag**: mindestens `VOLLER_TAG_H` Stunden erfasst. Nur volle Tage gehen in Tageswerte,
  Kennzahlen und Tagesprofil ein.
- **Verteilung je Stunde (Tagesprofil)**: SOC über alle Takte dieser Stunde an allen vollen Tagen.
  Netzsaldo und Speicher-Ausgang: erst das Stundenmittel je Tag, dann die Verteilung dieser Tageswerte –
  so zeigen die Bänder, wie unterschiedlich die Tage sind, und nicht kurze Lastspitzen.
- **Takt ohne Geräteabfrage (Sparmodus)**: Nach `Sparmodus an: N Zyklen ohne Geraete-Poll` (ältere Logs:
  `setze Polling fuer N Zyklen aus`) zählen die nächsten N Takte als eingespart, außer `Sparmodus aus`,
  `Sparmodus beendet` oder ein Neustart kommt vorher. Wie viele Einzelanfragen an die Geräte das spart,
  lässt sich aus dem Log nicht ablesen.
- **Störungen**: Zeilen mit `Geraet nicht erreichbar`, `Takt uebersprungen`, `Watchdog-Timeout`.
- **Neustart**: erkannt am Startblock des Controllers. Jede seiner Zeilen zählt (`Version …`,
  `Multi-Device Controller gestartet`, `Geraete    :`, `Interval   :`, `Watchdog   :`, `Setpoint   :`), so wird ein
  Neustart auch dann gezählt, wenn einzelne Zeilen im Log fehlen. Zeilen innerhalb `NEUSTART_ABSTAND_S` gelten als ein Neustart.

## Änderungen

- **1.4.0**: Gerätenamen mit Leerzeichen und Umlauten werden erkannt; Spaltenschlüssel werden daraus
  gebildet (`geraete.csv`). Vorher fehlten solche Geräte ohne Meldung in der Auswertung.
- **1.3.0**: Regelgüte misst gegen den jeweils gültigen Sollwert statt gegen 0 W; neue Spalten
  `sollwert_min_w`, `sollwert_max_w`, `regel_versatz_w` mit Plausibilitätshinweis. Neustarts werden am ganzen
  Startblock erkannt (vorher nur an „gestartet“, verschluckte Zeilen fehlten dann).
