# Changelog Multi-Configurator und lokaler Helfer

## 2.0.3
- Bestehende Config einlesen: neuer Button „📂 Datei laden…“ – lädt eine gespeicherte Datei (nur CONFIG-Block oder komplettes Script) ins Textfeld, übernommen wird wie bisher mit „Einlesen & übernehmen“
- Komplettes Script speichern: Dateiname enthält jetzt die Script-Version (z. B. `zerooutput_multi_kvs_mini_v5.0.8.js`)
- Link zur Anleitung (README) auf der Startseite

## 2.0.2
- Neuer Einführungstext auf der Startseite (DE/EN/FR)
- Link zur Liste kompatibler Shelly-Geräte (Wiki, Kapitel Voraussetzungen)
- Netzquelle http_json: Button „Testen“ öffnet die Smartmeter-URL in einem neuen Tab

## 2.0.1
- Update: Config mit Umlauten und Sonderzeichen wird jetzt korrekt vom Shelly gelesen
- Update: zusätzliche Scripte auf dem Shelly verhindern das Update nicht mehr
- Liegen weitere Scripte auf dem Shelly, entscheidest du vor dem Hochladen, ob sie gelöscht oder behalten werden

## 2.0
- Startdialog: Neu konfigurieren oder Updaten
- Update: installierte Versionen mit GitHub vergleichen und mit bisherigen Einstellungen aktualisieren
- Helfer merkt sich die Shelly-IPs und prüft vor dem Upload, ob nur ein Script auf dem Shelly liegt
