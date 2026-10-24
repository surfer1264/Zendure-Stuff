# Changelog – Zendure Dashboard Proxy (Home-Assistant-App)

Ausführliche Historie inklusive Shelly-Script:
https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/zendash_watch_API_ZenSDK/CHANGELOG.md

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
