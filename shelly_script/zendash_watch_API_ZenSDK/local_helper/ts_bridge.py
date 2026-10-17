"""
Cloud-Bridge fuer zendure_proxy.py: ThingSpeak und ThingsBoard
==============================================================
Der Dateiname bleibt ts_bridge.py, damit Dockerfile, Build und Anleitungen
unveraendert gelten.

Regeln:
  * Mindestens ein Ziel aktiv -> zu JEDER vollen Minute gehen die Werte an
                                 jedes aktive Ziel, Zeitstempel = volle Minute.
  * Kein Ziel aktiv           -> die Bridge stellt KEINE Anfrage an die
                                 zendash-API. Kein Thread, kein Mitlesen.
  * Die Ziele senden parallel; faellt eines aus, bremst es das andere nicht.

Datenquelle (fuer beide Ziele gemeinsam):
  1. Dashboard offen: mitgelesene status_api-Antworten (keine Zusatzabfrage).
  2. Kein Dashboard:  12 s vor der vollen Minute zwei eigene Abfragen
                      (die erste weckt die Hintergrundabfrage des Scripts,
                      die zweite liefert den frischen Stand).
Gesendet werden die echten Werte der letzten frischen status_api-Antwort
vor dem Sendezeitpunkt (kein Mittelwert, hoechstens ca. 8 s alt).

ThingSpeak - ein Channel pro Hub:
  field1 electricLevel   (soc)          field5 packInputPower  (packIn)
  field2 solarInputPower (pv)           field6 outputPackPower (packOut)
  field3 outputHomePower (home)         field7 Netzsaldo       (grid.power)
  field4 gridInputPower  (gridIn)       field8 minVol in V     (minVol / 100)
  Hub offline oder keine Daten: Eintrag nur mit Status, ohne Feldwerte.

ThingsBoard - ein Geraet pro Hub plus ein Geraet "Netz":
  Hub:  Auswahl aus TB_FIELDS, auf /thingsboard per Haekchen, gilt fuer alle
        Hubs gemeinsam und steht als "fields" in der Config. Ohne "fields"
        (aeltere Config) gelten die Standardwerte: electricLevel,
        solarInputPower, outputHomePower, gridInputPower, packInputPower,
        outputPackPower, minVol (V). Zusaetzlich waehlbar: batteryPower
        (packIn - packOut, + = Akku entlaedt) und offGridPower.
  Netz: gridPower (W, positiv = Bezug), immer
  Fehlende Werte werden weggelassen; Hub offline -> in dieser Minute nichts.
"""

import json
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

TS_URL = "https://api.thingspeak.com/update"
TS_FILE = "zendure_thingspeak_config.json"
TB_FILE = "zendure_thingsboard_config.json"
TB_DEFAULT_HOST = "https://eu.thingsboard.cloud"
TS_KEY_RE = re.compile(r"^[A-Z0-9]{16}$")
TB_TOKEN_RE = re.compile(r"^[A-Za-z0-9_\-.~]{1,128}$")

FRESH_S = 20        # letzte LIVE-Antwort juenger als das = Dashboard offen
LIVE_S = 14         # Abstand zur vorigen Anfrage < IDLE_MS (15 s) im Script:
                    # nur dann war die Hintergrundabfrage wach und die
                    # Antwort ist frisch. Sonst kam die Anfrage aus der
                    # Pause (z.B. gedrosselter Browser-Tab) und liefert
                    # noch den alten Stand.
PREP_S = 12         # Vorlauf vor der vollen Minute fuer den Fallback
WAKE_WAIT_S = 10    # pollIntervalSec (8 s) + Reserve
RETRY_S = 5
SEND_WAIT_S = 40    # so lange wartet der Takt hoechstens auf beide Sender

# status_api-Schluessel -> ThingSpeak-Feld (fest, ThingsBoard siehe TB_FIELDS)
HUB_VALUES = (
    ("soc",     "field1"),
    ("pv",      "field2"),
    ("home",    "field3"),
    ("gridIn",  "field4"),
    ("packIn",  "field5"),
    ("packOut", "field6"),
)
GRID_TB_KEY = "gridPower"
TB_GRID_ID = "grid"

LOG = True          # vom Proxy gesetzt (aus bei -q / -s); Fehler immer


def _log(tag, msg):
    if LOG:
        print("[{}] {}".format(tag, msg))


def _err(tag, msg):
    print("[{}] {}".format(tag, msg))


_lock = threading.Lock()
_stop = threading.Event()
_thread = None
_fetch = None
_dir = None
TS = {"enabled": False, "channels": {}}
TB = {"enabled": False, "host": TB_DEFAULT_HOST, "tokens": {}, "fields": []}
_latest = None      # letzte frische status_api-Antwort der laufenden Minute
_last_feed = 0.0    # letzte Antwort ueberhaupt (auch veraltete)
_last_live = 0.0    # letzte Antwort, die als frisch gilt


def _ts_active():
    return bool(TS.get("enabled")) and bool(TS.get("channels"))


def _tb_active():
    return bool(TB.get("enabled")) and bool(TB.get("tokens"))


def _active():
    """Einziges Tor fuer jede Shelly-Abfrage."""
    return _ts_active() or _tb_active()


# ---------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------
def _read_json(name):
    try:
        with open(os.path.join(_dir, name), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _write_json(name, obj):
    path = os.path.join(_dir, name)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def _load(app_dir):
    global _dir
    _dir = app_dir
    d = _read_json(TS_FILE)
    TS["enabled"] = bool(d.get("enabled"))
    TS["channels"] = dict(d.get("channels") or {})
    d = _read_json(TB_FILE)
    TB["enabled"] = bool(d.get("enabled"))
    TB["host"] = d.get("host") or TB_DEFAULT_HOST
    TB["tokens"] = dict(d.get("tokens") or {})
    f = d.get("fields")
    TB["fields"] = _tb_norm_fields(f) if isinstance(f, list) else list(TB_DEFAULT_FIELDS)


def _norm_host(h):
    h = (h or "").strip().rstrip("/")
    if not h:
        return TB_DEFAULT_HOST
    if not re.match(r"^https?://", h):
        h = "https://" + h
    return h


# ---------------------------------------------------------------
# Mitlesen (Proxy ruft das nach jedem erfolgreichen status_api auf)
# ---------------------------------------------------------------
def feed(body):
    global _last_feed, _last_live, _latest
    if not _active():
        return
    try:
        data = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return
    if not isinstance(data, dict):
        return
    with _lock:
        now = time.monotonic()
        live = (now - _last_feed) < LIVE_S
        _last_feed = now
        if live:                               # Antwort aus der Pause verwerfen
            _last_live = now
            _latest = data


def _take():
    """Letzte frische Antwort holen und verbrauchen (None = keine)."""
    global _latest
    with _lock:
        data, _latest = _latest, None
    return data


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _grid_power(data):
    gd = (data or {}).get("grid") or {}
    p = gd.get("power")
    return p if gd.get("online") and _num(p) else None    # Zaehler offline -> leer


def _min_vol(h):
    mv = h.get("minVol")                                   # Rohwert, 325 = 3,25 V
    return round(mv / 100, 2) if _num(mv) and mv > 0 else None


def _battery_power(h):
    """Akkuleistung: + = Akku entlaedt, - = Akku laedt (wie Solarflow-Leistung)."""
    pi, po = h.get("packIn"), h.get("packOut")
    return pi - po if _num(pi) and _num(po) else None


# ThingsBoard: waehlbare Werte je Hub, fuer alle Hubs gemeinsam.
# (Name in ThingsBoard, Beschriftung auf /thingsboard, Wert aus dem Hub,
#  Standard an). Reihenfolge = Reihenfolge auf der Seite und in der Config.
TB_FIELDS = (
    ("electricLevel",   "Ladestand (%)",                         lambda h: h.get("soc"),     True),
    ("solarInputPower", "PV-Eingang (W)",                        lambda h: h.get("pv"),      True),
    ("outputHomePower", "Abgabe ans Haus (W)",                   lambda h: h.get("home"),    True),
    ("gridInputPower",  "Aufnahme aus dem Netz (W)",             lambda h: h.get("gridIn"),  True),
    ("packInputPower",  "Entladen aus dem Akku (W)",             lambda h: h.get("packIn"),  True),
    ("outputPackPower", "Laden in den Akku (W)",                 lambda h: h.get("packOut"), True),
    ("minVol",          "Niedrigste Zellspannung (V)",           _min_vol,                   True),
    ("batteryPower",    "Akkuleistung (W, + entlaedt, - laedt)", _battery_power,             False),
    ("offGridPower",    "Offgrid-Leistung (W)",                  lambda h: h.get("offGrid"), False),
)
TB_DEFAULT_FIELDS = [f[0] for f in TB_FIELDS if f[3]]


def _tb_norm_fields(names):
    """Nur bekannte Namen, ohne Doppel, in Katalog-Reihenfolge."""
    wanted = set(n for n in names if isinstance(n, str))
    return [f[0] for f in TB_FIELDS if f[0] in wanted]


# ---------------------------------------------------------------
# ThingSpeak
# ---------------------------------------------------------------
def _ts_post(key, fields):
    body = urllib.parse.urlencode(dict(fields, api_key=key)).encode()
    try:
        with urllib.request.urlopen(TS_URL, data=body, timeout=10) as r:
            ans = r.read().decode().strip()
        return ans != "0", ans
    except Exception as e:
        return False, str(e)


def _ts_fields(data):
    out = {}
    if data is None:
        return out
    grid = _grid_power(data)
    for h in data.get("hubs") or []:
        hid = str(h.get("id"))
        if not h.get("online"):
            out[hid] = {"status": "offline"}
            continue
        f = {"field7": grid, "field8": _min_vol(h)}
        for key, fld in HUB_VALUES:
            f[fld] = h.get(key)
        out[hid] = {k: v for k, v in f.items() if _num(v)}
    return out


def _ts_send(data, stamp):
    fields_by_hub = _ts_fields(data)
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stamp))
    for hid, key in list(TS["channels"].items()):
        fields = dict(fields_by_hub.get(hid) or {"status": "keine Daten"})
        fields["created_at"] = created
        ok, ans = _ts_post(key, fields)
        if not ok and not _stop.wait(RETRY_S):
            ok, ans = _ts_post(key, fields)
        if ok:
            _log("thingspeak", "Hub {} {} gesendet (Eintrag {})".format(hid, created, ans))
        else:
            _err("thingspeak", "Hub {} {}: verworfen ({})".format(hid, created, ans))


# ---------------------------------------------------------------
# ThingsBoard
# ---------------------------------------------------------------
def _tb_post(host, token, kind, payload):
    """kind = 'telemetry' oder 'attributes'. Erfolg = HTTP 200."""
    url = "{}/api/v1/{}/{}".format(host, urllib.parse.quote(token, safe=""), kind)
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200, "HTTP {}".format(r.status)
    except urllib.error.HTTPError as e:
        return False, "HTTP {}".format(e.code)          # 401 = Token falsch
    except Exception as e:
        return False, str(e)


def _tb_values(data):
    """Werte pro Geraet: {hub-id: {...}, 'grid': {...}}; leere weglassen."""
    out = {}
    if data is None:
        return out
    sel = set(TB["fields"])
    for h in data.get("hubs") or []:
        if not h.get("online"):
            continue                                    # offline -> nichts
        v = {name: get(h) for name, _, get, _ in TB_FIELDS if name in sel}
        v = {k: x for k, x in v.items() if _num(x)}
        if v:
            out[str(h.get("id"))] = v
    g = _grid_power(data)
    if g is not None:
        out[TB_GRID_ID] = {GRID_TB_KEY: g}
    return out


def _tb_send(data, stamp):
    values = _tb_values(data)
    host = TB["host"]
    ts_ms = int(stamp * 1000)
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stamp))
    for dev, token in list(TB["tokens"].items()):
        name = "Netz" if dev == TB_GRID_ID else "Hub " + dev
        v = values.get(dev)
        if not v:
            _log("thingsboard", "{} {}: keine Daten (offline oder nicht geliefert)".format(name, created))
            continue
        payload = {"ts": ts_ms, "values": v}
        ok, ans = _tb_post(host, token, "telemetry", payload)
        if not ok and not _stop.wait(RETRY_S):
            ok, ans = _tb_post(host, token, "telemetry", payload)
        if ok:
            _log("thingsboard", "{} {} gesendet ({} Wert{})".format(name, created, len(v), "" if len(v) == 1 else "e"))
        else:
            _err("thingsboard", "{} {}: verworfen ({})".format(name, created, ans))


# ---------------------------------------------------------------
# Minutentakt
# ---------------------------------------------------------------
def _flush(stamp):
    data = _take()
    senders = []
    if _ts_active():
        senders.append(threading.Thread(target=_ts_send, args=(data, stamp), daemon=True))
    if _tb_active():
        senders.append(threading.Thread(target=_tb_send, args=(data, stamp), daemon=True))
    for t in senders:
        t.start()
    for t in senders:                         # parallel, keiner bremst den anderen
        t.join(SEND_WAIT_S)


def _fetch_fresh():
    """Fallback ohne Dashboard. Jede Abfrage einzeln hinter _active()."""
    try:
        if not _active():
            return
        _log("bridge", "kein Dashboard offen - eigene Abfrage status_api (wecken)")
        feed(_fetch())                        # weckt; alter Stand wird verworfen
        if _stop.wait(WAKE_WAIT_S) or not _active():
            return
        _log("bridge", "eigene Abfrage status_api (frischer Stand)")
        feed(_fetch())
    except Exception as e:
        _err("bridge", "Shelly nicht erreichbar: {}".format(e))


def _loop():
    while not _stop.is_set():
        now = time.time()
        boundary = (int(now // 60) + 1) * 60
        if boundary - now < PREP_S:           # zu knapp -> naechste Minute
            boundary += 60
        if _stop.wait(boundary - PREP_S - time.time()):
            break
        if not _active():
            break
        if time.monotonic() - _last_live > FRESH_S:
            _fetch_fresh()
        if _stop.wait(max(0, boundary - time.time())) or not _active():
            break
        _flush(boundary)


def _describe():
    parts = []
    if _ts_active():
        parts.append("ThingSpeak (Hub " + ", ".join(sorted(TS["channels"])) + ")")
    if _tb_active():
        devs = ["Netz" if d == TB_GRID_ID else "Hub " + d for d in sorted(TB["tokens"])]
        parts.append("ThingsBoard (" + ", ".join(devs) + "; je Hub: " + ", ".join(TB["fields"]) + ")")
    return " + ".join(parts)


def _apply():
    """Thread an den Konfigurationszustand anpassen."""
    global _thread
    if _active():
        if _thread is None or not _thread.is_alive():
            _stop.clear()
            _take()
            _thread = threading.Thread(target=_loop, daemon=True)
            _thread.start()
        _log("bridge", "aktiv: " + _describe())
    else:
        if not _stop.is_set():
            _log("bridge", "inaktiv - keine Abfragen")
        _stop.set()
        _take()


def start(app_dir, fetch_status):
    global _fetch
    _fetch = fetch_status
    _load(app_dir)
    _apply()


# ---------------------------------------------------------------
# Einrichtungsseiten
# ---------------------------------------------------------------
def handle_post(data):
    """/thingspeak: (ok, fehlertext). Key leer = behalten, "-" = entfernen."""
    new = dict(TS["channels"])
    for hid, key in (data.get("channels") or {}).items():
        key = (key or "").strip().upper()
        if key == "":
            continue
        if key == "-":
            new.pop(str(hid), None)
            continue
        if not TS_KEY_RE.match(key):
            return False, "Write API Key fuer Hub {} hat nicht das erwartete Format.".format(hid)
        ok, ans = _ts_post(key, {"status": "zendash bridge test"})
        if not ok:
            return False, "ThingSpeak lehnt den Key fuer Hub {} ab ({}).".format(hid, ans)
        new[str(hid)] = key
    TS["channels"] = new
    TS["enabled"] = bool(data.get("enabled"))
    _write_json(TS_FILE, TS)
    _apply()
    return True, None


def handle_post_tb(data):
    """/thingsboard: (ok, fehlertext). Token leer = behalten, "-" = entfernen.
    Bei geaenderter Server-Adresse werden alle Tokens neu geprueft.
    "fields" fehlt = Auswahl behalten; eine geaenderte Auswahl braucht
    keinen Token-Test."""
    host = _norm_host(data.get("host"))
    fields = TB["fields"]
    if "fields" in data:
        if not isinstance(data["fields"], list):
            return False, "Werteauswahl hat nicht das erwartete Format."
        fields = _tb_norm_fields(data["fields"])
        if not fields:
            return False, "Mindestens einen Wert je Speicher auswaehlen."
    new = dict(TB["tokens"])
    changed = {}
    for dev, tok in (data.get("tokens") or {}).items():
        tok = (tok or "").strip()
        dev = str(dev)
        if tok == "":
            continue
        if tok == "-":
            new.pop(dev, None)
            continue
        if not TB_TOKEN_RE.match(tok):
            return False, "Access Token fuer {} enthaelt ungueltige Zeichen.".format(dev)
        new[dev] = tok
        changed[dev] = tok
    if host != TB["host"]:
        changed = dict(new)                      # anderer Server: alle pruefen
    for dev, tok in changed.items():
        name = "Netz" if dev == TB_GRID_ID else "Hub " + dev
        ok, ans = _tb_post(host, tok, "attributes",
                           {"zendashBridgeTest": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        if not ok:
            return False, "ThingsBoard lehnt das Token fuer {} ab ({}).".format(name, ans)
    TB["host"] = host
    TB["tokens"] = new
    TB["fields"] = fields
    TB["enabled"] = bool(data.get("enabled"))
    _write_json(TB_FILE, TB)
    _apply()
    return True, None


_CSS = """
 body{background:#0B1220;color:#E5E9F0;font-family:system-ui,sans-serif;max-width:460px;margin:40px auto;padding:0 20px}
 h1{color:#4FD1C5;font-size:1.2rem} label{display:block;margin-top:14px;font-size:.85rem;color:#9AA7BD}
 input[type=text]{width:100%;box-sizing:border-box;padding:9px;border-radius:8px;border:1px solid #2a3750;background:#0B1220;color:#E5E9F0}
 button{margin-top:16px;width:100%;padding:11px;border:0;border-radius:8px;background:#4FD1C5;color:#0B1220;font-weight:600}
 button.sec{background:#1f2b42;color:#E5E9F0} #msg{margin-top:12px} .err{color:#F87171} .ok{color:#4FD1C5} a{color:#4FD1C5}
 .hint{font-size:.8rem;color:#9AA7BD;margin-top:6px}
 h2{color:#4FD1C5;font-size:1rem;margin-top:24px} label.fld{margin-top:8px;color:#E5E9F0} code{color:#9AA7BD}
"""


def _mask(k):
    return "****" + k[-4:]


def page_html():
    state = json.dumps({"enabled": TS["enabled"],
                        "masked": {h: _mask(k) for h, k in TS["channels"].items()}})
    return """<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ZenDash - ThingSpeak</title><style>""" + _CSS + """</style></head><body>
<h1>ThingSpeak-Upload</h1>
<label><input type="checkbox" id="en"> Upload aktiv (jede volle Minute)</label>
<div id="devs"></div>
<button class="sec" id="load">Geraete vom Shelly laden</button>
<button id="btn">Speichern &amp; Keys testen</button>
<div id="msg"></div>
<p><a href="./">&larr; Dashboard</a> &middot; <a href="thingsboard">ThingsBoard</a></p>
<script>
var S = """ + state + """;
en.checked = S.enabled;
function row(id, label){
  var m = S.masked[String(id)] || 'kein Key';
  return '<label>'+label+' (Hub '+id+') - Write API Key, aktuell: '+m+
    '<input type="text" data-id="'+id+'" placeholder="leer = behalten, - = entfernen"></label>';
}
// Ohne Klick keine Shelly-Abfrage: bekannte Channels aus der Config anzeigen
devs.innerHTML = Object.keys(S.masked).map(function(id){ return row(id, 'Hub'); }).join('');
load.onclick = function(){
  fetch('config_api').then(r=>r.json()).then(function(c){
    devs.innerHTML = c.devices.map(function(d){ return row(d.id, d.label); }).join('');
  }).catch(function(){ msg.className='err'; msg.textContent='Geraeteliste nicht ladbar.'; });
};
btn.onclick = async function(){
  var ch = {}; document.querySelectorAll('[data-id]').forEach(function(i){ ch[i.dataset.id]=i.value; });
  btn.disabled=true; msg.className=''; msg.textContent='Pruefe...';
  var r = await fetch('thingspeak',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({enabled:en.checked,channels:ch})});
  var d = await r.json(); btn.disabled=false;
  msg.className = d.ok?'ok':'err'; msg.textContent = d.ok?'Gespeichert.':d.error;
  if (d.ok) setTimeout(function(){ location.reload(); }, 800);
};
</script></body></html>"""


def page_html_tb():
    state = json.dumps({"enabled": TB["enabled"], "host": TB["host"], "grid": TB_GRID_ID,
                        "masked": {d: _mask(t) for d, t in TB["tokens"].items()},
                        "fields": [{"name": f[0], "label": f[1]} for f in TB_FIELDS],
                        "sel": TB["fields"]})
    return """<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ZenDash - ThingsBoard</title><style>""" + _CSS + """</style></head><body>
<h1>ThingsBoard-Upload</h1>
<label><input type="checkbox" id="en"> Upload aktiv (jede volle Minute)</label>
<label>Server-Adresse
<input type="text" id="host"></label>
<div class="hint">ThingsBoard Cloud EU: https://eu.thingsboard.cloud &middot; eigener Server z. B. http://nas:8080</div>
<div id="devs"></div>
<button class="sec" id="load">Geraete vom Shelly laden</button>
<h2>Werte je Speicher</h2>
<div class="hint">Gilt fuer alle Speicher gleich. Jeder Wert ist pro Speicher und Minute ein Datenpunkt
(Kontingent im Free-Tarif). Das Geraet &bdquo;Netz&ldquo; sendet immer <code>gridPower</code>.</div>
<div id="flds"></div>
<button id="btn">Speichern &amp; Tokens testen</button>
<div id="msg"></div>
<p><a href="./">&larr; Dashboard</a> &middot; <a href="thingspeak">ThingSpeak</a></p>
<script>
var S = """ + state + """;
en.checked = S.enabled; host.value = S.host;
flds.innerHTML = S.fields.map(function(f){
  return '<label class="fld"><input type="checkbox" data-f="'+f.name+'"'+
    (S.sel.indexOf(f.name) >= 0 ? ' checked' : '')+'> '+f.label+' <code>'+f.name+'</code></label>';
}).join('');
function row(id, label){
  var m = S.masked[String(id)] || 'kein Token';
  return '<label>'+label+' - Access Token, aktuell: '+m+
    '<input type="text" data-id="'+id+'" placeholder="leer = behalten, - = entfernen"></label>';
}
function gridRow(){ return row(S.grid, 'Netz (Netzsaldo)'); }
// Ohne Klick keine Shelly-Abfrage: bekannte Geraete aus der Config anzeigen
devs.innerHTML = Object.keys(S.masked).filter(function(id){ return id!==S.grid; })
  .map(function(id){ return row(id, 'Hub '+id); }).join('') + gridRow();
load.onclick = function(){
  fetch('config_api').then(r=>r.json()).then(function(c){
    devs.innerHTML = c.devices.map(function(d){ return row(d.id, d.label+' (Hub '+d.id+')'); }).join('') + gridRow();
  }).catch(function(){ msg.className='err'; msg.textContent='Geraeteliste nicht ladbar.'; });
};
btn.onclick = async function(){
  var tk = {}; document.querySelectorAll('[data-id]').forEach(function(i){ tk[i.dataset.id]=i.value; });
  var fs = []; document.querySelectorAll('[data-f]').forEach(function(c){ if (c.checked) fs.push(c.dataset.f); });
  btn.disabled=true; msg.className=''; msg.textContent='Pruefe...';
  var r = await fetch('thingsboard',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({enabled:en.checked,host:host.value,tokens:tk,fields:fs})});
  var d = await r.json(); btn.disabled=false;
  msg.className = d.ok?'ok':'err'; msg.textContent = d.ok?'Gespeichert.':d.error;
  if (d.ok) setTimeout(function(){ location.reload(); }, 800);
};
</script></body></html>"""
