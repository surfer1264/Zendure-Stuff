# Changelog Multi-Configurator und lokaler Helfer

## 2.6.0
Nicht vom Configurator verwaltete Einträge (z. B. dischargeResetMargin) werden beim Einlesen und Updaten unverändert übernommen. Ungültige Werte in eingelesenen Configs werden durch den Standard ersetzt und angezeigt. Der 

## 2.5.0
- Verbesserte Benutzerführung

## 2.4.0
- Netzquelle http_json: verschachtelte Felder (z. B. Tasmota) mit Punkten eingeben (`StatusSNS.DVS7420.power`), geschrieben wird ein Array für Controller und zenDash-API
- Fix: eingelesene Configs mit Feldpfad als Array gingen beim Einlesen/Update verloren (wurden zu einem ungültigen Text)
- Vorlagen für Zendure Smart Meter 3CT, Shelly 3EM (ohne Pro) und Tasmota; Platzhalter <IP>/<Gerät> müssen vor „Weiter“ ersetzt werden
- Aufklappbare Hilfe „So findest du den Feldnamen“ mit Beispielen
- Startdialog: „Neu konfigurieren“ heißt jetzt „Neu konfigurieren oder manuell updaten“ (Beschreibung nennt Einlesen per Einfügen, Datei oder vom Shelly)
- Link „Kompatible Shelly-Geräte“ auf die neue Wiki-Adresse angepasst
- Build-Datum unter der Überschrift entfernt – maßgeblich ist die Versionsnummer

## 2.3.0
- Passwortgeschützte Shellys: Der Configurator fragt nach dem Passwort, der Helfer meldet sich per Digest-Authentifizierung an (Upload, Update, Speicher prüfen, Log aufzeichnen); das Passwort bleibt nur im Arbeitsspeicher des Helfers
- Bestehende Config einlesen: zusätzlich direkt vom Shelly (Controller- bzw. Dashboard-Shelly, nur mit Helfer) – landet wie beim Datei-Laden zuerst im Textfeld
- Geräte: Button „Testen“ neben jeder Speicher-IP öffnet den Report (/properties/report) in einem neuen Tab
- Speicher prüfen: Läuft schon ein Script, wird der Gesamtspeicher (frei + belegt) berechnet und bewertet (✓ ab 25.000 Bytes); belegter Speicher und Spitze je Script werden angezeigt
- Update: abgebrochene Passwortabfrage wird in der Tabelle als „passwortgeschützt“ angezeigt statt „nicht erreichbar“

## 2.2.0
- Neuer Schritt „Watchdog-Schwellen“: Akku voll, Zellspannung und Temperatur mit Reset-Werten, vorbelegt aus der eingelesenen Config bzw. mit Standardwerten, inkl. Plausibilitätsprüfung
- Ergebnis: Debug-Ausgaben je Script per Häkchen ein-/ausschalten (auch über Update)
- Controller: errorThreshold-Standard auf 10
- Update: „Jetzt updaten“ zeigt den Fortschritt – Button mit Ladeanzeige, Hinweis daneben und Schrittliste (Einstellungen je Shelly lesen, übernehmen)

## 2.1.0
- Neu im Startdialog: „Log aufzeichnen“ (nur mit Helfer) – stoppt ein Script, startet es neu und zeichnet 140 oder 600 Sekunden lang seine Meldungen auf; das Log wird als Datei gespeichert
- Standard ist gefiltert (nur Ausgaben des gewählten Scripts), optional ungefiltert inkl. Systemmeldungen zum Script-Start
- Sensible Daten im Log werden maskiert (Webhook-IDs, Tokens, API-Keys, Passwörter, Telefonnummern; Seriennummern bis auf die letzten 4 Zeichen)
- Helfer: neuer Endpunkt /api/logcapture (läuft als Hintergrund-Job, der Configurator fragt den Stand ab), weiterhin ohne Zusatzmodule (eigener WebSocket-Client); das Debug-Log des Shelly wird bei Bedarf nur für die Aufzeichnung eingeschaltet

## 2.0.3
- Bestehende Config einlesen: neuer Button „📂 Datei laden…“ – lädt eine gespeicherte Datei (nur CONFIG-Block oder komplettes Script) ins Textfeld, übernommen wird wie bisher mit „Einlesen & übernehmen“
- Komplettes Script speichern: Dateiname enthält jetzt die Script-Version (z. B. `zerooutput_multi_kvs_mini_v5.0.8.js`)
- Link zur Anleitung (README) auf der Startseite, je nach Sprache auf die deutsche, englische oder französische Fassung
- Anleitung zusätzlich auf Englisch und Französisch (übersetzt mit Claude), Inhaltsverzeichnis mit allen Unterkapiteln

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
