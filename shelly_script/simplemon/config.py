# ============================================================================
#  Zendure Logger - Konfiguration (VORLAGE)
# ============================================================================
#  Diese Datei ist die Vorlage im Repo und enthaelt nur Platzhalter.
#  Eigene Werte NICHT hier eintragen, sondern:
#    1. diese Datei als config_local.py in denselben Ordner kopieren
#    2. dort die eigenen Adressen und Einstellungen eintragen
#  Gibt es config_local.py, liest das Programm nur diese. config_local.py
#  steht in .gitignore und landet so nie im Repo.
# ============================================================================

# ----------------------------- Geraete -----------------------------------
# Liste der Speicher. "name" erscheint in DB und CSV und muss eindeutig sein.
DEVICES = [
    {"name": "SF800 Pro", "url": "http://192.168.x.x/properties/report"},
    {"name": "SF800",     "url": "http://192.168.x.y/properties/report"},
]
# Aeltere Schreibweise fuer nur einen Speicher (wird ignoriert, wenn DEVICES
# gesetzt ist):
# DEVICE_URL = "http://192.168.x.x/properties/report"

POLL_INTERVAL = 30          # Sekunden zwischen Abfragen

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
# Konsolenausgabe: True unterdrueckt Routine-Meldungen. Fehler und
# Startmeldungen erscheinen unabhaengig davon immer.
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
