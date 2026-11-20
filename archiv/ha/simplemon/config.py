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
DEVICES = [
    {"name": "SF2400Pro", "url": "http://192.168.178.150/properties/report"},
    {"name": "SF800",     "url": "http://192.168.178.143/properties/report"},
]

# ----------------------------- Dateien -----------------------------------
DB_FILE = "zendure_log.db"
CSV_FILE = "zendure_log.csv"
PACK_CSV_FILE = "zendure_packs.csv"
SITE_CSV_FILE = "zendure_site.csv"   # nur mit Smartmeter

# Hinweis: Hat eine Datenbank oder CSV-Datei einen alten Aufbau, fragt das
# Programm beim Start, ob sie geloescht und neu angelegt werden soll.

# Was geschrieben wird. Mindestens eins muss True sein.
WRITE_DB = True     # SQLite-Datenbank (DB_FILE). False -> keine DB, kein Aufraeumen.
WRITE_CSV = True    # CSV-Dateien (Geraete-, Pack- und Smartmeter-CSV).

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
USE_SMARTMETER = True
SMARTMETER_URL = "http://192.168.178.117/rpc/EM.GetStatus?id=0"  # IP des 3EM Pro
