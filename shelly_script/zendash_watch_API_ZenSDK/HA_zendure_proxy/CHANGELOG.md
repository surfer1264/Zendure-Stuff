# Changelog – Zendure Dashboard Proxy (Home-Assistant-App)

Ausführliche Historie inklusive Shelly-Script:
https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/zendash_watch_API_ZenSDK/CHANGELOG.md

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
