# Changelog Multi-Configurator und lokaler Helfer

## 2.3.0
- Passwortgeschützte Shellys: Der Configurator fragt nach dem Passwort, der Helfer meldet sich per Digest-Authentifizierung an (Upload, Update, Speicher prüfen, Log aufzeichnen); das Passwort bleibt nur im Arbeitsspeicher des Helfers
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
