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

POLL_INTERVAL = 30          # Sekunden zwischen Abfragen

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
WRITE_TB = False    # Versand an ThingsBoard (Einstellungen ganz unten).

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
