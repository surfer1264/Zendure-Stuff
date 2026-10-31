# Changelog – Zendure Dashboard Proxy (Home-Assistant-App)

Ausführliche Historie inklusive Shelly-Script:
https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/zendash_watch_API_ZenSDK/CHANGELOG.md

## 3.5.12.5

- Verbindungsprobleme: Hinweis erst nach zwei gescheiterten Abfragen in Folge, mit Grund; Gerätekarten dann blass bzw. „veraltet“; keine überlappenden Abfragen mehr
- Proxy zählt Abfragefehler je Tag (Zeitüberschreitung, nicht erreichbar, Fehler vom Shelly): Anzeige im Fuß des Dashboards, Adresse `proxy_fehler`, jeder Fehler steht im Protokoll der App
- Neues Design: Offgrid mit Richtung – positiv = Abgabe ans Haus („Ausgang“), negativ = Einspeisung ins Gerät („Eingang“, wie PV). Der Energiefluss zeigt nur Beträge, die Animation läuft in Flussrichtung; vorher stand bei Einspeisung „nicht belegt“ und die Linie stand still

## 3.5.12.4

- Neues, alternatives Dashboard-Design unter der Adresse `neu` (in Home Assistant: „Web-UI öffnen“, dann im Menü „Ansicht“ → „Design“). Das klassische Dashboard bleibt unverändert die Startseite; beide Seiten verlinken sich gegenseitig im Menü „Ansicht“
- Gerätekarten im neuen Design: Status in Worten, Ladebalken mit schraffierter Reserve und Ladegrenze, PV · Akku · Offgrid, Hinweise nur bei Abweichung, Einstellungen nur bei freigegebener Bedienung, Technische Details als eigener Block
- Ansicht „Energiefluss“ als Alternative zu den Gerätekarten: PV, Akku, Haus, Netz und Offgrid mit animierten Flusslinien, für alle Geräte zusammen oder einzeln. Ansicht und Geräteauswahl merkt sich der Browser
- Link „Auswertung: Log-Bericht“ fehlte in der App, obwohl `/share/zendure/bericht.html` vorhanden war: Die Abfrage per HEAD kam durch Ingress nicht an. Jetzt fragt das Dashboard per GET unter `bericht_vorhanden` nach
- Neues Design: Hinweis „Laden aus dem Netz gesperrt“, wenn das Netzladen eines Geräts ausgeschaltet ist (fehlte bisher)

## 3.5.12.3

- Proxy: neue Seite `/bericht_zendure` zeigt den Bericht der Log-Auswertung (`bericht.html` aus `stat/auswertung/analyse.py`). In der App wird er unter `/share/zendure/bericht.html` gesucht; die App liest dafür den Ordner `share` (nur lesen)
- Dashboard: Link „Auswertung: Log-Bericht“ im Fuß der Seite, nur wenn ein Bericht vorhanden ist

## 3.5.12.2

- Dashboard: Schon beim Klick auf Start oder Ende des manuellen Ladens erscheint oben eine Leiste („… wird gestartet/beendet …“, „warte auf Bestätigung“), und die Bedienung ist gesperrt. Nach der Antwort zeigt die Leiste das Ergebnis und die Restzeit. 10 s lang ist die ganze Bedienung gesperrt, auch das Schloss. So ist klar, ob der Vorgang geklappt hat, und kein zweiter Klick trifft auf den Regler, während er die Änderung noch übernimmt. Danach lädt das Dashboard den echten Stand neu
- Dashboard: Bleibt die Bestätigung aus, erscheint nicht mehr sofort „konnte nicht beendet werden“. Stattdessen steht in der Leiste „keine Bestätigung erhalten – der Stand wird nach Ablauf geprüft“. Nach den 10 s vergleicht das Dashboard den echten Stand: Hat es geklappt, kommt die normale Erfolgsmeldung, sonst der Hinweis
- Proxy: `kvs_set_api` darf bis 25 s dauern (bisher 5 s wie alle Endpunkte). Das Shelly-Script schreibt beim Start und Ende des manuellen Ladens drei Keys nacheinander, mit Pausen und vorherigem Warten auf den eigenen Poll. Das dauerte oft länger als 5 s, der Proxy brach ab und das Dashboard meldete einen Fehler, obwohl alle Werte geschrieben waren

## 3.5.12.1

- Dashboard: Hilfetexte überarbeitet. Das Feld „Entlade-Hysterese“ heißt jetzt „Entlade-Sperre“, der Regler „Reserve (minSoc)“; Ladegrenze und Reserve tragen in den Hilfetexten den Konfigurationsschlüssel (`maxSoc`, `minSoc`)

## 3.5.12.0

- Dashboard: neues Eingabefeld „Entlade-Hysterese“ (`zdmc_dischargeResetMargin`) neben dem Sollwert, die 5 Kacheln der Übersicht stehen nebeneinander; braucht Shelly-Script 3.5.12 und Regel-Script 5.2.4. Eine Erhöhung der Reserve, mit der die Hysterese nicht mehr passt, wird mit einer Meldung abgelehnt
- Bisheriges Layout unter `/b` entfernt, die Adresse leitet auf das Dashboard weiter

## 3.5.11.2

- Dashboard: Die Links zu ThingSpeak und ThingsBoard öffnen die Einrichtungsseite im selben Fenster statt in einem neuen Tab. In der Home-Assistant-Companion-App (iPad/iPhone) kam sonst „401: Unauthorized“, weil der neue Tab die Anmeldung von Home Assistant nicht kennt

## 3.5.11.1

- Dashboard: Link „Dashboard-Shelly: IP / Script-ID ändern“ im Fuß der Seite. Damit ist die Einrichtungsseite auch über „Web-UI öffnen“ erreichbar, z. B. nach einem Wechsel des Shelly

## 3.5.11.0

- Weniger Last auf dem Shelly bei aktivem ThingSpeak-/ThingsBoard-Upload ohne offenes Dashboard: ein Poll-Durchlauf pro Minute statt drei bis vier
- Passt zum Shelly-Script zendash_watch 3.5.11 (mit älterem Script funktioniert alles wie bisher)

## 3.5.10.0

- Dashboard 3.5.10: Der Regler für die Reserve (minSoc) hält jetzt 5 Prozentpunkte Abstand zur Ladegrenze (vorher 1 Punkt)
- Passt zum Shelly-Script zendash_watch 3.5.10 und zum Regel-Script ab 5.2.1

## 3.5.9.6

- „Web-UI öffnen“ zeigt das Dashboard jetzt innerhalb von Home Assistant (Ingress) – funktioniert auch, wenn Home Assistant über `homeassistant.local` oder von unterwegs geöffnet ist
- Dashboard optional in der Seitenleiste („In Seitenleiste anzeigen“)
- Direkter Zugang über `http://<ha-ip>:8000/` bleibt unverändert

## 3.5.9.5

- Knopf „Web-UI öffnen“ auf der Seite der App und Link zum Projekt
- Beschreibung des Ports 8000 im Reiter Konfiguration (Deutsch und Englisch)
- Neu: Kurzbeschreibung im App Store und Bedienungsanleitung im Reiter Dokumentation

## 3.5.9.4

- ThingsBoard-Upload: neue Werte je Speicher `socLimit` (0 frei, 1 voll, 2 leer), `socSet` (obere Ladegrenze in %) und `minSoc` (untere Entladegrenze in %), standardmäßig aus
- Diese drei Werte werden nur bei Änderung gesendet, dazu einmal täglich und nach jedem Neustart oder Speichern der Einstellungen – spart Datenpunkte

## 3.5.9.3

- ThingsBoard-Seite zeigt die heute gesendeten Datenpunkte und Nachrichten (Zähler beginnt um Mitternacht und bei jedem Neustart neu)

## 3.5.9.2

- ThingsBoard-Upload: Werte je Speicher per Häkchen auswählbar (gilt für alle Speicher gemeinsam); ohne Auswahl bleiben die bisherigen sieben Werte
- Neue wählbare Werte `batteryPower` (+ = Akku entlädt, − = lädt) und `offGridPower`, standardmäßig aus
- Fehlerbehebung: Upload kurz aus- und wieder eingeschaltet → lief erst nach Neustart wieder

## 3.5.9.1

- Bisheriges Dashboard-Layout zusätzlich unter `/b`

## 3.5.9

- Neues Dashboard-Layout unter `/`
- Einrichtungs-, ThingSpeak- und ThingsBoard-Seite funktionieren auch hinter einem Pfad-Präfix (Ingress)
