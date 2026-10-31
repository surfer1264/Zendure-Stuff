# Changelog zendash API - WatchDog

## Changelog 3.5.12

- **Neu: Entlade-Sperre** (`zdmc_dischargeResetMargin`, ab Regel-Script 5.2.4): Eingabefeld im Dashboard neben dem Sollwert, erlaubt 3 bis (Ladegrenze − Reserve) − 11. Ist dieser Abstand zu klein, ist das Feld gesperrt und es gilt 3. Eine höhere Reserve, die nicht mehr zur Sperre passt, wird mit Meldung abgelehnt. Mit älterem Regel-Script wird der Wert gespeichert, aber nicht ausgewertet
- **Manuelles Laden:** Eine Leiste oben zeigt Start, Ergebnis und Restzeit. Während der Regler die Änderung übernimmt (10 s), ist die Bedienung gesperrt; danach prüft das Dashboard den echten Stand. Behoben: „Manuelles Laden … konnte nicht beendet werden“, obwohl die Werte richtig geschrieben waren
- **Neues Design** unter `/neu`, das klassische Dashboard bleibt unter `/`. Umschalten im Menü „Ansicht“ → „Design“. Gerätekarten mit Ladebalken, Hinweise nur bei Abweichungen, Ansicht „Energiefluss“ mit animierten Linien
- **Log-Bericht:** Liegt ein Bericht der Log-Auswertung (`bericht.html`) vor, zeigt der Proxy ihn unter `/bericht_zendure`, und im Fuß des Dashboards erscheint der Link „Auswertung: Log-Bericht“. Home Assistant: Datei nach `/share/zendure/bericht.html` legen. Details in der [Dashboard-Doku](dashboard.md)
- Übersicht: die 5 Kacheln stehen ab 1000 px Breite nebeneinander. Hilfetexte überarbeitet, Ladegrenze und Reserve mit Konfigurationsschlüssel (`maxSoc`, `minSoc`). Die Sperrschwelle der Zellspannung steht nur noch bei „Technische Details“
- Das alte Layout `zendure-dashboard-b.html` entfällt, `/b` leitet auf das Dashboard weiter
- Neues Design: Offgrid mit Richtung – positiv = Abgabe ans Haus („Ausgang“), negativ = Einspeisung ins Gerät („Eingang“, wie PV). Der Energiefluss zeigt nur Beträge, die Animation läuft in Flussrichtung; vorher stand bei Einspeisung „nicht belegt“ und die Linie stand still
- **Verbindungsprobleme (beide Designs):** Ein einzelner Abfrage-Aussetzer bleibt unsichtbar; erst nach zwei Fehlern in Folge erscheinen Hinweis (mit Grund, z. B. „Zeitüberschreitung“) und „Verbindungsproblem“, die Gerätekarten werden blass, im neuen Design „veraltet“, Animationen halten an. Läuft eine Abfrage noch, fällt der nächste Takt aus (vorher konnten sich Anfragen am Shelly stapeln)
- **Proxy zählt Abfragefehler** je Tag nach Art (Zeitüberschreitung, nicht erreichbar, Fehler vom Shelly) mit letztem Zeitpunkt und Grund: neue Adresse `/proxy_fehler`, im Fuß des Dashboards „Abfragefehler heute: …“, jeder Fehler auch im Protokoll (auch mit `-q` und in der Home-Assistant-App). Die 502-Antwort enthält jetzt `art`
- Home-Assistant-App bis Version 3.5.12.5

## Changelog 3.5.11

- **Weniger Last bei Cloud-Upload** (ThingSpeak/ThingsBoard) ohne offenes Dashboard: ein Abruf pro Minute statt drei bis vier. Wirkt mit Script und Proxy ab 3.5.11; ältere Kombinationen laufen wie bisher weiter
- Dashboard: Link „Dashboard-Shelly: IP / Script-ID ändern“ im Fuß der Seite, auch in Home Assistant
- Home-Assistant-Companion-App: Links zu ThingSpeak und ThingsBoard öffnen im selben Fenster, vorher kam „401: Unauthorized“
- Home-Assistant-App bis Version 3.5.11.2

## Changelog 3.5.10

- minSoc/maxSoc: Mindestabstand 5 Prozentpunkte wie im Regel-Script ab 5.2.1. Beim Start gilt `minSoc` 10–95 % und `maxSoc` mindestens `minSoc + 5` (vorher `minSoc + 1`)
- config_api: Die Reserve aus der KVS (`zdmc_devN_minSoc`) wird auf 10 … `maxSoc − 5` begrenzt, bevor sie ans Dashboard geht
- Dashboard (beide Layouts): Der Regler für die Reserve endet 5 Prozentpunkte unter der Ladegrenze (kleinerer Wert aus `maxSoc` und `socSet`), vorher 1 Punkt; Versionsnummer 3.5.10
- Passt zum Regel-Script ab 5.2.1; mit älterem Regel-Script funktioniert alles weiter, der Abstand wird dann nur im Dashboard eingehalten
- Home-Assistant-App-Version 3.5.10.0

## Proxy 3.5.9.4 (ohne Änderung am Script)

- ThingsBoard-Upload: neue Werte je Speicher `socLimit` (0 frei, 1 voll, 2 leer), `socSet` (obere Ladegrenze in %) und `minSoc` (untere Entladegrenze in %, aus `minSocHw`), standardmäßig aus. Sie werden nur bei Änderung gesendet, dazu einmal täglich und nach jedem Neustart oder Speichern der Einstellungen
- Home-Assistant-App-Version 3.5.9.4

## Proxy 3.5.9.3 (ohne Änderung am Script)

- ThingsBoard-Upload: Seite `/thingsboard` zeigt die heute gesendeten Datenpunkte und Nachrichten (Zähler im Speicher, beginnt um Mitternacht und bei jedem Proxy-Start neu); die Sendezeilen im Log enthalten den Tagesstand
- Home-Assistant-App-Version 3.5.9.3

## Proxy 3.5.9.2 (ohne Änderung am Script)

- ThingsBoard-Upload: Werte je Speicher auf `/thingsboard` per Häkchen auswählbar, für alle Speicher gemeinsam; gespeichert als `fields` in `zendure_thingsboard_config.json`. Ohne `fields` (ältere Konfiguration) bleiben die bisherigen sieben Werte
- ThingsBoard-Upload: neue Werte `batteryPower` (berechnet `packIn` − `packOut`, + = Akku entlädt, − = Akku lädt) und `offGridPower` (Leistung am Offgrid-Ausgang), standardmäßig aus
- ThingSpeak-Upload unverändert
- Fehlerbehebung Cloud-Upload: Wurde der Upload aus- und gleich wieder eingeschaltet, während gerade gesendet oder abgefragt wurde, lief danach kein Upload mehr bis zum Neustart des Proxys. Jeder Takt-Thread hat jetzt ein eigenes Stopp-Signal
- Home-Assistant-App-Version 3.5.9.2

## Changelog 3.5.9

- Neues Standard-Layout in `zendure-dashboard.html` (im Proxy unter `/`) – gleiche Funktionen, anderer Aufbau: Sperrknopf als deutlich markiertes Schloss, Menü „Ansicht“, Übersicht getrennt in „Jetzt“ und „Regelung“, technische Details (KVS-Schlüssel, IP, Rohcodes) nur auf Wunsch, Status in Klartext, größere Tippflächen, Beschriftungen für Screenreader. Ansichtsgröße, Tag/Nacht und Detailansicht werden gemerkt, „Ansicht zurücksetzen“ im Menü. Der Sperrknopf ändert beim Entsperren seine Breite nicht mehr (vorher verrutschte „Ansicht“ und Klicks gingen daneben). Die Zelle-min-Zeile mit Sperrschwelle steht immer auf einer eigenen Zeile
- Bisheriges Layout als `zendure-dashboard-b.html` weiterhin im Proxy unter `/b`; die exe und die Home-Assistant-App enthalten beide Dateien (HA-App-Version 3.5.9.1)
- Hilfe-Link zeigt auf die Doku-Seite (GitHub Pages) statt auf die Markdown-Datei auf GitHub
- Fußzeile: config_api und status_api sind anklickbar (Rohdaten als JSON im neuen Tab)
- Fußzeile: Links „Cloud-Upload einrichten: ThingSpeak · ThingsBoard“ auf die Einrichtungsseiten des Proxys
- status_api liefert je Hub zusaetzlich `temp` (Geraetetemperatur in ganzen °C aus `hyperTmp`: (hyperTmp - 2731) / 10, gerundet) und `offGrid` (Leistung am Offgrid-Ausgang in W aus `gridOffPower`, `null` = kein Offgrid-Ausgang)
- Dashboard: Zusatzzeile der Geraetekarte zeigt Offgrid-Leistung und Temperatur, z. B. "PV 420 W · Offgrid 0 W · 19 °C · min 3,28 V"
- Dashboard: Versionsnummer 3.5.9
- **Proxy:** Einrichtungsseite, ThingSpeak- und ThingsBoard-Seite verwenden relative Pfade (Link „← Dashboard“, Abrufe) – funktioniert damit auch hinter einem Pfad-Präfix (z. B. Home-Assistant-Ingress)
- https://github.com/surfer1264/Zendure-Stuff/issues/138

## Changelog 3.5.8

- Speicheroptimierung

## Changelog 3.5.7

- Speicheroptimierung

## Changelog 3.5.6

- Speicheroptimierung

## Changelog 3.5.5

- Fix 131; StackOverflow
- https://github.com/surfer1264/Zendure-Stuff/issues/131

## Changelog 3.5.4

- Schloss-Icons
- Zusatzsperre minSoc-Slider um versehentliche Fehlbedinung zu vermeiden
- Dashboard: Hinweis an der Geraetekarte, wenn `minSoc` am Geraet von Konfiguration des Dashboard (KVS-Wert) abweicht (durch Änderung von "außen", oder wenn KVS Wert nicht auf das Gerät geschrieben wurde - Fehlerfall)

## Changelog 3.5.3

- config_api liefert zusaetzlich `watchdog: {enabled, minVoltWarn, minVoltReset}` und je Geraet `watch` - nur zur Anzeige im Dashboard
- Dashboard: bei ueberwachten Geraeten steht hinter der schwaechsten Zelle die Sperrschwelle, z. B. "min 3,31 V (Sperre < 2,90 V)"; Farben nach den Watchdog-Schwellen (gelb unter minVoltReset, rot unter minVoltWarn). Antippen der Schwelle erklaert, was beim Unterschreiten passiert. Bei watch: false, abgeschaltetem Watchdog oder aelterem Script bleibt die Anzeige wie bisher
- Dashboard: Versionsnummer 3.5.3

## Changelog 3.5.2

- Watchdog: faellt eine Zelle unter `minVoltWarn`, wird zusaetzlich zur bisherigen Meldung `zdmc_dev{i}_dischargeAllowed = 0` in die KVS geschrieben und gemeldet "Entladen gesperrt wegen Unterschreitung minVol". Freigabe nur von Hand ueber den Dashboard-Schalter, API und Watch müssen. aktiviert sein
- Dashboard: Obergrenze des Reserve-Reglers (minSoc) = kleinere von maxSoc (Konfiguration) und socSet (am Geraet) minus 1 - die Reserve bleibt immer mindestens 1 % unter der tatsaechlichen Ladegrenze
- Dashboard: Versionsnummer 3.5.2

## Changelog 3.5.1

- status_api liefert je Hub zusaetzlich `socSet`: die am Geraet tatsaechlich eingestellte obere Ladegrenze in % (Report `socSet` / 10), `null` = Feld fehlt bzw. Hub offline - ein `jsonNum`-Aufruf auf dem ohnehin geholten Report, keine zusaetzliche Abfrage
- Dashboard: Hinweis an der Geraetekarte, wenn `socSet` am Geraet von `maxSoc` aus der Konfiguration abweicht (z. B. von aussen per App oder Home Assistant geaendert). Das Regel-Script gleicht den Wert nur beim Start ab. Kein Watchdog-Hinweis
- Dashboard: Versionsnummer 3.5.1

## Changelog 3.5.0

- status_api liefert je Hub zusaetzlich `home`, `gridIn`, `packIn`, `packOut` (Rohwerte `outputHomePower`, `gridInputPower`, `packInputPower`, `outputPackPower` in W, `null` = Feld fehlt bzw. Hub offline) - vier `jsonNum`-Aufrufe auf dem ohnehin geholten Report, keine zusaetzliche Abfrage
- Watchdog: Geraetename im Abend-/Morgen-Update auf 10 Zeichen gekuerzt (vorher 6)
- Changelog-Kommentare aus dem Script-Quelltext entfernt, die Historie steht nur noch hier
- Dashboard: pausiert alle Abfragen, solange der Tab verdeckt oder das Fenster minimiert ist, und fragt beim Zurueckkehren sofort `status_api` und `config_api` ab. Ein vergessener Hintergrund-Tab haelt die Hintergrundabfrage des Scripts damit nicht mehr dauerhaft wach
- Dashboard: Versionsnummer 3.5.0
- Proxy: optionaler ThingSpeak-Upload / ThingsBoard-Upload ueber `ts_bridge.py` mit Einrichtungsseite `/thingspeak` oder `thingsboard`, siehe [ThingSpeak-Upload](thingspeak.md) / [ThingsBoard-Upload](thingsboard.md). Fehlt `ts_bridge.py`, laeuft der Proxy unveraendert ohne ThingSpeak / Thingsboard
- Proxy: vom Browser abgebrochene Verbindungen (Tab geschlossen, Reload) erzeugen keinen Traceback mehr im Log

## Changelog 3.4.1

- config_api-Cache im Script wieder entfernt: kostete ~770 B Heap bei offenem Dashboard und traf bei einem Dashboard (Abfrage alle 32 s) nie - jede config_api-Abfrage liest die KVS frisch
- Dashboard: nur Versionsnummer angehoben (Script und Dashboard muessen gleich sein)

## Changelog 3.4.0

- Speicheroptimierung: Einmal-Code der Startphase nach dem Start freigegeben; je nach CONFIG ungenutzte Helfer freigegeben (`ENCODE_MAP`/`simpleEncode` bei WEBHOOK, `kvsItemsToMap` bei entfernter KVS, `readFieldPath` ohne http_json) - Grundlast ca. 900 B niedriger
- Dashboard fragt config_api nur noch alle 32 s ab (vorher 12 s) und beim Laden der Seite nur einmal (vorher doppelt)
- Heap-Ausgabe (memLog) an den wichtigsten Stellen, nur bei debug
- config_api-Antwort bis zu 30 s gecacht (in 3.4.1 wieder entfernt)

## Changelog 3.3.1

- Letzte Vollladung jetzt ereignisgesteuert: Im Poll wird bei SoC 100 % nur ein Merker gesetzt; Datum lesen und `zdmc_dev{i}_lastFull` schreiben passiert einmal nach dem Poll, danach ruht die Funktion je Geraet bis Mitternacht
- Keine Systemstatus-Abfrage (`sys`) mehr in jedem Poll - vorher bis zu drei je 8-s-Takt, erhoehte den Speicher-Peak bei offenem Dashboard
- Meldung "seit N Tagen nicht voll" wird einmal taeglich beim Morgen-Update geprueft statt in jedem Poll
- Schreibfehler: neuer Versuch fruehestens nach 10 min, hoechstens 3 Versuche je Tag

## Changelog 3.3

- Letzte Vollladung: echte 100 % SoC werden je Geraet als Datum (JJJJMMTT) in `zdmc_dev{i}_lastFull` gespeichert, hoechstens ein KVS-Schreibvorgang pro Geraet und Tag
- Schutz: harte Obergrenze von 3 Schreibversuchen je Geraet und 24 h Laufzeit; Datum in der Zukunft gilt als ungueltig und wird ueberschrieben; KVS-Wert wird immer uebernommen (auch aeltere, von Hand gesetzte Werte)
- config_api liefert je Geraet `lastFull` (0 = noch nie erfasst)
- Dashboard: Zeile "100 %: vor N Tagen" je Geraet, gruen < 7 Tage, gelb 7-20 Tage, rot darueber; Antippen zeigt das Datum
- Watchdog: einmalige Meldung "Geraet seit N Tagen nicht voll" ab 20 Tagen
- Watchdog-only-Betrieb liest beim Start ebenfalls die KVS

## Changelog 3.2

- FullScreenMode

## Changelog 3.1

- Zusammenlegung von Watchdog und zenDash API
