#!/usr/bin/env python3
"""
Zendure - Logger fuer einen oder mehrere Speicher.

Fragt die Speicher regelmaessig ab (lokale zenSDK-Schnittstelle,
GET /properties/report, alle Geraete parallel) und schreibt die Werte in
eine SQLite-Datenbank, optional zusaetzlich in CSV-Dateien. Optional wird
die Netzleistung eines Shelly Pro 3EM mitgeschrieben.

Kein Webserver, keine Nachrichten, keine Schwellwerte - nur Aufzeichnung.

Start:   python3 zendure_logger.py
Beenden: Strg+C

Keine externen Pakete noetig - nur Python 3 Standardbibliothek.
"""
import csv, json, os, sqlite3, sys, threading, time, urllib.request
from datetime import datetime

# ----------------------------- Konfiguration -----------------------------
# Alle Einstellungen stehen in config.py (im selben Ordner). Diese Datei hier
# muss nicht angefasst werden und kann bei Updates ersetzt werden.
try:
    import config
except ImportError as e:
    print("FEHLER: config.py nicht gefunden. Die Datei muss im selben Ordner")
    print("        liegen wie dieses Script. Details:", e)
    sys.exit(1)


def _cfg(name, default):
    return getattr(config, name, default)


POLL_INTERVAL = _cfg("POLL_INTERVAL", 30)
DB_FILE = _cfg("DB_FILE", "zendure_log.db")
WRITE_CSV = _cfg("WRITE_CSV", True)
CSV_FILE = _cfg("CSV_FILE", "zendure_log.csv")
PACK_CSV_FILE = _cfg("PACK_CSV_FILE", "zendure_packs.csv")
SITE_CSV_FILE = _cfg("SITE_CSV_FILE", "zendure_site.csv")
QUIET = _cfg("QUIET", False)
RETENTION_DAYS = _cfg("RETENTION_DAYS", 7)
USE_SMARTMETER = _cfg("USE_SMARTMETER", False)
SMARTMETER_URL = _cfg("SMARTMETER_URL", "")


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
except ValueError as e:
    print("FEHLER in config.py:", e)
    sys.exit(1)

# --- Technische Definitionen (gehoeren zum Code, nicht zur Nutzer-Konfig) ---

# Aufbau der Datenbank. Passt eine vorhandene Datei nicht dazu, wird sie
# geloescht und neu angelegt (keine Uebernahme alter Daten).
SCHEMA_VERSION = 2

# Felder des Hubs (properties), die gespeichert werden
PROPS = [
    "electricLevel", "packInputPower", "outputPackPower", "outputHomePower",
    "gridInputPower", "solarInputPower", "solarPower1", "solarPower2",
    "solarPower3", "solarPower4", "packState",
    "hyperTmp", "BatVolt", "outputLimit", "inputLimit", "socSet",
    "minSoc", "acMode", "rssi", "is_error",
]

# Felder pro Akku-Pack (Reihenfolge gilt fuer DB-Tabelle und Pack-CSV)
PACK_FIELDS = ["sn", "socLevel", "state", "power", "maxTemp",
               "totalVol", "batcur", "maxVol", "minVol"]

# SQLite-Spaltentyp je Pack-Feld (Felder ohne Eintrag -> Standard REAL)
PACK_TYPES = {"sn": "TEXT", "state": "INTEGER", "batcur": "INTEGER",
              "maxVol": "INTEGER", "minVol": "INTEGER"}

# Felder, die als Roh-Temperatur (Zehntel-Kelvin) geliefert werden und vor dem
# Speichern in ganze Grad Celsius umgewandelt werden: (roh - 2731) / 10, gerundet.
TEMP_FIELDS = {"hyperTmp", "maxTemp"}

# Kopfzeilen der CSV-Dateien. Hat eine vorhandene Datei einen anderen Kopf,
# wird sie geloescht und neu angelegt.
DEV_HEADER = ["ts", "dt", "name", "hub_sn", "dev_ts"] + PROPS
PACK_HEADER = ["ts", "dt", "name", "hub_sn", "packIndex"] + PACK_FIELDS
SITE_HEADER = ["ts", "dt", "gridMeterPower"]


def log(*args):
    """Routine-Ausgabe. Wird bei QUIET=True unterdrueckt."""
    if not QUIET:
        print(*args)


def log_always(*args):
    """Wichtige Ausgabe (Fehler, Start, Neuanlage). Erscheint immer."""
    print(*args)


def now():
    return f"{datetime.now():%H:%M:%S}"


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
    """Legt die Datenbank an. Eine vorhandene Datei mit anderem Aufbau
    (z. B. aus der Fassung fuer ein Geraet) wird geloescht und neu angelegt."""
    if os.path.exists(DB_FILE) and _db_version(DB_FILE) != SCHEMA_VERSION:
        os.remove(DB_FILE)
        log_always(f"Datenbank {DB_FILE} hatte einen alten Aufbau - geloescht und neu angelegt")

    con = sqlite3.connect(DB_FILE)
    dev_cols = ", ".join(f"{p} REAL" for p in PROPS)
    con.execute(f"CREATE TABLE IF NOT EXISTS device ("
                f"ts INTEGER, dt TEXT, name TEXT, hub_sn TEXT, dev_ts INTEGER, {dev_cols}, "
                f"PRIMARY KEY (name, ts))")
    pack_cols = ", ".join(f"{f} {PACK_TYPES.get(f, 'REAL')}" for f in PACK_FIELDS)
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
def prepare_csv(path, header):
    """Datei mit anderem Kopf (alte Fassung) loeschen - sie wird neu angelegt."""
    if not os.path.exists(path):
        return
    try:
        with open(path, newline="") as f:
            first = next(csv.reader(f), None)
    except OSError:
        first = None
    if first != header:
        os.remove(path)
        log_always(f"CSV {path} hatte einen alten Aufbau - geloescht und neu angelegt")


def append_csv(path, header, rows):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        w.writerows(rows)


def _csv_val(v):
    return "" if v is None else v


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
    """Schreibt eine Abfragerunde in einer Transaktion (nur dieser Thread schreibt)."""
    dt = datetime.now().isoformat(timespec="seconds")
    dev_rows, pack_rows = [], []
    for r in reports:
        if "data" not in r:
            continue
        data = r["data"]
        ts = cycle_ts                      # gleiche Zeit fuer alle Tabellen einer Runde
        dev_ts = data.get("timestamp")     # Zeit laut Geraet
        hub_sn = data.get("sn")
        props = dict(data.get("properties", {}))
        for f in TEMP_FIELDS:
            if f in props:
                props[f] = raw_to_celsius(props[f])
        dev_rows.append([ts, dt, r["name"], hub_sn, dev_ts] + [props.get(p) for p in PROPS])
        for i, pk in enumerate(data.get("packData", [])):
            pk = dict(pk)
            for f in TEMP_FIELDS:
                if f in pk:
                    pk[f] = raw_to_celsius(pk[f])
            pack_rows.append([ts, dt, r["name"], hub_sn, i] + [pk.get(fld) for fld in PACK_FIELDS])

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
            append_csv(CSV_FILE, DEV_HEADER, [[_csv_val(v) for v in row] for row in dev_rows])
        if pack_rows:
            append_csv(PACK_CSV_FILE, PACK_HEADER, [[_csv_val(v) for v in row] for row in pack_rows])
        if USE_SMARTMETER and grid_meter is not None:
            append_csv(SITE_CSV_FILE, SITE_HEADER, [[cycle_ts, dt, grid_meter]])


# ----------------------------- Abfrage-Schleife ---------------------------
def poll_loop():
    con = setup_db()
    if WRITE_CSV:
        prepare_csv(CSV_FILE, DEV_HEADER)
        prepare_csv(PACK_CSV_FILE, PACK_HEADER)
        if USE_SMARTMETER:
            prepare_csv(SITE_CSV_FILE, SITE_HEADER)
    ziele = DB_FILE + (" + CSV" if WRITE_CSV else " (CSV aus)")
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
            store(con, reports, grid_meter, cycle_ts)
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
    setup_db().close()   # Datenbank pruefen/anlegen, bevor aufgeraeumt wird
    cleanup_db()
    threading.Thread(target=cleanup_loop, daemon=True).start()
    log_always("Beenden mit Strg+C")
    try:
        poll_loop()
    except KeyboardInterrupt:
        log_always("\nGestoppt.")


if __name__ == "__main__":
    main()
