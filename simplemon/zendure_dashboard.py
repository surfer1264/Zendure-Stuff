#!/usr/bin/env python3
"""
Zendure SF240Pro - Logger + Web-Dashboard in einem.

Pollt das Gerät regelmaessig, speichert die Daten in CSV und SQLite
und stellt unter http://localhost:8080 ein Live-Dashboard bereit.

Kein CORS-Problem, weil Browser und Daten vom selben Server kommen.

Start:   python3 zendure_dashboard.py
Aufruf:  http://localhost:8080   (im Browser)

Keine externen Pakete noetig - nur Python 3 Standardbibliothek.
"""
import json, sqlite3, csv, time, os, threading, urllib.request, urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ----------------------------- Konfiguration -----------------------------
# Alle Einstellungen stehen in config.py (im selben Ordner). Diese Datei hier
# muss nicht angefasst werden und kann bei Updates ersetzt werden.
try:
    from config import (
        DEVICE_URL, POLL_INTERVAL, WEB_PORT, DEVICE_LABEL,
        CSV_FILE, PACK_CSV_FILE, DB_FILE, WRITE_CSV, QUIET,
        RETENTION_DAYS, MAX_POINTS,
        USE_SIGNAL, SIGNAL_PHONE, SIGNAL_KEY,
        VOLL_SCHWELLE, ENTLADE_RESET, MIN_VOLT_WARN, MIN_VOLT_RESET,
        TEMP_WARN, TEMP_RESET,
    )
except ImportError as e:
    import sys
    print("FEHLER: config.py nicht gefunden oder unvollstaendig.")
    print("        Die Datei config.py muss im selben Ordner liegen wie dieses Script")
    print("        und alle Einstellungen enthalten. Details:", e)
    sys.exit(1)

# --- Technische Definitionen (gehoeren zum Code, nicht zur Nutzer-Konfig) ---

# Felder pro Akku-Pack (Reihenfolge gilt fuer DB-Tabelle und Pack-CSV)
PACK_FIELDS = ["sn", "socLevel", "state", "power", "maxTemp",
               "totalVol", "batcur", "maxVol", "minVol"]

# SQLite-Spaltentyp je Pack-Feld (Felder ohne Eintrag -> Standard REAL)
PACK_TYPES = {"sn": "TEXT", "state": "INTEGER", "batcur": "INTEGER",
              "maxVol": "INTEGER", "minVol": "INTEGER"}

# Felder, die als Roh-Temperatur (Zehntel-Kelvin) geliefert werden und vor dem
# Speichern in ganze Grad Celsius umgewandelt werden: (roh - 2731) / 10, gerundet.
TEMP_FIELDS = {"hyperTmp", "maxTemp"}


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

PROPS = [
    "electricLevel", "packInputPower", "outputPackPower", "outputHomePower",
    "gridInputPower", "solarInputPower", "solarPower1", "solarPower2",
    "solarPower3", "solarPower4", "packState",
    "hyperTmp", "BatVolt", "outputLimit", "inputLimit", "socSet",
    "minSoc", "acMode", "rssi", "is_error",
]

# Letzter abgerufener Datensatz (vom Poll-Thread gefuellt, vom Webserver gelesen)
_latest = {"data": None, "ts": 0, "error": None}
_lock = threading.Lock()

# Alarm-Zustand fuer Hysterese: merkt sich, welche Warnung bereits gesendet wurde,
# damit nicht bei jedem Poll erneut benachrichtigt wird.
_alarm = {"voll": False, "temp": False, "lowvolt": {}}


def send_signal(text):
    """Sendet eine Signal-Nachricht ueber CallMeBot. No-op wenn USE_SIGNAL=False."""
    if not USE_SIGNAL:
        return
    try:
        params = urllib.parse.urlencode(
            {"phone": SIGNAL_PHONE, "apikey": SIGNAL_KEY, "text": text})
        url = "https://api.callmebot.com/signal/send.php?" + params
        with urllib.request.urlopen(url, timeout=15) as r:
            r.read()
        log(f"{datetime.now():%H:%M:%S}  Signal gesendet: {text.splitlines()[0]}")
    except Exception as e:
        log_always(f"{datetime.now():%H:%M:%S}  Signal-Fehler: {e}")


def check_alarms(props, packs):
    """Prueft Schwellwerte und sendet Warnungen mit Hysterese.

    Erwartet Roh-`props` und Roh-`packs` (Temperatur in Zehntel-Kelvin,
    Zellspannung in der vom Geraet gelieferten Roh-Einheit).
    """
    if not USE_SIGNAL:
        return

    # --- Akku voll ---
    soc = props.get("electricLevel")
    if soc is not None:
        if soc >= VOLL_SCHWELLE and not _alarm["voll"]:
            _alarm["voll"] = True
            send_signal(f"\U0001F50B Akku ist jetzt voll ({soc}%)")
        elif soc < ENTLADE_RESET:
            _alarm["voll"] = False

    # --- Geraete-Temperatur ---
    temp = raw_to_celsius(props.get("hyperTmp"))
    if temp is not None:
        if temp > TEMP_WARN and not _alarm["temp"]:
            _alarm["temp"] = True
            send_signal(f"\U0001F525 Achtung! Geraete-Temperatur zu hoch: {temp} \u00b0C")
        elif temp < TEMP_RESET:
            _alarm["temp"] = False

    # --- Unterspannung je Pack/Zelle ---
    for pk in packs:
        sn = pk.get("sn")
        raw = pk.get("minVol")
        if sn is None or raw is None:
            continue
        minv = raw / 100.0
        sent = _alarm["lowvolt"].get(sn, False)
        if 0 < minv < MIN_VOLT_WARN and not sent:
            _alarm["lowvolt"][sn] = True
            send_signal(f"\u26A0\uFE0F Zelle {sn} hat nur {minv:.2f} V!")
        elif minv > MIN_VOLT_RESET:
            _alarm["lowvolt"][sn] = False


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
    con = sqlite3.connect(DB_FILE, check_same_thread=False)

    # Tabellen anlegen, falls noch nicht vorhanden
    dev_cols = ", ".join(f"{p} REAL" for p in PROPS)
    con.execute(f"CREATE TABLE IF NOT EXISTS device (ts INTEGER PRIMARY KEY, dt TEXT, {dev_cols})")
    pack_cols = ", ".join(_pack_col_def(f) for f in PACK_FIELDS)
    con.execute(f"CREATE TABLE IF NOT EXISTS packs (ts INTEGER, dt TEXT, {pack_cols})")

    # Bestehende Tabellen migrieren: neue Felder aus PROPS / PACK_FIELDS nachziehen
    ensure_columns(con, "device", [(p, "REAL") for p in PROPS])
    ensure_columns(con, "packs", [(f, PACK_TYPES.get(f, "REAL")) for f in PACK_FIELDS])

    con.commit()
    return con


def fetch_device():
    req = urllib.request.Request(DEVICE_URL, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())


def log_csv(ts, dt, props):
    new = not os.path.exists(CSV_FILE)
    with open(CSV_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ts", "dt"] + PROPS)
        w.writerow([ts, dt] + [props.get(p, "") for p in PROPS])


def log_packs_csv(ts, dt, packs):
    new = not os.path.exists(PACK_CSV_FILE)
    with open(PACK_CSV_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["ts", "dt", "packIndex"] + PACK_FIELDS)
        for i, pk in enumerate(packs):
            w.writerow([ts, dt, i] + [pk.get(fld, "") for fld in PACK_FIELDS])


def store(con, data):
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

    dev_cols = ["ts", "dt"] + PROPS
    dev_ph = ", ".join("?" * len(dev_cols))
    con.execute(
        f"INSERT OR REPLACE INTO device ({', '.join(dev_cols)}) VALUES ({dev_ph})",
        [ts, dt] + [props.get(p) for p in PROPS])

    pack_cols = ["ts", "dt"] + PACK_FIELDS
    pack_ph = ", ".join("?" * len(pack_cols))
    for pk in packs:
        con.execute(
            f"INSERT INTO packs ({', '.join(pack_cols)}) VALUES ({pack_ph})",
            [ts, dt] + [pk.get(fld) for fld in PACK_FIELDS])
    con.commit()
    if WRITE_CSV:
        log_csv(ts, dt, props)
        log_packs_csv(ts, dt, packs)


# ----------------------------- Poll-Thread --------------------------------
def poll_loop():
    con = setup_db()
    ziele = DB_FILE + (f" + {CSV_FILE} + {PACK_CSV_FILE}" if WRITE_CSV else " (CSV aus)")
    log(f"Logging {DEVICE_URL} alle {POLL_INTERVAL}s -> {ziele}")
    while True:
        try:
            data = fetch_device()
            store(con, data)
            with _lock:
                _latest.update(data=data, ts=time.time(), error=None)
            # Alarme auf Basis der Rohdaten pruefen (vor jeder Umwandlung)
            check_alarms(data.get("properties", {}), data.get("packData", []))
            p = data.get("properties", {})
            log(f"{datetime.now():%H:%M:%S}  SoC={p.get('electricLevel')}%  "
                f"Solar={p.get('solarInputPower')}W  Out={p.get('outputHomePower')}W")
        except Exception as e:
            with _lock:
                _latest.update(error=str(e))
            log_always(f"{datetime.now():%H:%M:%S}  Fehler: {e}")
        time.sleep(POLL_INTERVAL)


# ----------------------------- Retention / Cleanup ------------------------
def cleanup_db():
    """Loescht DB-Zeilen aelter als RETENTION_DAYS aus device und packs.

    Die CSV-Dateien bleiben unangetastet (Langzeit-Archiv).
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
            log(f"{datetime.now():%H:%M:%S}  Cleanup: {d} device- und {p} pack-Zeilen "
                f"aelter als {RETENTION_DAYS} Tage geloescht")
        con.close()
    except Exception as e:
        log_always(f"{datetime.now():%H:%M:%S}  Cleanup-Fehler: {e}")


def cleanup_loop():
    """Fuehrt das Aufraeumen beim Start und danach einmal taeglich aus."""
    cleanup_db()
    while True:
        time.sleep(86400)  # 24 Stunden
        cleanup_db()


# ----------------------------- Energie / Arbeit ---------------------------
# Leistungsfelder, aus denen die Arbeit (kWh) integriert wird -> Ausgabename.
ENERGY_FIELDS = {
    "solar": "solarInputPower",
    "home": "outputHomePower",
    "grid": "gridInputPower",
    "charge": "outputPackPower",
    "discharge": "packInputPower",
}


def energy_by_day(days=None):
    """Berechnet je Kalendertag die Arbeit (kWh) aus den Leistungswerten.

    Integration: fuer jede DB-Zeile Leistung x Zeit zur Vorzeile. Zeitluecken
    groesser als 2x POLL_INTERVAL werden verworfen (Geraeteausfall/Neustart),
    damit die Summe nicht faelschlich hochgerechnet wird.

    Rueckgabe: dict {datum: {solar, home, grid, charge, discharge}} in kWh.
    """
    cols = list(ENERGY_FIELDS.keys())
    selects = ", ".join(ENERGY_FIELDS[c] for c in cols)
    max_gap = 2 * POLL_INTERVAL  # Sekunden; groessere Luecken werden ignoriert

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

    # runden und optional auf die letzten `days` Tage beschraenken
    for day in result:
        for c in result[day]:
            result[day][c] = round(result[day][c], 3)
    if days:
        keep = sorted(result.keys())[-days:]
        result = {d: result[d] for d in keep}
    return result


# ----------------------------- Webserver ----------------------------------
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # ruhige Konsole

    def _send(self, code, body, ctype="application/json"):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        route = parsed.path
        if route == "/" or route.startswith("/index"):
            self._send(200, PAGE.replace("__DEVICE_LABEL__", DEVICE_LABEL),
                       "text/html; charset=utf-8")
        elif route == "/data":
            with _lock:
                payload = {"data": _latest["data"], "ts": _latest["ts"],
                           "error": _latest["error"]}
            self._send(200, json.dumps(payload))
        elif route == "/history":
            # Anzahl Punkte aus ?n=... lesen, auf 1..MAX_POINTS begrenzen
            q = urllib.parse.parse_qs(parsed.query)
            try:
                n = int(q.get("n", [MAX_POINTS])[0])
            except (ValueError, TypeError):
                n = MAX_POINTS
            n = max(1, min(n, MAX_POINTS))
            con = sqlite3.connect(DB_FILE)
            rows = con.execute(
                "SELECT dt, electricLevel, solarInputPower, outputHomePower, "
                "outputPackPower, packInputPower "
                "FROM device ORDER BY ts DESC LIMIT ?", (n,)).fetchall()
            con.close()
            rows.reverse()
            self._send(200, json.dumps(rows))
        elif route == "/packhistory":
            # min/max-Spannungsverlauf je Pack, gruppiert nach Seriennummer
            q = urllib.parse.parse_qs(parsed.query)
            try:
                n = int(q.get("n", [MAX_POINTS])[0])
            except (ValueError, TypeError):
                n = MAX_POINTS
            n = max(1, min(n, MAX_POINTS))
            con = sqlite3.connect(DB_FILE)
            sns = [r[0] for r in con.execute(
                "SELECT DISTINCT sn FROM packs WHERE sn IS NOT NULL ORDER BY sn")]
            result = {}
            for sn in sns:
                rows = con.execute(
                    "SELECT dt, minVol, maxVol FROM packs WHERE sn = ? "
                    "ORDER BY ts DESC LIMIT ?", (sn, n)).fetchall()
                rows.reverse()
                result[sn] = rows
            con.close()
            self._send(200, json.dumps(result))
        elif route == "/energy":
            # Tages-Arbeit (kWh) je Sensor; optional ?days=N letzte Tage
            q = urllib.parse.parse_qs(parsed.query)
            days = None
            if "days" in q:
                try:
                    days = max(1, int(q["days"][0]))
                except (ValueError, TypeError):
                    days = None
            try:
                self._send(200, json.dumps(energy_by_day(days)))
            except Exception as e:
                self._send(200, json.dumps({"error": str(e)}))
        else:
            self._send(404, "not found", "text/plain")


# ----------------------------- HTML-Seite ---------------------------------
PAGE = r"""<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Zendure Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root{--bg:#0f1115;--card:#1a1d24;--soft:#22262f;--txt:#e7e9ee;--mut:#9aa0ac;
        --acc:#3b82f6;--solar:#f59e0b;--ok:#22c55e;--err:#ef4444;--bd:#2c3038;}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--txt);font:15px/1.5 system-ui,Segoe UI,Roboto,sans-serif;padding:18px;max-width:1000px;margin:0 auto}
  header{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;flex-wrap:wrap;gap:10px}
  h1{font-size:19px;font-weight:600}
  .sub{font-size:13px;color:var(--mut)}
  .badge{font-size:12px;padding:5px 12px;border-radius:8px;background:rgba(34,197,94,.15);color:var(--ok)}
  .badge.bad{background:rgba(239,68,68,.15);color:var(--err)}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:18px}
  .stat{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:14px 16px}
  .stat .lbl{font-size:12px;color:var(--mut);margin-bottom:6px}
  .stat .val{font-size:23px;font-weight:600}
  .bar{height:6px;background:var(--soft);border-radius:3px;margin-top:9px;overflow:hidden}
  .bar > div{height:100%;background:var(--acc);transition:width .4s}
  .panel{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:16px;margin-bottom:18px}
  .panel h2{font-size:14px;font-weight:600;margin-bottom:12px}
  .panelhead{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}
  .panelhead h2{margin-bottom:0}
  .rangesel{display:flex;gap:4px}
  .rbtn{font:inherit;font-size:12px;padding:4px 12px;border:1px solid var(--bd);background:var(--soft);color:var(--mut);border-radius:6px;cursor:pointer}
  .rbtn:hover{color:var(--txt)}
  .rbtn.active{background:var(--acc);border-color:var(--acc);color:#fff}
  .legend{display:flex;gap:16px;font-size:12px;color:var(--mut);margin-bottom:8px;flex-wrap:wrap}
  .legend span{display:flex;align-items:center;gap:5px}
  .legend .leg{cursor:pointer;user-select:none;padding:2px 4px;border-radius:4px}
  .legend .leg:hover{background:var(--soft)}
  .legend .leg.off{opacity:.4;text-decoration:line-through}
  .dot{width:10px;height:10px;border-radius:2px;display:inline-block}
  .chartwrap{position:relative;height:260px}
  .packs{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
  .pack{background:var(--soft);border-radius:10px;padding:12px}
  .pack h3{font-size:13px;font-weight:600;margin-bottom:8px}
  .row{display:flex;justify-content:space-between;font-size:13px;margin:4px 0}
  .row .m{color:var(--mut)}
</style></head>
<body>
<header>
  <div><h1 id="title">Zendure</h1><div class="sub" id="meta">verbinde …</div></div>
  <span class="badge" id="status">verbinde …</span>
</header>

<div class="grid">
  <div class="stat"><div class="lbl">Ladestand</div><div class="val"><span id="soc">–</span>%</div><div class="bar"><div id="socbar" style="width:0"></div></div></div>
  <div class="stat"><div class="lbl">Solar ein</div><div class="val"><span id="solar">–</span> W</div></div>
  <div class="stat"><div class="lbl">Ausgang Haus</div><div class="val"><span id="out">–</span> W</div></div>
  <div class="stat"><div class="lbl">Akku laden</div><div class="val"><span id="packin">–</span> W</div></div>
  <div class="stat"><div class="lbl">Akku entladen</div><div class="val"><span id="packout">–</span> W</div></div>
  <div class="stat"><div class="lbl">Netz ein</div><div class="val"><span id="grid">–</span> W</div></div>
  <div class="stat"><div class="lbl">Temperatur</div><div class="val"><span id="temp">–</span> °C</div></div>
  <div class="stat"><div class="lbl">Batteriespannung</div><div class="val"><span id="volt">–</span> V</div></div>
  <div class="stat"><div class="lbl">WLAN (RSSI)</div><div class="val"><span id="rssi">–</span> dBm</div></div>
</div>

<div class="panel">
  <div class="panelhead">
    <h2>Leistungsverlauf</h2>
    <div class="rangesel">
      <button class="rbtn" data-n="200">200</button>
      <button class="rbtn" data-n="400">400</button>
      <button class="rbtn" data-n="600">600</button>
    </div>
  </div>
  <div class="legend">
    <span class="leg" data-ds="0"><i class="dot" style="background:#f59e0b"></i>Solar W</span>
    <span class="leg" data-ds="1"><i class="dot" style="background:#3b82f6"></i>Ausgang W</span>
    <span class="leg" data-ds="2"><i class="dot" style="background:#a855f7"></i>Akku laden W</span>
    <span class="leg" data-ds="3"><i class="dot" style="background:#ef4444"></i>Akku entladen W (−)</span>
    <span class="leg" data-ds="4"><i class="dot" style="background:#22c55e"></i>SoC %</span>
  </div>
  <div class="chartwrap"><canvas id="chart"></canvas></div>
</div>

<div class="panel">
  <h2>Energiefluss (live)</h2>
  <div style="width:100%; overflow:hidden;">
  <svg id="flow" viewBox="0 0 600 320" style="width:100%; height:auto; font-family:inherit;">
    <defs>
      <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0,0 L10,5 L0,10 z" fill="#9aa0ac"/>
      </marker>
      <marker id="arrA" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0,0 L10,5 L0,10 z" fill="#3b82f6"/>
      </marker>
      <marker id="arrP" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M0,0 L10,5 L0,10 z" fill="#a855f7"/>
      </marker>
    </defs>

    <line id="l_solar" x1="120" y1="78"  x2="262" y2="140" stroke="#3a3f49" stroke-width="2.5" marker-end="url(#arr)"/>
    <line id="l_grid"  x1="120" y1="242" x2="262" y2="180" stroke="#3a3f49" stroke-width="2.5" marker-end="url(#arr)"/>
    <line id="l_home"  x1="338" y1="140" x2="480" y2="78"  stroke="#3a3f49" stroke-width="2.5" marker-end="url(#arr)"/>
    <line id="l_pack"  x1="338" y1="180" x2="480" y2="242" stroke="#3a3f49" stroke-width="2.5" marker-end="url(#arr)"/>

    <text id="t_solar" x="175" y="100" fill="#9aa0ac" font-size="13" text-anchor="middle">0 W</text>
    <text id="t_grid"  x="175" y="223" fill="#9aa0ac" font-size="13" text-anchor="middle">0 W</text>
    <text id="t_home"  x="425" y="100" fill="#9aa0ac" font-size="13" text-anchor="middle">0 W</text>
    <text id="t_pack"  x="425" y="223" fill="#9aa0ac" font-size="13" text-anchor="middle">0 W</text>

    <g>
      <rect x="40" y="44" width="80" height="64" rx="10" fill="#1a1d24" stroke="#2c3038"/>
      <text x="80" y="72" fill="#f59e0b" font-size="13" text-anchor="middle">Solar</text>
      <text x="80" y="92" fill="#e7e9ee" font-size="13" text-anchor="middle" id="n_solar">0 W</text>
    </g>
    <g>
      <rect x="40" y="208" width="80" height="64" rx="10" fill="#1a1d24" stroke="#2c3038"/>
      <text x="80" y="236" fill="#9aa0ac" font-size="13" text-anchor="middle">Netz</text>
      <text x="80" y="256" fill="#e7e9ee" font-size="13" text-anchor="middle" id="n_grid">0 W</text>
    </g>
    <g>
      <rect x="252" y="126" width="96" height="68" rx="10" fill="#22262f" stroke="#3b82f6"/>
      <text x="300" y="152" fill="#e7e9ee" font-size="13" text-anchor="middle">__DEVICE_LABEL__</text>
      <text x="300" y="172" fill="#9aa0ac" font-size="12" text-anchor="middle" id="n_soc">– %</text>
    </g>
    <g>
      <rect x="480" y="44" width="80" height="64" rx="10" fill="#1a1d24" stroke="#2c3038"/>
      <text x="520" y="72" fill="#3b82f6" font-size="13" text-anchor="middle">Haus</text>
      <text x="520" y="92" fill="#e7e9ee" font-size="13" text-anchor="middle" id="n_home">0 W</text>
    </g>
    <g>
      <rect x="480" y="208" width="80" height="64" rx="10" fill="#1a1d24" stroke="#2c3038"/>
      <text x="520" y="231" fill="#a855f7" font-size="13" text-anchor="middle">Akku</text>
      <text x="520" y="250" fill="#e7e9ee" font-size="13" text-anchor="middle" id="n_pack">– %</text>
      <text x="520" y="266" fill="#9aa0ac" font-size="10" text-anchor="middle" id="n_packcount"></text>
    </g>
  </svg>
  </div>
  <p style="font-size:12px;color:var(--mut);margin-top:6px;">Akku-Pfeil zeigt zum Akku beim Laden, zum __DEVICE_LABEL__ beim Entladen.</p>
</div>

<div class="panel">
  <h2>Arbeit heute (kWh)</h2>
  <div class="grid" id="energytiles" style="margin-bottom:16px;">
    <div class="stat"><div class="lbl">Solar</div><div class="val"><span id="e_solar">–</span></div></div>
    <div class="stat"><div class="lbl">Haus</div><div class="val"><span id="e_home">–</span></div></div>
    <div class="stat"><div class="lbl">Netz</div><div class="val"><span id="e_grid">–</span></div></div>
    <div class="stat"><div class="lbl">Akku geladen</div><div class="val"><span id="e_charge">–</span></div></div>
    <div class="stat"><div class="lbl">Akku entladen</div><div class="val"><span id="e_discharge">–</span></div></div>
  </div>
  <div class="legend">
    <span><i class="dot" style="background:#f59e0b"></i>Solar</span>
    <span><i class="dot" style="background:#3b82f6"></i>Haus</span>
    <span><i class="dot" style="background:#9aa0ac"></i>Netz</span>
    <span><i class="dot" style="background:#a855f7"></i>geladen</span>
    <span><i class="dot" style="background:#ef4444"></i>entladen</span>
  </div>
  <div class="chartwrap" style="height:220px;"><canvas id="echart"></canvas></div>
  <p style="font-size:12px;color:var(--mut);margin-top:6px;">Berechnet aus den Leistungswerten (Näherung). Reicht so weit zurück wie die DB Daten vorhält (siehe RETENTION_DAYS).</p>
</div>

<div class="panel">
  <h2>Akku-Packs</h2>
  <div class="packs" id="packs"></div>
</div>

<div class="panel">
  <h2>Zellspannungen je Pack (Verlauf)</h2>
  <div class="legend">
    <span><i class="dot" style="background:#3b82f6"></i>min V</span>
    <span><i class="dot" style="background:#f59e0b"></i>max V</span>
  </div>
  <div id="packcharts"></div>
</div>

<script>
let chart;
function initChart(){
  chart = new Chart(document.getElementById('chart'),{
    type:'line',
    data:{labels:[],datasets:[
      {label:'Solar W',yAxisID:'y',data:[],borderColor:'#f59e0b',backgroundColor:'rgba(245,158,11,.12)',borderWidth:2,tension:.3,pointRadius:0,fill:true},
      {label:'Ausgang W',yAxisID:'y',data:[],borderColor:'#3b82f6',backgroundColor:'rgba(59,130,246,.12)',borderWidth:2,tension:.3,pointRadius:0,fill:true},
      {label:'Akku laden W',yAxisID:'y',data:[],borderColor:'#a855f7',borderWidth:2,tension:.3,pointRadius:0},
      {label:'Akku entladen W',yAxisID:'y',data:[],borderColor:'#ef4444',borderWidth:2,tension:.3,pointRadius:0},
      {label:'SoC %',yAxisID:'y1',data:[],borderColor:'#22c55e',borderWidth:2,borderDash:[5,3],tension:.3,pointRadius:0}
    ]},
    options:{responsive:true,maintainAspectRatio:false,animation:false,
      plugins:{legend:{display:false}},
      scales:{
        y:{grid:{color:c=>c.tick.value===0?'#5a6172':'#2c3038'},ticks:{color:'#9aa0ac'},title:{display:true,text:'Watt (Akku: + laden / − entladen)',color:'#9aa0ac'}},
        y1:{position:'right',min:0,max:100,grid:{drawOnChartArea:false},ticks:{color:'#9aa0ac'},title:{display:true,text:'%',color:'#9aa0ac'}},
        x:{grid:{color:'#2c3038'},ticks:{color:'#9aa0ac',maxTicksLimit:8}}
      }}
  });
}
function initLegend(){
  document.querySelectorAll('.legend .leg').forEach(function(el){
    el.addEventListener('click',function(){
      var i=+el.dataset.ds;
      var vis=chart.isDatasetVisible(i);
      chart.setDatasetVisibility(i,!vis);
      el.classList.toggle('off',vis);
      chart.update();
    });
  });
}
function setStatus(ok,txt){const s=document.getElementById('status');s.textContent=txt;s.className='badge'+(ok?'':' bad');}
function fmtTime(iso){return new Date(iso).toLocaleTimeString('de-DE',{hour:'2-digit',minute:'2-digit'});}

let pointCount=200;  // aktuell gewaehlte Anzahl Datenpunkte (Standard: kleinste Stufe)

function initRange(){
  document.querySelectorAll('.rbtn').forEach(function(b){
    if(+b.dataset.n===pointCount) b.classList.add('active');
    b.addEventListener('click',function(){
      pointCount=+b.dataset.n;
      document.querySelectorAll('.rbtn').forEach(x=>x.classList.toggle('active',x===b));
      loadHistory();
      loadPackHistory();
    });
  });
}

async function loadHistory(){
  try{
    const r=await fetch('/history?n='+pointCount);const rows=await r.json();
    chart.data.labels=rows.map(x=>fmtTime(x[0]));
    chart.data.datasets[0].data=rows.map(x=>x[2]); // Solar
    chart.data.datasets[1].data=rows.map(x=>x[3]); // Ausgang
    chart.data.datasets[2].data=rows.map(x=>x[4]); // Akku laden (outputPackPower)
    chart.data.datasets[3].data=rows.map(x=>x[5]==null?null:-x[5]); // Akku entladen negativ (packInputPower)
    chart.data.datasets[4].data=rows.map(x=>x[1]); // SoC
    chart.update();
  }catch(e){}
}

let packCharts={};  // sn -> Chart-Objekt

function makePackChart(canvas){
  return new Chart(canvas,{
    type:'line',
    data:{labels:[],datasets:[
      {label:'min V',data:[],borderColor:'#3b82f6',borderWidth:2,tension:.3,pointRadius:0},
      {label:'max V',data:[],borderColor:'#f59e0b',borderWidth:2,tension:.3,pointRadius:0}
    ]},
    options:{responsive:true,maintainAspectRatio:false,animation:false,
      plugins:{legend:{display:false}},
      scales:{
        y:{grid:{color:'#2c3038'},ticks:{color:'#9aa0ac'},title:{display:true,text:'Volt',color:'#9aa0ac'}},
        x:{grid:{color:'#2c3038'},ticks:{color:'#9aa0ac',maxTicksLimit:6}}
      }}
  });
}

async function loadPackHistory(){
  try{
    const r=await fetch('/packhistory?n='+pointCount);const data=await r.json();
    const container=document.getElementById('packcharts');
    const sns=Object.keys(data);
    // Container fuer neue/unbekannte Packs anlegen
    sns.forEach(function(sn,idx){
      if(!packCharts[sn]){
        const wrap=document.createElement('div');
        wrap.style.marginBottom='14px';
        const title=document.createElement('div');
        title.style.cssText='font-size:13px;color:var(--mut);margin-bottom:4px';
        title.textContent='Pack '+(idx+1)+' · '+sn;
        const cw=document.createElement('div');
        cw.className='chartwrap';cw.style.height='180px';
        const cv=document.createElement('canvas');
        cw.appendChild(cv);wrap.appendChild(title);wrap.appendChild(cw);
        container.appendChild(wrap);
        packCharts[sn]=makePackChart(cv);
      }
      const rows=data[sn];
      const c=packCharts[sn];
      c.data.labels=rows.map(x=>fmtTime(x[0]));
      c.data.datasets[0].data=rows.map(x=>x[1]==null?null:x[1]/100); // min V
      c.data.datasets[1].data=rows.map(x=>x[2]==null?null:x[2]/100); // max V
      c.update();
    });
  }catch(e){}
}

let echart;
function initEnergyChart(){
  echart=new Chart(document.getElementById('echart'),{
    type:'bar',
    data:{labels:[],datasets:[
      {label:'Solar',data:[],backgroundColor:'#f59e0b'},
      {label:'Haus',data:[],backgroundColor:'#3b82f6'},
      {label:'Netz',data:[],backgroundColor:'#9aa0ac'},
      {label:'geladen',data:[],backgroundColor:'#a855f7'},
      {label:'entladen',data:[],backgroundColor:'#ef4444'}
    ]},
    options:{responsive:true,maintainAspectRatio:false,animation:false,
      plugins:{legend:{display:false}},
      scales:{
        y:{beginAtZero:true,grid:{color:'#2c3038'},ticks:{color:'#9aa0ac'},title:{display:true,text:'kWh',color:'#9aa0ac'}},
        x:{grid:{color:'#2c3038'},ticks:{color:'#9aa0ac'}}
      }}
  });
}

async function loadEnergy(){
  try{
    const r=await fetch('/energy');const data=await r.json();
    if(data.error) return;
    const days=Object.keys(data).sort();
    const keys=['solar','home','grid','charge','discharge'];
    // Balkendiagramm
    echart.data.labels=days.map(d=>d.slice(5)); // MM-DD
    keys.forEach(function(k,idx){
      echart.data.datasets[idx].data=days.map(d=>data[d][k]);
    });
    echart.update();
    // Kacheln fuer heute (letzter Tag)
    const today=days[days.length-1];
    const fmt=v=>(v==null?'–':v.toFixed(2)+' kWh');
    if(today){
      document.getElementById('e_solar').textContent=fmt(data[today].solar);
      document.getElementById('e_home').textContent=fmt(data[today].home);
      document.getElementById('e_grid').textContent=fmt(data[today].grid);
      document.getElementById('e_charge').textContent=fmt(data[today].charge);
      document.getElementById('e_discharge').textContent=fmt(data[today].discharge);
    }
  }catch(e){}
}

async function refresh(){
  try{
    const r=await fetch('/data');const j=await r.json();
    if(j.error||!j.data){setStatus(false,'Fehler: '+(j.error||'keine Daten'));return;}
    const p=j.data.properties,packs=j.data.packData||[];
    setStatus(true,'Live · '+fmtTime(new Date(j.ts*1000).toISOString()));
    const prod=j.data.product||'Zendure';
    document.getElementById('title').textContent=prod;
    document.title=prod;
    document.getElementById('meta').textContent='SN '+(j.data.sn||'–')+' · v'+(j.data.version||'?');
    const set=(id,v)=>document.getElementById(id).textContent=v;
    set('soc',p.electricLevel); document.getElementById('socbar').style.width=p.electricLevel+'%';
    set('solar',p.solarInputPower); set('out',p.outputHomePower); set('grid',p.gridInputPower);
    set('packin',p.outputPackPower); set('packout',p.packInputPower);
    set('temp',((p.hyperTmp-2731)/10).toFixed(1)); set('volt',(p.BatVolt/100).toFixed(2));
    set('rssi',p.rssi);
    updateFlow(p, packs);

    document.getElementById('packs').innerHTML=packs.map((pk,i)=>`
      <div class="pack"><h3>Pack ${i+1} ${pk.sn?'· '+pk.sn:''}</h3>
        <div class="row"><span class="m">Ladestand</span><span>${pk.socLevel}%</span></div>
        <div class="row"><span class="m">Leistung</span><span>${pk.power} W</span></div>
        <div class="row"><span class="m">Spannung</span><span>${(pk.totalVol/100).toFixed(2)} V</span></div>
        <div class="row"><span class="m">Max. Temp.</span><span>${((pk.maxTemp-2731)/10).toFixed(1)} °C</span></div>
        <div class="row"><span class="m">Zelle min</span><span>${(pk.minVol/100).toFixed(2)} V</span></div>
        <div class="row"><span class="m">Zelle max</span><span>${(pk.maxVol/100).toFixed(2)} V</span></div>
        <div class="row"><span class="m">Zelldifferenz</span><span>${(pk.maxVol-pk.minVol)*10} mV</span></div>
      </div>`).join('');
  }catch(e){setStatus(false,'Server nicht erreichbar');}
}

function updateFlow(p, packs){
  const svg=document.getElementById('flow'); if(!svg) return;
  const W=v=>(v||0)+' W';
  // Knoten-Werte
  document.getElementById('n_solar').textContent=W(p.solarInputPower);
  document.getElementById('n_grid').textContent=W(p.gridInputPower);
  document.getElementById('n_home').textContent=W(p.outputHomePower);
  document.getElementById('n_soc').textContent=(p.electricLevel!=null?p.electricLevel+' %':'– %');
  document.getElementById('n_pack').textContent=(p.electricLevel!=null?p.electricLevel+' %':'– %');
  // Pack-Anzahl nur anzeigen, wenn mehr als ein Pack vorhanden
  const cnt=(packs||[]).length;
  document.getElementById('n_packcount').textContent = cnt>1 ? cnt+' Packs' : '';

  // Pfeil-Beschriftungen
  const charge=p.outputPackPower||0, discharge=p.packInputPower||0;
  document.getElementById('t_solar').textContent=W(p.solarInputPower);
  document.getElementById('t_grid').textContent=W(p.gridInputPower);
  document.getElementById('t_home').textContent=W(p.outputHomePower);

  // Hilfsfunktion: Linie aktiv (farbig) oder inaktiv (grau) schalten
  function setLine(id,active){
    const l=document.getElementById(id);
    l.setAttribute('stroke', active?'#3b82f6':'#3a3f49');
    l.setAttribute('marker-end', active?'url(#arrA)':'url(#arr)');
  }
  setLine('l_solar',(p.solarInputPower||0)>0);
  setLine('l_grid',(p.gridInputPower||0)>0);
  setLine('l_home',(p.outputHomePower||0)>0);

  // Akku: laden -> Pfeil zum Akku (Standard), entladen -> Pfeil zum SF2400 (umdrehen)
  const pl=document.getElementById('l_pack');
  if(discharge>0){
    pl.setAttribute('x1','480'); pl.setAttribute('y1','242');
    pl.setAttribute('x2','338'); pl.setAttribute('y2','180');
    pl.setAttribute('stroke','#a855f7'); pl.setAttribute('marker-end','url(#arrP)');
    document.getElementById('t_pack').textContent=W(discharge);
  } else {
    pl.setAttribute('x1','338'); pl.setAttribute('y1','180');
    pl.setAttribute('x2','480'); pl.setAttribute('y2','242');
    pl.setAttribute('stroke', charge>0?'#a855f7':'#3a3f49');
    pl.setAttribute('marker-end', charge>0?'url(#arrP)':'url(#arr)');
    document.getElementById('t_pack').textContent=W(charge);
  }
}

initChart();
initLegend();
initRange();
initEnergyChart();
loadHistory().then(refresh);
loadPackHistory();
loadEnergy();
setInterval(refresh, 5000);
setInterval(loadHistory, 60000);
setInterval(loadPackHistory, 60000);
setInterval(loadEnergy, 300000);
</script>
</body></html>
"""


# ----------------------------- Main ---------------------------------------
def main():
    threading.Thread(target=poll_loop, daemon=True).start()
    threading.Thread(target=cleanup_loop, daemon=True).start()
    srv = ThreadingHTTPServer(("0.0.0.0", WEB_PORT), Handler)
    log_always(f"Dashboard:  http://localhost:{WEB_PORT}")
    if USE_SIGNAL:
        send_signal("\u2705 Zendure-Watchdog gestartet")
    log_always("Beenden mit Strg+C")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        log_always("\nGestoppt.")


if __name__ == "__main__":
    main()