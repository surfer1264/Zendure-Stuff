# Changelog Multi-Configurator und lokaler Helfer

## 2.9.4

- Configurator: Das Regel-Intervall (`interval`) steht im Ergebnis-Schritt immer als eigener Bereich, nicht nur bei Abweichung. Er zeigt den eingestellten Wert und die Empfehlung (3000 ms + 500 ms je Gerät); ändern geht jederzeit (Empfehlung übernehmen oder eigener Wert ab 3000 ms). Weicht ein übernommener Wert ab, steht wie bisher der Hinweis mit „Beibehalten“ dabei
- Configurator: Link „Spendier mir einen Kaffee“ ☕ (Ko-fi) im Startdialog

## 2.9.3

- Configurator: Prüft beim Öffnen still, ob es eine neue Version des Configurators/Helfers gibt, und zeigt das oben auf der Seite an. Bisher stand der Hinweis nur nach „Updates prüfen“. Ohne Internet oder ohne Antwort von GitHub bleibt er weg
- Configurator in der Home-Assistant-App: Statt des Download-Links (für die EXE) steht der Weg zum Update in Home Assistant (Einstellungen → Apps → Aktualisieren)
- Configurator: Neue Auswahl **„Downloads“** im Startdialog (auch ohne Helfer). Direkte Links auf das neueste Release für den Dashboard-Proxy (Windows, macOS) und den Helfer (Windows 64/32 Bit, macOS); das eigene Betriebssystem ist hervorgehoben. Dazu je die aktuelle Version aus dem Manifest, das App-Repository für Home Assistant, die Anleitungen und die Release-Seite mit den Prüfsummen
- Configurator: Dashboard-Proxy beim Script „zenDash-API + Watchdog“. Dashboard und Script tragen dieselbe Version, ein neues Script braucht deshalb auch einen neuen Proxy
  - Update-Tabelle: Bei „Update verfügbar“ steht der Hinweis mit den Download-Links bzw. dem Weg in Home Assistant
  - Nach erfolgreichem Direkt-Upload erscheint eine Box „Jetzt noch den Dashboard-Proxy aktualisieren“ (nur mit zenDash-API)
  - Ergebnis-Schritt: Zeile „Passender Dashboard-Proxy“ mit denselben Links, auch für das Hochladen von Hand
- Helfer: Neue Umgebungsvariable `ZENDURE_HELPER_HA_APP`. Gesetzt kennzeichnet der Helfer die ausgelieferte Seite als Home-Assistant-App; die App setzt sie in `run.sh`. Die EXE ist unverändert

## 2.9.2

- Configurator: Regel-Intervall (`interval`) richtet sich nach der Geräteanzahl – empfohlen 3000 ms + 500 ms je Gerät (1 Gerät 3500 ms, 2 Geräte 4000 ms, 3 Geräte 4500 ms). Bei einer neuen Einrichtung wird die Empfehlung gesetzt
- Configurator: Weicht beim Update oder Einlesen der übernommene Wert davon ab, zeigt die Ergebnisseite einen Hinweis: Empfehlung übernehmen, bisherigen Wert beibehalten oder eigenen Wert ab 3000 ms eintragen. Ohne Auswahl bleibt der bisherige Wert
- Configurator: Zusammenfassung zeigt das Regel-Intervall (mit Empfehlung, falls abweichend)
- Nachtrag Helfer (EXE und Home-Assistant-App 2.9.2.1): Upload robuster, gleiches Verfahren wie `upload_shelly.py`. Schlägt ein Block fehl, beginnt die ganze Übertragung neu (höchstens dreimal, 2 s Pause). Bisher wurde nur der fehlgeschlagene Block wiederholt: Brach die Verbindung erst nach dem Speichern ab, stand er doppelt im Code. Ein Verbindungsabbruch (`ConnectionResetError`) wurde außerdem gar nicht wiederholt und kam als unerwarteter Fehler im Browser an. Jetzt meldet der Configurator in diesem Fall „Upload unvollständig“, weil der alte Code dann schon überschrieben sein kann. Ein fehlendes Passwort wird nicht wiederholt
- Nachtrag Configurator und Helfer: **Fortschrittsanzeige beim Direkt-Upload.** Unter dem Knopf „Direkt hochladen“ zeigen ein Balken und ein Text die aktuelle Phase: vorhandene Scripte prüfen, Script stoppen bzw. entfernen bzw. anlegen, „Übertrage Block 23 von 46 …“, Script starten. Wird die Übertragung nach einem Verbindungsabbruch neu begonnen, springt der Balken zurück, und der Text nennt den Versuch („… neu gestartet (Versuch 2 von 3) …“)
  - Neuer Endpunkt `GET /api/upload_status?id=…` im Helfer, Feature `upload_progress` in `/api/health`. Der Browser schickt beim Upload eine eigene Kennung (`progress_id`) mit und fragt damit alle 400 ms den Stand ab
  - Mit einem älteren Helfer ohne dieses Feature erscheint wie bisher nur „Übertrage an … “

## 2.9.1

- Configurator: Aussehen wie das Dashboard – gleiche Farben, Schrift (IBM Plex, eingebettet) und Kopfzeile „ZENDURE // SHELLY MULTI DEVICE SUITE“
- Configurator: Tag-/Nachtsicht im neuen Menü „Ansicht“. Ohne eigene Wahl folgt die Seite dem System, eine eigene Wahl wird gemerkt
- Configurator: Sprache ebenfalls im Menü „Ansicht“ (DE → EN → FR) statt der drei Knöpfe

## 2.9.0

- **Neu: Home-Assistant-App** „Zendure Multi-Configurator“ (Ordner `HA_zendure_installer`): Configurator und Helfer laufen in Home Assistant, Aufruf über „Web-UI öffnen“. Anleitung: [HA_zendure_installer/INSTALLATION.md](HA_zendure_installer/INSTALLATION.md)
- Helfer: Adresse, Port, Ablageort der gemerkten IPs und das Öffnen des Browsers lassen sich über Umgebungsvariablen einstellen (`ZENDURE_HELPER_BIND`, `_PORT`, `_DATA_DIR`, `_NO_BROWSER`, `_TRUSTED_PEERS`). Ohne diese Variablen verhält sich die EXE wie bisher
- Helfer: Lauscht er im Netz, sind auch Anfragen von der eigenen Seite zugelassen (gleicher Origin, nur mit IP-Adresse)
- Configurator: Liefert der Helfer die Seite selbst aus, spricht der Configurator ihn relativ an statt über `http://127.0.0.1:8787` – nötig hinter dem Ingress von Home Assistant. Web-Configurator (githack) unverändert

## 2.8.1

- Hilfe-Links zeigen auf die neue Doku-Seite (GitHub Pages) statt auf GitHub bzw. das Wiki: Überblick über die Suite, kompatible Geräte (neue Seite), Anleitung zum Configurator, Script-Anleitungen
- Neue Fußzeile mit „Hilfe“, „Überblick über die Suite“ und Versionsnummer

## 2.8.0

- Netzquelle http_json: eigenes Feld „IP-Adresse des Smartmeters“ – die IP wird in die URL bzw. die gewählte Vorlage übernommen, kein Ersetzen von `<IP>` in der URL mehr nötig
- IP-Feld und URL-Feld bleiben synchron (Host in der URL von Hand geändert → IP-Feld zieht nach); beim Einlesen einer Config wird die IP aus der URL gelesen, die Config selbst bleibt unverändert

## 2.7.0

- Netzquelle http_json: neue Vorlagen „Zendure Smart Meter D0“ (`/properties/report`, Feld `total_power`) und „everHome EcoTracker“ (`/v1/json`, Feld `power`)
- Vorlagen mit Einrichtungshinweis: D0 – lokale Schnittstelle einmalig über HEMS in der Zendure-App freischalten; EcoTracker – „Lokaler HTTP-Server“ in der everHome-App einschalten; jeweils feste IP und Vorzeichen per „Testen“ prüfen
- Die gewählte Vorlage bleibt im Auswahlfeld sichtbar

## 2.6.0

- Nicht vom Configurator verwaltete Einträge (z. B. dischargeResetMargin) werden beim Einlesen und Updaten unverändert übernommen.
- Ungültige Werte in eingelesenen Configs werden durch den Standard ersetzt und angezeigt.

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
