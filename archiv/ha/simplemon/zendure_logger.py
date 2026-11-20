#!/usr/bin/env python3
"""
Zendure - Logger.

Fragt einen Zendure-Speicher regelmaessig ab (lokale zenSDK-Schnittstelle,
GET /properties/report) und schreibt die Werte in eine SQLite-Datenbank,
optional zusaetzlich in CSV-Dateien. Optional werden die Netzleistung eines
Shelly Pro 3EM und die Leistung eines weiteren Shellys mitgeschrieben.

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
# Eine aeltere config.py mit zusaetzlichen Eintraegen (Webserver, Nachrichten,
# Schwellwerte) funktioniert weiter - diese Eintraege werden ignoriert.
try:
    from config import (
        DEVICE_URL, POLL_INTERVAL,
        CSV_FILE, PACK_CSV_FILE, DB_FILE, WRITE_CSV, QUIET,
        RETENTION_DAYS,
    )
except ImportError as e:
    print("FEHLER: config.py nicht gefunden oder unvollstaendig.")
    print("        Die Datei config.py muss im selben Ordner liegen wie dieses Script")
    print("        und alle Einstellungen enthalten. Details:", e)
    sys.exit(1)

# Optionale Quellen mit Fallback: fehlen die Eintraege, bleiben sie aus.
try:
    from config import USE_SMARTMETER, SMARTMETER_URL
except ImportError:
    USE_SMARTMETER = False
    SMARTMETER_URL = ""

try:
    from config import USE_EXTRA_SHELLY, EXTRA_SHELLY_URL
except ImportError:
    USE_EXTRA_SHELLY = False
    EXTRA_SHELLY_URL = ""

# --- Technische Definitionen (gehoeren zum Code, nicht zur Nutzer-Konfig) ---

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

# Leistungsfelder, aus denen die Tagesenergie (kWh) integriert wird -> Spaltenname
ENERGY_FIELDS = {
    "solar": "solarInputPower",
    "home": "outputHomePower",
    "grid": "gridInputPower",
    "charge": "outputPackPower",
    "discharge": "packInputPower",
}


def log(*args):
    """Routine-Ausgabe. Wird bei QUIET=True unterdrueckt."""
    if not QUIET:
        print(*args)


def log_always(*args):
    """Wichtige Ausgabe (Fehler, Migration, Start). Erscheint immer."""
    print(*args)


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
def _pack_col_def(field):
    return f"{field} {PACK_TYPES.get(field, 'REAL')}"


def ensure_columns(con, table, expected):
    """Ergaenzt fehlende Spalten in einer bestehenden Tabelle per ALTER TABLE.

    `expected` ist eine Liste von (Spaltenname, Typ)-Tupeln. Bereits
    vorhandene Spalten bleiben unveraendert; nur fehlende werden hinzugefuegt.
    """
    have = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
    for name, ctype in expected:
        if name not in have:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ctype}")
            log_always(f"DB-Migration: Spalte '{name}' zu Tabelle '{table}' hinzugefuegt")


def setup_db():
    con = sqlite3.connect(DB_FILE)

    # gridMeterPower: Momentanwert vom Shelly Pro 3EM (echter Smartmeter-Wert,
    # unabhaengig von der Zendure-eigenen gridInputPower).
    dev_cols = ", ".join(f"{p} REAL" for p in PROPS)
    con.execute(f"CREATE TABLE IF NOT EXISTS device "
                f"(ts INTEGER PRIMARY KEY, dt TEXT, hub_sn TEXT, gridMeterPower REAL, "
                f"extraShellyPower REAL, {dev_cols})")
    pack_cols = ", ".join(_pack_col_def(f) for f in PACK_FIELDS)
    con.execute(f"CREATE TABLE IF NOT EXISTS packs (ts INTEGER, dt TEXT, {pack_cols})")

    # Dauerhafte Tages-Energiestatistik (bleibt auch nach Loeschung der Rohdaten)
    con.execute("""CREATE TABLE IF NOT EXISTS energy_daily (
        day TEXT PRIMARY KEY, solar REAL, home REAL, grid REAL,
        charge REAL, discharge REAL)""")

    # Bestehende Tabellen migrieren: neue Felder aus PROPS / PACK_FIELDS nachziehen
    ensure_columns(con, "device",
                   [("hub_sn", "TEXT"), ("gridMeterPower", "REAL"), ("extraShellyPower", "REAL")]
                   + [(p, "REAL") for p in PROPS])
    ensure_columns(con, "packs", [(f, PACK_TYPES.get(f, "REAL")) for f in PACK_FIELDS])

    con.commit()
    return con


# ----------------------------- Abfragen -----------------------------------
def _get_json(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def fetch_device():
    return _get_json(DEVICE_URL)


def fetch_smartmeter():
    """Aktuelle Netz-Wirkleistung vom Shelly Pro 3EM (EM.GetStatus)."""
    return _get_json(SMARTMETER_URL).get("total_act_power")


def fetch_extra_shelly():
    """Aktueller Leistungswert des weiteren Shellys (RPC).

    Erkennt 'total_act_power' (EM.GetStatus), 'act_power' (EM1.GetStatus)
    und 'apower' (Switch.GetStatus / PM1.GetStatus).
    """
    d = _get_json(EXTRA_SHELLY_URL)
    for key in ("total_act_power", "act_power", "apower"):
        if key in d:
            return d[key]
    return None


# ----------------------------- Schreiben ----------------------------------
def log_csv(ts, dt, hub_sn, props, grid_meter=None, extra_shelly=None):
    new = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ts", "dt", "hub_sn", "gridMeterPower", "extraShellyPower"] + PROPS)
        w.writerow([ts, dt, hub_sn if hub_sn is not None else "",
                    grid_meter if grid_meter is not None else "",
                    extra_shelly if extra_shelly is not None else ""] +
                   [props.get(p, "") for p in PROPS])


def log_packs_csv(ts, dt, packs):
    new = not os.path.exists(PACK_CSV_FILE)
    with open(PACK_CSV_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ts", "dt", "packIndex"] + PACK_FIELDS)
        for i, pk in enumerate(packs):
            w.writerow([ts, dt, i] + [pk.get(fld, "") for fld in PACK_FIELDS])


def store(con, data, grid_meter=None, extra_shelly=None):
    ts = data.get("timestamp", int(time.time()))
    dt = datetime.now().isoformat(timespec="seconds")
    props = dict(data.get("properties", {}))  # Kopie, Original unangetastet

    # Temperaturen vor dem Speichern in ganze Grad Celsius umwandeln
    for f in TEMP_FIELDS:
        if f in props:
            props[f] = raw_to_celsius(props[f])

    packs = [dict(pk) for pk in data.get("packData", [])]  # Kopien
    for pk in packs:
        for f in TEMP_FIELDS:
            if f in pk:
                pk[f] = raw_to_celsius(pk[f])

    hub_sn = data.get("sn")  # Seriennummer des Hubs (oberste Ebene im Report)

    dev_cols = ["ts", "dt", "hub_sn", "gridMeterPower", "extraShellyPower"] + PROPS
    dev_ph = ", ".join("?" * len(dev_cols))
    con.execute(
        f"INSERT OR REPLACE INTO device ({', '.join(dev_cols)}) VALUES ({dev_ph})",
        [ts, dt, hub_sn, grid_meter, extra_shelly] + [props.get(p) for p in PROPS])

    pack_cols = ["ts", "dt"] + PACK_FIELDS
    pack_ph = ", ".join("?" * len(pack_cols))
    for pk in packs:
        con.execute(
            f"INSERT INTO packs ({', '.join(pack_cols)}) VALUES ({pack_ph})",
            [ts, dt] + [pk.get(fld) for fld in PACK_FIELDS])
    con.commit()
    if WRITE_CSV:
        log_csv(ts, dt, hub_sn, props, grid_meter, extra_shelly)
        log_packs_csv(ts, dt, packs)


# ----------------------------- Abfrage-Schleife ---------------------------
def poll_loop():
    con = setup_db()
    ziele = DB_FILE + (f" + {CSV_FILE} + {PACK_CSV_FILE}" if WRITE_CSV else " (CSV aus)")
    log_always(f"Logging {DEVICE_URL} alle {POLL_INTERVAL}s -> {ziele}")
    if USE_SMARTMETER:
        log_always(f"Smartmeter zusaetzlich unter {SMARTMETER_URL}")
    if USE_EXTRA_SHELLY:
        log_always(f"Weiterer Shelly zusaetzlich unter {EXTRA_SHELLY_URL}")
    while True:
        try:
            data = fetch_device()

            # Ein Fehler bei den optionalen Quellen darf die Aufzeichnung des
            # Speichers nicht stoppen - der Wert bleibt dann einfach leer.
            grid_meter = None
            if USE_SMARTMETER:
                try:
                    grid_meter = fetch_smartmeter()
                except Exception as e:
                    log_always(f"{datetime.now():%H:%M:%S}  Smartmeter-Fehler: {e}")

            extra_shelly = None
            if USE_EXTRA_SHELLY:
                try:
                    extra_shelly = fetch_extra_shelly()
                except Exception as e:
                    log_always(f"{datetime.now():%H:%M:%S}  Shelly-Fehler: {e}")

            store(con, data, grid_meter, extra_shelly)
            p = data.get("properties", {})
            gm_txt = f"  Netz(Meter)={grid_meter}W" if USE_SMARTMETER else ""
            es_txt = f"  Shelly={extra_shelly}W" if USE_EXTRA_SHELLY else ""
            log(f"{datetime.now():%H:%M:%S}  SoC={p.get('electricLevel')}%  "
                f"Solar={p.get('solarInputPower')}W  Out={p.get('outputHomePower')}W{gm_txt}{es_txt}")
        except Exception as e:
            log_always(f"{datetime.now():%H:%M:%S}  Fehler: {e}")
        time.sleep(POLL_INTERVAL)


# ----------------------------- Tagesenergie / Aufraeumen ------------------
def energy_by_day():
    """Berechnet je Kalendertag die Energie (kWh) aus den Leistungswerten.

    Integration: fuer jede DB-Zeile Leistung x Zeit zur Vorzeile. Zeitluecken
    groesser als 2x POLL_INTERVAL werden verworfen (Geraeteausfall/Neustart).

    Rueckgabe: dict {datum: {solar, home, grid, charge, discharge}} in kWh.
    """
    cols = list(ENERGY_FIELDS.keys())
    selects = ", ".join(ENERGY_FIELDS[c] for c in cols)
    max_gap = 2 * POLL_INTERVAL

    con = sqlite3.connect(DB_FILE)
    rows = con.execute(
        f"SELECT ts, dt, {selects} FROM device ORDER BY ts ASC").fetchall()
    con.close()

    result = {}
    prev_ts = None
    for row in rows:
        ts, dt = row[0], row[1]
        day = (dt or "")[:10]  # YYYY-MM-DD
        if day and day not in result:
            result[day] = {c: 0.0 for c in cols}
        if prev_ts is not None and day in result:
            gap = ts - prev_ts
            if 0 < gap <= max_gap:
                hours = gap / 3600.0
                for i, c in enumerate(cols):
                    val = row[2 + i]
                    if val:  # None/0 ueberspringen
                        result[day][c] += val * hours / 1000.0  # Wh -> kWh
        prev_ts = ts

    for day in result:
        for c in result[day]:
            result[day][c] = round(result[day][c], 3)
    return result


def persist_energy_daily():
    """Schreibt die aus den Rohdaten berechneten Tageswerte dauerhaft fest.

    INSERT OR REPLACE: der laufende Tag wird aktualisiert, abgeschlossene Tage
    bleiben erhalten - auch nachdem das Aufraeumen ihre Rohdaten geloescht hat.
    """
    try:
        fresh = energy_by_day()
        if not fresh:
            return
        con = sqlite3.connect(DB_FILE)
        for day, v in fresh.items():
            con.execute(
                "INSERT OR REPLACE INTO energy_daily "
                "(day, solar, home, grid, charge, discharge) VALUES (?,?,?,?,?,?)",
                (day, v["solar"], v["home"], v["grid"], v["charge"], v["discharge"]))
        con.commit()
        con.close()
    except Exception as e:
        log_always(f"{datetime.now():%H:%M:%S}  Energie-Fehler: {e}")


def cleanup_db():
    """Loescht DB-Zeilen aelter als RETENTION_DAYS aus device und packs.

    RETENTION_DAYS = 0 -> nichts loeschen. Die CSV-Dateien bleiben unangetastet.
    """
    if not RETENTION_DAYS or RETENTION_DAYS <= 0:
        return
    cutoff = int(time.time()) - RETENTION_DAYS * 86400
    try:
        con = sqlite3.connect(DB_FILE)
        d = con.execute("DELETE FROM device WHERE ts < ?", (cutoff,)).rowcount
        p = con.execute("DELETE FROM packs WHERE ts < ?", (cutoff,)).rowcount
        con.commit()
        if d or p:
            con.execute("VACUUM")  # Datei physisch verkleinern
            con.commit()
            log(f"{datetime.now():%H:%M:%S}  Aufraeumen: {d} device- und {p} pack-Zeilen "
                f"aelter als {RETENTION_DAYS} Tage geloescht")
        con.close()
    except Exception as e:
        log_always(f"{datetime.now():%H:%M:%S}  Aufraeum-Fehler: {e}")


def cleanup_loop():
    """Sichert taeglich die Tagesenergie und raeumt dann alte Rohdaten auf.

    Reihenfolge ist wichtig: erst die Tageswerte festschreiben, DANN alte
    Rohdaten loeschen - sonst gingen die Werte verloren.
    """
    while True:
        persist_energy_daily()
        cleanup_db()
        time.sleep(86400)  # 24 Stunden


def main():
    setup_db().close()   # Tabellen anlegen, bevor das Aufraeumen sie liest
    threading.Thread(target=cleanup_loop, daemon=True).start()
    log_always("Beenden mit Strg+C")
    try:
        poll_loop()
    except KeyboardInterrupt:
        log_always("\nGestoppt.")


if __name__ == "__main__":
    main()
