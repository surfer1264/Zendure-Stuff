#!/usr/bin/env python3
"""
Zendure - Logger fuer einen oder mehrere Speicher.

Fragt die Speicher regelmaessig ab (lokale zenSDK-Schnittstelle,
GET /properties/report, alle Geraete parallel) und schreibt die Werte in
eine SQLite-Datenbank, in CSV-Dateien und/oder an ThingsBoard - jede
Ausgabe einzeln abschaltbar. Optional wird die Netzleistung eines
Shelly Pro 3EM mitgeschrieben.

Kein Webserver, keine Nachrichten, keine Schwellwerte - nur Aufzeichnung.

Start:   python3 zendure_logger.py
Beenden: Strg+C

Testmodus ThingsBoard:
         python3 zendure_logger.py --once
         Fragt alle Speicher einmal ab und schreibt die Daten, die an
         ThingsBoard gingen, in TB_TEST_FILE (JSON). Sendet nichts, schreibt
         weder DB noch CSV, Tokens stehen nicht in der Datei.

Keine externen Pakete noetig - nur Python 3 Standardbibliothek.
"""
import csv, importlib, json, os, re, sqlite3, sys, threading, time
import urllib.error, urllib.parse, urllib.request
from datetime import datetime

# ----------------------------- Konfiguration -----------------------------
# Alle Einstellungen stehen in config_local.py (eigene Werte, wird nicht
# committet) oder, wenn es die nicht gibt, in config.py (Vorlage mit
# Platzhaltern im Repo). Beide liegen im selben Ordner wie dieses Script,
# das nicht angefasst werden muss und bei Updates ersetzt werden kann.
import importlib.util
CONFIG_NAME = "config_local" if importlib.util.find_spec("config_local") else "config"

# Kommandozeile: ohne Argument Dauerbetrieb, --once = Testmodus ThingsBoard
_ARGS = sys.argv[1:]
if any(a not in ("--once",) for a in _ARGS):
    print("Aufruf: python3 zendure_logger.py [--once]")
    print("  --once  Testmodus: einmal abfragen, ThingsBoard-Daten in TB_TEST_FILE schreiben, nichts senden")
    sys.exit(2)
ONCE = "--once" in _ARGS
try:
    config = importlib.import_module(CONFIG_NAME)
except ImportError as e:
    print("FEHLER: weder config_local.py noch config.py gefunden. Die Datei muss im")
    print("        selben Ordner liegen wie dieses Script. Details:", e)
    sys.exit(1)


def _cfg(name, default):
    return getattr(config, name, default)


POLL_INTERVAL = _cfg("POLL_INTERVAL", 30)
DB_FILE = _cfg("DB_FILE", "zendure_log.db")
WRITE_DB = _cfg("WRITE_DB", True)
WRITE_CSV = _cfg("WRITE_CSV", True)
CSV_FILE = _cfg("CSV_FILE", "zendure_log.csv")
PACK_CSV_FILE = _cfg("PACK_CSV_FILE", "zendure_packs.csv")
SITE_CSV_FILE = _cfg("SITE_CSV_FILE", "zendure_site.csv")
QUIET = _cfg("QUIET", False)
RETENTION_DAYS = _cfg("RETENTION_DAYS", 7)
USE_SMARTMETER = _cfg("USE_SMARTMETER", False)
SMARTMETER_URL = _cfg("SMARTMETER_URL", "")

# ThingsBoard (Beschreibung und Beispiele in config.py)
WRITE_TB = _cfg("WRITE_TB", False)
TB_HOST = str(_cfg("TB_HOST", "https://eu.thingsboard.cloud")).strip().rstrip("/")
TB_INTERVAL = _cfg("TB_INTERVAL", 60)
TB_HUB_TOKENS = _cfg("TB_HUB_TOKENS", {})
TB_PACK_TOKENS = _cfg("TB_PACK_TOKENS", {})
TB_GRID_TOKEN = _cfg("TB_GRID_TOKEN", "")
TB_GRID_KEY = _cfg("TB_GRID_KEY", "gridPower")
# Standard = Namen wie im Dashboard-Proxy (ts_bridge.py), damit ein Umstieg
# dieselben ThingsBoard-Geraete und Verlaeufe weiterverwenden kann.
TB_HUB_FIELDS = _cfg("TB_HUB_FIELDS", {
    "electricLevel": "electricLevel", "solarInputPower": "solarInputPower",
    "outputHomePower": "outputHomePower", "gridInputPower": "gridInputPower",
    "packInputPower": "packInputPower", "outputPackPower": "outputPackPower",
    "minVol": "minVol", "batteryPower": "batteryPower", "gridOffPower": "offGridPower",
    "hyperTmp": "temp", "packTempLow": "packTempLow",
    "socLimit": "socLimit", "socSet": "socSet", "minSoc": "minSoc", "heatState": "heatState",
})
TB_PACK_FIELDS = _cfg("TB_PACK_FIELDS", {
    "socLevel": "socLevel", "power": "power", "maxTemp": "maxTemp",
    "totalVol": "totalVol", "maxVol": "maxVol", "minVol": "minVol", "batcur": "batcur",
})
TB_ON_CHANGE = _cfg("TB_ON_CHANGE", [
    "socLimit", "socStatus", "socSet", "minSoc", "heatState", "gridOffMode",
    "chargeMaxLimit", "inverseMaxPower", "gridReverse",
])
TB_HUB_ATTRIBUTES = _cfg("TB_HUB_ATTRIBUTES", {
    "product": "product", "version": "version", "sn": "hub_sn", "packNum": "packNum",
})
TB_PACK_ATTRIBUTES = _cfg("TB_PACK_ATTRIBUTES", {
    "sn": "sn", "packType": "packType", "softVersion": "softVersion",
})
TB_PACK_NAME_ATTRIBUTE = _cfg("TB_PACK_NAME_ATTRIBUTE", "name")
TB_PACK_NAME_FORMAT = _cfg("TB_PACK_NAME_FORMAT", "{hub} Akku {nr}")
TB_TEST_FILE = _cfg("TB_TEST_FILE", "tb_test.json")   # Ausgabe des Testmodus --once


_TB_TOKEN_RE = re.compile(r"^[A-Za-z0-9_\-.~]{1,128}$")


def _check_mapping(name, m):
    if not isinstance(m, dict):
        raise ValueError(f"{name} muss ein Dictionary sein: {{\"Reportname\": \"Name in ThingsBoard\"}}")
    for k, v in m.items():
        if not isinstance(k, str) or not isinstance(v, str) or not k.strip() or not v.strip():
            raise ValueError(f"{name}: Eintrag {k!r}: {v!r} - beide Namen muessen Text sein")


def check_tb_config(tokens=True):
    """ThingsBoard-Einstellungen pruefen (nur Form, keine Verbindung).
    tokens=False (Testmodus): Tokens nicht pruefen, Platzhalter sind erlaubt."""
    if not TB_HOST.startswith(("http://", "https://")):
        raise ValueError("TB_HOST muss mit http:// oder https:// beginnen")
    if not isinstance(TB_INTERVAL, int) or TB_INTERVAL < 10:
        raise ValueError("TB_INTERVAL muss eine ganze Zahl ab 10 (Sekunden) sein")
    for name in ("TB_HUB_TOKENS", "TB_PACK_TOKENS"):
        m = globals()[name]
        if not isinstance(m, dict):
            raise ValueError(f"{name} muss ein Dictionary sein")
        for k, tok in (m.items() if tokens else ()):
            if not _TB_TOKEN_RE.match(str(tok or "")):
                raise ValueError(f"{name}: Token fuer {k!r} fehlt oder enthaelt ungueltige Zeichen")
    if tokens and TB_GRID_TOKEN and not _TB_TOKEN_RE.match(str(TB_GRID_TOKEN)):
        raise ValueError("TB_GRID_TOKEN enthaelt ungueltige Zeichen")
    if tokens and not TB_HUB_TOKENS and not TB_PACK_TOKENS and not TB_GRID_TOKEN:
        raise ValueError("WRITE_TB = True, aber kein Token eingetragen")
    names = {d["name"] for d in DEVICES}
    for k in TB_HUB_TOKENS:
        if k not in names:
            raise ValueError(f"TB_HUB_TOKENS: {k!r} steht nicht in DEVICES")
    for name in ("TB_HUB_FIELDS", "TB_PACK_FIELDS", "TB_HUB_ATTRIBUTES", "TB_PACK_ATTRIBUTES"):
        _check_mapping(name, globals()[name])
    if not isinstance(TB_ON_CHANGE, (list, tuple)):
        raise ValueError("TB_ON_CHANGE muss eine Liste von Reportnamen sein")
    try:
        TB_PACK_NAME_FORMAT.format(hub="x", nr=1, sn="x")
    except (KeyError, IndexError, ValueError, AttributeError):
        raise ValueError("TB_PACK_NAME_FORMAT: erlaubt sind {hub}, {nr} und {sn}")


def load_devices():
    """Geraeteliste aus DEVICES; aeltere config.py mit nur DEVICE_URL -> ein Geraet."""
    devs = _cfg("DEVICES", None)
    if devs is None:
        url = _cfg("DEVICE_URL", "")
        devs = [{"name": "Hub", "url": url}] if url else []
    out, names = [], set()
    for i, d in enumerate(devs):
        name = str((d or {}).get("name") or "").strip()
        url = str((d or {}).get("url") or "").strip()
        if not name or not url:
            raise ValueError(f"DEVICES[{i}]: 'name' und 'url' muessen gesetzt sein")
        if name in names:
            raise ValueError(f"DEVICES: Name '{name}' kommt doppelt vor - Namen muessen eindeutig sein")
        names.add(name)
        out.append({"name": name, "url": url})
    if not out:
        raise ValueError("Keine Geraete konfiguriert (DEVICES leer)")
    return out


try:
    DEVICES = load_devices()
    if ONCE:
        check_tb_config(tokens=False)
    else:
        if not WRITE_DB and not WRITE_CSV and not WRITE_TB:
            raise ValueError("WRITE_DB, WRITE_CSV und WRITE_TB sind alle False - es wuerde nichts geschrieben")
        if WRITE_TB:
            check_tb_config()
except ValueError as e:
    print(f"FEHLER in {CONFIG_NAME}.py:", e)
    sys.exit(1)

# --- Technische Definitionen (gehoeren zum Code, nicht zur Nutzer-Konfig) ---

# Aufbau der Datenbank. Passt eine vorhandene Datei nicht dazu, wird sie beim
# Start umbenannt (Datum und Uhrzeit im Namen) und neu angelegt.
SCHEMA_VERSION = 4

# Felder der obersten Ebene des Reports (neben sn und timestamp)
TOP_FIELDS = ["product", "version"]

# Felder des Hubs (properties), die gespeichert werden. Gerätefelder, die ein
# Modell nicht liefert (z. B. Offgrid beim SolarFlow 800), bleiben leer.
PROPS = [
    "electricLevel", "packInputPower", "outputPackPower", "outputHomePower",
    "gridInputPower", "solarInputPower", "solarPower1", "solarPower2",
    "solarPower3", "solarPower4", "packState", "packNum",
    "hyperTmp", "heatState", "BatVolt", "outputLimit", "inputLimit", "socSet",
    "minSoc", "socLimit", "socStatus", "acMode", "gridReverse",
    "chargeMaxLimit", "inverseMaxPower", "gridOffPower", "gridOffMode",
    "faultLevel", "rssi", "is_error",
]

# Felder pro Akku-Pack (Reihenfolge gilt fuer DB-Tabelle und Pack-CSV)
PACK_FIELDS = ["sn", "packType", "softVersion", "socLevel", "state", "power",
               "maxTemp", "totalVol", "batcur", "maxVol", "minVol"]

# SQLite-Spaltentyp je Feld (Felder ohne Eintrag -> Standard REAL)
FIELD_TYPES = {"product": "TEXT", "version": "INTEGER", "sn": "TEXT",
               "packType": "INTEGER", "softVersion": "INTEGER",
               "state": "INTEGER", "batcur": "INTEGER"}

# Umrechnungen vor dem Speichern (gelten fuer DB und CSV):
#   Temperatur:   Zehntel-Kelvin -> ganze °C:  (roh - 2731) / 10, gerundet
#   Spannungen:   0,01 V -> V (2 Nachkommastellen): BatVolt, totalVol, maxVol, minVol
#   minSoc/socSet: Zehntel-Prozent -> % (1 Nachkommastelle)
TEMP_FIELDS = {"hyperTmp", "maxTemp"}
VOLT_FIELDS = {"BatVolt", "totalVol", "maxVol", "minVol"}
PERMILLE_FIELDS = {"minSoc", "socSet"}

# Kopfzeilen der Datenbank (Reportnamen). Die CSV nutzt sie mit Einheit, siehe
# _csv_name(); eine CSV mit anderem Kopf wird beim Start umbenannt.
DEV_HEADER = ["ts", "dt", "name", "hub_sn", "dev_ts"] + TOP_FIELDS + PROPS
PACK_HEADER = ["ts", "dt", "name", "hub_sn", "packIndex"] + PACK_FIELDS
SITE_HEADER = ["ts", "dt", "gridMeterPower"]


def _csv_name(field):
    """Spaltenname in der CSV: umgerechnete Werte mit Einheit, z. B. 'BatVolt (V)'.
    So passt eine CSV aus einer Fassung mit anderer Einheit nicht mehr zum Kopf
    und wird beim Start umbenannt statt weitergeschrieben."""
    if field in TEMP_FIELDS:
        return f"{field} (Grad C)"
    if field in VOLT_FIELDS:
        return f"{field} (V)"
    if field in PERMILLE_FIELDS:
        return f"{field} (%)"
    return field


DEV_CSV_HEADER = [_csv_name(f) for f in DEV_HEADER]
PACK_CSV_HEADER = [_csv_name(f) for f in PACK_HEADER]


def log(*args):
    """Routine-Ausgabe. Wird bei QUIET=True unterdrueckt."""
    if not QUIET:
        print(*args)


def log_always(*args):
    """Wichtige Ausgabe (Fehler, Start, Neuanlage). Erscheint immer."""
    print(*args)


def now():
    return f"{datetime.now():%H:%M:%S}"


def _num(raw):
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def convert(field, raw):
    """Rohwert eines Feldes in die gespeicherte Einheit umrechnen."""
    if field in TEMP_FIELDS:
        return raw_to_celsius(raw)
    if field in VOLT_FIELDS:
        v = _num(raw)
        return None if v is None else round(v / 100, 2)
    if field in PERMILLE_FIELDS:
        v = _num(raw)
        return None if v is None else round(v / 10, 1)
    return raw


def raw_to_celsius(raw):
    """Wandelt Roh-Temperatur (Zehntel-Kelvin) in ganze Grad Celsius um.

    Gibt None zurueck, wenn kein Wert vorliegt (bleibt in DB/CSV leer/NULL).
    """
    if raw is None or raw == "":
        return None
    try:
        return round((float(raw) - 2731) / 10)
    except (TypeError, ValueError):
        return None


# ----------------------------- Datenbank ----------------------------------
def _db_version(path):
    """user_version einer vorhandenen Datenbank; None, wenn nicht lesbar."""
    try:
        con = sqlite3.connect(path)
        try:
            return con.execute("PRAGMA user_version").fetchone()[0]
        finally:
            con.close()
    except sqlite3.Error:
        return None


def setup_db():
    """Legt die Datenbank an bzw. oeffnet sie. Eine Datei mit altem Aufbau
    wurde vorher in check_old_files() umbenannt."""
    if os.path.exists(DB_FILE) and _db_version(DB_FILE) != SCHEMA_VERSION:
        raise RuntimeError(f"Datenbank {DB_FILE} hat einen alten Aufbau")
    con = sqlite3.connect(DB_FILE)
    dev_cols = ", ".join(f"{p} {FIELD_TYPES.get(p, 'REAL')}" for p in TOP_FIELDS + PROPS)
    con.execute(f"CREATE TABLE IF NOT EXISTS device ("
                f"ts INTEGER, dt TEXT, name TEXT, hub_sn TEXT, dev_ts INTEGER, {dev_cols}, "
                f"PRIMARY KEY (name, ts))")
    pack_cols = ", ".join(f"{f} {FIELD_TYPES.get(f, 'REAL')}" for f in PACK_FIELDS)
    con.execute(f"CREATE TABLE IF NOT EXISTS packs ("
                f"ts INTEGER, dt TEXT, name TEXT, hub_sn TEXT, packIndex INTEGER, {pack_cols})")
    # Werte, die zum Haus gehoeren und nicht zu einem Geraet: einmal je Abfrage
    con.execute("CREATE TABLE IF NOT EXISTS site ("
                "ts INTEGER PRIMARY KEY, dt TEXT, gridMeterPower REAL)")
    con.execute("CREATE INDEX IF NOT EXISTS packs_ts ON packs (ts)")
    con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    con.commit()
    return con


# ----------------------------- CSV ----------------------------------------
# Trennzeichen fuer Excel mit deutschen Einstellungen: Spalten mit Semikolon,
# Dezimalzahlen mit Komma. Gilt nur fuer die CSV, die DB speichert Zahlen.
CSV_DELIMITER = ";"
CSV_DECIMAL = ","

def _csv_is_old(path, header):
    """True, wenn die Datei existiert und einen anderen Kopf hat (alte Fassung)."""
    if not os.path.exists(path):
        return False
    try:
        with open(path, newline="") as f:
            first = next(csv.reader(f, delimiter=CSV_DELIMITER), None)
    except OSError:
        first = None
    return first != header


def _archive_name(path, stamp):
    """zendure_log.db -> zendure_log_alt_20261121-153000.db (bei Kollision _2, _3 ...)."""
    base, ext = os.path.splitext(path)
    name = f"{base}_alt_{stamp}{ext}"
    n = 2
    while os.path.exists(name):
        name = f"{base}_alt_{stamp}_{n}{ext}"
        n += 1
    return name


def check_old_files():
    """Dateien im alten Aufbau umbenennen (Datum und Uhrzeit im Namen), damit
    neue Dateien angelegt werden koennen. Es wird nichts geloescht und nicht
    nachgefragt - laeuft also auch als Hintergrunddienst."""
    old = []
    if WRITE_DB and os.path.exists(DB_FILE) and _db_version(DB_FILE) != SCHEMA_VERSION:
        old.append(DB_FILE)
    if WRITE_CSV:
        csvs = [(CSV_FILE, DEV_CSV_HEADER), (PACK_CSV_FILE, PACK_CSV_HEADER)]
        if USE_SMARTMETER:
            csvs.append((SITE_CSV_FILE, SITE_HEADER))
        old += [path for path, header in csvs if _csv_is_old(path, header)]
    if not old:
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_always("Diese Dateien haben einen alten Aufbau und werden umbenannt (nichts geloescht):")
    for path in old:
        neu = _archive_name(path, stamp)
        try:
            os.replace(path, neu)
        except OSError as e:
            log_always(f"FEHLER: {path} laesst sich nicht umbenennen ({e}).")
            log_always("        Die Datei ist vermutlich geoeffnet - schliessen und neu starten.")
            sys.exit(1)
        log_always(f"  {path} -> {neu}")
    log_always("Neue Dateien werden angelegt.")


def append_csv(path, header, rows):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f, delimiter=CSV_DELIMITER)
        if new:
            w.writerow(header)
        w.writerows(rows)


def _csv_val(v):
    """Wert fuer die CSV: leer statt None, Dezimalkomma statt Punkt.
    Kommazahlen ohne Nachkommaanteil (z. B. 40.0) als ganze Zahl."""
    if v is None:
        return ""
    if isinstance(v, float):
        if v.is_integer():
            return str(int(v))
        return repr(v).replace(".", CSV_DECIMAL)
    return v


# ----------------------------- Abfragen -----------------------------------
def _get_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def fetch_smartmeter():
    """Aktuelle Netz-Wirkleistung vom Shelly Pro 3EM (EM.GetStatus)."""
    return _get_json(SMARTMETER_URL).get("total_act_power")


def fetch_all():
    """Alle Speicher und den Smartmeter parallel abfragen.

    Rueckgabe: (reports, grid_meter). reports: Liste je Geraet, Eintrag
    {"name", "data"} oder {"name", "error"}. Ein ausgefallenes Geraet haelt
    die anderen nicht auf.
    """
    reports = [None] * len(DEVICES)
    meter = {"value": None, "error": None}

    def hole_geraet(i, dev):
        try:
            reports[i] = {"name": dev["name"], "data": _get_json(dev["url"])}
        except Exception as e:
            reports[i] = {"name": dev["name"], "error": str(e)}

    def hole_meter():
        try:
            meter["value"] = fetch_smartmeter()
        except Exception as e:
            meter["error"] = str(e)

    threads = [threading.Thread(target=hole_geraet, args=(i, d), daemon=True)
               for i, d in enumerate(DEVICES)]
    if USE_SMARTMETER:
        threads.append(threading.Thread(target=hole_meter, daemon=True))
    for t in threads:
        t.start()
    for t in threads:
        t.join(15)
    for i, dev in enumerate(DEVICES):
        if reports[i] is None:
            reports[i] = {"name": dev["name"], "error": "keine Antwort"}
    if USE_SMARTMETER and meter["error"]:
        log_always(f"{now()}  Smartmeter-Fehler: {meter['error']}")
    return reports, meter["value"]


# ----------------------------- Schreiben ----------------------------------
def store(con, reports, grid_meter, cycle_ts):
    """Schreibt eine Abfragerunde: in die DB in einer Transaktion (nur dieser
    Thread schreibt; con None = DB aus) und/oder in die CSV-Dateien."""
    dt = datetime.now().isoformat(timespec="seconds")
    dev_rows, pack_rows = [], []
    for r in reports:
        if "data" not in r:
            continue
        data = r["data"]
        ts = cycle_ts                      # gleiche Zeit fuer alle Tabellen einer Runde
        dev_ts = data.get("timestamp")     # Zeit laut Geraet
        hub_sn = data.get("sn")
        props = data.get("properties", {})
        dev_rows.append([ts, dt, r["name"], hub_sn, dev_ts]
                        + [data.get(f) for f in TOP_FIELDS]
                        + [convert(p, props.get(p)) for p in PROPS])
        for i, pk in enumerate(data.get("packData", [])):
            pack_rows.append([ts, dt, r["name"], hub_sn, i]
                             + [convert(f, pk.get(f)) for f in PACK_FIELDS])

    if con is not None:
        with con:   # eine Transaktion; bei Fehler alles zurueck
            if dev_rows:
                ph = ", ".join("?" * len(DEV_HEADER))
                con.executemany(f"INSERT OR REPLACE INTO device ({', '.join(DEV_HEADER)}) VALUES ({ph})", dev_rows)
            if pack_rows:
                ph = ", ".join("?" * len(PACK_HEADER))
                con.executemany(f"INSERT INTO packs ({', '.join(PACK_HEADER)}) VALUES ({ph})", pack_rows)
            if USE_SMARTMETER and grid_meter is not None:
                con.execute("INSERT OR REPLACE INTO site (ts, dt, gridMeterPower) VALUES (?,?,?)",
                            (cycle_ts, dt, grid_meter))

    if WRITE_CSV:
        if dev_rows:
            append_csv(CSV_FILE, DEV_CSV_HEADER, [[_csv_val(v) for v in row] for row in dev_rows])
        if pack_rows:
            append_csv(PACK_CSV_FILE, PACK_CSV_HEADER, [[_csv_val(v) for v in row] for row in pack_rows])
        if USE_SMARTMETER and grid_meter is not None:
            append_csv(SITE_CSV_FILE, SITE_HEADER, [[cycle_ts, dt, _csv_val(grid_meter)]])


# ----------------------------- ThingsBoard --------------------------------
# Jeder Solarflow und jeder Akkupack ist in ThingsBoard ein eigenes Geraet mit
# eigenem Access Token (Device-API wie im Dashboard-Proxy, ts_bridge.py):
#   POST {TB_HOST}/api/v1/{token}/telemetry   Messwerte {"ts": ms, "values": {...}}
#   POST {TB_HOST}/api/v1/{token}/attributes  feste Angaben {...}
# Solarflow: Token ueber den Namen aus DEVICES, Akku: ueber die Seriennummer,
# Netz (Smartmeter): eigenes Token. Gesendet wird im eigenen Thread zu jedem
# Vielfachen von TB_INTERVAL (volle Minute bei 60) der letzte Stand der
# Abfrage; ein langsames ThingsBoard bremst Abfrage, DB und CSV nicht.
# Ein Wiederholversuch nach 5 s, dann verworfen (Daten liegen in DB/CSV).
_tb_lock = threading.Lock()
_tb_latest = {"snap": None}     # (cycle_ts, reports, grid_meter) der letzten Runde
_tb_last = {}                   # Geraet -> {TB-Name: (Wert, Datum)} fuer TB_ON_CHANGE
_tb_attr_last = {}              # Geraet -> (Attribute, Datum)
_tb_bad = set()                 # von ThingsBoard abgelehnte Tokens (HTTP 401)
_tb_warned = set()              # bereits gemeldete Akkus ohne Token
TB_RETRY_S = 5


def tb_update(reports, grid_meter, cycle_ts):
    """Letzten Stand fuer den Sende-Thread ablegen (aus der Abfrage-Schleife)."""
    with _tb_lock:
        _tb_latest["snap"] = (cycle_ts, reports, grid_meter)


def _tb_post(token, kind, payload):
    """kind = 'telemetry' oder 'attributes'. Rueckgabe (ok, Text). 401 = Token falsch."""
    url = "{}/api/v1/{}/{}".format(TB_HOST, urllib.parse.quote(token, safe=""), kind)
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200, "HTTP {}".format(r.status)
    except urllib.error.HTTPError as e:
        return False, "HTTP {}".format(e.code)
    except Exception as e:
        return False, str(e)


def _tb_is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _hub_min_vol(data):
    """Kleinste Zellspannung aller Packs in V; Packs mit 0 (schlafend) zaehlen nicht."""
    werte = [pk.get("minVol") for pk in data.get("packData", [])]
    werte = [v for v in werte if _tb_is_number(v) and v > 0]
    return round(min(werte) / 100, 2) if werte else None


def _hub_pack_temp_low(data):
    """Kuehlstes Pack: kleinster maxTemp-Wert in ganzen Grad C; 0 zaehlt nicht."""
    werte = [pk.get("maxTemp") for pk in data.get("packData", [])]
    werte = [v for v in werte if _tb_is_number(v) and v > 0]
    return raw_to_celsius(min(werte)) if werte else None


def _hub_battery_power(data):
    """Akkuleistung: + = Akku entlaedt, - = Akku laedt (packInputPower - outputPackPower)."""
    p = data.get("properties", {})
    pi, po = p.get("packInputPower"), p.get("outputPackPower")
    return pi - po if _tb_is_number(pi) and _tb_is_number(po) else None


# Berechnete Werte je Solarflow, genau wie im Dashboard-Proxy (ts_bridge.py).
# In TB_HUB_FIELDS wie Reportnamen verwendbar; schon umgerechnet (V, Grad C, W).
TB_HUB_DERIVED = {
    "minVol": _hub_min_vol,
    "packTempLow": _hub_pack_temp_low,
    "batteryPower": _hub_battery_power,
}


def _hub_value(data, props, key):
    """Wert fuer TB_HUB_FIELDS: Reportfeld (umgerechnet) oder berechneter Wert."""
    if key in props:
        return convert(key, props.get(key))
    if key in TB_HUB_DERIVED:
        return TB_HUB_DERIVED[key](data)
    return None


def _tb_lookup(data, src, key):
    """Wert aus dem Pack bzw. aus properties, sonst aus der obersten Ebene (z. B. sn, product)."""
    if key in src:
        return src.get(key)
    return data.get(key)


def _tb_devices(reports, grid_meter, preview=False):
    """Liste der Sendeziele: (Schluessel, Anzeige, Token, Messwerte, Attribute, Info).
    preview=True (Testmodus): auch Geraete ohne Token, Token dann None."""
    out = []
    for r in reports:
        if "data" not in r:
            continue                                     # Solarflow offline -> nichts
        data, hub = r["data"], r["name"]
        props = data.get("properties", {})
        tok = TB_HUB_TOKENS.get(hub)
        if tok or preview:
            tel = {tb: _hub_value(data, props, k) for k, tb in TB_HUB_FIELDS.items()}
            att = {tb: convert(k, _tb_lookup(data, props, k)) for k, tb in TB_HUB_ATTRIBUTES.items()}
            out.append(("hub:" + hub, hub, tok,
                        {k: v for k, v in tel.items() if _tb_is_number(v)},
                        {k: v for k, v in att.items() if v is not None},
                        {"art": "Solarflow", "solarflow": hub}))
        for i, pk in enumerate(data.get("packData", [])):
            sn = pk.get("sn")
            tok = TB_PACK_TOKENS.get(sn)
            if not tok and not preview:
                if sn and sn not in _tb_warned:
                    _tb_warned.add(sn)
                    log_always(f"{now()}  ThingsBoard: Akku {sn} ({hub} Akku {i + 1}) hat kein Token "
                               f"in TB_PACK_TOKENS - wird nicht gesendet")
                continue
            tel = {tb: convert(k, pk.get(k)) for k, tb in TB_PACK_FIELDS.items()}
            att = {tb: convert(k, _tb_lookup(data, pk, k)) for k, tb in TB_PACK_ATTRIBUTES.items()}
            att = {k: v for k, v in att.items() if v is not None}
            if TB_PACK_NAME_ATTRIBUTE:
                att[TB_PACK_NAME_ATTRIBUTE] = TB_PACK_NAME_FORMAT.format(hub=hub, nr=i + 1, sn=sn)
            out.append(("pack:" + str(sn), f"Akku {sn}", tok,
                        {k: v for k, v in tel.items() if _tb_is_number(v)}, att,
                        {"art": "Akku", "solarflow": hub, "position": i + 1, "seriennummer": sn}))
    if (TB_GRID_TOKEN or (preview and USE_SMARTMETER)) and _tb_is_number(grid_meter):
        out.append(("grid", "Netz", TB_GRID_TOKEN or None, {TB_GRID_KEY: grid_meter}, {},
                    {"art": "Netz"}))
    return out


def _tb_on_change_keys():
    """TB-Namen der Werte, die nur bei Aenderung gesendet werden."""
    names = set(TB_ON_CHANGE)
    return ({tb for k, tb in TB_HUB_FIELDS.items() if k in names}
            | {tb for k, tb in TB_PACK_FIELDS.items() if k in names})


def _tb_send_all(snap, stamp):
    _, reports, grid_meter = snap
    heute = time.strftime("%Y-%m-%d")
    on_change = _tb_on_change_keys()
    ts_ms = int(stamp * 1000)
    geraete = werte = 0
    for key, label, tok, tel, att, _info in _tb_devices(reports, grid_meter):
        if tok in _tb_bad:
            continue
        # Feste Angaben: beim ersten Mal, bei Aenderung und einmal je Tag
        if att and _tb_attr_last.get(key) != (att, heute):
            ok, ans = _tb_post(tok, "attributes", att)
            if ok:
                _tb_attr_last[key] = (att, heute)
            else:
                _tb_fail(tok, label, "Attribute", ans)
                if tok in _tb_bad:
                    continue
        # Status-Werte nur bei Aenderung (und einmal je Tag)
        last = _tb_last.get(key, {})
        tel = {k: v for k, v in tel.items() if not (k in on_change and last.get(k) == (v, heute))}
        if not tel:
            continue
        payload = {"ts": ts_ms, "values": tel}
        ok, ans = _tb_post(tok, "telemetry", payload)
        if not ok and not ans.startswith("HTTP 401"):
            time.sleep(TB_RETRY_S)
            ok, ans = _tb_post(tok, "telemetry", payload)
        if ok:
            merk = _tb_last.setdefault(key, {})
            for k in on_change & set(tel):
                merk[k] = (tel[k], heute)
            geraete += 1
            werte += len(tel)
        else:
            _tb_fail(tok, label, "Messwerte", ans)
    zeit = time.strftime("%H:%M:%S", time.localtime(stamp))
    log(f"{now()}  ThingsBoard {zeit}: {werte} Werte an {geraete} Geraet(e) gesendet")


def _tb_fail(tok, label, was, ans):
    if ans.startswith("HTTP 401"):
        _tb_bad.add(tok)
        log_always(f"{now()}  ThingsBoard: Token fuer {label} abgelehnt (HTTP 401) - "
                   f"wird bis zum Neustart nicht mehr verwendet")
    else:
        log_always(f"{now()}  ThingsBoard: {was} fuer {label} verworfen ({ans})")


def _tb_check_tokens():
    """Beim Start jedes Token einmal pruefen (Test-Attribut wie in ts_bridge)."""
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
    tokens = [(f"Solarflow {k}", t) for k, t in TB_HUB_TOKENS.items()]
    tokens += [(f"Akku {k}", t) for k, t in TB_PACK_TOKENS.items()]
    if TB_GRID_TOKEN:
        tokens.append(("Netz", TB_GRID_TOKEN))
    for label, tok in tokens:
        ok, ans = _tb_post(tok, "attributes", {"simplemonStart": stamp})
        if ok:
            log_always(f"  ThingsBoard {label}: Token ok")
        else:
            _tb_fail(tok, label, "Test", ans)
    for d in DEVICES:
        if d["name"] not in TB_HUB_TOKENS:
            log_always(f"  ThingsBoard: Solarflow {d['name']} hat kein Token - wird nicht gesendet")


def tb_once():
    """Testmodus --once: einmal abfragen, Sendedaten in TB_TEST_FILE schreiben.
    Sendet nichts, schreibt weder DB noch CSV. Tokens stehen nicht in der Datei."""
    log_always(f"Testmodus ThingsBoard (--once), Einstellungen aus {CONFIG_NAME}.py - es wird nichts gesendet")
    reports, grid_meter = fetch_all()
    stamp = int(time.time())
    on_change = _tb_on_change_keys()
    geraete, ohne_token, punkte, punkte_dauer = [], [], 0, 0
    for key, label, tok, tel, att, info in _tb_devices(reports, grid_meter, preview=True):
        name = info.get("solarflow") if info["art"] == "Solarflow" else (
            f"{info['solarflow']} Akku {info['position']}" if info["art"] == "Akku" else "Netz")
        eintrag = dict(info)
        eintrag["token"] = "eingetragen" if tok else "fehlt - wird nicht gesendet"
        eintrag["telemetry"] = {"url": f"{TB_HOST}/api/v1/<TOKEN>/telemetry",
                                "payload": {"ts": stamp * 1000, "values": tel}}
        eintrag["nur_bei_aenderung"] = sorted(on_change & set(tel))
        if att:
            eintrag["attributes"] = {"url": f"{TB_HOST}/api/v1/<TOKEN>/attributes", "payload": att}
        geraete.append(eintrag)
        if tok:
            punkte += len(tel)
            punkte_dauer += len(set(tel) - on_change)
        else:
            ohne_token.append(name if info["art"] != "Akku" else f"{name} (Seriennummer {info['seriennummer']})")
    nicht_erreicht = [{"solarflow": r["name"], "fehler": r["error"]} for r in reports if "error" in r]
    doc = {
        "erstellt": datetime.fromtimestamp(stamp).isoformat(timespec="seconds"),
        "hinweis": "Testmodus --once: nichts gesendet. Tokens sind nicht enthalten. "
                   "Die Datei enthaelt Seriennummern - nicht weitergeben.",
        "einstellungen": {"datei": f"{CONFIG_NAME}.py", "WRITE_TB": WRITE_TB, "TB_HOST": TB_HOST,
                          "TB_INTERVAL": TB_INTERVAL},
        "geraete": geraete,
        "nicht_erreicht": nicht_erreicht,
        "ohne_token": ohne_token,
        "datenpunkte": {
            "erste_sendung": punkte,
            "je_sendung_danach": punkte_dauer,
            "je_tag_ca": punkte_dauer * (86400 // TB_INTERVAL),
            "hinweis": "nur Geraete mit Token; Werte aus nur_bei_aenderung zaehlen nur bei Aenderung",
        },
    }
    with open(TB_TEST_FILE, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    log_always(f"{len(geraete)} Geraet(e) -> {TB_TEST_FILE}")
    for g in nicht_erreicht:
        log_always(f"  nicht erreicht: {g['solarflow']} ({g['fehler']})")
    for n in ohne_token:
        log_always(f"  ohne Token: {n}")
    log_always(f"  Datenpunkte je Sendung: {punkte_dauer} (erste Sendung {punkte}), "
               f"je Tag ca. {doc['datenpunkte']['je_tag_ca']}")


def tb_loop():
    _tb_check_tokens()
    max_alter = max(2 * POLL_INTERVAL, TB_INTERVAL)
    while True:
        nxt = (int(time.time()) // TB_INTERVAL + 1) * TB_INTERVAL
        time.sleep(max(0.0, nxt - time.time()))
        with _tb_lock:
            snap = _tb_latest["snap"]
        if snap is None or nxt - snap[0] > max_alter:
            log(f"{now()}  ThingsBoard: kein aktueller Stand - nichts gesendet")
            continue
        try:
            _tb_send_all(snap, nxt)
        except Exception as e:
            log_always(f"{now()}  ThingsBoard-Fehler: {e}")


# ----------------------------- Abfrage-Schleife ---------------------------
def poll_loop():
    con = setup_db() if WRITE_DB else None
    ziele = " + ".join(([DB_FILE] if WRITE_DB else []) + (["CSV"] if WRITE_CSV else [])
                       + ([f"ThingsBoard alle {TB_INTERVAL}s"] if WRITE_TB else []))
    log_always(f"Einstellungen aus {CONFIG_NAME}.py")
    log_always(f"Logging von {len(DEVICES)} Geraet(en) alle {POLL_INTERVAL}s -> {ziele}")
    for d in DEVICES:
        log_always(f"  {d['name']}: {d['url']}")
    if USE_SMARTMETER:
        log_always(f"  Smartmeter: {SMARTMETER_URL}")
    while True:
        start = time.time()
        cycle_ts = int(start)
        try:
            reports, grid_meter = fetch_all()
            if WRITE_DB or WRITE_CSV:
                store(con, reports, grid_meter, cycle_ts)
            if WRITE_TB:
                tb_update(reports, grid_meter, cycle_ts)
            for r in reports:
                if "error" in r:
                    log_always(f"{now()}  {r['name']}: Fehler: {r['error']}")
                    continue
                p = r["data"].get("properties", {})
                log(f"{now()}  {r['name']}: SoC={p.get('electricLevel')}%  "
                    f"Solar={p.get('solarInputPower')}W  Out={p.get('outputHomePower')}W  "
                    f"Packs={len(r['data'].get('packData', []))}")
            if USE_SMARTMETER:
                log(f"{now()}  Netz(Meter)={grid_meter}W")
        except Exception as e:
            log_always(f"{now()}  Fehler: {e}")
        # Takt halten: Dauer der Abfrage vom Intervall abziehen
        time.sleep(max(1.0, POLL_INTERVAL - (time.time() - start)))


# ----------------------------- Aufraeumen ---------------------------------
def cleanup_db():
    """Loescht Zeilen aelter als RETENTION_DAYS aus device, packs und site.

    RETENTION_DAYS = 0 -> nichts loeschen. Die CSV-Dateien bleiben unangetastet.
    """
    if not RETENTION_DAYS or RETENTION_DAYS <= 0:
        return
    cutoff = int(time.time()) - RETENTION_DAYS * 86400
    try:
        con = sqlite3.connect(DB_FILE, timeout=30)
        n = 0
        for table in ("device", "packs", "site"):
            n += con.execute(f"DELETE FROM {table} WHERE ts < ?", (cutoff,)).rowcount
        con.commit()
        if n:
            con.execute("VACUUM")  # Datei physisch verkleinern
            log(f"{now()}  Aufraeumen: {n} Zeilen aelter als {RETENTION_DAYS} Tage geloescht")
        con.close()
    except Exception as e:
        log_always(f"{now()}  Aufraeum-Fehler: {e}")


def cleanup_loop():
    while True:
        time.sleep(86400)  # erst nach einem Tag, dann taeglich
        cleanup_db()


def main():
    if ONCE:
        tb_once()
        return
    check_old_files()
    if WRITE_DB:
        setup_db().close()   # Datenbank pruefen/anlegen, bevor aufgeraeumt wird
        cleanup_db()
        threading.Thread(target=cleanup_loop, daemon=True).start()
    if WRITE_TB:
        threading.Thread(target=tb_loop, daemon=True).start()
    log_always("Beenden mit Strg+C")
    try:
        poll_loop()
    except KeyboardInterrupt:
        log_always("\nGestoppt.")


if __name__ == "__main__":
    main()
