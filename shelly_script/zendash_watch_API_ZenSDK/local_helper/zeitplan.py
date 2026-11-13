"""
zeitplan.py - Entlade-Zeitplan fuer den Zendure Dashboard Proxy
================================================================
Optionales Modul neben zendure_proxy.py (wie ts_bridge.py). Fehlt die
Datei, laeuft der Proxy ohne Zeitplan weiter.

Ein gemeinsamer Plan fuer alle Geraete: In den Entladefenstern darf
entladen werden, ausserhalb ist Entladen gesperrt. Geschaltet wird ueber
das Shelly-Script (kvs_set_api, Key zdmc_devN_dischargeAllowed) - an den
Shelly-Scripten selbst aendert sich nichts.

Regeln (je Geraet):
  - Geschaltet wird nur zu den Planzeiten (Flanke). Was dazwischen von Hand
    umgestellt wird, bleibt bis zum naechsten Wechsel stehen.
  - Sperren klappt immer.
  - Freigeben nur, wenn die schwaechste Zelle ueber minVoltReset des
    Watchdogs liegt (sonst ist dessen Unterspannungssperre noch nicht wieder
    scharf). Sonst neuer Versuch alle zwei Minuten, solange das Fenster offen ist.
  - Der Zeitplan braucht den Watchdog (watchdog.enabled) und schaltet nur
    Geraete mit watch:true. Er liest dessen Werte mit (status_api?bg=read,
    kein eigener Poll der Speicher); geprueft wird alle zwei Minuten, an den
    Planzeiten sofort.
  - Manuelles Laden (dischargeAllowed 0, reverse 0, inputLimit > 0): Der
    Plan laesst das Geraet bis zum naechsten Wechsel in Ruhe.
  - Voller Akku (socLimit 1) waehrend einer Plansperre: freigeben, damit
    Solarstrom durchkommt. Ist er nicht mehr voll und gibt der Akku selbst
    mehr als FULL_RELOCK_W ab (PV reicht nicht mehr), wird wieder gesperrt.
  - Nach einem Neustart des Proxys greift der Plan beim naechsten Wechsel,
    nach dem Speichern eines geaenderten Plans sofort.

Massgeblich ist die Uhrzeit des Rechners, auf dem der Proxy laeuft.
Endpunkte (im Proxy verdrahtet): GET /zeitplan (Seite), GET /schedule
(Plan + Zustand), POST /schedule (Plan speichern, nur JSON).
"""

import datetime
import json
import os
import re
import threading
import time

SCHEDULE_FILE = "zendure_schedule_config.json"

LOG = True
_say = print            # vom Proxy gesetzt
_get = None             # vom Proxy gesetzt: _get(endpoint, query, timeout) -> bytes
_data_dir = "."

CONFIG_TIMEOUT = 10
STATUS_TIMEOUT = 5
KVS_SET_TIMEOUT = 25
CHECK_S = 120           # zwischen den Planzeiten: so oft pruefen (voll, Zellspannung, Hand)
CACHE_CONFIG_S = 45     # config_api vom Dashboard (alle 32 s) gilt so lange als aktuell
CACHE_EDGE_S = 10       # an einer Planzeit: nur ganz frische config_api nutzen
CACHE_STATUS_S = 30     # status_api vom Dashboard gilt so lange als aktuell
CACHE_IDLE_S = 600      # Plan aus: Geraeteliste nur so oft auffrischen
TICK_OFFSET_S = 3       # Sekunden nach der vollen Minute
MAX_WINDOWS = 20
MAX_DEVICES = 64

RE_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

_lock = threading.RLock()
_wake = threading.Event()
_thread = None

PLAN = {"enabled": False, "windows": [], "excluded": []}

# Laufzeitzustand, nur im Speicher
_rt = {
    "prev_allowed": None,   # Planzustand beim letzten Takt (None = noch keiner)
    "apply_now": False,     # nach dem Speichern sofort anwenden
    "devices": {},          # id -> {"owned", "pending", "reason", "want"}
    "cfg": None, "cfg_at": 0.0,
    "status": None, "status_at": 0.0,
    "last_write_at": 0.0,
    "last_run": None, "error": None,
    "last_check": 0.0,      # monotonic des letzten Pruefens
    "no_watchdog": False,   # Watchdog aus: Plan schaltet nicht
}


# ---------------------------------------------------------------
# Hilfen
# ---------------------------------------------------------------
def _log(msg):
    if LOG:
        _say("[zeitplan] " + msg)


def _err(msg):
    _say("[zeitplan] " + msg)


_note = _err            # Schaltvorgaenge: immer ins Log, auch mit -q


def _path():
    return os.path.join(_data_dir, SCHEDULE_FILE)


def _to_min(hhmm):
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _fmt(m):
    m %= 1440
    return "%02d:%02d" % (m // 60, m % 60)


def _prev_day(d):
    return 7 if d == 1 else d - 1


def plan_active(plan=None):
    p = plan or PLAN
    return bool(p.get("enabled")) and bool(p.get("windows"))


def allowed_at(plan, day, minute):
    """day: 1 = Mo ... 7 = So. Fenster ueber Mitternacht zaehlen zum Starttag."""
    for w in plan.get("windows", []):
        f, t = _to_min(w["from"]), _to_min(w["to"])
        days = w["days"]
        if f < t:
            if day in days and f <= minute < t:
                return True
        else:
            if day in days and minute >= f:
                return True
            if _prev_day(day) in days and minute < t:
                return True
    return False


def _now():
    n = datetime.datetime.now()
    return n.isoweekday(), n.hour * 60 + n.minute, n


def next_change(plan, day, minute):
    """Naechster Wechsel ab jetzt: (minute_des_tages, tage_voraus) oder None."""
    if not plan_active(plan):
        return None
    cur = allowed_at(plan, day, minute)
    for k in range(1, 8 * 1440 + 1):
        m = minute + k
        add = m // 1440
        d = day
        for _ in range(add):
            d = 1 if d == 7 else d + 1
        if allowed_at(plan, d, m % 1440) != cur:
            return m % 1440, add
    return None


def validate(data):
    """Prueft einen Plan aus dem Browser. (plan, None) oder (None, Fehlertext)."""
    if not isinstance(data, dict):
        return None, "Ungueltige Daten"
    enabled = data.get("enabled")
    if not isinstance(enabled, bool):
        return None, "enabled fehlt"
    windows = data.get("windows")
    if not isinstance(windows, list) or len(windows) > MAX_WINDOWS:
        return None, "Fensterliste ungueltig (hoechstens %d)" % MAX_WINDOWS
    out = []
    for w in windows:
        if not isinstance(w, dict):
            return None, "Fenster ungueltig"
        f, t, days = w.get("from"), w.get("to"), w.get("days")
        if not (isinstance(f, str) and RE_HHMM.match(f) and isinstance(t, str) and RE_HHMM.match(t)):
            return None, "Zeit ungueltig (HH:MM)"
        if f == t:
            return None, "Start und Ende sind gleich"
        if not isinstance(days, list) or not days:
            return None, "Mindestens ein Wochentag"
        clean = sorted(set(d for d in days if isinstance(d, int) and not isinstance(d, bool) and 1 <= d <= 7))
        if len(clean) != len(set(days)):
            return None, "Wochentag ungueltig (1 = Mo ... 7 = So)"
        out.append({"from": f, "to": t, "days": clean})
    out.sort(key=lambda w: _to_min(w["from"]))
    excluded = data.get("excluded", [])
    if not isinstance(excluded, list) or len(excluded) > MAX_DEVICES:
        return None, "excluded ungueltig"
    ex = sorted(set(e for e in excluded if isinstance(e, int) and not isinstance(e, bool) and 0 <= e < MAX_DEVICES))
    if len(ex) != len(set(excluded)):
        return None, "excluded ungueltig"
    return {"enabled": enabled, "windows": out, "excluded": ex}, None


# ---------------------------------------------------------------
# Laden / Speichern
# ---------------------------------------------------------------
def _load():
    global PLAN
    try:
        with open(_path(), encoding="utf-8") as fh:
            plan, error = validate(json.load(fh))
        if plan is not None:
            PLAN = plan
        else:
            _err("Plandatei ungueltig ({}) - Zeitplan aus".format(error))
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as e:
        _err("Plandatei nicht lesbar ({}) - Zeitplan aus".format(e))


def _save(plan):
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, indent=1)
    os.replace(tmp, _path())


def handle_post(data):
    """POST /schedule. Gibt (ok, fehler) zurueck."""
    global PLAN
    plan, error = validate(data)
    if plan is None:
        return False, error
    try:
        _save(plan)
    except OSError as e:
        return False, "Speichern nicht moeglich: {}".format(e)
    with _lock:
        PLAN = plan
        _rt["apply_now"] = plan_active(plan)
        if not plan_active(plan):
            _rt["prev_allowed"] = None
            _rt["devices"] = {}
    _note("Plan gespeichert: " + describe(plan))
    _wake.set()
    return True, None


def describe(plan=None):
    p = plan or PLAN
    if not p["enabled"]:
        return "aus"
    if not p["windows"]:
        return "an, aber kein Fenster - tut nichts"
    return "an, " + ", ".join("{}-{} ({})".format(w["from"], w["to"], ",".join(str(d) for d in w["days"]))
                              for w in p["windows"]) + \
        (" - ohne Geraet " + ",".join(str(e) for e in p["excluded"]) if p["excluded"] else "")


# ---------------------------------------------------------------
# Mitlesen: Antworten, die das Dashboard ohnehin ueber den Proxy holt
# ---------------------------------------------------------------
def feed(endpoint, body):
    try:
        data = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, AttributeError):
        return
    now = time.monotonic()
    with _lock:
        if endpoint == "config_api" and isinstance(data, dict) and "devices" in data:
            # Eine Antwort, die vor unserem letzten Schreiben angefragt wurde,
            # kann noch den alten Wert tragen - erst danach wieder uebernehmen.
            if now - _rt["last_write_at"] > CONFIG_TIMEOUT:
                _rt["cfg"], _rt["cfg_at"] = data, now
        elif endpoint == "status_api" and isinstance(data, dict) and "hubs" in data:
            _rt["status"], _rt["status_at"] = data, now


RE_DEV_KEY = re.compile(r"^zdmc_dev(\d+)_(dischargeAllowed|reverse|inputLimit)$")


def feed_kvs(query, body):
    """Erfolgreiches kvs_set_api aus dem Dashboard: die geschriebenen
    Geraetewerte gleich im Zwischenspeicher nachziehen, damit die naechste
    Pruefung nicht mit einem veralteten Schalterstand arbeitet."""
    try:
        from urllib.parse import parse_qs
        res = json.loads(body.decode("utf-8"))
        if not (isinstance(res, dict) and res.get("success") is True):
            return
        data = json.loads(parse_qs(query).get("data", [""])[0])
    except (ValueError, UnicodeDecodeError, AttributeError):
        return
    if not isinstance(data, dict):
        return
    with _lock:
        devs = {d.get("id"): d for d in ((_rt["cfg"] or {}).get("devices") or [])}
        for k, v in data.items():
            m = RE_DEV_KEY.match(str(k))
            if not m or int(m.group(1)) not in devs:
                continue
            d = devs[int(m.group(1))]
            if m.group(2) == "inputLimit":
                try:
                    d["inputLimit"] = float(v)
                except (TypeError, ValueError):
                    pass
            else:
                d[m.group(2)] = bool(int(v)) if str(v).lstrip("-").isdigit() else bool(v)


def _fetch_json(endpoint, query, timeout):
    return json.loads(_get(endpoint, query, timeout).decode("utf-8"))


def _config(max_age=CACHE_CONFIG_S):
    with _lock:
        if _rt["cfg"] is not None and time.monotonic() - _rt["cfg_at"] < max_age:
            return _rt["cfg"]
    cfg = _fetch_json("config_api", "", CONFIG_TIMEOUT)
    if not isinstance(cfg, dict) or not isinstance(cfg.get("devices"), list):
        raise RuntimeError("config_api ohne Geraeteliste")
    with _lock:
        _rt["cfg"], _rt["cfg_at"] = cfg, time.monotonic()
    return cfg


def _status():
    """Nur lesen (bg=read): die Werte, die der Watchdog alle intervalSec
    holt bzw. das offene Dashboard. Kein zusaetzlicher Poll der Speicher."""
    with _lock:
        if _rt["status"] is not None and time.monotonic() - _rt["status_at"] < CACHE_STATUS_S:
            return _rt["status"]
    st = _fetch_json("status_api", "bg=read", STATUS_TIMEOUT)
    with _lock:
        _rt["status"], _rt["status_at"] = st, time.monotonic()
    return st


# ---------------------------------------------------------------
# Entscheidung je Geraet
# ---------------------------------------------------------------
def _manual(d):
    return (not d.get("dischargeAllowed")) and (not d.get("reverse")) and float(d.get("inputLimit") or 0) > 0


def _volt_ok(d, hub, wd):
    """Darf freigegeben werden? (Watchdog an und watch:true sind Voraussetzung,
    siehe evaluate.)"""
    reset = wd.get("minVoltReset")
    if not isinstance(reset, (int, float)):
        return True                              # aelteres Script ohne Schwellen
    mv = (hub or {}).get("minVol")
    if not isinstance(mv, (int, float)) or mv <= 0:
        return False                             # unbekannt: warten
    return mv / 100.0 > reset


FULL_RELOCK_W = 30      # Akku gibt mehr als das ab -> Freigabe "voll" zuruecknehmen


def _pack_discharging(hub):
    """Entlaedt der Akku selbst (packInputPower)? Ohne Messwert: nein."""
    p = (hub or {}).get("packIn")
    return isinstance(p, (int, float)) and p > FULL_RELOCK_W


def evaluate(plan, cfg, status, allowed, edge, rt_devices):
    """Reine Entscheidung ohne Ein-/Ausgabe (auch fuer Tests).
    Aendert rt_devices und gibt {id: 0/1} zurueck, was geschrieben werden soll."""
    writes = {}
    wd = cfg.get("watchdog") or {}
    if not wd.get("enabled"):
        rt_devices.clear()                       # ohne Watchdog schaltet der Plan nicht
        return writes
    hubs = {h.get("id"): h for h in ((status or {}).get("hubs") or []) if isinstance(h, dict)}
    for d in cfg.get("devices") or []:
        i = d.get("id")
        if not isinstance(i, int):
            continue
        if i in plan["excluded"] or not d.get("watch"):
            rt_devices.pop(i, None)              # nicht im Plan bzw. vom Watchdog nicht ueberwacht
            continue
        r = rt_devices.setdefault(i, {"owned": True, "pending": False, "reason": None, "want": None})
        da = bool(d.get("dischargeAllowed"))
        hub = hubs.get(i) or {}
        soc_limit = hub.get("socLimit")

        if edge:
            r.update({"owned": True, "pending": False, "reason": None, "want": None})
            if _manual(d):
                r.update({"owned": False, "reason": "manual"})
            elif not allowed:
                if soc_limit == 1:
                    r.update({"owned": False, "reason": "full"})   # gar nicht erst sperren
                    if not da:
                        r["want"] = 1
                elif da:
                    r["want"] = 0
            else:
                if not da:
                    if _volt_ok(d, hub, wd):
                        r["want"] = 1
                    else:
                        r["pending"] = True
        elif r["owned"]:
            if _manual(d):
                r.update({"owned": False, "pending": False, "reason": "manual", "want": None})
            elif r["want"] is not None:
                pass                                 # Schreiben fehlgeschlagen: erneut
            elif not allowed:
                if soc_limit == 1:
                    r.update({"owned": False, "reason": "full"})
                    if not da:
                        r["want"] = 1
                elif da:
                    r.update({"owned": False, "reason": "hand"})
            else:
                if r["pending"]:
                    if da:
                        r["pending"] = False     # schon frei (von Hand)
                    elif _volt_ok(d, hub, wd):
                        r["pending"] = False
                        r["want"] = 1
                elif not da:
                    r.update({"owned": False, "reason": "hand"})
        elif r["reason"] == "hand" and da == allowed and not _manual(d):
            # Von Hand wieder auf den Planstand gestellt: Plan uebernimmt wieder
            r.update({"owned": True, "reason": None})
        elif (r["reason"] == "full" and not allowed and da and not _manual(d)
              and soc_limit != 1 and _pack_discharging(hub)):
            # Freigabe wegen vollem Akku war nur fuer die PV-Durchleitung
            # gedacht. Nicht mehr voll und der Akku gibt selbst ab (PV reicht
            # nicht mehr): Plansperre wieder herstellen. Wird er wieder voll,
            # gibt der naechste Durchlauf erneut frei.
            r.update({"owned": True, "reason": None, "want": 0})
        elif r["want"] is not None and _manual(d):
            r["want"] = None

        if r["want"] is not None and r["want"] != (1 if da else 0):
            writes[i] = r["want"]
        elif r["want"] is not None:
            r["want"] = None
    return writes


def _write(writes, cfg):
    data = {"zdmc_dev{}_dischargeAllowed".format(i): v for i, v in sorted(writes.items())}
    query = "data=" + _quote(json.dumps(data, separators=(",", ":")))
    with _lock:
        _rt["last_write_at"] = time.monotonic()
    try:
        res = _fetch_json("kvs_set_api", query, KVS_SET_TIMEOUT)
        ok = isinstance(res, dict) and res.get("success") is True
    except Exception as e:
        ok = False
        _err("Schreiben fehlgeschlagen ({}) - neuer Versuch in einer Minute".format(e))
    labels = {d.get("id"): d.get("label") for d in cfg.get("devices") or []}
    with _lock:
        _rt["last_write_at"] = time.monotonic()
        for i, v in writes.items():
            r = _rt["devices"].get(i)
            if ok:
                if r is not None:
                    r["want"] = None
                for d in (_rt["cfg"] or {}).get("devices") or []:
                    if d.get("id") == i:
                        d["dischargeAllowed"] = bool(v)
                _note("{}: Entladen {}".format(labels.get(i, "dev%d" % i), "freigegeben" if v else "gesperrt"))
        if ok:
            _rt["cfg_at"] = 0.0                  # naechster Takt liest frisch
    return ok


def _quote(s):
    from urllib.parse import quote
    return quote(s, safe="")


def tick():
    """Ein Durchlauf. Laeuft im Thread einmal pro Minute; zwischen den
    Planzeiten wird nur alle CHECK_S geprueft."""
    day, minute, _ = _now()
    with _lock:
        plan = PLAN
        active = plan_active(plan)
        if not active:
            _rt["prev_allowed"] = None
            _rt["devices"] = {}
            _rt["last_run"] = time.time()
            _rt["error"] = None
            stale = _rt["cfg"] is None or time.monotonic() - _rt["cfg_at"] > CACHE_IDLE_S
        if not active:
            # Nur fuer die Geraeteliste auf /zeitplan, selten
            if stale:
                try:
                    _config()
                except Exception:
                    pass
            return
        allowed = allowed_at(plan, day, minute)
        prev = _rt["prev_allowed"]
        edge = _rt["apply_now"] or (prev is not None and prev != allowed)
        retry = any(r["want"] is not None for r in _rt["devices"].values())
        due = time.monotonic() - _rt["last_check"] >= CHECK_S - 5
        if not (edge or due or retry or prev is None):
            return                                   # zwischen den Planzeiten: alle zwei Minuten
    try:
        cfg = _config(CACHE_EDGE_S if edge else CACHE_CONFIG_S)
        status = _status()
    except Exception as e:
        with _lock:
            _rt["error"] = str(e)[:200]
            _rt["last_run"] = time.time()
        _err("Shelly nicht erreichbar: {}".format(e))
        return                                       # Flanke bleibt offen: naechster Takt
    with _lock:
        if edge:
            _note("Wechsel: Entladen {} ({:s})".format("erlaubt" if allowed else "gesperrt", _fmt(minute)))
        writes = evaluate(plan, cfg, status, allowed, edge, _rt["devices"])
        no_wd = not (cfg.get("watchdog") or {}).get("enabled")
        if no_wd and not _rt["no_watchdog"]:
            _err("Watchdog im zendash-Script ist aus - der Zeitplan schaltet nicht")
        _rt["no_watchdog"] = no_wd
        _rt["prev_allowed"] = allowed
        _rt["apply_now"] = False
        _rt["error"] = None
        _rt["last_run"] = time.time()
        _rt["last_check"] = time.monotonic()
    if writes:
        _write(writes, cfg)


def _loop(stop):
    while not stop.is_set():
        try:
            tick()
        except Exception as e:                       # nie den Thread verlieren
            _err("Fehler im Ablauf: {}".format(e))
        now = time.time()
        nxt = (int(now // 60) + 1) * 60 + TICK_OFFSET_S
        _wake.clear()
        while not stop.is_set() and time.time() < nxt:
            if _wake.wait(min(5, max(0.1, nxt - time.time()))):
                break


def start(data_dir, get, say=print):
    """Vom Proxy beim Start aufgerufen. get(endpoint, query, timeout) -> bytes."""
    global _data_dir, _get, _say, _thread
    _data_dir, _get, _say = data_dir, get, say
    _load()
    _note("Plan " + describe())
    stop = threading.Event()
    _thread = threading.Thread(target=_loop, args=(stop,), name="zeitplan", daemon=True)
    _thread.start()


# ---------------------------------------------------------------
# GET /schedule
# ---------------------------------------------------------------
def state():
    day, minute, now = _now()
    with _lock:
        plan = json.loads(json.dumps(PLAN))
        active = plan_active(plan)
        allowed = allowed_at(plan, day, minute) if active else None
        nc = next_change(plan, day, minute)
        cfg = _rt["cfg"] or {}
        wd_on = bool((cfg.get("watchdog") or {}).get("enabled")) if cfg else None
        # Erreichbarkeit nur zur Anzeige: Am Verhalten aendert "offline"
        # nichts (Sperren geht ueber die KVS, Freigeben wartet auf minVol).
        online = {h.get("id"): h.get("online") for h in ((_rt["status"] or {}).get("hubs") or [])
                  if isinstance(h, dict)}
        devices = []
        for d in cfg.get("devices") or []:
            i = d.get("id")
            if not isinstance(i, int):
                continue
            follows = i not in plan["excluded"]
            r = _rt["devices"].get(i)
            if not plan["enabled"]:
                st = "off"
            elif not plan["windows"]:
                st = "empty"
            elif not follows:
                st = "excluded"
            elif wd_on is False:
                st = "nowd"
            elif not d.get("watch"):
                st = "nowatch"
            elif online.get(i) is False:
                st = "offline"
            elif r is None:
                st = "unknown"
            elif not r["owned"]:
                st = r["reason"] or "hand"
            elif allowed and r["pending"]:
                st = "volt"
            else:
                st = "free" if allowed else "locked"
            devices.append({"id": i, "label": d.get("label"), "follows": follows, "state": st,
                            "dischargeAllowed": bool(d.get("dischargeAllowed"))})
        return {
            "version": 1,
            "plan": plan,
            "active": active,
            "allowed": allowed,
            "now": _fmt(minute), "weekday": day,
            "next": ({"time": _fmt(nc[0]), "days": nc[1]} if nc else None),
            "devices": devices,
            "error": _rt["error"],
            "watchdog": wd_on,
            "lastRun": (time.strftime("%H:%M:%S", time.localtime(_rt["last_run"])) if _rt["last_run"] else None),
        }


# ---------------------------------------------------------------
# GET /zeitplan - die Seite
# ---------------------------------------------------------------
def page_html():
    return _PAGE


_PAGE = r"""<!DOCTYPE html>
<html lang="de" data-theme="dark">
<script>(function(){var d=document.documentElement,s=null,f=null;
  try{s=localStorage.getItem('zendash_b_theme');f=localStorage.getItem('zendash_b_fontsize');}catch(e){}
  try{if(s!=='dark'&&s!=='light')s=(window.matchMedia&&!window.matchMedia('(prefers-color-scheme: dark)').matches)?'light':'dark';
    d.setAttribute('data-theme',s);}catch(e){}
  f=f||'large';if(f!=='normal')d.setAttribute('data-fontsize',f);})();</script>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0B1220">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" sizes="180x180" href="apple-touch-icon.png">
<link rel="stylesheet" href="fonts.css">
<title>Zendure Grid · Zeitplan</title>
<style>
  :root{ --amber:#F2A93B; --amber-deep:#C97C1D; --teal:#4FD1C5; --teal-deep:#1FA394; --alert:#E2574C;
    --radius-lg:1.25rem; --radius-md:.875rem; --radius-sm:.625rem; --tap:2.75rem; }
  html[data-theme="dark"]{ color-scheme:dark; --bg:#0B1220;
    --bg-glow:radial-gradient(circle at 15% -10%, rgba(79,209,197,0.14), transparent 42%),radial-gradient(circle at 92% 6%, rgba(242,169,59,0.11), transparent 38%);
    --surface:#141E33; --surface-2:#1B2740; --border:rgba(255,255,255,0.08); --text:#EAF0F6; --text-muted:#8B9BB4;
    --shadow:0 10px 30px rgba(0,0,0,0.35), 0 2px 8px rgba(0,0,0,0.25);
    --amber-text:#F2A93B; --teal-text:#4FD1C5; --alert-text:#F0776B;
    --win:rgba(79,209,197,0.30); --win-edge:#4FD1C5; --lock:rgba(139,155,180,0.14); }
  html[data-theme="light"]{ color-scheme:light; --bg:#EEF3F1;
    --bg-glow:radial-gradient(circle at 12% -10%, rgba(79,209,197,0.20), transparent 42%),radial-gradient(circle at 92% 4%, rgba(242,169,59,0.18), transparent 38%);
    --surface:#FFFFFF; --surface-2:#F3F7F6; --border:rgba(15,23,32,0.08); --text:#10192B; --text-muted:#536379;
    --shadow:0 10px 24px rgba(20,30,45,0.10), 0 2px 6px rgba(20,30,45,0.06);
    --amber-text:#8A5608; --teal-text:#1B6F68; --alert-text:#CF2E22;
    --win:rgba(31,163,148,0.28); --win-edge:#1B6F68; --lock:rgba(83,99,121,0.10); }
  *{box-sizing:border-box;} html,body{margin:0;padding:0;}
  html{ font-size:100%; background:var(--bg); }
  html[data-fontsize="large"]{ font-size:115%; } html[data-fontsize="xlarge"]{ font-size:130%; } html[data-fontsize="xxlarge"]{ font-size:150%; }
  body{ font-family:'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; color:var(--text); background:var(--bg); }
  .app{ min-height:100vh; background-image:var(--bg-glow); padding:calc(1.25rem + env(safe-area-inset-top, 0px)) 20px 3.75rem; }
  .shell{ max-width:40rem; margin:0 auto; }
  .num{ font-family:'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace; font-feature-settings:'ss04' 1; font-variant-numeric:tabular-nums; }
  :focus-visible{ outline:2px solid var(--teal-text); outline-offset:3px; }
  h1,h2{ margin:0; font:inherit; }
  header{ display:flex; align-items:center; gap:.75rem; padding:.25rem .25rem 1.25rem; }
  .back{ display:inline-flex; align-items:center; justify-content:center; min-width:var(--tap); height:var(--tap); border-radius:999px;
    background:var(--surface); border:1px solid var(--border); box-shadow:var(--shadow); color:var(--text); text-decoration:none; font-size:1.1rem; }
  .title{ display:flex; flex-direction:column; gap:.15rem; min-width:0; }
  .title .word{ font-family:'IBM Plex Mono', monospace; font-feature-settings:'ss04' 1; font-weight:600; letter-spacing:.14em; text-transform:uppercase; font-size:1.1rem; }
  .title .word span{ color:var(--teal-text); }
  .title .sub{ font-size:.82rem; color:var(--text-muted); }
  .section-title{ font-size:.8rem; color:var(--text-muted); letter-spacing:.08em; text-transform:uppercase; margin:1.75rem .25rem .75rem; }
  .card{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg); box-shadow:var(--shadow); padding:1rem 1.125rem; }
  .row{ display:flex; align-items:center; justify-content:space-between; gap:.75rem; }
  .lbl{ font-size:.95rem; font-weight:600; }
  .hint{ display:block; font-size:.78rem; color:var(--text-muted); margin-top:.2rem; line-height:1.4; }
  .sw-btn{ position:relative; width:3.25rem; height:1.875rem; flex-shrink:0; padding:0; cursor:pointer; border-radius:999px; border:1px solid var(--border); background:var(--surface-2); }
  .sw-btn::after{ content:""; position:absolute; top:.1875rem; left:.1875rem; width:1.375rem; height:1.375rem; border-radius:50%; background:var(--text-muted); transition:transform .2s ease; }
  .sw-btn[aria-checked="true"]{ background:var(--teal-deep); border-color:transparent; }
  .sw-btn[aria-checked="true"]::after{ transform:translateX(1.375rem); background:#fff; }
  .banner{ margin-top:.875rem; padding:.75rem 1rem; border-radius:var(--radius-md); font-size:.84rem; line-height:1.45; background:var(--surface-2); border:1px solid var(--border); }
  .banner.warn{ color:var(--alert-text); }
  .banner[hidden]{ display:none; }
  .dev + .dev{ border-top:1px solid var(--border); margin-top:.875rem; padding-top:.875rem; }
  .dev-head{ display:flex; align-items:center; justify-content:space-between; gap:.75rem; }
  .dev-name{ font-weight:600; font-size:.95rem; }
  .dev-state{ font-size:.82rem; margin-top:.15rem; }
  .st-ok{ color:var(--teal-text); } .st-lock{ color:var(--text-muted); } .st-pause{ color:var(--amber-text); } .st-warn{ color:var(--alert-text); }
  .tl{ position:relative; height:1.5rem; margin-top:.625rem; border-radius:.4rem; background:var(--lock); overflow:hidden; }
  .tl .seg{ position:absolute; top:0; bottom:0; background:var(--win); border-left:2px solid var(--win-edge); }
  .tl .now{ position:absolute; top:-2px; bottom:-2px; width:2px; background:var(--alert-text); }
  .tl.off{ opacity:.35; }
  .ticks{ display:flex; justify-content:space-between; font-size:.68rem; color:var(--text-muted); margin-top:.2rem; }
  .follow{ display:flex; align-items:center; gap:.5rem; font-size:.78rem; color:var(--text-muted); }
  .follow .sw-btn{ transform:scale(.85); }
  .win{ display:flex; align-items:center; justify-content:space-between; gap:.75rem; padding:.75rem 0; cursor:pointer; }
  .win + .win, .win + .edit, .edit + .win{ border-top:1px solid var(--border); }
  .win .t{ font-size:1.05rem; font-weight:600; }
  .win .d{ font-size:.8rem; color:var(--text-muted); margin-top:.1rem; }
  .win .chev{ color:var(--text-muted); font-size:1.1rem; }
  .empty{ font-size:.88rem; color:var(--text-muted); padding:.5rem 0; }
  .edit{ padding:.875rem 0 .375rem; }
  .times{ display:grid; grid-template-columns:minmax(0,1fr) auto minmax(0,1fr); gap:.5rem; align-items:center; }
  .times label{ display:block; font-size:.72rem; color:var(--text-muted); margin-bottom:.2rem; }
  .times .sep{ color:var(--text-muted); padding-top:1rem; }
  input[type="time"]{ width:100%; min-height:var(--tap); padding:0 .625rem; font:inherit; font-size:1rem; color:var(--text); background:var(--surface-2); border:1px solid var(--border); border-radius:var(--radius-sm); }
  .chips{ display:flex; flex-wrap:wrap; gap:.375rem; margin-top:.75rem; }
  .chip{ appearance:none; min-width:2.6rem; min-height:2.4rem; padding:0 .7rem; border-radius:999px; cursor:pointer; font:inherit; font-size:.85rem; font-weight:600; color:var(--text-muted); background:var(--surface-2); border:1px solid var(--border); }
  .chip[aria-pressed="true"]{ background:var(--teal-deep); color:#06201D; border-color:transparent; }
  .presets{ display:flex; gap:.375rem; margin-top:.5rem; flex-wrap:wrap; }
  .preset{ appearance:none; background:none; border:0; padding:.3rem .1rem; cursor:pointer; font:inherit; font-size:.8rem; color:var(--teal-text); text-decoration:underline; text-underline-offset:3px; }
  .note{ font-size:.78rem; color:var(--text-muted); margin-top:.5rem; }
  .err{ font-size:.82rem; color:var(--alert-text); margin-top:.5rem; }
  .err:empty{ display:none; }
  .btns{ display:flex; gap:.5rem; margin-top:.875rem; }
  .btn{ font:inherit; font-size:.88rem; font-weight:600; color:var(--text); background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-sm); min-height:var(--tap); padding:.5rem .875rem; cursor:pointer; flex:1; }
  .btn:active{ transform:scale(.98); }
  .btn.ok{ background:var(--teal-deep); color:#06201D; border-color:transparent; }
  .btn.del{ flex:0 0 auto; color:var(--alert-text); }
  .btn.add{ width:100%; margin-top:.5rem; border-style:dashed; color:var(--teal-text); }
  .btn[hidden]{ display:none; }
  .rules{ margin:0; padding-left:1.1rem; font-size:.84rem; line-height:1.55; color:var(--text-muted); }
  .rules b{ color:var(--text); font-weight:600; }
  .foot{ margin-top:1.25rem; font-size:.75rem; color:var(--text-muted); text-align:center; }
  .savebar{ position:sticky; bottom:calc(.75rem + env(safe-area-inset-bottom, 0px)); margin-top:1.25rem; z-index:5; }
  .savebar .btn{ width:100%; box-shadow:var(--shadow); }
  .savebar[hidden]{ display:none; }
  .toast{ position:fixed; left:50%; bottom:calc(1rem + env(safe-area-inset-bottom, 0px)); z-index:60; transform:translate(-50%, .75rem); max-width:calc(100vw - 32px);
    background:var(--text); color:var(--bg); border-radius:var(--radius-sm); box-shadow:var(--shadow); padding:.625rem 1rem; font-size:.86rem;
    opacity:0; pointer-events:none; transition:opacity .2s ease, transform .2s ease; }
  .toast.show{ opacity:1; transform:translate(-50%, 0); }
</style>
</head>
<body>
<div class="app"><div class="shell">
  <header>
    <a class="back" href="./" id="back">←</a>
    <div class="title"><h1 class="word" id="ttl">Zeit<span>plan</span></h1><div class="sub" data-t="sub"></div></div>
  </header>

  <div class="card">
    <div class="row">
      <span><span class="lbl" id="planLbl" data-t="active"></span><span class="hint" data-t="activeHint"></span></span>
      <button type="button" class="sw-btn" id="planSw" role="switch" aria-checked="false" aria-labelledby="planLbl"></button>
    </div>
    <div class="banner warn" id="errBanner" hidden></div>
    <div class="banner" id="clockBanner" hidden></div>
  </div>

  <h2 class="section-title" data-t="today"></h2>
  <div class="card" id="devices"></div>

  <h2 class="section-title" data-t="windows"></h2>
  <div class="card">
    <div id="windows"></div>
    <button type="button" class="btn add" id="addWin" data-t="add"></button>
  </div>

  <h2 class="section-title" data-t="how"></h2>
  <div class="card"><ul class="rules" id="rules"></ul></div>

  <div class="foot" id="foot"></div>
  <div class="savebar" id="saveBar" hidden><button type="button" class="btn ok" id="saveBtn" data-t="save"></button></div>
</div></div>
<div class="toast" id="toast" role="status" aria-live="polite"></div>

<script>
(function(){
  'use strict';
  var T = {
    de: { sub:'Entladefenster für alle Geräte', back:'Zurück zum Dashboard', active:'Zeitplan aktiv',
      activeHint:'In den Fenstern darf entladen werden, außerhalb ist Entladen gesperrt.',
      today:'Heute', windows:'Entladefenster', how:'So arbeitet der Plan', add:'+ Fenster hinzufügen', save:'Plan speichern',
      empty:'Noch kein Fenster. Ohne Fenster tut der Plan nichts.', from:'Von', to:'Bis', cancel:'Abbrechen', del:'Löschen', ok:'Übernehmen',
      daily:'täglich', wd:'Mo–Fr', we:'Sa, So', night:'über Mitternacht', nightNote:'Geht über Mitternacht und zählt zum Starttag.',
      days:['Mo','Di','Mi','Do','Fr','Sa','So'], daysAria:'Wochentage', follows:'folgt', followsAria:'{d} folgt dem Plan',
      errTime:'Gib Start- und Endzeit ein.', errSame:'Start und Ende sind gleich. Wähle eine andere Endzeit.', errDays:'Wähle mindestens einen Wochentag.',
      stOff:'Zeitplan aus', stEmpty:'Kein Fenster angelegt', stExcluded:'Folgt dem Plan nicht', stUnknown:'Plan · greift ab {w}',
      stFree:'Plan · frei {w}', stLocked:'Plan · gesperrt {w}', stManual:'Plan · pausiert {w} (manuelles Laden)', stFull:'Plan · pausiert {w} (Akku voll)',
      stVolt:'Plan · wartet auf Zellspannung über {v} V', stHand:'von Hand · {w}',
      stOffline:'Plan · Gerät offline', stNoWd:'Plan · schaltet nicht (Watchdog aus)', stNoWatch:'Folgt dem Plan nicht (Watchdog überwacht das Gerät nicht)',
      noWd:'Der Zeitplan braucht den Watchdog im zendash-Script (watchdog.enabled: true). Solange er aus ist, schaltet der Plan nicht.',
      until:'bis {t}', untilTomorrow:'bis morgen {t}', untilDay:'bis {d} {t}', always:'dauerhaft', next:'nächster Wechsel',
      saved:'Plan gespeichert', saveFail:'Nicht gespeichert: {e}', deleted:'Fenster gelöscht', loadFail:'Proxy nicht erreichbar: {e}',
      shelly:'Shelly nicht erreichbar – der Plan kann gerade nicht schalten ({e}).',
      clock:'Uhrzeit des Proxys: {p} – dieses Gerät zeigt {b}. Der Plan richtet sich nach dem Proxy.',
      leave:'Änderungen sind noch nicht gespeichert.',
      foot:'Proxy-Zeit {t} · letzter Durchlauf {r}',
      rules:['Geschaltet wird <b>nur zu den Planzeiten</b>. Was du dazwischen von Hand umstellst, gilt bis zum nächsten Wechsel.',
        '<b>Sperren</b> klappt immer. <b>Freigeben</b> nur, wenn die schwächste Zelle über der Freigabeschwelle des Watchdogs liegt{v}, sonst wird alle zwei Minuten neu versucht.',
        'Der Plan braucht den <b>Watchdog</b> und schaltet nur Geräte, die er überwacht (<span class="num">watch: true</span>). Er nutzt dessen Messwerte und prüft zwischen den Planzeiten alle zwei Minuten.',
        '<b>Manuelles Laden</b> oder <b>voller Akku</b> unterbrechen den Plan für dieses Gerät bis zum nächsten Wechsel. Bei vollem Akku wird freigegeben, damit Solarstrom durchkommt – sobald der Akku danach selbst Strom abgibt, sperrt der Plan wieder.',
        'Der Plan läuft im Proxy und richtet sich nach dessen Uhrzeit. Ist der Proxy aus, bleibt der letzte Zustand stehen. Nach einem Neustart greift er beim nächsten Wechsel.'] },
    en: { sub:'Discharge windows for all devices', back:'Back to the dashboard', active:'Schedule active',
      activeHint:'Discharging is allowed inside the windows and blocked outside them.',
      today:'Today', windows:'Discharge windows', how:'How the schedule works', add:'+ Add window', save:'Save schedule',
      empty:'No window yet. Without a window the schedule does nothing.', from:'From', to:'To', cancel:'Cancel', del:'Delete', ok:'Apply',
      daily:'daily', wd:'Mon–Fri', we:'Sat, Sun', night:'past midnight', nightNote:'Runs past midnight and counts for the start day.',
      days:['Mon','Tue','Wed','Thu','Fri','Sat','Sun'], daysAria:'Weekdays', follows:'follows', followsAria:'{d} follows the schedule',
      errTime:'Enter a start and end time.', errSame:'Start and end are the same. Pick another end time.', errDays:'Pick at least one weekday.',
      stOff:'Schedule off', stEmpty:'No window yet', stExcluded:'Doesn’t follow the schedule', stUnknown:'Schedule · takes over {w}',
      stFree:'Schedule · free {w}', stLocked:'Schedule · blocked {w}', stManual:'Schedule · paused {w} (manual charging)', stFull:'Schedule · paused {w} (battery full)',
      stVolt:'Schedule · waiting for cell voltage above {v} V', stHand:'manual change · {w}',
      stOffline:'Schedule · device offline', stNoWd:'Schedule · not switching (watchdog off)', stNoWatch:'Doesn’t follow the schedule (not monitored by the watchdog)',
      noWd:'The schedule needs the watchdog in the zendash script (watchdog.enabled: true). While it is off, the schedule doesn’t switch.',
      until:'until {t}', untilTomorrow:'until tomorrow {t}', untilDay:'until {d} {t}', always:'permanently', next:'next change',
      saved:'Schedule saved', saveFail:'Not saved: {e}', deleted:'Window deleted', loadFail:'Proxy not reachable: {e}',
      shelly:'Shelly not reachable – the schedule can’t switch right now ({e}).',
      clock:'Proxy time: {p} – this device shows {b}. The schedule follows the proxy.',
      leave:'Changes aren’t saved yet.',
      foot:'Proxy time {t} · last run {r}',
      rules:['Switching happens <b>only at the scheduled times</b>. Anything you change by hand in between stays until the next change.',
        '<b>Blocking</b> always works. <b>Releasing</b> only if the weakest cell is above the watchdog’s release threshold{v}; otherwise it retries every two minutes.',
        'The schedule needs the <b>watchdog</b> and only switches devices it monitors (<span class="num">watch: true</span>). It uses the watchdog’s readings and checks every two minutes between the scheduled times.',
        '<b>Manual charging</b> or a <b>full battery</b> pause the schedule for that device until the next change. With a full battery it releases so solar power gets through – as soon as the battery itself starts discharging, the schedule blocks again.',
        'The schedule runs in the proxy and follows its clock. If the proxy is off, the last state stays. After a restart it takes over at the next change.'] },
    fr: { sub:'Plages de décharge pour tous les appareils', back:'Retour au tableau de bord', active:'Planning actif',
      activeHint:'La décharge est autorisée dans les plages et bloquée en dehors.',
      today:'Aujourd’hui', windows:'Plages de décharge', how:'Fonctionnement du planning', add:'+ Ajouter une plage', save:'Enregistrer le planning',
      empty:'Aucune plage. Sans plage, le planning ne fait rien.', from:'De', to:'À', cancel:'Annuler', del:'Supprimer', ok:'Appliquer',
      daily:'tous les jours', wd:'lun–ven', we:'sam, dim', night:'après minuit', nightNote:'Dépasse minuit et compte pour le jour de début.',
      days:['lun','mar','mer','jeu','ven','sam','dim'], daysAria:'Jours de la semaine', follows:'suit', followsAria:'{d} suit le planning',
      errTime:'Saisis une heure de début et de fin.', errSame:'Début et fin sont identiques. Choisis une autre heure de fin.', errDays:'Choisis au moins un jour.',
      stOff:'Planning arrêté', stEmpty:'Aucune plage', stExcluded:'Ne suit pas le planning', stUnknown:'Planning · actif {w}',
      stFree:'Planning · libre {w}', stLocked:'Planning · bloqué {w}', stManual:'Planning · en pause {w} (charge manuelle)', stFull:'Planning · en pause {w} (batterie pleine)',
      stVolt:'Planning · attend une tension de cellule > {v} V', stHand:'modifié à la main · {w}',
      stOffline:'Planning · appareil hors ligne', stNoWd:'Planning · ne commute pas (watchdog arrêté)', stNoWatch:'Ne suit pas le planning (non surveillé par le watchdog)',
      noWd:'Le planning a besoin du watchdog du script zendash (watchdog.enabled: true). Tant qu’il est arrêté, le planning ne commute pas.',
      until:'jusqu’à {t}', untilTomorrow:'jusqu’à demain {t}', untilDay:'jusqu’à {d} {t}', always:'en permanence', next:'prochain changement',
      saved:'Planning enregistré', saveFail:'Non enregistré\u00a0: {e}', deleted:'Plage supprimée', loadFail:'Proxy injoignable\u00a0: {e}',
      shelly:'Shelly injoignable – le planning ne peut pas commuter ({e}).',
      clock:'Heure du proxy\u00a0: {p} – cet appareil affiche {b}. Le planning suit le proxy.',
      leave:'Les modifications ne sont pas encore enregistrées.',
      foot:'Heure du proxy {t} · dernier passage {r}',
      rules:['La commutation se fait <b>uniquement aux heures prévues</b>. Ce que tu modifies à la main entre-temps reste jusqu’au prochain changement.',
        '<b>Bloquer</b> fonctionne toujours. <b>Libérer</b> seulement si la cellule la plus faible dépasse le seuil de libération du watchdog{v}, sinon nouvel essai toutes les deux minutes.',
        'Le planning a besoin du <b>watchdog</b> et ne commute que les appareils qu’il surveille (<span class="num">watch: true</span>). Il utilise ses mesures et contrôle toutes les deux minutes entre les heures prévues.',
        'La <b>charge manuelle</b> ou une <b>batterie pleine</b> suspendent le planning pour cet appareil jusqu’au prochain changement. Avec une batterie pleine, il libère pour laisser passer le solaire – dès que la batterie se décharge elle-même, le planning bloque à nouveau.',
        'Le planning tourne dans le proxy et suit son horloge. Si le proxy est arrêté, le dernier état reste. Après un redémarrage, il reprend au prochain changement.'] }
  };
  var lang = 'en';
  try { var sv = localStorage.getItem('zendash_lang'); if (T[sv]) lang = sv; else throw 0; }
  catch (e) { var nl = (navigator.languages && navigator.languages.length) ? navigator.languages : [navigator.language || ''];
    for (var li = 0; li < nl.length; li++) { var b = String(nl[li] || '').slice(0, 2).toLowerCase(); if (T[b]) { lang = b; break; } } }
  document.documentElement.setAttribute('lang', lang);
  var L = T[lang];
  function t(k, p){ var s = L[k] || T.de[k] || k; if (p) Object.keys(p).forEach(function(n){ s = s.split('{' + n + '}').join(p[n]); }); return s; }
  function $(id){ return document.getElementById(id); }
  function esc(s){ return String(s == null ? '' : s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  function toMin(s){ var p = s.split(':'); return (+p[0]) * 60 + (+p[1]); }
  function prevDay(d){ return d === 1 ? 7 : d - 1; }
  function fmtV(v){ return String(v).replace('.', lang === 'en' ? '.' : ','); }

  var S = null;          // letzter Stand vom Proxy
  var plan = null;       // Arbeitskopie
  var dirty = false, editIdx = null, draft = null, minVoltReset = null;

  document.querySelectorAll('[data-t]').forEach(function(el){ el.textContent = t(el.getAttribute('data-t')); });
  $('back').setAttribute('aria-label', t('back'));

  function allowedAt(p, day, min){
    for (var i = 0; i < p.windows.length; i++){
      var w = p.windows[i], f = toMin(w.from), to = toMin(w.to);
      if (f < to){ if (w.days.indexOf(day) >= 0 && min >= f && min < to) return true; }
      else { if (w.days.indexOf(day) >= 0 && min >= f) return true; if (w.days.indexOf(prevDay(day)) >= 0 && min < to) return true; }
    }
    return false;
  }
  function segments(p, day){
    var segs = [], st = null;
    for (var m = 0; m <= 1440; m++){
      var a = m < 1440 && allowedAt(p, day, m);
      if (a && st === null) st = m;
      if (!a && st !== null){ segs.push([st, m]); st = null; }
    }
    return segs;
  }
  function whenText(){
    var n = S && S.next;
    if (!n) return t('always');
    if (n.days === 0) return t('until', { t:n.time });
    if (n.days === 1) return t('untilTomorrow', { t:n.time });
    var d = ((S.weekday - 1 + n.days) % 7);
    return t('untilDay', { d:L.days[d], t:n.time });
  }
  function stateLine(dv){
    var w = whenText(), st = dv.state;
    // "von Hand" erkennt der Proxy erst bei seiner Pruefung (alle 2 min) -
    // weicht der Schalter schon ab, gleich so anzeigen
    if (typeof dv.dischargeAllowed === 'boolean' && S && typeof S.allowed === 'boolean') {
      if ((st === 'free' || st === 'locked') && dv.dischargeAllowed !== (st === 'free')) st = 'hand';
      else if (st === 'hand' && dv.dischargeAllowed === S.allowed) st = S.allowed ? 'free' : 'locked';
    }
    switch (st){
      case 'off': return ['st-lock', t('stOff')];
      case 'empty': return ['st-lock', t('stEmpty')];
      case 'excluded': return ['st-lock', t('stExcluded')];
      case 'free': return ['st-ok', t('stFree', { w:w })];
      case 'locked': return ['st-lock', t('stLocked', { w:w })];
      case 'manual': return ['st-pause', t('stManual', { w:w })];
      case 'full': return ['st-pause', t('stFull', { w:w })];
      case 'volt': return ['st-warn', t('stVolt', { v: minVoltReset != null ? fmtV(minVoltReset) : '–' })];
      case 'hand': return ['st-pause', t('stHand', { w:w })];
      case 'nowd': return ['st-warn', t('stNoWd')];
      case 'offline': return ['st-warn', t('stOffline')];
      case 'nowatch': return ['st-lock', t('stNoWatch')];
      default: return ['st-lock', t('stUnknown', { w: S && S.next ? S.next.time : '' })];
    }
  }
  function daysText(days){
    var s = days.slice().sort().join(',');
    if (s === '1,2,3,4,5,6,7') return t('daily');
    if (s === '1,2,3,4,5') return t('wd');
    if (s === '6,7') return t('we');
    return days.slice().sort().map(function(d){ return L.days[d - 1]; }).join(', ');
  }

  function renderDevices(){
    if (!S) return;
    var nowMin = toMin(S.now), html = '';
    var segs = segments(plan, S.weekday);
    var devs = S.devices || [];
    devs.forEach(function(dv){
      var follows = plan.excluded.indexOf(dv.id) < 0;
      var keep = dv.state === 'nowd' || dv.state === 'nowatch' || dv.state === 'offline';
      var shown = dirty ? { state: !plan.enabled ? 'off' : (!plan.windows.length ? 'empty' : (!follows ? 'excluded' : (keep || dv.follows ? dv.state : 'unknown'))) } : dv;
      var st = stateLine(shown);
      html += '<div class="dev"><div class="dev-head"><div><div class="dev-name">' + esc(dv.label) + '</div>' +
        '<div class="dev-state ' + st[0] + '">' + esc(st[1]) + '</div></div>' +
        '<label class="follow">' + esc(t('follows')) + '<button type="button" class="sw-btn" role="switch" data-follow="' + dv.id + '" aria-checked="' + follows + '" aria-label="' + esc(t('followsAria', { d:dv.label })) + '"></button></label></div>' +
        '<div class="tl' + ((!plan.enabled || !follows) ? ' off' : '') + '" aria-hidden="true">';
      segs.forEach(function(s){ html += '<div class="seg" style="left:' + (s[0] / 14.4) + '%;width:' + ((s[1] - s[0]) / 14.4) + '%"></div>'; });
      html += '<div class="now" style="left:' + (nowMin / 14.4) + '%"></div></div>' +
        '<div class="ticks num"><span>0</span><span>6</span><span>12</span><span>18</span><span>24</span></div></div>';
    });
    $('devices').innerHTML = html || '<div class="empty">–</div>';
  }

  function renderWindows(){
    var html = '';
    if (!plan.windows.length && editIdx === null) html = '<div class="empty">' + esc(t('empty')) + '</div>';
    plan.windows.forEach(function(w, i){
      if (i === editIdx) { html += editForm(); return; }
      var night = toMin(w.to) <= toMin(w.from);
      html += '<div class="win" role="button" tabindex="0" data-edit="' + i + '"><div><div class="t num">' + w.from + ' – ' + w.to + '</div>' +
        '<div class="d">' + esc(daysText(w.days)) + (night ? ' · ' + esc(t('night')) : '') + '</div></div><span class="chev" aria-hidden="true">›</span></div>';
    });
    if (editIdx === plan.windows.length) html += editForm();
    $('windows').innerHTML = html;
    $('addWin').hidden = editIdx !== null;
  }
  function editForm(){
    var isNew = editIdx === plan.windows.length, chips = '';
    for (var d = 1; d <= 7; d++) chips += '<button type="button" class="chip" data-day="' + d + '" aria-pressed="' + (draft.days.indexOf(d) >= 0) + '">' + esc(L.days[d - 1]) + '</button>';
    var night = draft.from !== draft.to && toMin(draft.to) <= toMin(draft.from);
    return '<div class="edit">' +
      '<div class="times"><div><label for="fFrom">' + esc(t('from')) + '</label><input type="time" id="fFrom" value="' + draft.from + '"></div>' +
      '<span class="sep">–</span><div><label for="fTo">' + esc(t('to')) + '</label><input type="time" id="fTo" value="' + draft.to + '"></div></div>' +
      '<div class="note" id="fNight"' + (night ? '' : ' hidden') + '>' + esc(t('nightNote')) + '</div>' +
      '<div class="chips" role="group" aria-label="' + esc(t('daysAria')) + '">' + chips + '</div>' +
      '<div class="presets"><button type="button" class="preset" data-preset="all">' + esc(t('daily')) + '</button>' +
      '<button type="button" class="preset" data-preset="wd">' + esc(t('wd')) + '</button><button type="button" class="preset" data-preset="we">' + esc(t('we')) + '</button></div>' +
      '<div class="err" id="fErr"></div>' +
      '<div class="btns"><button type="button" class="btn" id="fCancel">' + esc(t('cancel')) + '</button>' +
      (isNew ? '' : '<button type="button" class="btn del" id="fDel">' + esc(t('del')) + '</button>') +
      '<button type="button" class="btn ok" id="fOk">' + esc(t('ok')) + '</button></div></div>';
  }
  function validate(d){
    if (!/^\d\d:\d\d$/.test(d.from) || !/^\d\d:\d\d$/.test(d.to)) return t('errTime');
    if (d.from === d.to) return t('errSame');
    if (!d.days.length) return t('errDays');
    return '';
  }
  function renderRules(){
    var v = minVoltReset != null ? ' (<span class="num">' + fmtV(minVoltReset) + '</span> V)' : '';
    $('rules').innerHTML = L.rules.map(function(r){ return '<li>' + r.replace('{v}', v) + '</li>'; }).join('');
  }
  function renderBanners(){
    var eb = $('errBanner');
    if (S && S.error && plan.enabled) { eb.textContent = t('shelly', { e:S.error }); eb.hidden = false; }
    else if (S && S.watchdog === false) { eb.textContent = t('noWd'); eb.hidden = false; }
    else eb.hidden = true;
    var cb = $('clockBanner');
    if (S) {
      var n = new Date(), b = n.getHours() * 60 + n.getMinutes(), p = toMin(S.now);
      var diff = Math.abs(b - p); diff = Math.min(diff, 1440 - diff);
      if (diff > 3) { cb.textContent = t('clock', { p:S.now, b:('0' + n.getHours()).slice(-2) + ':' + ('0' + n.getMinutes()).slice(-2) }); cb.hidden = false; }
      else cb.hidden = true;
    }
    $('foot').textContent = S ? t('foot', { t:S.now, r:S.lastRun || '–' }) : '';
  }
  function render(){
    $('planSw').setAttribute('aria-checked', String(!!plan.enabled));
    renderDevices(); renderWindows(); renderRules(); renderBanners();
  }
  function setDirty(v){ dirty = v; $('saveBar').hidden = !v; }

  var toastTimer = null;
  function toast(msg){ var e = $('toast'); e.textContent = msg; e.classList.add('show'); clearTimeout(toastTimer); toastTimer = setTimeout(function(){ e.classList.remove('show'); }, 2600); }

  function load(first){
    return fetch('schedule', { cache:'no-store' }).then(function(r){ if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function(j){
        S = j;
        if (!dirty && editIdx === null) plan = JSON.parse(JSON.stringify(j.plan));
        if (plan) render();
      }).catch(function(e){ if (first) toast(t('loadFail', { e:e.message })); });
  }
  function loadVolt(){
    return fetch('config_api', { cache:'no-store' }).then(function(r){ return r.ok ? r.json() : null; }).then(function(c){
      var w = c && c.watchdog;
      if (w && w.enabled && typeof w.minVoltReset === 'number') minVoltReset = w.minVoltReset;
      // Die Antwort laeuft durch den Proxy - danach kennt er die Geraete und
      // deren aktuellen Schalterstand sicher
      return load(false);
    }).catch(function(){});
  }

  $('planSw').addEventListener('click', function(){ if (!plan) return; plan.enabled = !plan.enabled; setDirty(true); render(); });
  $('devices').addEventListener('click', function(e){
    var b = e.target.closest('[data-follow]'); if (!b || !plan) return;
    var id = +b.getAttribute('data-follow'), i = plan.excluded.indexOf(id);
    if (i >= 0) plan.excluded.splice(i, 1); else { plan.excluded.push(id); plan.excluded.sort(function(a, c){ return a - c; }); }
    setDirty(true); render();
  });
  $('addWin').addEventListener('click', function(){
    if (!plan) return;
    editIdx = plan.windows.length; draft = { from:'17:00', to:'22:00', days:[1,2,3,4,5,6,7] }; renderWindows(); $('fFrom').focus();
  });
  function openEdit(i){ var w = plan.windows[i]; editIdx = i; draft = { from:w.from, to:w.to, days:w.days.slice() }; renderWindows(); }
  $('windows').addEventListener('click', function(e){
    var tg = e.target;
    var row = tg.closest('[data-edit]'); if (row && editIdx === null){ openEdit(+row.getAttribute('data-edit')); return; }
    var chip = tg.closest('[data-day]');
    if (chip){ var d = +chip.getAttribute('data-day'), k = draft.days.indexOf(d);
      if (k >= 0) draft.days.splice(k, 1); else draft.days.push(d);
      chip.setAttribute('aria-pressed', String(k < 0)); $('fErr').textContent = ''; return; }
    var pr = tg.closest('[data-preset]');
    if (pr){ var p = pr.getAttribute('data-preset'); draft.days = p === 'all' ? [1,2,3,4,5,6,7] : p === 'wd' ? [1,2,3,4,5] : [6,7]; renderWindows(); return; }
    if (tg.id === 'fCancel'){ editIdx = null; renderWindows(); return; }
    if (tg.id === 'fDel'){ plan.windows.splice(editIdx, 1); editIdx = null; setDirty(true); render(); toast(t('deleted')); return; }
    if (tg.id === 'fOk'){
      var err = validate(draft); if (err){ $('fErr').textContent = err; return; }
      plan.windows[editIdx] = { from:draft.from, to:draft.to, days:draft.days.slice().sort() };
      plan.windows.sort(function(a, c){ return toMin(a.from) - toMin(c.from); });
      editIdx = null; setDirty(true); render();
    }
  });
  $('windows').addEventListener('keydown', function(e){
    var row = e.target.closest && e.target.closest('[data-edit]');
    if (row && (e.key === 'Enter' || e.key === ' ')){ e.preventDefault(); openEdit(+row.getAttribute('data-edit')); }
  });
  $('windows').addEventListener('input', function(e){
    if (e.target.id !== 'fFrom' && e.target.id !== 'fTo') return;
    if (e.target.id === 'fFrom') draft.from = e.target.value; else draft.to = e.target.value;
    $('fErr').textContent = '';
    $('fNight').hidden = !(draft.from && draft.to && draft.from !== draft.to && toMin(draft.to) <= toMin(draft.from));
  });
  $('saveBtn').addEventListener('click', function(){
    var btn = $('saveBtn'); btn.disabled = true;
    fetch('schedule', { method:'POST', headers:{ 'Content-Type':'application/json' }, body: JSON.stringify(plan) })
      .then(function(r){ return r.json(); })
      .then(function(j){
        if (!j.ok) throw new Error(j.error || '?');
        setDirty(false); toast(t('saved'));
        setTimeout(function(){ load(false); }, 800);
      })
      .catch(function(e){ toast(t('saveFail', { e:e.message })); })
      .then(function(){ btn.disabled = false; });
  });
  window.addEventListener('beforeunload', function(e){ if (dirty){ e.preventDefault(); e.returnValue = t('leave'); } });

  load(true).then(loadVolt);
  setInterval(function(){ if (!document.hidden) load(false); }, 30000);
  document.addEventListener('visibilitychange', function(){ if (!document.hidden) load(false); });
})();
</script>
</body>
</html>
"""
