"""
ThingSpeak-Bridge fuer zendure_proxy.py (Skizze, v2)
=====================================================
Regeln:
  * ThingSpeak aktiv  -> zu JEDER vollen Minute geht je Hub ein Update raus,
                         Zeitstempel = volle Minute (created_at).
  * ThingSpeak inaktiv -> die Bridge stellt KEINE Anfrage an die zendash-API.
                         Kein Thread, kein Mitlesen, keine Abfrage.

Datenquelle:
  1. Dashboard offen: mitgelesene status_api-Antworten (keine Zusatzabfrage).
  2. Kein Dashboard:  12 s vor der vollen Minute zwei eigene Abfragen
                      (die erste weckt die Hintergrundabfrage des Scripts,
                      die zweite liefert den frischen Stand).

Gesendet werden die echten Werte der letzten status_api-Antwort vor dem
Sendezeitpunkt (kein Mittelwert, hoechstens ca. 8 s alt).

Feldbelegung je Channel (ein Channel pro Hub):
  field1 electricLevel   (status_api: soc)
  field2 solarInputPower (status_api: pv)
  field3 outputHomePower (status_api: home)
  field4 gridInputPower  (status_api: gridIn)
  field5 packInputPower  (status_api: packIn)
  field6 outputPackPower (status_api: packOut)
  field7 Netzsaldo       (status_api: grid.power)
  field8 frei
home/gridIn/packIn/packOut liefert status_api erst ab der erweiterten
zendash_watch-Version. Fehlen sie, bleiben die Felder einfach leer.
Hub offline oder keine Daten: Eintrag nur mit Status, ohne Feldwerte.
"""

import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request

TS_URL = "https://api.thingspeak.com/update"
CFG_FILE = "zendure_thingspeak_config.json"
KEY_RE = re.compile(r"^[A-Z0-9]{16}$")
FRESH_S = 20        # letzte LIVE-Antwort juenger als das = Dashboard offen
LIVE_S = 14         # Abstand zur vorigen Anfrage < IDLE_MS (15 s) im Script:
                    # nur dann war die Hintergrundabfrage wach und die
                    # Antwort ist frisch. Sonst kam die Anfrage aus der
                    # Pause (z.B. gedrosselter Browser-Tab) und liefert
                    # noch den alten Stand.
PREP_S = 12         # Vorlauf vor der vollen Minute fuer den Fallback
WAKE_WAIT_S = 10    # pollIntervalSec (8 s) + Reserve
RETRY_S = 5
VALUE_FIELDS = (("field2", "pv"), ("field3", "home"), ("field4", "gridIn"),
              ("field5", "packIn"), ("field6", "packOut"))
LOG = True          # vom Proxy gesetzt (aus bei -q / -s); Fehler immer

def _log(msg):
    if LOG:
        print("[thingspeak] " + msg)

_lock = threading.Lock()
_stop = threading.Event()
_thread = None
_fetch = None
_path = None
CFG = {"enabled": False, "channels": {}}
_latest = None      # letzte gueltige status_api-Antwort der laufenden Minute
_last_feed = 0.0    # letzte Antwort ueberhaupt (auch veraltete)
_last_live = 0.0    # letzte Antwort, die als frisch gilt


def _active():
    """Einziges Tor fuer jede Shelly-Abfrage."""
    return bool(CFG.get("enabled")) and bool(CFG.get("channels"))


# ---------------------------------------------------------------
# Konfiguration
# ---------------------------------------------------------------
def _load(app_dir):
    global _path
    _path = os.path.join(app_dir, CFG_FILE)
    try:
        with open(_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        CFG["enabled"] = bool(data.get("enabled"))
        CFG["channels"] = dict(data.get("channels") or {})
    except (OSError, ValueError):
        pass


def _save():
    tmp = _path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(CFG, f)
    os.replace(tmp, _path)


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
    """Letzte Antwort in Feldwerte umsetzen und verbrauchen."""
    global _latest
    with _lock:
        data, _latest = _latest, None
    if data is None:
        return {}
    gd = data.get("grid") or {}
    grid = gd.get("power") if gd.get("online") else None   # Zaehler offline -> leer
    out = {}
    for h in data.get("hubs") or []:
        hid = str(h.get("id"))
        if not h.get("online"):
            out[hid] = {"status": "offline"}
            continue
        f = {"field1": h.get("soc"), "field7": grid}   # soc = electricLevel
        for fld, k in VALUE_FIELDS:
            f[fld] = h.get(k)
        out[hid] = {k: v for k, v in f.items() if isinstance(v, (int, float))}
    return out


# ---------------------------------------------------------------
# Senden
# ---------------------------------------------------------------
def _post(key, fields):
    body = urllib.parse.urlencode(dict(fields, api_key=key)).encode()
    try:
        with urllib.request.urlopen(TS_URL, data=body, timeout=10) as r:
            ans = r.read().decode().strip()
        return ans != "0", ans
    except Exception as e:
        return False, str(e)


def _flush(stamp):
    data = _take()
    created = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(stamp))
    for hid, key in list(CFG["channels"].items()):
        # Pflichtmeldung auch ohne Daten: dann online=0
        fields = dict(data.get(hid) or {"status": "keine Daten"})
        fields["created_at"] = created
        ok, ans = _post(key, fields)
        if not ok and not _stop.wait(RETRY_S):
            ok, ans = _post(key, fields)
        if ok:
            _log("Hub {} {} gesendet (Eintrag {})".format(hid, created, ans))
        else:
            print("[thingspeak] Hub {} {}: verworfen ({})".format(hid, created, ans))


# ---------------------------------------------------------------
# Minutentakt
# ---------------------------------------------------------------
def _fetch_fresh():
    """Fallback ohne Dashboard. Jede Abfrage einzeln hinter _active()."""
    try:
        if not _active():
            return
        _log("kein Dashboard offen - eigene Abfrage status_api (wecken)")
        feed(_fetch())                        # weckt; alter Stand wird verworfen
        if _stop.wait(WAKE_WAIT_S) or not _active():
            return
        _log("eigene Abfrage status_api (frischer Stand)")
        feed(_fetch())
    except Exception as e:
        print("[thingspeak] Shelly nicht erreichbar: {}".format(e))


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


def _apply():
    """Thread an den Konfigurationszustand anpassen."""
    global _thread
    if _active():
        if _thread is None or not _thread.is_alive():
            _stop.clear()
            _take()
            _thread = threading.Thread(target=_loop, daemon=True)
            _thread.start()
            _log("aktiv, Channels fuer Hub " + ", ".join(sorted(CFG["channels"])))
    else:
        if not _stop.is_set():
            _log("inaktiv - keine Abfragen")
        _stop.set()
        _take()


def start(app_dir, fetch_status):
    global _fetch
    _fetch = fetch_status
    _load(app_dir)
    _apply()


# ---------------------------------------------------------------
# Einrichtungsseite /thingspeak
# ---------------------------------------------------------------
def handle_post(data):
    """(ok, fehlertext). Key leer = behalten, "-" = entfernen."""
    new = dict(CFG["channels"])
    for hid, key in (data.get("channels") or {}).items():
        key = (key or "").strip().upper()
        if key == "":
            continue
        if key == "-":
            new.pop(str(hid), None)
            continue
        if not KEY_RE.match(key):
            return False, "Write API Key fuer Hub {} hat nicht das erwartete Format.".format(hid)
        ok, ans = _post(key, {"status": "zendash bridge test"})
        if not ok:
            return False, "ThingSpeak lehnt den Key fuer Hub {} ab ({}).".format(hid, ans)
        new[str(hid)] = key
    CFG["channels"] = new
    CFG["enabled"] = bool(data.get("enabled"))
    _save()
    _apply()
    return True, None


def page_html():
    masked = {h: "****" + k[-4:] for h, k in CFG["channels"].items()}
    state = json.dumps({"enabled": CFG["enabled"], "masked": masked})
    return """<!doctype html><html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ZenDash - ThingSpeak</title>
<style>
 body{background:#0B1220;color:#E5E9F0;font-family:system-ui,sans-serif;max-width:460px;margin:40px auto;padding:0 20px}
 h1{color:#4FD1C5;font-size:1.2rem} label{display:block;margin-top:14px;font-size:.85rem;color:#9AA7BD}
 input[type=text]{width:100%;box-sizing:border-box;padding:9px;border-radius:8px;border:1px solid #2a3750;background:#0B1220;color:#E5E9F0}
 button{margin-top:16px;width:100%;padding:11px;border:0;border-radius:8px;background:#4FD1C5;color:#0B1220;font-weight:600}
 button.sec{background:#1f2b42;color:#E5E9F0} #msg{margin-top:12px} .err{color:#F87171} .ok{color:#4FD1C5} a{color:#4FD1C5}
</style></head><body>
<h1>ThingSpeak-Upload</h1>
<label><input type="checkbox" id="en"> Upload aktiv (jede volle Minute)</label>
<div id="devs"></div>
<button class="sec" id="load">Geraete vom Shelly laden</button>
<button id="btn">Speichern &amp; Keys testen</button>
<div id="msg"></div>
<p><a href="/">&larr; Dashboard</a></p>
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
  fetch('/config_api').then(r=>r.json()).then(function(c){
    devs.innerHTML = c.devices.map(function(d){ return row(d.id, d.label); }).join('');
  }).catch(function(){ msg.className='err'; msg.textContent='Geraeteliste nicht ladbar.'; });
};
btn.onclick = async function(){
  var ch = {}; document.querySelectorAll('[data-id]').forEach(function(i){ ch[i.dataset.id]=i.value; });
  btn.disabled=true; msg.className=''; msg.textContent='Pruefe...';
  var r = await fetch('/thingspeak',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({enabled:en.checked,channels:ch})});
  var d = await r.json(); btn.disabled=false;
  msg.className = d.ok?'ok':'err'; msg.textContent = d.ok?'Gespeichert.':d.error;
  if (d.ok) setTimeout(function(){ location.reload(); }, 800);
};
</script></body></html>"""
