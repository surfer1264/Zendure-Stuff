# Changelog Controller

## v5.2.4

- **Entlade-Hysterese per KVS änderbar:** `dischargeResetMargin` (Prozentpunkte über `minSoc`, ab denen ein bis zur Reserve entladenes Gerät wieder entladen darf) lässt sich jetzt live über `zdmc_dischargeResetMargin` ändern, systemweit für alle Geräte. Der Key wird beim Start mit dem CONFIG-Wert (Standard 3) angelegt, falls er fehlt.
  - Gültig sind ganze Zahlen von 3 bis 79, andere Werte werden ignoriert.
  - Untergrenze jetzt 3 statt 1. Ein im CONFIG-Block gesetzter Wert unter 3 wird beim Start auf 3 angehoben.
  - Wirksam ist je Gerät höchstens `maxSoc − minSoc − 11`. Ist das Fenster eines Geräts dafür zu klein (unter 14 Punkte), gilt für dieses Gerät 3.

Keine Änderung am CONFIG-Block nötig.

## v5.2.3

- **Sprungfaktor optional im CONFIG-Block:** Der Faktor der schnellen Flanke (`JUMP_FACTOR`, bisher fest 0,9) lässt sich jetzt mit `jumpFactor` im CONFIG-Block setzen. Der Eintrag ist optional: Fehlt er, gilt wie bisher 0,9.
  - Ein gesetzter Wert hat Vorrang vor dem Standard und wird auf 0,4 bis 0,9 begrenzt (nie über 0,9).
  - Ungültige Werte (keine Zahl) werden ignoriert, dann gilt 0,9.
  - Der wirksame Wert steht im Startbanner in der Zeile „Damping“.
  - Nicht per KVS änderbar.
- **Regelndes Gerät wird zuletzt abgefragt, direkt vor dem Zähler:** Bisher wurden die Geräte in CONFIG-Reihenfolge abgefragt und danach der Zähler. Jede Abfrage dauert je nach Gerät/Netzwerk rund 1 s. Stand das regelnde Gerät vorne, lagen bei 3 Geräten ca. 2 s zwischen seinem Ist und dem Netzwert. Der Netzwert zeigte die neue Leistung schon, das Ist noch die alte – das Regelsignal sprang im Wechsel hoch und runter (Zickzack).
  - Jetzt werden zuerst die Geräte abgefragt, die gerade nicht regeln (zuletzt geschriebenes Soll 0 W und Ist 0 W), danach die regelnden, dann sofort der Zähler.
  - Regeln alle Geräte (Verteilen), bleibt die Reihenfolge wie bisher.
  - Kein zusätzlicher Aufruf, keine Änderung am Sparmodus.

Keine Änderung am CONFIG-Block nötig.

## v5.2.2

- **Kein Laden mehr, solange noch entladen wird:** Fällt die Last kurz weg (z. B. Wasserkocher aus), entsteht beim Entladen ein kurzer Export. Bisher konnte im selben Zyklus schon ein anderes Gerät (mit `reverse: true`) mit dem Laden beginnen – ein Speicher entlud, der andere lud, und die Regelung wechselte unnötig die Richtung. Jetzt wird zuerst nur die Entladung zurückgenommen. Erst wenn kein Gerät mehr real entlädt (Ist-Leistung höchstens `dischargeStopPower`) und der Export weiter anliegt, startet das Laden regulär.
  - Laufendes Laden ist davon nicht betroffen.
  - Geräte mit vollem Akku (`socLimit` 1, PV-Bypass) zählen nicht als „entlädt“ – ihre Einspeisung darf ein anderes Gerät weiterhin laden.
  - Bei aktivem `dischargeFixed` gilt die Sperre nicht: Die feste Entladung ist gewollt, PV-Überschuss darf weiter von einem anderen Gerät geladen werden (wie bisher).
- **Entladen startet nach einer Exportspitze schneller wieder:** Das gedämpfte Entlade-Signal fällt nicht mehr unter 0 W. Ein negativer Wert hatte keine Wirkung, musste nach einer kurzen Exportspitze aber erst über mehrere Zyklen wieder hochlaufen – so lange wurde Strom aus dem Netz bezogen, bevor das Entladen wieder einsetzte.
- Leerzeichen am Zeilenende im Quelltext entfernt (ohne Auswirkung auf die Funktion).

Keine Änderung am CONFIG-Block nötig.

## v5.2.1

- **minSoc/maxSoc: Mindestabstand 5 Prozentpunkte:** Beim Start gilt jetzt `minSoc` 10–95 % und `maxSoc` mindestens `minSoc + 5` (vorher `minSoc + 1`). Liegen beide Werte zu eng beieinander, wird `maxSoc` angehoben, die Reserve bleibt erhalten.
- **KVS-Override `zdmc_devN_minSoc` wird gegen `maxSoc` geprüft:** Übernommen wird nur ein Wert zwischen 10 und `maxSoc − 5`. Vorher galt 10–99 ohne Bezug zu `maxSoc` – ein zu hoher Wert (z. B. aus Home Assistant oder Node-RED) wurde übernommen und per `syncMinSocDevice()` sogar aufs Gerät geschrieben. Ungültige Werte werden jetzt ignoriert (mit `debug: true` steht ein Hinweis im Log).
- Fehlt `minSoc` oder `maxSoc` im CONFIG-Block eines Geräts, gilt 10 % bzw. 100 % (vorher `NaN`).

Keine Änderung am CONFIG-Block nötig. Steht in einer CONFIG `minSoc` über 95 oder liegt `maxSoc` weniger als 5 Punkte darüber, wird der Wert beim Start angepasst.

## v5.2.0

- **Ruhigere Regelung bei konstanter Last (Nachbesserung zu 5.1.8):** Die schnelle Flanke (Faktor 0.9) greift nur noch, wenn das Signal in Richtung „weniger Export“ um mehr als 3 × hysteresis (höchstens 50 W) springt, also beim Entladen die Last deutlich fällt oder beim Laden der Überschuss deutlich steigt. Sprünge in die Gegenrichtung und kleinere Abweichungen werden weiter mit dampingFactor gedämpft. Die Regel lautet also: Droht Export, wird schnell reagiert. Droht Netzbezug, wird gedämpft reagiert (konfigurierbar über `dampingFactor`).

- **Schnelle Flanke mit Faktor 0,9 statt ungedämpft:** Bei einem Sprung übernimmt der Controller 90 % der Änderung sofort, nicht 100 %. Wegen der Reaktionszeit der Solarflows (~3 s) steckt das Gerät beim nächsten Messen oft noch in der Rampe. Ein voller Sprung schoss dann leicht über und wurde im Folgetakt wieder zurückgenommen.
- Simulation mit 4 s Takt und 3 s Reaktionszeit: beim Wasserkocher ein Drittel weniger Richtungswechsel, beim Herd-Thermostat rund 35 % weniger, bei taktender Induktion ein Viertel weniger Schreibbefehle. Der Export ist dabei nur 5–10 % höher als mit voll ungedämpfter Flanke, liegt aber weiter deutlich unter 5.1.7 (Wasserkocher: 23,8 statt 30,5 Wh).
- Der Faktor steht als Konstante `JUMP_FACTOR` im Skript, nicht im CONFIG-Block.
- **`dampingFactor` jetzt höchstens 0,8** (vorher 1,0, Untergrenze unverändert 0,4). Höhere Werte werden beim Start auf 0,8 gesetzt. Über 0,7 bringt ein höherer Wert in der Simulation keine bessere Energiebilanz, sondern nur mehr Schreibbefehle und Richtungswechsel; bei taktenden Lasten kann es dann auch häufiger zwischen Laden und Entladen wechseln. Empfehlung: Standard (`local`, Takt 4 s) 0,6–0,7, Default 0,65; bei `remote`/`http_json` oder 3 und mehr Geräten 0,5–0,6; bei Takt 3 s 0,6. Details: [Gesamtdokumentation, Kapitel 8.2](gesamtdoku.md#empfehlung-für-dampingfactor).
- Hintergrund: Seit 5.1.8 kam auch das Messrauschen nach unten ungedämpft durch, nach oben nur gedämpft. Bei konstanter Last schwankte das Regelsignal stärker, es wurde öfter geschrieben, und der Mittelwert lag leicht Richtung Netzbezug. Aufgeschaukelt hat sich die Regelung dabei nicht.
- Schwelle: bei `hysteresis: 12` 36 W, bei 13 W 39 W, ab 17 W 50 W. Schwelle und Faktor stehen im Startbanner in der Zeile „Damping“.
- Simulation: Bei konstanter Last wird wieder so oft geschrieben wie in 5.1.7 (64 statt 97 Schreibbefehle in 20 min). Der Gewinn bei Lastsprüngen aus 5.1.8 bleibt („Wasserkocher aus“: 15,0 Wh Export statt 18,0 Wh in 5.1.7).

Keine Änderung am CONFIG-Block nötig.

## v5.1.9

- **Offgrid-Leistung im Log (nur mit `debug: true`):** Die Gerätezeile zeigt zusätzlich `offGP <W> W`, wenn der Speicher einen Offgrid-Ausgang hat (`gridOffPower`). Geräte ohne Offgrid-Ausgang und Betrieb ohne debug: Logzeile unverändert.
- Ohne debug kein zusätzlicher Laufzeitspeicher; die Mini-Fassung wird um rund 130 Bytes größer.

Keine Änderung am CONFIG-Block nötig.

## v5.1.8

**Dämpfung nur noch in eine Richtung:** In Richtung „weniger Export“ reagiert der Controller sofort, ohne `dampingFactor`:

- Entladen wird sofort zurückgenommen, wenn die Last sinkt.
- Laden wird sofort erhöht, wenn der PV-Überschuss steigt.
- Die Gegenrichtung (mehr entladen, weniger laden) bleibt wie bisher gedämpft. Dort gibt es kurz Netzbezug statt Einspeisung.
- Nach „Wasserkocher aus“ ist die Einspeisung deutlich kürzer. In der Simulation sank die Dauer mit mehr als 50 W Export um rund 40–70 %
- Etwas weniger Schreibbefehle an die Geräte.
- Die erste Exportspitze direkt nach dem Abschalten bleibt. Sie entsteht, weil das Gerät seine Leistung nur mit begrenzter Geschwindigkeit herunterfährt, und lässt sich durch die Regelung nicht verhindern.

Keine Änderung am CONFIG-Block nötig.

## v5.1.7

Nur Konsolenausgaben gekürzt. Keine Änderung an Regelung, Verteilung,
Schreibvorgängen, Fehlerbehandlung oder Benachrichtigungsinhalten.

- socLimit-Wechsel: drei Meldungen zu einer zusammengefasst,
  Format `<Label>: socLimit 0->1 (Ladesperre|Entladesperre|normal)`
- socStatus-Wechsel: eine Meldung,
  `<Label>: socStatus 1 (Kalibrierung, aus Verteilung)` / `socStatus 0 (Kalibrierung beendet)`
- maxSoc: "maxSoc erreicht (soc/maxSoc%)" bzw. "unter maxSoc (soc/maxSoc%)"
- Sparmodus: "Sparmodus an: N Zyklen ohne Geraete-Poll" /
  "Sparmodus aus (Hysterese/Richtung)" (Hysterese/cyclesUnchanged nur noch im Banner)
- Bypass-Korrektur: "Bypass-Korrektur: X W umverteilt"
- Ausgleich: `Ausgleich -> <Label> (+N%)`
- Benachrichtigungen: neuer gemeinsamer Ergebnis-Callback msgResult(typ) für
  WEBHOOK/SIGNAL/WHATSAPP; "Sende ..."-Zeilen entfernt; Ausgabe nennt jetzt
  den tatsächlichen Kanal (vorher bei WhatsApp fälschlich "Signal-Nachricht")
- msgResult wird bei signal.enabled:false nach dem Start freigegeben
- Wirkung: weniger Scriptspeicher

## Changelog 5.1.6

- kvs-lesen im Controleller robuster gestalten
- https://github.com/surfer1264/Zendure-Stuff/issues/128

## Changelog 5.1.5

- https://github.com/surfer1264/Zendure-Stuff/issues/125
- Startmeldung ergänzt
- gridReverse=2 (Export verboten) soll nicht gesetzt werden, wenn ein Gerät nicht erreicht wird.

## Changelog 5.1.4

- **Kein Hin- und Herschalten mehr an der unteren Akkugrenze**

- *Worum geht es?*
Hat ein Gerät bis `minSoc` entladen, sperrt die Firmware das Entladen
(`socLimit: 2`). Sie hebt die Sperre aber schon 1 % später wieder auf. Lädt
morgens die PV ein leeres Gerät gerade so weit nach, hat der Controller es
sofort wieder entladen – wenige Sekunden später war es wieder leer. Das Gerät
schaltete dadurch im Sekundentakt zwischen Entladen und Standby hin und her.

- *Was ist neu?*
Ein leer gelaufenes Gerät darf erst wieder entladen, wenn es **3 % über
`minSoc`** liegt (bei `minSoc` 15 % also ab 18 %). Bis dahin lädt die PV in
Ruhe nach. Der Akku wird weiterhin bis `minSoc` genutzt – nur das
Wiedereinschalten wartet etwas länger.

- *Was merke ich davon?*
Deutlich weniger Schaltvorgänge an der unteren Akkugrenze. Im Testlauf
  (06–09 Uhr) sank die Zahl der Moduswechsel von rund 480 auf unter 10 pro
  Gerät, die Schreibbefehle an die Geräte von rund 1430 auf 116.
- In dieser Phase etwas mehr Netzbezug, weil das fast leere Gerät erst
  nachladen darf, bevor es wieder liefert.

Keine Änderung am CONFIG-Block nötig. Wer einen anderen Abstand möchte, kann
`dischargeResetMargin: <Wert>` zusätzlich in den CONFIG-Block schreiben
(mindestens 1).

## Changelog 5.1.3

**Neue Logzeile: übersprungener Takt**

Braucht ein Regelzyklus länger als das eingestellte `interval` (z. B. weil
ein Gerät langsam antwortet), wird der nächste Takt ausgelassen. Das passierte
bisher unsichtbar. Jetzt steht im Log:

`Takt uebersprungen - Zyklus 1234 laeuft noch seit 4100 ms`

Vereinzelt ist das harmlos. Taucht die Zeile häufig auf, ist `interval` für
die Anzahl der Geräte zu knapp gewählt und sollte erhöht werden.

Keine Änderung am CONFIG-Block nötig.

## Changelog 5.1.2

**Fehlerbehebung: Ungewolltes Laden bei Bypass-Überschuss**

*Worum geht es?*
Ist ein Gerät voll (`socLimit: 1`), läuft die PV-Leistung im Bypass einfach
durch das Gerät ins Haus. Liefert es dabei mehr, als das Haus gerade braucht,
regelt der Controller die übrigen Geräte entsprechend herunter. Bisher konnte
er sie dabei aber nicht nur auf 0 W herunterregeln, sondern ihnen sogar einen
**Ladebefehl** geben. Das hatte drei Schwächen:

- Es betraf auch Geräte mit `reverse: false` – also Geräte, die laut
  Konfiguration gar nicht laden dürfen.
- Grenzen wie `maxInputPower` und `maxSoc` wurden dabei nicht beachtet.
- Das vollere Gerät bekam den größeren Ladeanteil statt das leerere.

*Was ist neu?*

- Die Bypass-Korrektur regelt die übrigen Geräte nur noch **herunter,
  höchstens bis 0 W** – nie mehr ins Laden.
- Bleibt danach noch Überschuss übrig, übernimmt ab dem nächsten Takt die
  normale Ladesteuerung – mit allen Einstellungen (`reverse`, `maxSoc`,
  `maxInputPower`, Start-/Stop-Schwellen).
- Gibt es kein Gerät, das laden darf, wird der Überschuss eingespeist
  (sofern `gridReverse` den Export erlaubt).

*Was merke ich davon?*

- Geräte mit `reverse: false` laden nie mehr ungewollt.
- Geräte mit `reverse: true` laden den Bypass-Überschuss wie bisher – das
  Laden beginnt nur etwa einen Takt (rund 4 s) später.
- Ohne Bypass-Situation ändert sich nichts.

Keine Änderung am CONFIG-Block nötig.

**Dokumentation**

Die Gesamtdokumentation wurde komplett mit dem Code abgeglichen (u. a.
Plausibilitätsprüfungen, Entprellung beim Zuschalten weiterer Geräte,
Wartezeit vor `smartMode: 0`, manuelles Laden, SOC-Kalibrierung,
Ablaufdiagramm).

## Changelog 5.1.1

- Webhook-/Signal-Meldungen mit Icon wie in zenDash: ✅ Start, ❌ Fehler, ✅ Fehler behoben

## Changelog 5.1.0

Speicheroptimierung (mem_peak im Regelbetrieb 19 880 -> 19 026 Bytes)

- geparstes Report-Objekt in readDevice vor callback() freigeben
- ungenutzte Funktionen je nach CONFIG nach dem Start freigeben
- Heap-Ausgabe (memLog) im Debug-Modus

## Changelog 5.0.8

Bei `standbySmartModeZero: false` (Standard) ist das Verhalten unverändert.

Mit `standbySmartModeZero: true`
wirkt ein `CONFIG.standbyHoldCycles = 15` (15 Takte) bevor der Standby mit `smartmode: 0` geschrieben wird

`standbySmartModeZero: true` ist grundsätzlich nicht empfohlen.
Es gibt Geräte, die nicht sauber in den (echten) Standby wechseln und latent z.B: 20W einspeisen oder laden

Diese Anpassung sorgt dafür, dass ein Pendeln um den Nullpunkt nicht zu einem latenten Flash-Schreiben führt, sondern erst nach einer Wartezeit (15 Takte = 1 Minute) zu einem Standby führt.

## Changelog 5.0.7

Manuelle Kalibrierung wird über `socStatus` gemeldet
`socStatus: 1` Kalibrierung aktiv

Gerät wird aus der Verteilung herausgenommen.

- https://github.com/surfer1264/Zendure-Stuff/issues/107

## Changelog 5.0.6

NEUER Parameter hinter dem CONFIG-Block (da Default:0)
`CONFIG.dischargeFixed`

Erweiterung: Regelung wird mit einem festen Regeltarget (Fixer Wert) überschrieben
Die Regelung wird damit deaktiviert und nur der fixe Wert geliefert

`CONFIG.dischargeFixed=0` : Regelung aktiv
`CONFIG.dischargeFixed ≥ dischargeStartupPower` : Regelung deaktiviert, System gibt `dischargeFixed` aus
nur als KVS-Wert verfügbar wenn kvsEnabled: true

- https://github.com/surfer1264/Zendure-Stuff/issues/103

## Changelog 5.0.4

Bug: manuelles Laden startet nur sporadisch

- https://github.com/surfer1264/Zendure-Stuff/issues/104

## Changelog 5.0.2

Entprellung Concentrate => Above

Beispiel:
ein kurzer Lastimpuls (Kühlschrank-Kompressor: 1500 W) soll nicht zu einer Zuschaltung von weiteren Geräten führen...
1 Takt sorgt dafür , dass solche kurzen Impulse Entprellt werden
Parameter SPREAD_TRIGGER_CYCLES ist NICHT Teil des CONFIG-Blocks und steht per Default auf 1

## Changelog 4.5.2/5.0.0

AC-input-Limit in KVS aufgenommen

## Changelog 4.4.0

doppelte Verifikation gelöscht

## Changelog 4.2.3 / 4.3.0

Nur interne Speicheroptimierung, zur Laufzeit 1kB gespart ( das sind knapp 10%)

## Changelog 4.2.2

adressiert das Verhalten von mehr als zwei Solarflows im selektiven Bypass-Fall
**Geräte im Bypass sind nicht mehr steuerbar** sie laufen einfach weiter.

Hier geht es um die korrekte Berücksichtigung Ihres Anteils unter Berücksichtigung verschiedener Fallgruppen.

- https://github.com/surfer1264/Zendure-Stuff/issues/80
- https://github.com/surfer1264/Zendure-Stuff/issues/81

## Changelog  4.2.1

- https://github.com/surfer1264/Zendure-Stuff/issues/87

4.2.1 - idleSkip nutzt jetzt `CONFIG.hysteresis` als Toleranzband um den
zuletzt geschriebenen Wert (ds.outputLimit) statt exakter
Signaturgleichheit.. Richtungswechsel (Export vs.
Idle/Import) zaehlt weiterhin immer als Aenderung.

Adaptive Polling: NEUER PARAMETER  (`CONFIG.idleSkip`) eingefuehrt:
reduziert HTTP-Last auf die Zendure-Geraete, wenn der Regel-Output ueber
mehrere Zyklen stabil bleibt. Netzmessung laeuft davon
unberuehrt weiterhin jeden Zyklus (readGridPower unveraendert).

Neuer Konfigurator verfügbar

[Konfigurator](https://raw.githack.com/surfer1264/Zendure-Stuff/main/shelly_script/Controller/zendure-config-wizard.html)

## Changelog *Major Change* 4.0.0

ab hier beginnt eigene Releasestrecke für den Controller

Ab 4.0.0 wird das Script mit einem Minifier verkleinert: [aktuelles Script herunterladen](https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Controller/zerooutput_multi_kvs_mini.js). Die alte, nicht verkleinerte Fassung bis 3.x liegt nicht mehr im Repo.

Eine Weiterentwicklung kann nur erfolgen unter Nutzung von **Minify**, da die Script-Engine nur js-Scripte bis 50kB zulässt.
Mit einem **Terser** werden alle unnötigen Leerzeichen, Zeilenumbrüche und Kommentare aus dem Code entfernt. Dies kann auch ein Python-Script erledigen.
siehe: https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Controller/minify_keep_config.py
Es sind Kürzungen von bis zu 50% möglich.

[Konfigurator](https://raw.githack.com/surfer1264/Zendure-Stuff/main/shelly_script/Controller/zendure-config-wizard.html)

**NEU in 4.0.0**
socMin kann per KVS Zugriff ohne Neustart des Scriptes geändert werden und wird direkt auf den Solarflow synchronisiert

## CHANGELOG 3.2.1

Bugfix in calculate(): die "excessSocLimit1"-Korrektur wurde aus der
Ladeziel-Berechnung (rawCharge) entfernt.
Problem: ein nicht volles Geraet wurde mit etwa der doppelten sinnvollen Leistung geladen, waehrend
gleichzeitig ein anderes (volles) Geraet entlud - Nettoeffekt: ein dauerhafter, ungedeckter Netzbezug trotz vorhandener Kapazitaet.

## Changelog 3.2.0

Der Konfigurator:

[Konfigurator](https://raw.githack.com/surfer1264/Zendure-Stuff/main/shelly_script/Controller/zendure-config-wizard.html)

**Achtung**

**Neu:** `CONFIG.gridReverseMode` ersetzt `CONFIG.immerBypass`

Vorher (3.1.1): Boolean `immerBypass:` false. false = dynamische Fleet-Sperrlogik aktiv; true = komplett umgangen, beim Start wurde stattdessen fix gridReverse = 1 gesetzt.

Jetzt (3.2.0): String-Enum `gridReverseMode`: "dynamic" mit drei Werten:

"dynamic" – wie bisher immerBypass: false; Netzexport ist so lange erlaubt wie Geräte per AC Ladebedarf haben, wenn alle Geräte socLimit: 1 (Akkus voll) melden, dann wird `grid_revers:2` gesetzt und der Export von Energie verboten  (automatische Sperre/Freigabe pro Zyklus über updateGridReverseLock()). mit `chargeResetMargin`wird die Sperre aufgehoben
"always1" – beim Start wird `gridReverse: 1` fix geschrieben (Netzexport dauerhaft erlaubt), die dynamische Logik läuft nicht
"always2" – neu, gab es vorher gar nicht: beim Start wird `gridReverse: 2` fix geschrieben (Netzexport dauerhaft verboten).

Auswirkung: Fein granularere Kontrolle beim Start – vorher konnte man den gridReverse-Wert beim Start nur "automatisch" oder "immer erlaubt" setzen, jetzt zusätzlich auch dauerhaft "immer verboten" fest vorgeben, ohne die dynamische Logik zu nutzen.

- Bypass immer erlauben (always1)
- Bypass immer verbieten (always2)
- Bypass dynamisch setzen/verbieten (dynamic)

## Changelog 3.1.1

Bezugnahme ist

- https://github.com/surfer1264/Zendure-Stuff/issues/80
- https://github.com/surfer1264/Zendure-Stuff/issues/81

Der Konfigurationsparamteer `revers: true/false`steuert die AC-Ladefähigkeit der Solarflow im Controller.

Der Geräteparameter `gridRevers`steuert die Fähigkeit des Solarflow den Export von Überschussenergie zu erlauben oder zu verbieten.

Beide Parameter haben inhaltlich keine Berührungspunkte, waren im Code aber in einer Abhängigkeit verbunden. Die wurde aufgelöst.

**Problem:** Ein Gerät mit `reverse: false` hätte zwar Energie exportieren können, wurde aber von der Steuerung mit `gridReveers`ausgeschlossen.  

### Entfernt: `excessSocLimit1`-Korrekturterm

Solarflows folgen den Vorgaben des Controllers im Bypass Fall nicht ....
Es wird nicht nur die Entladeleistung gliefert sondern der gesamte PV-Überschuss, der zum Laden eines AC-ladefähigen Hubs dienen kann.

**Problem:** Der Überschusswert wurde defacto "doppelt" angerechnet. Ein AC-ladefähiges Gerät bekam damit im Zweifel den doppelten Ladebefehl. Je nach Gerätekonstellation konnte das sogar zu extra Netzbezug führen.

### Neu: Zustandserkennung beim Start

**Problem:** In einem Testfall war `gridRevers: 2` (Exportsperre aktiv). Nach Scriptstart wurde die Sperre nicht aufgehoben, obwohl alle Voraussetzungen erfüllt waren.

- In `syncSocLimitsDevice()` (einmalig beim Boot) wird jetzt geprüft: `if (data.properties && data.properties.gridReverse === 2) state.allMaxedLogged = true;`
- Damit erkennt der Controller nach einem Neustart sofort, wenn ein Gerät bereits mit `gridReverse: 2` (Netzexport verboten) läuft, statt diesen Zustand erst nach einer vollen Regelrunde (Stunden später) neu herzuleiten.
- Defacto wird die Prüfung durch Setzen des Status `state.allMaxedLogged = true` quasi erzwungen.

## Fazit

v3.1.1 ist im Kern ein **Bugfix-Release**: Die Kopplung von `reverse` (Geräteeigenschaft: darf vom Netz laden) an die fleet-weite `gridReverse`-Steuerung (Geräteeigenschaft: darf bei Ladesperre noch Netzexport machen) wurde entfernt. Beide Mechanismen laufen jetzt, wie beschrieben, komplett unabhängig voneinander – `socLimit` bestimmt allein, wann fleet-weit gesperrt/freigegeben wird, `reverse` bestimmt weiterhin ausschließlich, wie die Ladeleistung auf die Geräte verteilt wird.

## Changelog 3.0.3

Update Logging, siehe Kapitel 12 Gesamtdoku

Codebase: https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Controller/zerooutput_multi_kvs.js

## Changelog 3.0.2

Bei Neustart des Scriptes wird die Reinitialisierung des Status von GridR auf den Wert 1 (Export erlaubt) forciert.

**Hintergrund:** externe Zugriffe auf die Konfiguration des Solatflows (durch HA oder durch die Zendure App) korrumpieren ggf. den Zustand
Ein Neustart kann das beheben.

**Wichtig** Im laufenden Betrieb des Controllers findet KEINE Synchronisation von Einstellugnen statt mit dem Solarflow statt.

Bezugnahme ist

- https://github.com/surfer1264/Zendure-Stuff/issues/80

Es is kein Fix im eigentlichen Sinne, der Zustand bildet sich im Controller automatisch über die Zeit korrekt ab.

## Changelog 3.0.1

**Sperren** (gridReverse: 2, bei allMaxed) bleibt in computeChargeWeights() – läuft weiterhin im Charge-Kontext, wo der Übergang zuverlässig erkannt wird.

**Freigeben** (gridReverse: 1, bei clearlyBelow) wurde von computeChargeWeights() nach distributeDischarge() verschoben.

**Grund:** Die Freigabe hing zuvor an chargeTarget < 0 – bei aktiver Export-Sperre wird jedoch im Zweifel kein Ladebefehl mehr ausgelöst (nur durch starkes Überschwingen an der Regelung), wodurch dieser Zweig nicht deterministisch erreicht wird, sondern eher zufällig. Der Discharge-Zweig läuft dagegen zuverlässig, solange Haushaltslast gedeckt wird. Beide Zweige behalten ihren Flankenschutz (state.allMaxedLogged).

Fixed:

- https://github.com/surfer1264/Zendure-Stuff/issues/79

httpTimeOut: 3 (vorher 5)

## Changelog 3.0.0

Dokumentation aktualisiert

## Changelog 2.4.5

`gridReverse` wird ins Log aufgenommen
`gridReverse` aktiv zur Laufzeit zwischen `1 (Export erlaubt)` und `2 (Export gesperrt)`

Logzeile:

`SF2400: SOC 45% | socL 0 | gridR 2 | Ist 195 W | Soll 195 W | acMode 2 (Export)`

Zweck: `grid_Reverse` ist eine Geräte-Property, die steuert, ob das Zendure-Gerät (Überschuss-)Energie exportieren darf.

Werte, die der Controller selbst setzt:

- Wert 1: Export erlaubt/aktiviert
    - a) beim initialen SoC-Sync, wenn immerBypass: true (Zeile ~1593), dauerhaft freigegeben, danach nie wieder verändert.
    - b) wenn nach einer Vollsperre (allMaxed) mind. ein Gerät wieder klar unter seinem maxSoc − chargeResetMargin liegt (clearlyBelow) – nur bei `immerBypass: false`
- Wert 2: Export gesperrt, wenn alle Geräte ihren maxSoc erreicht haben (allMaxed) – nur bei `immerBypass: false`, um unnötigen Export zu verhindern.

Wenn `immerBypass: true` findet kein aktives Schreiben oder Initalisieren dieses Wertes statt.

## Changelog 2.4.4

- CONFIG.httpTimeout als Parameter entfernt (wird im Code hhtpGet und httpPost als fester Wert mitgegeben))
- CONFIG.watchdog wird als abgeleiteter Wert von intervall (Faktor 2.5) definiert und ist nicht mehr veränderbar

## Changelog 2.4.3

Feature Toggle `compensateSocLimitExcess`entfernt...keine Funktionsänderung

## Changelog 2.4.2

**Geändert (Defaults)**

- `compensateSocLimitExcess`: Default von false auf true geändert.
- `hysteresis`: Default von 10 auf 12 W erhöht.
- `dampingFactor`: Default von 0.6 auf 0.65 erhöht.
- Grid-Log gerundet: Die Log-Zeile Grid: ... W gibt state.gridPower jetzt gerundet aus (Math.round(...)) statt mit Nachkommastellen.

**Neu hinzugefügt**

- Neue Banner-Zeile beim Start: Bypass immer erlauben: aktiviert/deaktiviert.

## Changelog 2.4.0

**Feature**: Hub-seitige GridReverse-Steuerung ("Bypass-Verhalten")

Die Solarflow-Firmware besitzt einen eigenen Schalter `gridReverse` (0/1/2) auf Hub-Ebene. Er steuert nicht das Laden vom Netz, sondern ob der Hub im Bypass-Betrieb (Akku voll, PV-Überschuss wird direkt durchgereicht) Energie ins Netz exportieren darf - betrifft also den Export-Zweig (outputLimit), unabhängig von der script-internen Ladeverteilung.

**Änderung**

- Neuer **CONFIG-Schalter** immerBypass (Default: false) steuert, ob das Feature aktiv genutzt wird:
    - **true**: gridReverse wird nur einmalig beim Start auf 1 (Export erlaubt) gesetzt, danach nie mehr verändert - kein Laufzeit-Effekt, geringstes Risiko.
    - **false** (Default): Script schaltet `gridReverse` aktiv zur Laufzeit zwischen `1 (Export erlaubt)` und `2 (Export gesperrt)` um.
- Neuer CONFIG-Parameter chargeResetMargin (Default: 5 Prozentpunkte) - Hysterese-Abstand unterhalb maxSoc, den mindestens ein Gerät unterschreiten muss, bevor eine gesetzte Sperre wieder aufgehoben wird.

**Codeänderung**
computeChargeWeights() erweitert: erkennt, wenn kein reverse:true-Gerät mehr Lade-Kapazität hat (allMaxed, d. h. Bypass-Betrieb droht) und löst darüber gridReverse=2 (Export gesperrt) aus; erkennt zusätzlich, wenn mindestens ein Gerät klar unter die Reset-Marge gefallen ist (clearlyBelow) und setzt gridReverse=1 (Export erlaubt) zurück. Beide Übergänge sind flankengetriggert (state.allMaxedLogged) - kein wiederholtes Schreiben pro Zyklus, schont den Flash-Speicher der Hubs.
Neue Funktionen setGridReverseDevice()/setGridReverseAll() kapseln den properties/write-Aufruf; nur Geräte mit reverse:true werden angefasst, dryRun-Geräte werden übersprungen.
syncSocLimitsDevice(): Bei immerBypass:true wird gridReverse:1 direkt in denselben properties/write-Aufruf wie minSoc/socSet gepackt (ein Request statt zwei separater Schreibvorgänge beim Start).
state.devices[i].gridReverse (zuletzt geschriebener Wert) und state.allMaxedLogged (Flankenerkennung) neu ergänzt.
Debug-Diagnose bei fehlgeschlagenem Schreibvorgang (DEBUG [Label]/gridReverse - res: ... | error_code: ... | error_message: ...), analog zu den bestehenden Schreibvorgängen (writeDevice, syncSocLimitsDevice).

Nicht per KVS live-überschreibbar: immerBypass/chargeResetMargin sind reine CONFIG-Werte, aktuell ohne Live-Override-Key.

## Changelog 2.3.3

**Problem**: Wenn in einer MultiDevice-Konfig ein Gerät bereits auf 100% (Bypass) stand, wurde der Überschuss genau dieses Gerätes nicht mehr aktiv auf die verbleibenden Geräte aufgeteilt

**Änderung** Feature-Toggle compensateSocLimitExcess (neuer CONFIG-Schalter, Default: true).
Kompensiert beim Laden (rawCharge) die Leistung von Geräten, die socLimit === 1 melden und ein outputLimit gesetzt haben: der Überschuss (zenPower - outputLimit, wenn > 0) wird über alle betroffenen Geräte aufsummiert (excessSocLimit1) und von rawCharge abgezogen.
Alt: rawCharge = round((gridPower - setpoint) + sumZenReverse)
Neu: rawCharge = round((gridPower - setpoint) + sumZenReverse - excessSocLimit1)
kann deaktiviert werden, der FIx wird dadurch deaktiviert

## Changelog 2.3.2

### Konstellationen mit ≥2 reverse:true-Geräten (mit eigener PV)

**Problem**

- keine Überschussverarbeitung in PV-enabled Geräten
- Betrifft Konstellationen mit ≥2 `reverse:true`-Geräten, bei denen mindestens eines direkt angeschlossene PV-Module hat.
- `sumZenReverse` schloss Geräte mit `socLimit === 1` (Laden vom Netz gesperrt) bisher nicht aus. Dadurch konnte die unsteuerbare, PV-erzwungene Weiterausspeisung eines an seiner SOC-Grenze blockierten Speichers einen echten Ladebedarf bei anderen, noch ladefähigen Geräten maskieren – der Regler berechnete fälschlich weiter einen positiven Entlade-Zielwert, statt Laden auszulösen.

**Änderung**

- `calculate()`: `sumZenReverse` prüft zusätzlich `state.devices[i].socLimit !== 1`, analog zur bereits bestehenden Filterung in `computeChargeWeights()`.
- Fetaure Toggle `compensateSocLimitExcess`

**Adressierte Bugs:**

- https://github.com/surfer1264/Zendure-Stuff/issues/69

## Changelog 2.3.1

### Konstellationen Mischung aus reverse:true- und reverse:false Geräten (keine Überschussannahme)

**Effekt:** Ein netzladefähiges Gerät (`reverse:true`) kann jetzt im selben Zyklus laden, während andere Geräte (`reverse:false`, z.B. PV-gekoppelte Entlader) unverändert weiter exportieren – vorher hat der jeweils "verlierende" Zweig alle Geräte per `zeroOutputs()` auf 0 gezwungen.

**Sonst nichts geändert:** `concentrateBelow`/`spreadAbove`, SOC-Balancing, Cooldown, socLimit-Handling, KVS-Logik – alles 1:1 wie in 2.3.0. Bei einer reinen "alle Geräte `reverse:true`"-Flotte ist `sumZenReverse === sumZen`, also verhält sich 2.3.1 dort exakt wie 2.3.0 (kein Regressionsrisiko).

**Adressierte Bugs:**

- https://github.com/surfer1264/Zendure-Stuff/issues/56
- https://github.com/surfer1264/Zendure-Stuff/issues/52

1. **Neue Variable `sumZenReverse`** – zählt beim Einlesen der Geräte zusätzlich zur bisherigen `sumZen` (alle Geräte) eine zweite Summe **nur** für Geräte mit `reverse:true`.

2. **Zwei getrennte Zielsignale statt einem:**

    ```js
    dischargeTarget = gridPower + sumZen          // wie bisher, unveraendert
    chargeTarget     = gridPower + sumZenReverse   // NEU
    ```

    Dazu eine zweite, eigene Glättung (`state.smoothedCharge` statt nur `state.smoothedOutput`).

3. **`calculate()` berechnet jetzt beide Pools im selben Zyklus** statt sich per `if/else` für genau eine Richtung zu entscheiden:
    - Lade-Pool zuerst (`distributeCharge(chargeTarget)`), Geräte die dabei laden landen in `chargeExclude`
    - Entlade-Pool danach (`distributeDischarge(dischargeTarget, chargeExclude)`) – **mit** dem neuen zweiten Parameter, der die gerade ladenden Geräte ausschließt
    - Ergebnis wird gemerged: `output[i] = chargeOutput[i] || dischargeOutput[i]`

4. **`computeDischargeWeights()` und `distributeDischarge()`** bekommen dafür einen neuen optionalen `exclude`-Parameter.

## Changelog 3.0.1 (VERWORFEN)

### 1. dryRun-Feature komplett entfernt

**Hintergrund**: Seicher zur Laufzeit sparen

Lasttests zeigen aber Lauffähigkeit auf

- Shelly 3EM Pro
- Shelly 3EM-63
- Shelly 1PM Gen4
- Shelly Plus1PM (Gen2?)

3.0.1 entspricht ansonsten inhaltlich der 2.3.0

## ChangeLog 2.3.0

**Kurz zusammengefasst:** Die wichtigste inhaltliche Änderung ist, dass 2.3.0 dem Gerät selbst vertraut (`socLimit`), statt SOC-Grenzen rein lokal zu berechnen, und dass der Richtungswechsel-Schutz von einer zeitbasierten "letzte-Richtung-halten"-Logik auf eine zyklenbasierte "erzwungener Standby"-Logik umgestellt wurde. Dazu kommt der neue `standbySmartModeZero`-Schalter und der Wegfall der Live-Überschreibbarkeit von `hysteresis`/`dampingFactor` per KVS.

### 1. SOC-Sperre kommt jetzt vom Gerät (`socLimit`) statt lokal berechnet

- **Alt:** `ds.atMaxSoc = (ds.soc >= cfg.maxSoc)` – lokal aus dem konfigurierten `maxSoc` berechnet.
- **Neu:** Liest `data.properties.socLimit` direkt vom Zendure-Gerät (0 = frei, 1 = Laden gesperrt, 2 = Entladen gesperrt), loggt Änderungen und nutzt es aktiv:
    - `computeDischargeWeights()`: Entladen wird zusätzlich blockiert, wenn `socLimit === 2`
    - `computeChargeWeights()`: Laden wird zusätzlich blockiert, wenn `socLimit === 1`
    - Das ist eine echte Verhaltensänderung – vorher zählte nur der lokal konfigurierte `maxSoc`, jetzt zählt auch, was das Gerät selbst meldet.

### 2. Richtungswechsel-Schutz komplett umgebaut

- **Alt:** `directionChangeCooldown` (Millisekunden, zeitbasiert). Bei Richtungswechsel wurde einfach der letzte `acMode` beibehalten und die Leistung auf 0 gesetzt, bis die Cooldown-Zeit abgelaufen war.
- **Neu:** `directionChangeHoldCycles` (Anzahl Regelzyklen statt Zeit). Es gibt jetzt `realDirection` (nur bei tatsächlich geschriebener Leistung ≠ 0 aktualisiert) und `reversalHoldCount`. Bei Richtungswechsel wird das Gerät für N Zyklen in einen expliziten **Standby-Plan** gezwungen (`acMode:1, outputLimit:0, inputLimit:0`), nicht mehr in die alte Richtung.
- Die Sanity-Checks am Anfang wurden entsprechend ersetzt (Clamp auf 0–20 Zyklen statt der alten ms-Clamps).

### 3. Neuer Parameter `standbySmartModeZero`

- Steuert, welcher `smartMode` (0 oder 1) beim Schreiben von 0 W (Standby) verwendet wird. Vorher war `smartMode` beim Schreiben **immer fest auf 1** gesetzt.
- `planWrite()` liefert jetzt auch `smartMode` als Teil des Plans zurück (vorher nur `acMode`/`outputLimit`/`inputLimit`).
- Erzwingt das Standby bei einigen Geräten (2400AC), die mit `smartmode: 1` partout nicht in den Standby gehen

### 4. KVS-Live-Override für `hysteresis` und `dampingFactor` entfernt

- In 2.2.0 konnten `zdmc_hysteresis` und `zdmc_dampingFactor` per KVS live überschrieben werden (inkl. Seeding der Default-Werte).
- In 2.3.0 sind diese beiden Blöcke sowohl aus `readKvsOverrides()` als auch aus `seedKvsDefaults()` entfernt. Nur noch `setpoint` sowie `dev{n}_dischargeAllowed`/`dev{n}_reverse` sind live überschreibbar.

### 5. `applyOutputs()` / `writeDevice()` refactored

- **Alt:** `writeDevice()` hat `planWrite()` und `enforceDirectionCooldown()` beim eigentlichen Schreiben **erneut** ausgeführt (mit frischem `Date.now()`), losgelöst von der Vorschau in `applyOutputs()`.
- **Neu:** Der Plan wird einmal in `applyOutputs()` berechnet, in einem `plans`-Array zwischengespeichert und an `writeDevice()`/`writeAllDevices()` durchgereicht – Vorschau und tatsächlicher Schreibvorgang benutzen garantiert denselben Plan.
- Die Hysterese-Skip-Bedingung ist strenger geworden: Ein Schreibvorgang wird jetzt auch dann ausgelöst, wenn sich `acMode` oder `smartMode` ändern, selbst wenn sich die Leistung kaum ändert (vorher wurde nur die Leistungsdifferenz gegen `CONFIG.hysteresis` geprüft).

### 6. `state.devices[i]`-Struktur geändert

- Entfernt: `atMaxSoc`, `acModeChangedAt`
- Neu: `socLimit`, `smartMode`, `realDirection`, `reversalHoldCount`

### 7. Banner-Ausgabe passend angepasst

- „Richtungswechsel-Cooldown: X s" → „Richtungswechsel-Bremse: X Takt(e)"
- KVS-Zeile nennt nur noch `setpoint`/`dev{n}_dischargeAllowed`/`dev{n}_reverse` (kein `hysteresis`/`dampingFactor` mehr)

---

## 2.2.0 Initiale Version
