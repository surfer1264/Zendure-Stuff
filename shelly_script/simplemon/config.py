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
# Beispiel: zwei Solarflows mit zusammen drei Akkupacks
#   SF800 Pro  mit 2 Akkupacks
#   SF800      mit 1 Akkupack
# Die Akkupacks muessen hier nicht eingetragen werden - simplemon liest sie aus
# dem Report des jeweiligen Solarflows. Nur fuer ThingsBoard braucht jeder Akku
# ein Token (unten, TB_PACK_TOKENS).
DEVICES = [
    {"name": "SF800 Pro", "url": "http://192.168.x.x/properties/report"},
    {"name": "SF800",     "url": "http://192.168.x.y/properties/report"},
]
# Aeltere Schreibweise fuer nur einen Speicher (wird ignoriert, wenn DEVICES
# gesetzt ist):
# DEVICE_URL = "http://192.168.x.x/properties/report"

POLL_INTERVAL = 60          # Sekunden zwischen Abfragen (60 = jede Minute, wie ts_bridge)
# Abfrage am Raster ausrichten: jeweils POLL_LEAD Sekunden vor einem Vielfachen
# von POLL_INTERVAL, bei 60 also um hh:mm:50. Der ThingsBoard-Versand zur vollen
# Minute hat dann einen frischen Stand (ca. 10 s alt, wie im Dashboard-Proxy).
# POLL_LEAD hoechstens das halbe Intervall. POLL_ALIGN = False: Abfrage ab Start
# im festen Abstand, ohne Raster.
POLL_ALIGN = True
POLL_LEAD = 10

# ----------------------------- Dateien -----------------------------------
DB_FILE = "zendure_log.db"
CSV_FILE = "zendure_log.csv"
PACK_CSV_FILE = "zendure_packs.csv"
SITE_CSV_FILE = "zendure_site.csv"   # nur mit Smartmeter

# Hinweis: Hat eine Datenbank oder CSV-Datei einen alten Aufbau, wird sie beim
# Start umbenannt (z. B. zendure_log_alt_20261121-153000.db) und neu angelegt.

# Was geschrieben wird. Mindestens eins muss True sein.
WRITE_DB = True     # SQLite-Datenbank (DB_FILE). False -> keine DB, kein Aufraeumen.
WRITE_CSV = True    # CSV-Dateien (Geraete-, Pack- und Smartmeter-CSV).
WRITE_TB = False   # Versand an ThingsBoard (Einstellungen ganz unten).

# ----------------------------- Ausgabe & Speicherung ---------------------
# Konsolenausgabe: True unterdrueckt Routine-Meldungen. Fehler und
# Startmeldungen erscheinen unabhaengig davon immer.
QUIET = False

# Gleitender Datenbestand in der DB: aeltere Rohdaten werden einmal am Tag
# geloescht (z. B. 1 / 3 / 7 / 20). 0 -> nie loeschen. Die CSV-Dateien
# bleiben immer erhalten.
RETENTION_DAYS = 31

# ----------------------------- Smartmeter --------------------------------
# Optional: Netzleistung (W, positiv = Bezug) einmal je Abfrage, gespeichert in
# der Tabelle site (Spalte gridMeterPower), an ThingsBoard als Geraet "Netz".
# Typen wie im Multi-Configurator:
#
#   SMARTMETER_TYPE  Geraet                         noetig
#   "pro3em"         Shelly Pro 3EM                 SMARTMETER_IP, SMARTMETER_EM_ID
#   "zendure3ct"     Zendure Smart Meter 3CT        SMARTMETER_IP
#   "zendured0"      Zendure Smart Meter D0         SMARTMETER_IP
#   "ecotracker"     everHome EcoTracker            SMARTMETER_IP
#   "shelly3em"      Shelly 3EM (Gen1, nicht Pro)   SMARTMETER_IP
#   "tasmota"        Tasmota-Lesekopf               SMARTMETER_IP, SMARTMETER_FIELD
#   "http_json"      beliebiges Geraet mit JSON     SMARTMETER_URL, SMARTMETER_FIELD
#
# SMARTMETER_FIELD: Feld mit der gesamten Netzleistung in W. Bei den Vorlagen
# schon gesetzt (leer lassen), bei "tasmota" und "http_json" selbst eintragen.
# Verschachtelte Antwort mit Punkten verbinden, z. B. bei Tasmota
# "StatusSNS.<Geraet>.power" - den mittleren Namen aus der Antwort von
# http://<IP>/cm?cmnd=STATUS%2010 einsetzen.
# SMARTMETER_INVERT = True, wenn der Wert bei Netzbezug negativ ist.
USE_SMARTMETER = False
SMARTMETER_TYPE = "pro3em"
SMARTMETER_IP = "192.168.x.z"      # Adresse des Smartmeters
SMARTMETER_EM_ID = 0               # nur pro3em: Nummer des EM-Kanals, meist 0
SMARTMETER_URL = ""                # nur http_json: vollstaendige Adresse, z. B. "http://192.168.x.z/status"
SMARTMETER_FIELD = ""              # nur tasmota/http_json, sonst leer lassen
SMARTMETER_INVERT = False

# Beispiele (Adressen sind Platzhalter) - passenden Block nach oben uebernehmen:
#
# Shelly Pro 3EM          -> http://192.168.x.z/rpc/EM.GetStatus?id=0, Feld total_act_power
#   SMARTMETER_TYPE = "pro3em"
#   SMARTMETER_IP = "192.168.x.z"
#   SMARTMETER_EM_ID = 0
#
# Zendure Smart Meter 3CT -> http://192.168.x.z/properties/report, Feld total_power
#   SMARTMETER_TYPE = "zendure3ct"          (D0: "zendured0", gleiche Adresse)
#   SMARTMETER_IP = "192.168.x.z"
#
# everHome EcoTracker     -> http://192.168.x.z/v1/json, Feld power
#   SMARTMETER_TYPE = "ecotracker"
#   SMARTMETER_IP = "192.168.x.z"
#
# Shelly 3EM (Gen1)       -> http://192.168.x.z/status, Feld total_power
#   SMARTMETER_TYPE = "shelly3em"
#   SMARTMETER_IP = "192.168.x.z"
#
# Tasmota-Lesekopf        -> http://192.168.x.z/cm?cmnd=STATUS%2010
#   SMARTMETER_TYPE = "tasmota"
#   SMARTMETER_IP = "192.168.x.z"
#   SMARTMETER_FIELD = "StatusSNS.DVS7420.power"   # mittleren Namen aus der Antwort
#
# Beliebiges JSON         -> genau SMARTMETER_URL
#   SMARTMETER_TYPE = "http_json"
#   SMARTMETER_URL = "http://192.168.x.z/api/werte"
#   SMARTMETER_FIELD = "daten.netz"
#   SMARTMETER_INVERT = True                       # wenn Bezug negativ geliefert wird

# ----------------------------- ThingsBoard -------------------------------
# Nur mit WRITE_TB = True. Jeder Solarflow und jeder Akkupack ist in
# ThingsBoard ein eigenes Geraet mit eigenem Access Token:
#   - Geraete in ThingsBoard selbst anlegen (Akku: Seriennummer als Name),
#   - je Geraet unter "Zugangsdaten" das Access Token kopieren und unten
#     eintragen. Geraete ohne Token werden nicht gesendet (Meldung beim Start).
# Tokens sind Zugangsdaten: nur in config_local.py, nie ins Repo.
TB_HOST = "https://eu.thingsboard.cloud"   # eigener Server: z. B. "http://192.168.x.x:8080"
TB_INTERVAL = 60    # Sekunden zwischen zwei Sendungen (60 = jede volle Minute), ab 10

# Platzhalter in <...> durch die echten Werte ersetzen. Solange noch ein
# Platzhalter drinsteht, bricht der Start mit WRITE_TB = True mit Meldung ab.
# Ein Geraet, das nicht gesendet werden soll: Zeile loeschen.

# Solarflow: Name wie in DEVICES -> Token (2 Geraete)
TB_HUB_TOKENS = {
    "SF800 Pro": "<TOKEN-SF800-PRO>",
    "SF800":     "<TOKEN-SF800>",
}
# Akkupack: Seriennummer -> Token (3 Geraete). Die Seriennummern stehen in der
# DB bzw. CSV (Spalte sn); fehlt ein Token, nennt die Konsole beim Senden
# Seriennummer und Position des Akkus (z. B. "SF800 Pro Akku 2").
TB_PACK_TOKENS = {
    "<SN-AKKU-1>": "<TOKEN-SF800-PRO-AKKU-1>",   # SF800 Pro, Akku 1
    "<SN-AKKU-2>": "<TOKEN-SF800-PRO-AKKU-2>",   # SF800 Pro, Akku 2
    "<SN-AKKU-3>": "<TOKEN-SF800-AKKU-1>",       # SF800, Akku 1
}
# Netz (Smartmeter, nur mit USE_SMARTMETER = True): Token und Name des Wertes.
# Leer lassen, wenn kein Smartmeter gesendet werden soll.
TB_GRID_TOKEN = ""   # z. B. "<TOKEN-NETZ>"
TB_GRID_KEY = "gridPower"

# Gesendete Messwerte: "Name im Report": "Name in ThingsBoard".
# Reihenfolge und Namen frei waehlbar; was fehlt, wird nicht gesendet.
# Umrechnungen wie in DB/CSV: hyperTmp/maxTemp in Grad C, BatVolt/totalVol/maxVol/minVol in V,
# socSet/minSoc in %. Jeder Wert kostet Datenpunkte in ThingsBoard.
# Standard: dieselben Namen wie der Dashboard-Proxy (ts_bridge) - wer umsteigt,
# nutzt seine ThingsBoard-Geraete und Verlaeufe einfach weiter.
# minVol, batteryPower und packTempLow sind berechnet (wie in ts_bridge):
#   minVol       kleinste Zellspannung aller Packs des Solarflows in V
#   batteryPower packInputPower - outputPackPower in W (+ entlaedt, - laedt)
#   packTempLow  kuehlstes Pack (kleinstes maxTemp) in ganzen Grad C
TB_HUB_FIELDS = {
    "electricLevel":   "electricLevel",
    "solarInputPower": "solarInputPower",
    "outputHomePower": "outputHomePower",
    "gridInputPower":  "gridInputPower",
    "packInputPower":  "packInputPower",
    "outputPackPower": "outputPackPower",
    "minVol":          "minVol",
    "batteryPower":    "batteryPower",
    "gridOffPower":    "offGridPower",
    "hyperTmp":        "temp",
    "packTempLow":     "packTempLow",
    "socLimit":        "socLimit",
    "socSet":          "socSet",
    "minSoc":          "minSoc",
    "heatState":       "heatState",
}
TB_PACK_FIELDS = {
    "socLevel": "socLevel",
    "power":    "power",
    "maxTemp":  "maxTemp",
    "totalVol": "totalVol",
    "maxVol":   "maxVol",
    "minVol":   "minVol",
    "batcur":   "batcur",
}
# Diese Werte (Reportnamen) nur bei Aenderung senden, dazu einmal je Tag und
# nach einem Neustart. Wirkt nur, wenn sie oben in TB_HUB_FIELDS/TB_PACK_FIELDS stehen.
TB_ON_CHANGE = ["socLimit", "socStatus", "socSet", "minSoc", "heatState",
                "gridOffMode", "chargeMaxLimit", "inverseMaxPower", "gridReverse"]

# Feste Angaben als Attribute (beim Start, bei Aenderung, einmal je Tag):
# "Name im Report": "Name in ThingsBoard". "sn" beim Solarflow = Seriennummer des Hubs.
TB_HUB_ATTRIBUTES = {
    "product": "product",
    "version": "version",
    "sn":      "hub_sn",
    "packNum": "packNum",
}
TB_PACK_ATTRIBUTES = {
    "sn":          "sn",
    "packType":    "packType",
    "softVersion": "softVersion",
}
# Lesbarer Name des Akkus als Attribut. Platzhalter: {hub} Name des
# Solarflows, {nr} Position im Report (1, 2, ...), {sn} Seriennummer.
# TB_PACK_NAME_ATTRIBUTE = "" -> kein Namens-Attribut.
TB_PACK_NAME_ATTRIBUTE = "name"
TB_PACK_NAME_FORMAT = "{hub} Akku {nr}"

# Testmodus: "python3 zendure_logger.py --once" fragt einmal ab und schreibt
# die Daten, die an ThingsBoard gingen, in diese Datei (JSON) - ohne zu senden,
# ohne DB/CSV, ohne Tokens. Geht auch mit WRITE_TB = False und mit Platzhaltern.
# Die Datei enthaelt Seriennummern und steht deshalb in .gitignore.
TB_TEST_FILE = "tb_test.json"
