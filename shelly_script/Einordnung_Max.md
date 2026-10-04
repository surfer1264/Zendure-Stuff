# Vergleich: ioBroker-Adapter (Nograx) – Z-HA – SMDC – EMS SolarFlow (basecubedev)

Stand der Recherche: 03.10.2026. Nograx-Adapter 6.0.0-alpha.4, Z-HA 1.4.4, EMS SolarFlow v0.8.12.

## Technik und Funktionen

| Aspekt | ioBroker-Adapter (Nograx) | Z-HA | SMDC | EMS SolarFlow |
|---|---|---|---|---|
| GitHub | [nograx/ioBroker.zendure-solarflow](https://github.com/nograx/ioBroker.zendure-solarflow) | [Zendure/Zendure-HA](https://github.com/Zendure/Zendure-HA) | [surfer1264/Zendure-Stuff](https://github.com/surfer1264/Zendure-Stuff) | [basecubedev/ems-solarflow-api-control](https://github.com/basecubedev/ems-solarflow-api-control) |
| Rolle | Schnittstelle, ab 6.0.0-alpha mit eingebautem Regler | Integration mit Regler | reiner Regler | eigenständiges EMS (Regler + Dashboard + Verwaltung) |
| Läuft auf | ioBroker-Server | HA-Server | Controller-Shelly (Gen2+) | eigener Host: Docker (NAS, Server, Pi) oder Pi-Appliance-Image; arm64/amd64 |
| Regelung eingebaut | ab 6.0.0-alpha ja (PI-Regler, optional), vorher nein | ja (Zendure Manager; Modi Manuell, Smart, Nur Entladen, Nur Laden, Solar speichern) | ja | ja, Regelschleife standardmäßig alle 5 s |
| Abhängigkeit im Regelpfad | ioBroker + eigenes Skript | HA | nur Shelly + Netz | nur EMS-Container/Host; HA, InfluxDB und Admin Console nicht nötig |
| Geräte | alle (zenSDK, Legacy via MQTT) | alle (zenSDK, Legacy via MQTT) | nur zenSDK-Geräte | zenSDK-Geräte (800 Pro 2 validiert, übrige „Family-supported“), Legacy per MQTT („Reverse-engineered“) |
| Verbindungsarten | zenSDK, lokales MQTT | zenSDK, lokales MQTT | zenSDK (HTTP) | Local API, lokales MQTT und Zendure-Cloud-MQTT, auch gemischt in einer Regelschleife |
| Smartmeter | beliebig (Skript) | jeder HA-Sensor | Pro 3EM lokal/remote oder HTTP-JSON (z. B. 3CT) | Shelly Pro (validiert), Shelly Gen1–3, Zendure 3CT/D0, EcoTracker, Tasmota, generisches MQTT, HA-Entität (Legacy) |
| Sollwert | ab 6.0.0-alpha einstellbar (setPoint), sonst frei im Skript | fest auf 0 | einstellbar, live per KVS | Ziel Netzsaldo 0, kein frei einstellbarer Offset dokumentiert |
| Stellgröße | frei | Laden und Entladen | Laden und Entladen | `outputLimit` (Ausgang); AC-Laden aus dem Netz per „AC-Rolle“ und Ladeleistung je Gerät |
| Mehrgeräte-Logik | ab 6.0.0-alpha SoC-gewichtet mit Lead-Device, sonst selbst bauen | relativer SoC, 85-%-Schwelle, proportional | Concentrate/Spread, Water-Fill, Sticky-Device mit SoC-Marge | PV-first mit Ladeausgleich, Batterie-Top-up gewichtet nach nutzbarer Energie (kWh × (SoC − minSoc)), Prioritäten, Umverteilung bei Limit |
| Stellschrauben | unbegrenzt | wenige | viele (Hysterese, Dämpfung, Start-/Stopp-Schwellen, Richtungs-Cooldown) | viele (Median/EMA-Filter, Totbänder, Rampen gesamt und je Gerät, Vorzeichenwechsel-Schnellreaktion, Mindestausgang) |
| Bypass / Einspeisesperre | selbst bauen | intern | gridReverse dynamisch mit Hysterese, Bypass-Überschusskorrektur | Off-Grid-Steckdosenmodus konfigurierbar; Bypass-Logik nicht gesondert dokumentiert |
| Saisonale / Akku-Strategie | im Skript | Automationen in HA | von außen über KVS | eingebaut: Wintermodus (minSoc-Reserve je Monat), Vollladeassistent, Nacht-/minSoc-Parken |
| Tarif / Prognose | im Skript | Automationen in HA | von außen über KVS | nicht eingebaut; Strompreis nur für Ersparnisrechnung; Steuerung von außen über HA-Helfer oder CLI |
| Ausfallverhalten | Regelzyklus nur bei neuem Zählerwert; ohne ioBroker keine Regelung | bei ungültigem P1-Wert kein Regelzyklus; seit 1.4.4 zenSDK-Geräte bei fehlgeschlagener Abfrage offline | Zyklus-Watchdog im Script, Timeouts bei Zähler- und Gerätelesen | dokumentiert: Halten bei Zählerausfall, Telemetrie-Altersprüfung, Fail-closed-Schreibsperren |
| Testbetrieb | – | – | – | Dry-Run ohne Schreibzugriff, getrennte Schreibfreigaben je Transportweg |
| Benachrichtigung | ioBroker | HA | eingebaut (Webhook, Signal, WhatsApp) | keine Push-Benachrichtigung dokumentiert |
| Lizenz | MIT (package.json nennt GPL-3.0-only) | MIT | MIT | AGPL v3 |

## Architektur-Einordnung

| Aspekt | ioBroker-Adapter (Nograx) | Z-HA | SMDC | EMS SolarFlow |
|---|---|---|---|---|
| Regelschicht (Sekundentakt) | ab 6.0.0-alpha eingebaut, sonst eigenes Regelskript | ja, Zendure Manager | ja, Hauptrolle | ja, Hauptrolle |
| Strategieschicht (Minuten/Stunden) | ja, per Skript/Blockly | ja, per HA-Automationen | nein, empfängt Vorgaben per KVS | teilweise eingebaut (Wintermodus, Vollladeassistent, AC-Rollen); Tarif/Prognose von außen |
| Monitoringschicht | ja, neben SMDC nur lesend | ja, neben SMDC (Manager aus, nur lesend) | nur Log und Meldungen | ja, eigenes Dashboard und Analytics |
| Verwaltungsschicht | ioBroker-Admin | HA/HACS | Configurator + Helfer | Admin Console (Erkennung, Updates, Backup); auf dem Pi zusätzlich Appliance Manager |
| Rolle im Kombi-Setup mit SMDC | Strategie + Monitoring, schreibt KVS | Strategie + Monitoring, schreibt KVS | Regler | Alternative zum SMDC, nicht kombinierbar als zweiter Regler |
| Tabu im Kombi-Setup | eigene Regelskripte parallel | Zendure Manager im Smart-Modus | HEMS in der App aktiv | parallel zu HEMS, HA-Automationen oder anderen Reglern auf `outputLimit` schreiben |

## Dashboard / Anzeige

| Aspekt | ioBroker-Adapter (Nograx) | Z-HA | SMDC | EMS SolarFlow |
|---|---|---|---|---|
| Eigenes Dashboard | nein | nein | ja, Web-Dashboard (`zendure-dashboard.html`) über Proxy | ja, eingebaut auf Port 8080 |
| Typische Anzeige | ioBroker VIS / vis-2, Admin-Objektbaum, Grafana | HA-Dashboards (Lovelace), eigene Karten | Dashboard im Browser: Netzsaldo, Ladestand, Leistung je Speicher | Ansichten Overview (Energiefluss), Devices, Control, Energy, History, Analytics, Diagnose, Logs, Maintenance |
| Besonderheit | – | – | Mini-Kurven der letzten 2 Minuten | „Control Explain“: Regelentscheidung Schritt für Schritt nachvollziehbar; Firmware-Status im Klartext |
| Datenweg | Adapter-Datenpunkte | HA-Entitäten | Browser → Proxy → Dashboard-Shelly (zenDash-API) → Controller-Shelly (KVS) | direkt vom EMS-Prozess |
| Zusatz-Hardware/-Software | keine (läuft in ioBroker) | keine (läuft in HA) | zweiter Shelly (zenDash-API + Watchdog) und Proxy auf PC/NAS/HA/Raspi | keine über den EMS-Host hinaus |
| Bedienung aus der Anzeige | über VIS-Widgets auf Steuer-Datenpunkte | über HA-Entitäten (Modus, Limits …) | Sollwert, Reserve, manuelles Laden u. a. (setzt `kvsEnabled: true` voraus) | EMS an/aus, Limits gesamt und je Gerät, Intervall, Priorität, Wintermodus, AC-Rolle; Schreibmodus nur mit Passwort |
| Zugriffsschutz | ioBroker | HA | – | Passwort, optional HTTPS; Internetfreigabe ausdrücklich nicht empfohlen |
| HA-Anbindung | – | – | über REST/KVS | optional: Statuswerte an HA, Helfer zum Ändern von Laufzeitwerten, Beispiel-Dashboard |
| Zendure-App parallel | im Cloud-Key-Modus nutzbar, im Offline-Modus nicht | im lokalen Betrieb ohne Funktion | nur bei Cloud-Verbindung; HEMS muss aus sein | nutzbar, HEMS muss aus sein |
| Warnungen | ioBroker-Skripte / Adapter | HA-Automationen | Watchdog meldet Akku voll, Übertemperatur, Unterspannung, Ausfälle | Diagnose- und Log-Ansicht; Push-Meldungen nicht dokumentiert |

## Statistik

| Aspekt | ioBroker-Adapter (Nograx) | Z-HA | SMDC | EMS SolarFlow |
|---|---|---|---|---|
| Energiewerte (kWh) | vom Adapter berechnet | aus Leistungswerten in HA, Energy Dashboard laut Z-HA-Wiki einzurichten | keine auf dem Shelly (Speicher zu knapp) | eingebaut: Tag, Woche, Monat, Jahr, gesamt; Ersparnis über konfigurierbaren Strompreis; Autarkiegrad |
| Kurzzeit-Verlauf | je nach History-Adapter | HA-Recorder | 2 Minuten im Dashboard | lokal in SQLite, ohne externe Datenbank |
| Langzeit-Speicherung | History-Adapter (InfluxDB, SQL, History) | HA-Recorder und Langzeitstatistik | extern: ThingSpeak und/oder ThingsBoard über den Proxy (`ts_bridge.py`) | optional mitgeliefertes InfluxDB |
| Takt der Aufzeichnung | frei wählbar | je nach Entität/Recorder | fester Minutentakt | Regeltakt (Standard 5 s) |
| Auswertung / Diagramme | Grafana, Flot, Echarts | HA Energy Dashboard, Statistik-Karten | ThingSpeak-Diagramme, ThingsBoard-Dashboards mit Stunden-/Tageswerten | Analytics-Ansicht: freie Zeiträume, Zoom, Gerätefilter, Überlagerung von SoC, Netzleistung und EMS-Ziel |
| Lokal ohne Cloud | ja | ja | nein, Langzeitverlauf nur über ThingSpeak/ThingsBoard (Cloud oder eigener ThingsBoard-Server) | ja |
| Regelgüte-Analyse | selbst bauen | selbst bauen | ThingsBoard-Kennzahlen (z. B. Regelgüte), Log-Mitschnitt per Script-Poller | Überlagerung Netzleistung vs. EMS-Ziel, Control-Ansicht, Qualitätschecks in der Diagnose |
| Datenlücken | je nach Adapter | je nach Recorder | – | Lücken werden als fehlende Messung behandelt, nicht hochgerechnet (seit v0.8.12) |
| Abhängigkeit vom Regler | keine | keine | keine, Upload läuft über Proxy; ohne aktiven Upload keine Anfragen an die zendash-API | Statistik läuft im selben Prozess; InfluxDB ist für die Regelung nicht nötig |
| Backup der Daten | ioBroker-Backup | HA-Backup | extern (ThingSpeak/ThingsBoard) | eingebaut: Konfiguration, SQLite und InfluxDB, Restore mit Vorschau und Rückfall-Backup |

## Installation / Einrichtung

| Aspekt | ioBroker-Adapter (Nograx) | Z-HA | SMDC | EMS SolarFlow |
|---|---|---|---|---|
| Bezugsquelle | ioBroker-Adapterliste (Admin) bzw. GitHub/npm | HACS in Home Assistant | GitHub-Release „Helfer“ (Windows oder Mac mit Apple Silicon) | GitHub: Installationsskript für Docker oder Pi-Image |
| Installationsweg | Adapter im Admin installieren, Instanz anlegen | Repository über HACS laden, Integration unter „Geräte & Dienste“ hinzufügen | Helfer starten, Configurator im Browser, „Direkt hochladen“ auf den Controller-Shelly | Skript lädt Admin Console als Container (Port 8090); alternativ Pi-Image flashen; für Profis Docker-Bootstrap oder natives Python |
| Geführte Konfiguration | Adapter-Einstellungsseite | Konfigurationsdialog der Integration | Configurator-Assistent (Speicher, Netzquelle, Benachrichtigungen, Regelparameter) | Guided Setup mit automatischer Erkennung von Geräten, MQTT-Brokern und Zählern; Konfigurationsvorschlag zur Prüfung |
| Zugangsdaten | Cloud Key aus der Zendure-App (oder rein lokal per MQTT) | Zendure-App-Token (oder lokales MQTT für Legacy-Geräte) | keine Cloud-Zugangsdaten, nur IP-Adressen der Speicher | je nach Verbindung: keine (Local API), Broker-Zugang oder Zendure-API-Key |
| Voraussetzungen | laufendes ioBroker | laufendes Home Assistant mit HACS | zwei Shellys Gen2+ (Controller und Dashboard), zenSDK-Speicher mit fester IP, Smartmeter | Docker mit Compose v2 (≥ 2.24) oder Raspberry Pi 3/3B+/4/5; 512 MB RAM ohne, 1 GB mit InfluxDB |
| Vorbereitung in der Zendure-App | Cloud Key erzeugen | Token erzeugen; für Regelung HEMS/Smart CT deaktivieren | Speicher aus dem HEMS entfernen | HEMS deaktivieren; ggf. API-Key für Cloud-MQTT |
| Offline-/Lokalbetrieb | Legacy: Cloud Disconnector / BT-Manager oder DNS-Umleitung; MQTT-Server ohne Auth auf Port 1883 | lokales MQTT (Legacy) bzw. lokaler Modus (zenSDK) | von Haus aus lokal per zenSDK | lokal per Local API oder eigenem Broker; Cloud-MQTT optional |
| Manuelle Alternative | – | – | minifiziertes Script per Hand laden und CONFIG-Block anpassen | `config.json` direkt bearbeiten, CLI `emsctl.py` |
| Dashboard-Einrichtung | Visualisierung separat (VIS, Grafana) | HA-Dashboards selbst anlegen | Proxy als Programm, Python-Script, Synology-Aufgabe oder HA-App; Einrichtungsseite im Browser | entfällt, Dashboard ist enthalten |
| Updates | über ioBroker-Admin | über HACS | über den Configurator (Update-Funktion); Dashboard-Seite und Script-Version müssen zusammenpassen | Guided Upgrade mit Vorabprüfung, Backup und Gesundheitscheck; Pi-Image aktualisiert per apt |
| Reifegrad | stabil, lange im Einsatz | offiziell unterstützt, aktive Entwicklung | aktive Entwicklung | junges Projekt (v0.8.x); validiert nur auf SF 800 Pro 2 + Shelly Pro; Pi-Image nur teilweise auf Hardware bestätigt |
| Einstiegshürde | mittel (Regelung muss selbst gebaut werden) | mittel bis hoch (komplexe Integration, knappe Doku) | niedrig bis mittel (geführt, aber zusätzliche Hardware) | mittel (geführt, aber eigener Docker-Host oder Pi nötig) |

## Dokumentation

| Aspekt | ioBroker-Adapter (Nograx) | Z-HA | SMDC | EMS SolarFlow |
|---|---|---|---|---|
| Haupt-Doku | README im GitHub-Repo (Features, Modi, Geräte, Offline-Betrieb) | README plus GitHub-Wiki | READMEs je Ordner im Repo plus umfangreiches GitHub-Wiki | README plus Doku-Ordner im Repo, gegliedert in User, Technical und Developer |
| Umfang | ein README (seit 6.0 mit Abschnitt zur Regelautomatik) | Wiki mit 9 Seiten, ca. 3.700 Wörter | 24 Markdown-Dateien im Repo, dazu zahlreiche Wiki-Seiten | ca. 110 Markdown-Dateien im Doku-Ordner |
| Wiki | angelegt, aber praktisch leer (nur Begrüßungsseite) | Installation, Function description, Fuse Group, Local MQTT, Power distribution strategy, SolarFlow 800, Hub1200 (DE), Troubleshooting | eigene SMDC-Seiten: Getting Started, Benutzerdokumentation, Gesamtdokumentation MultiController, Prinzipien erklärt, Development Inside, Regelalgorithmus | kein Wiki; alles im Repo |
| Aktualität | Changelog im README, ältere Einträge in CHANGELOG_OLD.md | Wiki zuletzt im März 2026 aktualisiert, Teile laut eigenem Hinweis veraltet | CHANGELOG je Komponente; Versionsabgleich Dashboard/Script dokumentiert | ausführliche Release Notes je Version; Doku wird mit Releases aktualisiert |
| Technische Referenz | wichtige Steuer-Datenpunkte im README (z. B. setDeviceAutomationInOutLimit) | Funktionsbeschreibung der Entitäten und Manager-Modi | API.md (zenDash-API), CONFIG-Parameter im Script kommentiert | Regellogik, Regelfluss, Konfigurationsreferenz, Sicherheitsmodell, Architektur |
| Anleitungen | Offline-Modus mit Cloud Disconnector / BT-Manager | Installation, Token, Fuse Group, lokales MQTT | Configurator-Anleitung, Dashboard-Einrichtung (Programm, Python, Synology, HA-App), ThingSpeak, ThingsBoard, Script-Poller | Schritt-für-Schritt mit Screenshots und Demo-Videos (Admin Console, Dashboard, Pi-Appliance), Erststart-Checkliste, Sicherheitsleitfaden, FAQ |
| Kompatibilitätsangaben | Geräteliste im README | Geräteseiten im Wiki | unterstützte Geräte im README | Matrix mit Status je Gerät (Validated, Family-supported, Reverse-engineered, User-reported) |
| Sprachen | Englisch (README), Support im Forum überwiegend Deutsch | Englisch, eine deutsche Geräteseite | Deutsch; Configurator-Anleitung auch Englisch und Französisch | Englisch; Release-Ankündigungen im Zendure-Forum zweisprachig DE/EN |
| Externe Doku / Tutorials | wenig | viele Drittquellen (Blogs, Tutorials DE/EN/NL, Zendure-Wiki, Zendure-Forum) | kaum, Doku liegt gebündelt im eigenen Repo/Wiki | kaum, Doku liegt gebündelt im Repo |
| Support-Kanal | sehr langer Thread im ioBroker-Forum, GitHub-Issues | GitHub-Issues und Discussions, Zendure-Forum | GitHub (Repo/Wiki), Zendure-Forum | GitHub-Issues (inkl. Vorlage für Kompatibilitätsberichte), Discussions, Zendure-Forum |
| Qualitätssicherung | – | – | – | über 13.600 automatisierte Tests, CodeQL, Dependabot |
| Einschätzung der Doku-Lage | knapp, Wissen steckt im Forum | in der Community als rudimentär beschrieben, durch Drittquellen ergänzt | ausführlich und strukturiert, auf Einsteiger und Entwickler ausgerichtet | sehr umfangreich und formal, eher technisch; Englisch als Hürde für deutschsprachige Einsteiger |
