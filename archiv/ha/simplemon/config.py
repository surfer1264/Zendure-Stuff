# ============================================================================
#  Zendure Logger - Konfiguration
# ============================================================================
#  Diese Datei enthaelt alle Einstellungen. Nur hier etwas aendern.
#  Das Hauptscript (zendure_logger.py) muss nicht angefasst werden und
#  kann bei einem Update einfach ersetzt werden - diese Datei bleibt erhalten.
# ============================================================================

# ----------------------------- Geraet ------------------------------------
DEVICE_URL = "http://192.168.178.150/properties/report"   # IP deiner Zendure
POLL_INTERVAL = 60          # Sekunden zwischen Abfragen

# Mehrere Speicher: Liste DEVICES statt DEVICE_URL. Ist DEVICES gesetzt, wird
# DEVICE_URL ignoriert. "name" erscheint in DB und CSV und muss eindeutig sein.
# DEVICES = [
#     {"name": "SF800 Pro", "url": "http://192.168.x.x/properties/report"},
#     {"name": "SF800",     "url": "http://192.168.x.y/properties/report"},
# ]

# ----------------------------- Dateien -----------------------------------
DB_FILE = "zendure_log.db"
CSV_FILE = "zendure_log.csv"
PACK_CSV_FILE = "zendure_packs.csv"
SITE_CSV_FILE = "zendure_site.csv"   # nur mit Smartmeter

# Hinweis: Eine Datenbank oder CSV-Datei im alten Aufbau (Fassung fuer nur
# ein Geraet) wird beim Start geloescht und neu angelegt.

# Schreiben der CSV-Dateien (Geraete- und Pack-CSV). False -> nur Datenbank.
WRITE_CSV = True

# ----------------------------- Ausgabe & Speicherung ---------------------
# Konsolenausgabe: True unterdrueckt Routine-Meldungen. Fehler, DB-Migrations-
# und Startmeldungen erscheinen unabhaengig davon immer.
QUIET = False

# Gleitender Datenbestand in der DB: aeltere Rohdaten werden einmal am Tag
# geloescht (z. B. 1 / 3 / 7 / 20). 0 -> nie loeschen. Die CSV-Dateien
# bleiben immer erhalten.
RETENTION_DAYS = 7

# ----------------------------- Smartmeter (Shelly Pro 3EM) ---------------
# Optional: Netzleistung direkt vom Shelly Pro 3EM (lokale RPC-API),
# gespeichert einmal je Abfrage in der Tabelle site (Spalte gridMeterPower).
USE_SMARTMETER = False
SMARTMETER_URL = "http://192.168.x.z/rpc/EM.GetStatus?id=0"  # IP des 3EM Pro
