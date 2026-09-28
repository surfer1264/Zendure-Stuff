# Changelog zendash API - WatchDog

## Changelog 3.5.0

- status_api liefert je Hub zusaetzlich `home`, `gridIn`, `packIn`, `packOut` (Rohwerte `outputHomePower`, `gridInputPower`, `packInputPower`, `outputPackPower` in W, `null` = Feld fehlt bzw. Hub offline) - vier `jsonNum`-Aufrufe auf dem ohnehin geholten Report, keine zusaetzliche Abfrage
- Watchdog: Geraetename im Abend-/Morgen-Update auf 10 Zeichen gekuerzt (vorher 6)
- Changelog-Kommentare aus dem Script-Quelltext entfernt, die Historie steht nur noch hier
- Dashboard: pausiert alle Abfragen, solange der Tab verdeckt oder das Fenster minimiert ist, und fragt beim Zurueckkehren sofort `status_api` und `config_api` ab. Ein vergessener Hintergrund-Tab haelt die Hintergrundabfrage des Scripts damit nicht mehr dauerhaft wach
- Dashboard: Versionsnummer 3.5.0
- Proxy: optionaler ThingSpeak-Upload ueber `ts_bridge.py` mit Einrichtungsseite `/thingspeak`, siehe [ThingSpeak-Upload](thingspeak.md). Fehlt `ts_bridge.py`, laeuft der Proxy unveraendert ohne ThingSpeak
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