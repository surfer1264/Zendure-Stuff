# Changelog Dashboard und Proxy

Es gibt drei Changelogs:

- [Shelly-Script `zendash_watch` (mit API)](CHANGELOG.md)
- **Dashboard und Proxy** – diese Datei (Dashboard in beiden Designs, `zendure_proxy.py`, EXE und local_helper)
- [Home-Assistant-App Dashboard-Proxy](HA_zendure_proxy/CHANGELOG.md) – nur was die App selbst betrifft

Script, Dashboard und Proxy tragen dieselbe Versionsnummer. Änderungen bis 3.5.12 stehen im [Changelog des Shelly-Scripts](CHANGELOG.md).

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
