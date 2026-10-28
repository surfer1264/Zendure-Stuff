# Zendure Multi-Configurator – Bedienung

Die App enthält den Multi-Configurator und den Upload-Helfer – denselben wie die
EXE für Windows und macOS. Der Browser spricht nur mit der App, die App schreibt
die Scripte per RPC auf die Shellys im Heimnetz.

## Benutzung

1. App starten, dann **„Web-UI öffnen“**.
2. Im Startdialog **„Neu konfigurieren“** oder **„Updaten“** wählen – weiter wie in der
   [Anleitung zum Configurator](https://surfer1264.github.io/Zendure-Stuff/Multiconfigurator/).
3. Nach getaner Arbeit kann die App gestoppt werden. Die Scripte laufen auf den
   Shellys weiter.

Alle Funktionen des Helfers stehen zur Verfügung: Direkt hochladen, Update,
Speicher prüfen, Log aufzeichnen.

## Was die App sich merkt

- Nach jedem erfolgreichen Upload die **IP-Adresse** des Controller- bzw.
  Dashboard-Shelly – in `/data/zendure_helper_config.json`. Das übersteht
  Neustarts und **Updates** der App.
- Das **Passwort** eines passwortgeschützten Shelly nur im Arbeitsspeicher, bis die
  App gestoppt wird.
- Keine Konfiguration – die steht im Script auf dem Shelly.

**Nicht deinstallieren**, um zu aktualisieren – das löscht `/data`, danach fehlen
nur die gemerkten IPs.

## Hinweis „neue Version verfügbar“

Gibt es eine neue Version, zeigt der Configurator das gleich beim Öffnen oben
auf der Seite an – mit dem Weg zum Update: **Einstellungen → Apps → Zendure
Multi-Configurator → Aktualisieren**. Fehlt der Knopf noch, im App-Store oben
rechts **⋮ → Nach Updates suchen**. Einen Download-Link gibt es in der App
nicht (ab 2.9.3.0; ältere Versionen zeigten den Link für die EXE).

## Zugriff und Sicherheit

- Über **„Web-UI öffnen“** läuft der Zugriff über Home Assistant (Ingress) – nur
  angemeldete HA-Benutzer können den Configurator öffnen.
- Der Port **8787** ist standardmäßig **aus**. Wer den Configurator ohne
  Home Assistant im Browser öffnen will (`http://<ha-ip>:8787/`), kann ihn im Reiter
  **Konfiguration → Netzwerk** freigeben. Dann gibt es **keinen Passwortschutz**:
  Jeder im Heimnetz kann Scripte auf die Shellys schreiben. Danach wieder
  abschalten und den Port **nie** ins Internet freigeben.

## Häufige Probleme

| Problem | Lösung |
|---|---|
| „Shelly nicht erreichbar“ | IP prüfen; Test im Browser: `http://<shelly-ip>/rpc/Shelly.GetDeviceInfo` |
| Shelly aus der App nicht erreichbar, obwohl die IP stimmt | Getrennte Netzsegmente: in der Netzwerk-Einstellung der App auf Host-Netzwerk umstellen |
| Direkt-Upload und Update werden nicht angeboten | Seite neu laden; App läuft? Protokoll der App prüfen |
| Nach einem Update fehlt eine neue Funktion | Update wurde nicht neu gebaut – im App Store über ⋮ „Nach Updates suchen“ und **Aktualisieren** |

## Links

- [Projekt auf GitHub](https://github.com/surfer1264/Zendure-Stuff)
- [Anleitung zum Configurator](https://surfer1264.github.io/Zendure-Stuff/Multiconfigurator/)
- [Installation dieser App (für Fortgeschrittene)](https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Multiconfigurator/HA_zendure_installer/INSTALLATION.md)
- [Fehler melden / Fragen](https://github.com/surfer1264/Zendure-Stuff/issues)
