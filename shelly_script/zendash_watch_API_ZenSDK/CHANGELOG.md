# Changelog zendash API - WatchDog

## Changelog 3.5.12

- Entlade-Hysterese `zdmc_dischargeResetMargin` (ab Regel-Script 5.2.4): `config_api` liefert den Wert als `dischargeResetMargin` (fehlt der Key: 3). `kvs_set_api` lehnt Werte außerhalb 3–79 oder mit Nachkommastellen mit `400` ab
- Dashboard: neues Eingabefeld „Entlade-Hysterese“ (Zahl, wie die Fix-Entladung) neben dem Sollwert. Bereich 3 bis (kleinstes Fenster Ladegrenze − Reserve aller Geräte) − 11, ungültige Eingaben werden mit Meldung verworfen. Ist das Fenster unter 14 Punkten, ist das Feld gesperrt und es gilt 3. Ladegrenze = kleinerer Wert aus `maxSoc` und `socSet`
- Dashboard: Die 5 Kacheln der Übersicht stehen ab 1000 px Breite nebeneinander. KVS-Schlüssel unter dem Kacheltitel in eigener Zeile
- Dashboard: Eine Erhöhung der Reserve wird nicht gespeichert, wenn die eingestellte Entlade-Hysterese danach nicht mehr passt (Reserve höchstens Ladegrenze − 11 − Hysterese). Es erscheint eine Meldung, der Reserve-Regler springt zurück. Senken geht immer
- Mit älterem Regel-Script: Der Key wird geschrieben, aber nicht ausgewertet
- Bisheriges Layout `zendure-dashboard-b.html` entfernt. Proxy, exe und Home-Assistant-App enthalten es nicht mehr; `/b` leitet auf das Dashboard weiter
- Home-Assistant-App-Version 3.5.12.0
- Nachtrag Dashboard: Hilfetexte überarbeitet. „Entlade-Hysterese“ heißt jetzt „Entlade-Sperre“, der Regler „Reserve (minSoc)“; Ladegrenze und Reserve tragen den Konfigurationsschlüssel (`maxSoc`, `minSoc`). Home-Assistant-App-Version 3.5.12.1
- Nachtrag Dashboard: Schon beim Klick auf Start oder Ende des manuellen Ladens erscheint oben eine Leiste („SF2400: manuelles Laden wird gestartet …“ bzw. „… wird beendet …“, darunter „Bedienung gesperrt – warte auf Bestätigung …“), und die gesamte Bedienung ist gesperrt. Nach der Antwort zeigt die Leiste das Ergebnis („SF2400: manuelles Laden mit 1000 W“ bzw. „SF2400: zurück in der Regelung“ oder die Fehlermeldung) und die Restzeit. 10 s lang ist die gesamte Bedienung gesperrt, auch das Schloss. Danach holt das Dashboard den echten KVS-Stand. Bisher gab es nur einen kurzen Hinweis am unteren Rand (2,6 s), und die Bedienung war sofort wieder frei, während der Regler die Änderung noch übernahm. Bleibt die Bestätigung aus, zeigt die Leiste „keine Bestätigung erhalten – der Stand wird nach Ablauf geprüft“. Nach der Haltezeit vergleicht das Dashboard den echten Stand und meldet erst dann Erfolg oder Fehler. Home-Assistant-App-Version 3.5.12.2
- Nachtrag Proxy (`zendure_proxy.py`, auch in der Home-Assistant-App und im local_helper): `kvs_set_api` darf bis 25 s dauern, die übrigen Endpunkte bleiben bei 5 s. Ursache der Meldung „Manuelles Laden … konnte nicht beendet werden“ trotz korrekt geschriebener Werte: Das Script schreibt drei Keys nacheinander (je bis 5 s, 0,5 s Pause dazwischen, vorher bis 2 s Warten auf den eigenen Poll), und der Proxy brach nach 5 s mit `502` ab
- Nachtrag Proxy (`zendure_proxy.py`, auch in der Home-Assistant-App und im local_helper): neue Seite `/bericht_zendure` liefert den Bericht der Log-Auswertung (`bericht.html` aus `stat/auswertung`) aus. Gesucht wird mit `--bericht=PFAD` (Datei oder Ordner) bzw. der Umgebungsvariable `ZENDURE_BERICHT` genau dort, sonst neben der Konfiguration, neben Script/exe und im Repo-Ordner `stat/auswertung`. Ein neu erzeugter Bericht wirkt ohne Neustart. Home-Assistant-App: Datei unter `/share/zendure/bericht.html`, Version 3.5.12.3

## Changelog 3.5.11

- Weniger Last ohne offenes Dashboard bei aktivem Cloud-Upload: Der Proxy holte bisher jede Minute zweimal `status_api` ab, und jede Abfrage startete im Script den schnellen 8-s-Takt für 15 s – das Script lief so rund 25 s pro Minute mit 3–4 vollen Abfragen von Netzzähler und Hubs
- `status_api` versteht den optionalen Parameter `bg`: `bg=wake` löst genau einen Poll aus, `bg=read` liest nur, beide ohne schnellen Takt. Ohne Parameter (Dashboard) unverändert
- Proxy/ts_bridge: weckt mit `?bg=wake` 14 s vor der vollen Minute und liest 12 s später mit `?bg=read`. Ergebnis: ein Poll-Durchlauf pro Minute statt drei bis vier
- Kompatibel: Ein älteres Script ignoriert `bg` und verhält sich wie bisher; der neue Proxy funktioniert damit weiter
- Dashboard: nur Versionsnummer 3.5.11
- Home-Assistant-App-Version 3.5.11.0
- Nachtrag Dashboard (beide Layouts): Link „Dashboard-Shelly: IP / Script-ID ändern“ im Fuß der Seite öffnet die Einrichtungsseite `setup` – funktioniert auch in Home Assistant über „Web-UI öffnen“. Home-Assistant-App-Version 3.5.11.1
- Nachtrag Dashboard (beide Layouts): Links zu ThingSpeak und ThingsBoard öffnen im selben Fenster statt in einem neuen Tab – in der Home-Assistant-Companion-App kam sonst „401: Unauthorized“. Home-Assistant-App-Version 3.5.11.2

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
