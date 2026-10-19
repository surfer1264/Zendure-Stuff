# Zendure Dashboard Proxy

Live-Dashboard für Zendure-Speicher (SolarFlow, Hyper), die über ein Shelly-Script
gesteuert werden – direkt aus Home Assistant heraus.

- **Dashboard** für alle Speicher: Ladestand, Leistungen, Netzsaldo, Regelung, Sperren
- **Löst das CORS-Problem** der Shelly-Firmware: Der Browser spricht nur mit dieser App,
  die App holt die Daten vom Shelly
- **Optional:** Messwerte jede Minute an **ThingSpeak** und/oder **ThingsBoard** senden
- Einstellungen (Shelly-IP, Zugangsdaten) überstehen Updates der App

Nach der Installation **„Web-UI öffnen“** wählen – beim ersten Start erscheint die
Einrichtungsseite für Shelly-IP und Script-ID.

Voraussetzung: das zenDash-API-Script (Watchdog) läuft auf einem Shelly im Heimnetz.

[Projekt auf GitHub](https://github.com/surfer1264/Zendure-Stuff) ·
[Dokumentation](https://surfer1264.github.io/Zendure-Stuff/)
