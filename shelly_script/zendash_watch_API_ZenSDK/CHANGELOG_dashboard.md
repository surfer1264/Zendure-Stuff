# Changelog Dashboard und Proxy

Es gibt drei Changelogs:

- [Shelly-Script `zendash_watch` (mit API)](CHANGELOG.md)
- **Dashboard und Proxy** – diese Datei (Dashboard in beiden Designs, `zendure_proxy.py`, EXE und local_helper)
- [Home-Assistant-App Dashboard-Proxy](HA_zendure_proxy/CHANGELOG.md) – nur was die App selbst betrifft

Ab 5.0.0 zählen Dashboard und Proxy unabhängig vom Shelly-Script. Dashboard und Proxy tragen untereinander dieselbe Nummer. Welche Script-Version mindestens nötig ist, steht im jeweiligen Abschnitt. Bis 4.1.0 trugen alle drei dieselbe Nummer, Änderungen bis 3.5.12 stehen im [Changelog des Shelly-Scripts](CHANGELOG.md).

## Changelog 5.4.0

**Ziel:** Aufgeräumte Fußzeile im neuen Design und eigenes Zeichen im Kopf des Dashboards. Braucht das Shelly-Script ab 4.1.0.

- **Fußzeile:** Sichtbar bleiben Version, Update-Hinweis, Abfragefehler und der Link „Hilfe“.
- **„Mehr ▾“:** Klappt die Einrichtung auf (IP / Script-ID, ThingSpeak, ThingsBoard, Log-Bericht), dazu Verlauf und letzte Aktualisierung. Die Wahl wird nicht gespeichert.
- **API-Links:** `config_api`, `status_api` und `kvs_set_api` erscheinen nur noch bei eingeschalteten technischen Details.
- **Update-Hinweis:** in Fettschrift, damit er auffällt. Der Satz „Eigenständige Seite …“ entfällt.
- **Ligatur „ZS“ (beide Designs):** Links neben „ZENDURE // GRID“ steht jetzt das Zeichen „ZS“ für Zendure und Shelly, mit einem eigenen Bild für jeden Monat. Der Monat kommt aus dem Datum des Browsers und wechselt auch bei offener Seite.
- **Größe und Farben:** Das Zeichen reicht von der Oberkante von „ZENDURE“ bis zur Grundlinie der Unterzeile und passt sich an Ansichtsgröße, Sprache und Fensterbreite an. Tag- und Nachtansicht haben eigene Farben.
- Mit `?zmonth=1` bis `?zmonth=12` in der Adresse lässt sich jedes Monatsbild ansehen.
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
