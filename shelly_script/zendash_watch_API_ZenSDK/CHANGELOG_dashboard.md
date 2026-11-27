# Changelog Dashboard und Proxy

Es gibt drei Changelogs:

- [Shelly-Script `zendash_watch` (mit API)](CHANGELOG.md)
- **Dashboard und Proxy** – diese Datei (Dashboard, `zendure_proxy.py`, `zeitplan.py`, EXE und local_helper)
- [Home-Assistant-App Dashboard-Proxy](HA_zendure_proxy/CHANGELOG.md) – nur was die App selbst betrifft

Ab 5.0.0 zählen Dashboard und Proxy unabhängig vom Shelly-Script. Dashboard und Proxy tragen untereinander dieselbe Nummer. Welche Script-Version mindestens nötig ist, steht im jeweiligen Abschnitt. Bis 4.1.0 trugen alle drei dieselbe Nummer, Änderungen bis 3.5.12 stehen im [Changelog des Shelly-Scripts](CHANGELOG.md).

## Changelog 5.8.3

**Ziel:** Den Energiefluss auf dem Handy quer im Vollbild zeigen, ohne die übrige Seite. Keine Änderung an den Shelly-Scripten und am Regler.

- **Neuer Knopf im Energiefluss** rechts neben dem Hintergrund-Knopf (Symbol: vier Ecken). Nur auf Handy und Tablet (Touch ohne Maus) im Querformat; am PC und im Hochformat ausgeblendet. Ohne Standort am Shelly fehlt nur der Hintergrund-Knopf, der Vollbild-Knopf bleibt.
- **Vollbild nur für den Energiefluss:** Das Flowchart wird so groß, dass es ohne seitliches Wischen auf das Display passt; Geräteauswahl, Hintergrund (Bild/Bewegung) und Linien laufen mit. Mit Fullscreen-API (Android, iPad) echtes Vollbild, sonst (Safari auf dem iPhone) legt sich der Energiefluss über die Seite – dort bleiben die Safari-Leisten sichtbar, als Home-Bildschirm-App nicht.
- **Beenden:** gleicher Knopf, Zurück-Geste/Esc, Drehen ins Hochformat oder Wechsel zur Geräteansicht. Ein Seiten-Vollbild aus dem Menü bleibt danach bestehen.
- **Display bleibt an,** solange das Vollbild läuft, wo der Browser es erlaubt (Wake Lock, nur über https, z. B. Home Assistant).
- Geprüft mit Edge (Handy-Emulation 844 × 390 quer und 390 × 844 hoch, PC 1280 × 720). Echtes Vollbild auf dem Gerät noch nicht geprüft.
- Home-Assistant-App 5.8.3.0. Der Proxy ändert sich nur in der Versionsnummer.

Keine Änderung am CONFIG-Block nötig.

## Changelog 5.8.2

**Ziel:** Die Knöpfe passen auf dem Handy wieder in eine Zeile – auch bei Ansichtsgröße A2 und A3. Keine Änderung an den Shelly-Scripten und am Regler.

- **Kopfzeile:** Der Status-Punkt sitzt in der Uhr-Pille (eine Pille weniger). Auf schmalen Bildschirmen zeigt das Menü nur ⚙, Uhr links, Schloss und ⚙ rechts. „Verbinde…“/„Verbindungsproblem“ ist dort nur noch am roten Punkt zu sehen, Antippen zeigt die Erklärung, Screenreader lesen den Text weiter vor.
- **Details:** eigener runder Knopf (Symbol `</>`) neben **Geräte | Energiefluss** statt dritter Teil des Umschalters. Auf schmalen Bildschirmen füllt der Umschalter die ganze Breite, die Überschrift „Geräte“/„Energiefluss“ entfällt dort (für Screenreader bleibt sie). Tastenkürzel **T** wie bisher.
- **Energiefluss:** Hintergrund über einen runden Knopf, der Aus → Bild → Bewegung durchschaltet, statt drei Knöpfen. Die Geräteauswahl bricht nicht mehr um, sondern lässt sich waagerecht wischen.
- **Grenze für „schmal“ wächst mit der Ansichtsgröße:** Abgefragt wird die Breite von Kopfzeile bzw. Leiste (Container Query, 37 em) statt fester 640 px Fensterbreite. Bei A1 ab 600 px, bei A2 ab 690 px, bei A3 ab 780 px Inhaltsbreite. iPad quer und PC bleiben unverändert, iPad hochkant wird bei großer Schrift kompakt.
- **Ansichtsgröße A4 (150 %) entfällt.** Eine gemerkte A4 wird beim nächsten Laden zu A3, auch für die Zeitplan-Seite.
- Geprüft mit Edge bei 360, 402, 820 und 1280 px in DE und FR. Im Extremfall (Französisch, A3, 360 px) wird „Flux d’énergie“ gekürzt, nichts ragt mehr aus dem Bild. Safari ab iOS 16 und Chrome ab 105 unterstützen Container Queries.
- Home-Assistant-App 5.8.2.0. Der Proxy ändert sich nur in der Versionsnummer.

Keine Änderung am CONFIG-Block nötig.

## Changelog 5.8.1

**Ziel:** Technische Details direkt auf dem Dashboard schalten statt über das Menü „Ansicht“. Keine Änderung an den Shelly-Scripten und am Regler.

- **Taste „Details“** (technische Details) sitzt jetzt im Umschalter: **Geräte | Energiefluss | Details**, durch einen dünnen Strich abgesetzt, weil sie unabhängig ein/aus schaltet. Sichtbar in beiden Ansichten, eingeschaltet farbig hinterlegt wie die gewählte Ansicht. Der Zustand wird weiter pro Browser gemerkt, Tastenkürzel **T** und „Ansicht zurücksetzen“ wirken wie bisher.
- **Menü „Ansicht“:** die Zeile „Technische Details“ entfällt.
- Home-Assistant-App 5.8.1.0. Der Proxy ändert sich nur in der Versionsnummer.

Keine Änderung am CONFIG-Block nötig.

## Changelog 5.8.0

**Ziel:** Zeitplan, Technische Details und Übersicht lassen sich per Tastenkürzel aufrufen. Keine Änderung an den Shelly-Scripten und am Regler.

- **Tastenkürzel auf der Startseite:** **Z** öffnet den Zeitplan, **T** schaltet Technische Details ein/aus, **O** klappt die Übersicht auf/zu, **?** zeigt die Kürzel 6 s lang unten an. Ohne Zeitplan im Proxy meldet **Z** „Zeitplan nicht verfügbar“.
- **Keine Konflikte:** Die Kürzel greifen nicht beim Tippen in Eingabefeldern und nicht mit Strg, Alt oder Cmd. Groß- und Kleinschreibung ist egal.
- **Menü „Ansicht“:** neue Zeile „Tastenkürzel“ mit der Liste. Die Schalter tragen `aria-keyshortcuts` für Screenreader.
- Home-Assistant-App 5.8.0.0. Der Proxy ändert sich nur in der Versionsnummer.

Keine Änderung am CONFIG-Block nötig.

## Changelog 5.7.2

**Ziel:** Fehlerkorrektur zu 5.7.1 – ohne Offgrid-Steckdose verschwindet jetzt auch die Flusslinie.

- **Offgrid-Linie:** Bei Geräten ohne Offgrid-Steckdose (z. B. SolarFlow 800) war in 5.7.1 nur der Knoten ausgeblendet, Linie und Spur blieben stehen. Jetzt verschwinden beide mit dem Knoten.
- Home-Assistant-App 5.7.2.0. Der Proxy ändert sich nur in der Versionsnummer.

Keine Änderung am CONFIG-Block nötig.

## Changelog 5.7.1

**Ziel:** Der Energiefluss zeigt Offgrid nur noch, wenn ein Solarflow eine Offgrid-Steckdose hat. Keine Änderung an den Shelly-Scripten und am Regler.

- **Offgrid nur mit Steckdose:** Knoten, Linie und Punkte erscheinen nur, wenn im gewählten Ausschnitt mindestens ein Gerät eine Offgrid-Steckdose hat (bei „Gesamt“ irgendein Gerät, sonst genau das gewählte). Erkannt wird das wie beim Reiter „Offgrid“ an `offGrid` (Report `gridOffPower`). Bisher stand der Knoten immer da, ohne Steckdose mit „nicht belegt“.
- **Gemischte Anlagen:** Bei „Gesamt“ zählt die Summe der Geräte mit Steckdose. Ein einzeln gewähltes Gerät ohne Steckdose zeigt keinen Offgrid-Knoten.
- **Kein Flackern:** Der Browser merkt sich je Gerät „hat Steckdose“ (`localStorage`). Ist ein solches Gerät offline, bleibt der Knoten stehen und zeigt „keine Daten“. Meldet ein Gerät online keinen Offgrid-Wert mehr (z. B. nach einem Tausch), oder ist es nicht mehr konfiguriert, fällt es aus der Merkliste.
- **Steckdose aus:** Ist die Offgrid-Steckdose am Gerät ausgeschaltet (`gridOffModeHw` = 2) und fließt nichts, steht unter dem Knoten „Steckdose aus“.
- Home-Assistant-App 5.7.1.0. Der Proxy ändert sich nur in der Versionsnummer.

Keine Änderung am CONFIG-Block nötig.

## Changelog 5.7.0

**Ziel:** Eine zusätzliche Einspeisung im Haushalt (Balkonkraftwerk, weiterer Wechselrichter), die ein Shelly misst, erscheint im Energiefluss, und der Hausverbrauch stimmt wieder. Keine Änderung an den Shelly-Scripten und am Regler.

- **Einstellung:** Menü **Ansicht → Einspeisung**: Schalter, frei wählbarer Name (bis 24 Zeichen) und bis zu zwei IP-Adressen. Gespeichert beim Proxy in `zendure_einspeisung_config.json` (HA-App: Datenordner), gilt für alle Browser. Neue Adresse `/einspeisung` (GET, mit `?mess=1` samt Messung; POST zum Speichern, nur JSON).
- **Messung im Proxy:** Der Proxy fragt die Shellys direkt ab, beide parallel, nur solange ein Browser den Energiefluss zeigt (Zwischenspeicher 2 s für mehrere Browser). Typ wird selbst erkannt: `Shelly.GetStatus` mit `switch:0`/`pm1:0` (`apower`), `em1:0` (`act_power`), `em:0` (`total_act_power`); ohne RPC Gen1 `/status` mit `meters[0]` bzw. `emeters` (3EM: Summe der drei Phasen). Kein Passwortschutz.
- **Testabfrage beim Speichern:** Bei eingeschalteter Funktion fragt der Proxy jede Adresse einmal ab und speichert nur, wenn alle einen Leistungswert liefern. Sonst „Nicht gespeichert: Shelly unter … nicht erreichbar“ bzw. „… liefert keine Leistung“, Schalter und Eingaben bleiben zum Korrigieren stehen. Ungültige IP-Adressen werden abgelehnt. Bei Erfolg zeigt die Bestätigung die aktuelle Leistung je Shelly. Ausschalten speichert ohne Test.
- **Wert:** je Shelly der Betrag (Vorzeichen je nach Generation verschieden), unter 5 W = 0 (Ruheverbrauch nachts), Summe der erreichbaren Shellys.
- **Hausverbrauch im Energiefluss:** Haus = Netzsaldo + Summe der Ausgänge + Einspeisung. Bisher fehlte die Einspeisung, der Hausverbrauch war um genau diese Leistung zu niedrig.
- **Anzeige:** eigener Knoten über dem Haus (Rahmen wie PV, Punkte laufen ins Haus), nur im Energiefluss, nur bei „Gesamt“ und nur, wenn eingeschaltet und eine Adresse eingetragen ist. Ein Shelly nicht erreichbar: „1 von 2 offline“, es zählt der erreichbare. Keiner erreichbar: Knoten grau mit „offline“, die Einspeisung fehlt in der Hausrechnung. DE/EN/FR.
- Home-Assistant-App 5.7.0.0

Keine Änderung am CONFIG-Block nötig.

## Changelog 5.6.0

**Ziel:** Jedes Entladefenster im Zeitplan bekommt eine Betriebsart – Nulleinspeisung oder Entladen mit fester Leistung. Braucht das Shelly-Script ab 4.1.0, keine Änderung an den Shelly-Scripts und am Regler.

- **Betriebsart je Fenster:** Beim Bearbeiten eines Fensters wählst du **Nulleinspeisung** (Regelung nach Zähler) oder **Entladen fix** mit Leistung in Watt. Der Proxy schreibt dazu neben `zdmc_devN_dischargeAllowed` auch `zdmc_dischargeFixed` (im Fenster „fix“ die Leistung, sonst 0). Außerhalb der Fenster ist Entladen weiterhin immer gesperrt. Bestehende Pläne laufen unverändert weiter: Fenster ohne Betriebsart gelten als Nulleinspeisung.
- **Planwechsel:** Jeder Wechsel der Betriebsart zählt als Planzeit, auch fix 800 W → Nulleinspeisung oder 800 W → 200 W.
- **Fix-Leistung von Hand:** Verstellst du die Fix-Leistung im Dashboard, gilt das bis zum nächsten Wechsel; die Plan-Seite zeigt es an. Stellst du sie wieder auf den Planwert, übernimmt der Plan wieder.
- **Prüfung:** Die Plan-Seite und der Proxy lassen nur Leistungen ab `dischargeStartupPower` bis zur Summe `maxOutput` zu und keine sich überschneidenden Fenster. Lehnt das Shelly-Script einen Wert trotzdem ab, zeigt die Plan-Seite den Fehler und der Proxy versucht es erst beim nächsten Wechsel wieder.
- **Schreiben:** Alle Änderungen gehen in einem `kvs_set_api`-Aufruf raus, in der Reihenfolge sperren → Fix-Leistung → freigeben, damit kein Zwischenstand mehr entlädt als geplant. Nach jedem Schreibversuch liest der Proxy frisch nach; kam nur ein Teil an, schreibt er beim nächsten Durchlauf nur den Rest.
- **Anzeige:** Plan-Seite mit Etikett je Fenster, farbiger Zeitleiste (türkis Nulleinspeisung, orange fix, grau gesperrt), Legende und Hinweis zur Fix-Leistung. Die Gerätekarte im Dashboard zeigt z. B. „Plan · fix 800 W bis 15:00“ und die Leiste in denselben Farben. DE/EN/FR.
- **Zeitplan nach manuellem Laden:** Bisher blieb „Plan · pausiert … (manuelles Laden)“ bis zum nächsten Planwechsel stehen, auch wenn das Laden längst beendet war. Jetzt übernimmt der Plan bei seiner nächsten Prüfung (spätestens nach zwei Minuten) wieder, wenn „Entladen erlaubt“ zum Plan passt. Weicht der Schalter ab, zeigt die Karte „von Hand · bis …“; ist der Akku voll, gilt die Regel für vollen Akku. Gerätekarte und Plan-Seite zeigen das Ende des manuellen Ladens sofort an.
- Home-Assistant-App 5.6.0.0

Keine Änderung am CONFIG-Block nötig.

## Changelog 5.5.1

**Ziel:** Zeitplan hält die Sperre auch nach vollem Akku ein, und der Energiefluss zeigt PV-Durchleitung richtig an. Braucht das Shelly-Script ab 4.1.0.

- **Zeitplan, voller Akku:** Bei vollem Akku (`socLimit 1`) gibt der Plan weiterhin frei, damit Solarstrom durchkommt. Neu: Ist der Akku danach nicht mehr voll und gibt er selbst mehr als 30 W ab (`packInputPower`), sperrt der Plan wieder – bisher blieb das Gerät bis zum nächsten Planwechsel frei und entlud außerhalb der Fenster. Wird der Akku wieder voll, gibt der Plan erneut frei. Hilfetexte der Plan-Seite (DE/EN/FR) angepasst.
- **Energiefluss und Gerätekarten:** Die AC-Leistung wird jetzt aus `outputHomePower − gridInputPower` berechnet, unabhängig von `acMode`. Ein volles Gerät in `acMode 1`, das PV ans Haus durchreicht, zeigte bisher 0 W und im Energiefluss „Akku lädt“; auch der Hausverbrauch war zu niedrig.
- **Akku im Energiefluss:** direkt gemessen (`outputPackPower − packInputPower`), die bisherige Rechnung PV − AC − Offgrid bleibt als Rückfall.
- Home-Assistant-App 5.5.1.0

Keine Änderung am CONFIG-Block nötig.

## Changelog 5.5.0

**Ziel:** Entladen nach Zeitplan und nur noch ein Dashboard. Braucht das Shelly-Script ab 4.1.0, keine Änderung an den Shelly-Scripts.

- **Zeitplan (neu):** Auf der Seite `/zeitplan` legst du Entladefenster für alle Geräte fest (Von/Bis, Wochentage, auch über Mitternacht). In den Fenstern darf entladen werden, außerhalb ist Entladen gesperrt. Der Proxy schaltet dazu `zdmc_devN_dischargeAllowed` über `kvs_set_api`. Je Gerät lässt sich wählen, ob es dem Plan folgt.
- **Regeln:** Geschaltet wird nur zu den Planzeiten; was du dazwischen von Hand umstellst, bleibt bis zum nächsten Wechsel. Sperren klappt immer. Freigegeben wird nur, wenn die schwächste Zelle über `minVoltReset` des Watchdogs liegt, sonst neuer Versuch alle zwei Minuten. Manuelles Laden und voller Akku unterbrechen den Plan für das Gerät bis zum nächsten Wechsel, bei vollem Akku wird vorher freigegeben.
- **Watchdog nötig:** Der Plan braucht den Watchdog im zendash-Script und schaltet nur Geräte mit `watch: true`. Er liest nur dessen Werte mit (`status_api?bg=read`), fragt die Speicher also nicht zusätzlich ab. An den Planzeiten schaltet er sofort, dazwischen prüft er alle zwei Minuten.
- **Gerät offline:** Gesperrt wird trotzdem, freigegeben erst, wenn das Gerät wieder erreichbar ist. Plan-Seite und Gerätekarte zeigen dann „Plan · Gerät offline“.
- **Dashboard:** Menü „Ansicht“ hat den Eintrag „Zeitplan“. Jede Gerätekarte zeigt bei aktivem Plan eine Zeile mit Zustand und nächstem Wechsel und eine dünne Leiste für heute; Antippen öffnet den Zeitplan.
- **Proxy:** neue Datei `zeitplan.py` (optional wie `ts_bridge.py`), neue Adressen `/zeitplan`, `/schedule` (GET/POST) und `/fonts.css`. Der Plan liegt in `zendure_schedule_config.json` und richtet sich nach der Uhrzeit des Proxy-Rechners. Antworten von `config_api` und `status_api`, die das Dashboard holt, nutzt der Plan mit.
- **„von Hand“ sofort:** Schaltest du „Entladen erlaubt“ abweichend vom Plan um, zeigen Gerätekarte und Plan-Seite sofort „von Hand · bis …“, nicht erst nach der nächsten Prüfung im Proxy. Stellst du ihn wieder auf den Planstand, verschwindet „von Hand“ sofort und der Plan übernimmt das Gerät wieder. Der Proxy zieht Schaltvorgänge aus dem Dashboard dafür gleich nach.
- **Gerätekarten:** Bei gesperrter Bedienung stehen die technischen Details in allen Karten wieder auf gleicher Höhe, auch wenn nur eine Karte die Zeitplan-Zeile zeigt.
- **Klassisches Dashboard entfernt:** `zendure-dashboard.html` gibt es nicht mehr, `/klassisch` führt auf die Startseite. Die Kennung für das Versions-Manifest trägt jetzt `zendure-dashboard-neu.html`.
- Home-Assistant-App 5.5.0.0

## Changelog 5.4.4

**Ziel:** Verbindungsstatus als Punkt und neue Werte für ThingsBoard. Braucht das Shelly-Script ab 4.1.0.

- **Verbindungsstatus (neues Design):** Statt „Live · Poll alle 4s“ steht oben rechts nur noch der grüne Punkt. Der Tooltip erklärt ihn: Das Dashboard fragt alle 4 s den Status beim Shelly-Script ab, grün heißt, die letzte Abfrage hat geklappt. Bei einem Verbindungsproblem bleiben roter Punkt und Text wie bisher, mit eigenem Tooltip. Das klassische Dashboard ist unverändert.
- **ThingsBoard-Upload:** neue wählbare Werte `temp` (Gerätetemperatur), `packTempLow` (kühlstes Akkupack) und `heatState` (Heizung, 0 aus / 1 an), auf `/thingsboard` standardmäßig aus. `heatState` geht wie `minSoc` nur bei Änderung raus, dazu einmal am Tag und nach einem Neustart. Die Werte brauchen das Shelly-Script ab 3.5.9 (`temp`), 4.2.0 (`heatState`) bzw. 4.3.0 (`packTempLow`), sonst fehlen sie.
- Home-Assistant-App 5.4.4.0

## Changelog 5.4.3

**Ziel:** Optische Kleinigkeiten im Kopf des Dashboards. Braucht das Shelly-Script ab 4.1.0.

- Das Dashboard bekommt kleine optische Änderungen in beiden Designs.
- Der Proxy hat nur die neue Versionsnummer bekommen.
- Home-Assistant-App 5.4.3.0

## Changelog 5.4.2

**Ziel:** iOS übernimmt das Zeichen „ZS“ beim Hinzufügen zum Home-Bildschirm. Braucht das Shelly-Script ab 4.1.0.

- **Icon-Links relativ:** Das Dashboard verweist auf `favicon.svg` und `apple-touch-icon.png` ohne führenden Schrägstrich. Damit kommen die Icons auch über die Seitenleiste von Home Assistant (Ingress) vom Proxy und nicht von Home Assistant.
- **Neu laden erzwingen:** Die Links tragen `?v=5.4.2`, damit iOS und Browser ein zwischengespeichertes altes Symbol nicht weiterverwenden.
- **HEAD-Anfragen:** Der Proxy beantwortet Anfragen nach den Icons jetzt auch per HEAD, vorher kam „nicht gefunden“.
- Home-Assistant-App 5.4.2.0

## Changelog 5.4.1

**Ziel:** Das Zeichen „ZS“ auch als Symbol im Browser-Tab und auf dem Home-Bildschirm. Braucht das Shelly-Script ab 4.1.0.

- **Favicon:** Der Proxy liefert statt des Blitzes die Ligatur „ZS“ aus dem Designsystem (Teal nach Amber auf dunklem Grund), für `favicon.svg` und `favicon.ico`.
- **Home-Bildschirm (iOS):** Dasselbe Motiv als PNG 180 × 180 für alle `apple-touch-icon`-Pfade. Ein schon angelegtes Symbol auf dem Home-Bildschirm bleibt, bis es neu hinzugefügt wird.
- Das Dashboard hat nur die neue Versionsnummer bekommen.
- Home-Assistant-App 5.4.1.0

## Changelog 5.4.0

**Ziel:** Aufgeräumte Fußzeile im neuen Design und eigenes Zeichen im Kopf des Dashboards. Braucht das Shelly-Script ab 4.1.0.

- **Fußzeile:** Sichtbar bleiben Version, Update-Hinweis, Abfragefehler und der Link „Hilfe“.
- **„Mehr ▾“:** Klappt die Einrichtung auf (IP / Script-ID, ThingSpeak, ThingsBoard, Log-Bericht), dazu Verlauf und letzte Aktualisierung. Die Wahl wird nicht gespeichert.
- **API-Links:** `config_api`, `status_api` und `kvs_set_api` erscheinen nur noch bei eingeschalteten technischen Details.
- **Update-Hinweis:** in Fettschrift, damit er auffällt. Der Satz „Eigenständige Seite …“ entfällt.
- **Ligatur „ZS“ (beide Designs):** Links neben „ZENDURE // GRID“ steht jetzt das Zeichen „ZS“ für Zendure und Shelly.
- **Größe und Farben:** Das Zeichen reicht von der Oberkante von „ZENDURE“ bis zur Grundlinie der Unterzeile und passt sich an Ansichtsgröße, Sprache und Fensterbreite an. Tag- und Nachtansicht haben eigene Farben.
- Der Proxy hat nur die neue Versionsnummer bekommen.
- Home-Assistant-App 5.4.0.0 und 5.4.0.1

## Changelog 5.3.0

**Ziel:** Der Solarflow-Knoten im Energiefluss zeigt, was das Gerät insgesamt macht. Braucht das Shelly-Script ab 4.1.0.

- **Solarflow-Knoten (neues Design):** Der Untertext lautet jetzt „gibt ab“ (AC über 5 W oder Offgrid ab 5 W), „nimmt auf“ (sonst AC unter −5 W, Offgrid ab −5 W oder PV ab 5 W) oder „Bereitschaft“ (sonst). Bisher stand dort auch dann „Bereitschaft“, wenn nur die PV den Akku lud oder nur die Offgrid-Dose lieferte. Der Wert darüber bleibt die AC-Leistung.
- **Deutsche Texte (neues Design):** „Standby“ heißt in der Gerätekarte und in den technischen Details jetzt „Bereitschaft“.
- Das klassische Dashboard und der Proxy haben nur die neue Versionsnummer bekommen.
- Home-Assistant-App 5.3.0.0

## Changelog 5.2.0

**Ziel:** Kühlstes Pack in den technischen Details anzeigen. Läuft weiter ab Shelly-Script 4.1.0, die neue Zeile erscheint ab Script 4.3.0.

- **Technische Details (neues Design):** neue Zeile „Kühlstes Pack“, z. B. „17 °C“. Das ist der kleinste `maxTemp`-Wert aller Packs, also eine Näherung: Die kälteste Zelle kann darunter liegen. Liefert ein Gerät den Wert nicht, steht dort „–“. Liefert ihn keines, entfällt die Zeile.
- **Offgrid-Reiter:** Der KVS-Schlüssel `zdmc_devN_gridOffMode` erscheint bei eingeblendeten technischen Details in derselben kleinen Schrift wie die anderen Schlüssel. Bisher war er viel zu groß.
- Das klassische Dashboard und der Proxy haben nur die neue Versionsnummer bekommen.
- Home-Assistant-App 5.2.0.0

## Changelog 5.1.0

**Ziel:** Heizzustand des Geräts in der Karte und in den technischen Details anzeigen. Läuft weiter ab Shelly-Script 4.1.0, die neuen Anzeigen erscheinen ab Script 4.2.0.

- **Flamme hinter dem Gerätenamen (neues Design):** Sie erscheint, solange die Heizung an ist (`heatState` = 1). Antippen oder mit der Maus darauf zeigen erklärt sie. Bei 0, ohne Wert, offline und bei veralteten Daten ist sie ausgeblendet.
- **Technische Details (neues Design):** neue Zeile `heatState`, z. B. „0 · Heizung aus“. Wie bei den anderen Zeilen gilt: Liefert ein Gerät den Wert nicht, steht dort „–“. Liefert ihn keines, entfällt die Zeile.
- **Offgrid im Energiefluss:** Der Untertext unterscheidet jetzt „keine Last“ (Gerät meldet Offgrid, unter 5 W), „nicht belegt“ (kein Gerät meldet Offgrid) und „keine Daten“ (kein Gerät online).
- **Hintergrund im Energiefluss:** Das Wort „Hintergrund“ in der Auswahl entfällt, weil es wie ein Button aussah. Die Erklärung steht jetzt im Tooltip der drei Buttons.
- Das klassische Dashboard und der Proxy haben nur die neue Versionsnummer bekommen.
- Home-Assistant-App 5.1.0.0

## Changelog 5.0.0

**Ziel:** Eigene Versionsnummer für Dashboard und Proxy und Hinweis auf neuere Versionen. Braucht das Shelly-Script ab 4.1.0.

- **Eigene Versionsnummer:** Dashboard und Proxy zählen ab jetzt unabhängig vom Shelly-Script. Die Fußzeile zeigt beide Nummern, z. B. „v5.0.0 · Script v4.1.0“. Gelb wird sie nur noch, wenn das Script älter ist als die Mindestversion.
- **Update-Hinweis:** Gibt es auf GitHub eine neuere Version von Dashboard, Proxy oder Shelly-Script, steht in der Fußzeile „⬆ Update … verfügbar“ mit Link auf den Changelog. Ohne Internet bleibt der Hinweis weg.
- **Proxy:** neue Adresse `/versions` (eigene Version und zuletzt geholter Stand von GitHub). Der Proxy fragt beim Start und dann alle 12 Stunden nach und meldet eine neuere Version auch in der Konsole. Mit `--no-update-check` fragt er nie.
- Home-Assistant-App 5.0.0.0

## Changelog 4.1.0

**Ziel:** Der Reiter „Offgrid“ in der Gerätekarte (neues Design) funktioniert jetzt. Dafür braucht es das Shelly-Script 4.1.0 und das Regel-Script ab 5.3.8.

- **Modus wählen:** Ein Klick auf „Aus“, „Ein“ oder „Öko“ schreibt sofort `zdmc_devN_gridOffMode` (`2`, `0` bzw. `1`) über `kvs_set_api`. Wie die anderen Bedienelemente geht das nur bei freigegebener Bedienung. Während des Schreibens sind die drei Buttons kurz gesperrt. Schlägt das Schreiben fehl, springt die Auswahl zurück.
- **Anzeige:** Markiert ist der Wert aus der KVS. Gibt es noch keinen KVS-Key, ist der Modus am Gerät markiert. Darunter steht „Am Gerät: …“, orange mit „abweichend, KVS …“, solange das Gerät einen anderen Modus hat. Ohne KVS-Key steht dort, dass das Regel-Script am Gerät nichts ändert.
- **Hinweis bei Abweichung:** Weicht der Modus am Gerät länger als 75 s von der KVS ab (z. B. nach einer Änderung in der App), erscheint in der Karte der Hinweis „Offgrid am Gerät … · abweichend, KVS …“, mit Hilfetext. Das Prinzip ist dasselbe wie bei der Reserve.
- **Technische Details:** neue Zeile „Offgrid KVS / Gerät“ mit den Rohwerten.
- Der Reiter erscheint weiterhin nur bei Geräten mit Offgrid-Ausgang. Das klassische Dashboard hat nur die neue Versionsnummer bekommen.
- Home-Assistant-App 4.1.0.0

## Changelog 4.0.1

- Nur die Versionsnummer, passend zum Shelly-Script 4.0.1 (kleiner minifiziert). Dashboard und Proxy unverändert
- Home-Assistant-App 4.0.1.0

## Changelog 4.0.0

Ziel: Das neue Design wird die Startseite des Dashboards; dazu robustere Verbindung zum Shelly und Fehlerzähler im Proxy.

- **Neues Design ist die Startseite** `/`, das klassische Dashboard liegt unter `/klassisch`. Alte Lesezeichen auf `/neu` leiten auf die Startseite weiter. Umschalten weiter im Menü „Ansicht“ → „Design“. Gerätekarten mit Ladebalken (Reserve und Ladegrenze schraffiert), Hinweise nur bei Abweichungen, Einstellungen nur bei freigegebener Bedienung, Ansicht „Energiefluss“ mit animierten Linien
- **Energiefluss:** In der Gesamtansicht steht in der Mitte „Solarflows“ statt der Liste aller Gerätenamen; Ansicht und Geräteauswahl merkt sich der Browser
- **Offgrid mit Richtung:** positiv = Abgabe ans Haus („Ausgang“), negativ = Einspeisung ins Gerät („Eingang“, wie PV). Der Energiefluss zeigt nur Beträge, die Animation läuft in Flussrichtung; vorher stand bei Einspeisung „nicht belegt“ und die Linie stand still
- **Sonnenaufgang und -untergang** neben der Uhr (nur neues Design). Der Proxy liest den Standort einmal am Tag aus `Sys.GetConfig` des Dashboard-Shellys (neue Adresse `/standort`), gerechnet wird im Browser
- **Verbindungsprobleme (beide Designs):** Ein einzelner Abfrage-Aussetzer bleibt unsichtbar; erst nach zwei Fehlern in Folge erscheinen Hinweis (mit Grund, z. B. „Zeitüberschreitung“) und „Verbindungsproblem“, die Gerätekarten werden blass, im neuen Design „veraltet“, Animationen halten an. Läuft eine Abfrage noch, fällt der nächste Takt aus (vorher konnten sich Anfragen am Shelly stapeln)
- **Proxy zählt Abfragefehler** je Tag nach Art (Zeitüberschreitung, nicht erreichbar, Fehler vom Shelly) mit letztem Zeitpunkt und Grund: neue Adresse `/proxy_fehler`, im Fuß des Dashboards „Abfragefehler heute: …“, jeder Fehler auch im Protokoll (auch mit `-q` und in der Home-Assistant-App). Die 502-Antwort enthält jetzt `art`
- **Proxy:** `config_api` darf 10 s statt 5 s dauern (das Script wartet dort bis zu 2 s auf seine Geräteabfrage und liest die KVS vom Regler-Shelly); die Zeitüberschreitungen traten nur dort auf. Messwerte (`status_api`) bleiben bei 5 s
- Neues Design: Gerätekarten schlanker – der Hinweisbereich reserviert keinen Platz mehr, die Einstellungen beginnen weiter in allen Karten auf gleicher Höhe
- Home-Assistant-App 4.0.0.0 (die Punkte oben kamen teils schon mit 3.5.12.4 bis 3.5.12.6)
- Nachtrag (Home-Assistant-App 4.0.0.1, Dashboard ohne neue Versionsnummer): **Hintergrund nach Tageszeit** im Energiefluss, Schalter in der Karte **Aus · Bild · Bewegung** (Standard Aus, pro Browser gemerkt). Sonne, Himmel, Mond, Sterne und Landschaft folgen Sonnenauf- und -untergang, gerechnet einmal pro Minute im Browser; ohne Standort am Shelly ausgeblendet. Shelly-Script und Proxy unverändert
- Nachtrag (Home-Assistant-App 4.0.0.1): **Kontraste nach WCAG 2.2** geprüft und angehoben – alle Texte mindestens 4,5:1 in hell und dunkel, auch auf dem Hintergrundbild (Kacheln dort deckender). Aktive Schalter mit dunkler Schrift auf Türkis, Rot (dunkel) und Grün, Grau, Türkis, Orange (hell) etwas kräftiger, „Keine Hinweise“ besser lesbar. Kacheln im Energiefluss mit 2-px-Rahmen, Haus, Offgrid, Netz und Mitte jetzt farbig umrandet. Farbwerte gelten auch für das klassische Dashboard
- Nachtrag (Home-Assistant-App 4.0.0.2): Hintergrund mit **Jahreszeiten** – Sonnenhöhe und Landschaftsfarben über das Jahr, echte **Mondphase**, als festes Bild Schnee (Dezember bis Februar), Blüte (April/Mai), Getreidefeld (Spätsommer) und Herbstlaub; Südhalbkugel um ein halbes Jahr versetzt. „Bewegung“ zeigt nur ziehende Wolken, funkelnde Sterne und im Hochsommer nachts gelegentlich eine Sternschnuppe – keine fallenden Teilchen
- Nachtrag (Home-Assistant-App 4.0.0.3): Energiefluss-Kacheln mit leichtem **3D-Effekt** – Lichtkante oben, sanfter Verlauf von oben und kurzer, weicher Schatten; Kontraste bleiben WCAG-konform
- Nachtrag (Home-Assistant-App 4.0.0.4): Hintergrund mit **Trübung nach PV** – liefern alle Geräte zusammen deutlich weniger PV als der beste Wert der letzten 14 Tage in derselben Viertelstunde, wird die Sonne etwas blasser und der Wolkenschleier etwas dichter. Die Vergleichswerte merkt sich der Browser; bei vollem Akku (PV wird abgeregelt) und in den ersten Tagen bleibt der Himmel klar
- Nachtrag (Home-Assistant-App 4.0.0.5): **Geräte-Einstellungen neu** mit Reitern **Regelung · Offgrid · Laden** (nach dem Laden und nach jedem Entsperren immer „Regelung“, nicht übernommene Änderungen werden verworfen, nichts wird gespeichert), Einklappen entfällt. Reserve (`minSoc`) mit −/+ in 1-%-Schritten (gedrückt halten läuft schnell weiter); geschrieben wird erst mit „Übernehmen“ – ein KVS-Aufruf statt einem pro Klick; das eigene Reserve-Schloss am Touchgerät entfällt damit im neuen Design (im klassischen Dashboard bleibt es). Manuelles Laden mit festen Stufen aus `maxInputPower` (z. B. Aus · 200 · 400 · 600 · Max bei 800 W) statt Schieberegler. Reiter Offgrid (Aus · Ein · Öko) nur bei Geräten mit Offgrid-Ausgang, noch ohne Funktion
