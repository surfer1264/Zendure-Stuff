# ============================================================================
#  Zendure Logger - Konfiguration
# ============================================================================
#  Diese Datei enthaelt alle Einstellungen. Nur hier etwas aendern.
#  Das Hauptscript (zendure_logger.py) muss nicht angefasst werden und
#  kann bei einem Update einfach ersetzt werden - diese Datei bleibt erhalten.
# ============================================================================

# ----------------------------- Geraet ------------------------------------
DEVICE_URL = "http://192.168.x.x/properties/report"   # IP deiner Zendure
POLL_INTERVAL = 30          # Sekunden zwischen Abfragen

# ----------------------------- Dateien -----------------------------------
DB_FILE = "zendure_log.db"
CSV_FILE = "zendure_log.csv"
PACK_CSV_FILE = "zendure_packs.csv"

# Schreiben der CSV-Dateien (Geraete- und Pack-CSV). False -> nur Datenbank.
WRITE_CSV = True

# ----------------------------- Ausgabe & Speicherung ---------------------
# Konsolenausgabe: True unterdrueckt Routine-Meldungen. Fehler, DB-Migrations-
# und Startmeldungen erscheinen unabhaengig davon immer.
QUIET = False

# Gleitender Datenbestand in der DB: aeltere Rohdaten werden einmal am Tag
# geloescht (z. B. 1 / 3 / 7 / 20). 0 -> nie loeschen. Die Tagesenergie
# (Tabelle energy_daily) und die CSV-Dateien bleiben immer erhalten.
RETENTION_DAYS = 7

# ----------------------------- Smartmeter (Shelly Pro 3EM) ---------------
# Optional: Netzleistung direkt vom Shelly Pro 3EM (lokale RPC-API),
# gespeichert in der Spalte gridMeterPower.
USE_SMARTMETER = True
SMARTMETER_URL = "http://192.168.x.y/rpc/EM.GetStatus?id=0"  # IP des 3EM Pro

# ----------------------------- Weiterer Shelly ---------------------------
# Optional: Leistung eines weiteren Shelly-Geraets (z. B. Zaehler an einer
# PV-Einspeisung), gespeichert in der Spalte extraShellyPower.
USE_EXTRA_SHELLY = True
EXTRA_SHELLY_URL = "http://192.168.x.y/rpc/Switch.GetStatus?id=0"  # IP des Geraets
