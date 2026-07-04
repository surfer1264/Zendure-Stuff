# ============================================================================
#  Zendure Dashboard - Konfiguration
# ============================================================================
#  Diese Datei enthaelt alle Einstellungen. Nur hier etwas aendern.
#  Das Hauptscript (zendure_dashboard.py) muss nicht angefasst werden und
#  kann bei einem Update einfach ersetzt werden - diese Datei bleibt erhalten.
# ============================================================================

# ----------------------------- Geraet & Server ---------------------------
DEVICE_URL = "http://192.168.178.143/properties/report"   # IP deiner Zendure
POLL_INTERVAL = 30          # Sekunden zwischen Abfragen
WEB_PORT = 8085             # Port des Dashboards (http://<NAS-IP>:PORT)
DEVICE_LABEL = "Hub"     # kurzer Name des Geraets im Energiefluss-Diagramm

# ----------------------------- Dateien -----------------------------------
CSV_FILE = "zendure_log.csv"
PACK_CSV_FILE = "zendure_packs.csv"
DB_FILE = "zendure_log.db"

# Schreiben der CSV-Dateien (Geraete- und Pack-CSV). False -> keine CSV.
WRITE_CSV = True

# ----------------------------- Ausgabe & Speicherung ---------------------
# Konsolenausgabe: True unterdrueckt Routine-Meldungen. Fehler, DB-Migrations-
# und Startmeldungen erscheinen unabhaengig davon immer.
QUIET = False

# Speicherung: gleitender Datenbestand in der DB (CSV bleibt unbegrenzt als Archiv).
RETENTION_DAYS = 7          # aeltere DB-Zeilen werden geloescht (z. B. 1 / 3 / 7 / 20)

# Anzeige: max. Anzahl Datenpunkte im Chart (Umschalter im Dashboard).
MAX_POINTS = 600            # Obergrenze; der Umschalter bietet 200 / 400 / 600

# ----------------------------- Benachrichtigungen ------------------------
# Signal-Versand ueber CallMeBot. Master-Schalter: auf False -> keine Nachrichten.
USE_SIGNAL = False
SIGNAL_PHONE = "+49170XXXXXXX"   # deine Signal-Nummer im Format +49...
SIGNAL_KEY = "DEIN_API_KEY"      # dein CallMeBot API-Key

# Schwellwerte mit Hysterese (Warnung einmalig, Reset erst im sicheren Bereich)
VOLL_SCHWELLE = 99     # %  - ab hier gilt der Akku als "voll"
ENTLADE_RESET = 90     # %  - darunter ist eine erneute Vollmeldung wieder erlaubt
MIN_VOLT_WARN = 2.9    # V  - Unterspannungsgrenze je Zelle
MIN_VOLT_RESET = 3.1   # V  - Erholungsgrenze
TEMP_WARN = 45.0       # °C - Geraete-Temperaturgrenze
TEMP_RESET = 35.0      # °C - Ruecksetz-Grenze