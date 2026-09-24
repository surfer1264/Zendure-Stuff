#!/usr/bin/env python3
"""
Zendure Dashboard Proxy
=======================
Kleiner lokaler Proxy, nur Python-Standardbibliothek (kein "pip install"
noetig). Loest zwei Probleme, die ein reiner Browser nicht loesen kann:

  1. CORS: die Shelly-Firmware sendet keine CORS-Header, ein direkter
     fetch() vom Dashboard zum Shelly wuerde vom Browser blockiert. Dieser
     Proxy laeuft lokal und spricht das Shelly stattdessen serverseitig an
     - dort gelten keine Browser-CORS-Regeln.
  2. Einrichtung ohne Editor: anders als frueher steht die Shelly-IP nicht
     mehr fest im Quelltext. Fehlt eine gueltige Konfiguration, liefert
     der Proxy unter "/" statt des Dashboards eine kleine Einrichtungsseite
     (IP + Script-ID, Speichern testet die Verbindung gleich mit). Das
     Ergebnis landet in "zendure_proxy_config.json" direkt neben der exe
     bzw. neben diesem Script - unter "/setup" bleibt die Seite jederzeit
     erreichbar, falls sich die Shelly-IP spaeter mal aendert (neues
     Geraet, DHCP-Wechsel).

Als exe gebaut (PyInstaller, --onefile) ist die Dashboard-HTML mit
eingebettet (siehe --add-data im build-and-release.yml-Workflow) -
resource_path() findet sie dann im temporaeren Entpack-Ordner
sys._MEIPASS, im normalen Skriptbetrieb daneben im selben Verzeichnis.
Die Konfigurationsdatei liegt dagegen bewusst NICHT dort, sondern in
app_dir() (siehe unten) - sys._MEIPASS wird bei --onefile bei jedem Start
neu angelegt und danach wieder geloescht, eine dort abgelegte config.json
waere beim naechsten Start unwiderruflich weg.

Start:
    python3 zendure_proxy.py         normal, mit Zugriffsprotokoll
    python3 zendure_proxy.py -q      leise: Startmeldung ja, Zugriffe nein
    python3 zendure_proxy.py -s      still: gar keine Ausgabe (Fehler nach stderr)

Das Zugriffsprotokoll ist im Normalbetrieb recht gespraechig - die Seite
fragt alle 4 Sekunden an. Zum Einrichten ist es hilfreich, im Dauerbetrieb
eher nicht.

Oeffnet beim Start automatisch http://localhost:8000/ im Standardbrowser.
Klappt der Auto-Open nicht (z.B. auf einem Rechner ohne registrierten
Standardbrowser), die Adresse manuell eintragen.

Beenden: Strg+C im Terminal.

Anpassen falls noetig: PORT, BIND_ADDRESS weiter unten. SHELLY_IP und
SHELLY_SCRIPT_ID nicht mehr hier eintragen - das erledigt die
Einrichtungsseite unter /setup.
"""

import http.server
import json
import os
import socket
import sys
import urllib.error
import urllib.request
import webbrowser
import re

# ---------------------------------------------------------------
# Konfiguration - hier anpassen
# ---------------------------------------------------------------
PORT = 8000

# "0.0.0.0" = auf allen Netzwerk-Schnittstellen lauschen (von jedem Rechner
# im selben Netz erreichbar). Fuer "nur dieser Rechner" stattdessen wieder
# "localhost" eintragen.
BIND_ADDRESS = "0.0.0.0"

# Ausgabefreudigkeit. Laesst sich beim Start ueberschreiben:
#   -q / --quiet    kein Zugriffsprotokoll, Startmeldung bleibt
#   -s / --silent   gar keine Ausgabe
# Fehler gehen unabhaengig davon immer nach stderr - ein stiller Proxy, der
# einen kaputten Port verschweigt, waere schwer zu diagnostizieren.
QUIET = False
SILENT = False

HTML_FILENAME = "zendure-dashboard.html"
CONFIG_FILENAME = "zendure_proxy_config.json"

API_ENDPOINTS = ("config_api", "status_api", "kvs_set_api")
TIMEOUT = 5
SETUP_TEST_TIMEOUT = 4

IP_PATTERN = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

# Kleines, selbst gezeichnetes SVG-Icon (Blitz in Teal auf dunklem
# Hintergrund, passend zur Optik des Dashboards). Wird fuer favicon.ico,
# favicon.svg und alle gaengigen Apple-Touch-Icon-Pfade ausgeliefert -
# damit hat der Browser-Tab ein Icon UND die vielen 404-Zeilen im Log
# fuer diese automatischen Anfragen verschwinden.
FAVICON_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="14" fill="#0B1220"/>
<path d="M34 6 L14 34 H28 L24 58 L50 26 H36 Z" fill="#4FD1C5"/>
</svg>"""

ICON_PATHS = (
    "favicon.ico",
    "favicon.svg",
    "apple-touch-icon.png",
    "apple-touch-icon-precomposed.png",
    "apple-touch-icon-120x120.png",
    "apple-touch-icon-120x120-precomposed.png",
)


# ---------------------------------------------------------------
# Pfade - zwei bewusst getrennte Vorstellungen von "hier":
#   resource_path() = mitgelieferte, GEBUENDELTE Datei (Dashboard-HTML).
#                      Bei --onefile im temporaeren sys._MEIPASS, sonst
#                      neben diesem Script. Nur zum LESEN.
#   app_dir()       = Ordner der exe bzw. des Scripts selbst. Hier landet
#                      die Konfiguration - muss exe-Neustarts ueberleben,
#                      sys._MEIPASS tut das nicht.
# ---------------------------------------------------------------
def resource_path(filename):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, filename)


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def config_path():
    return os.path.join(app_dir(), CONFIG_FILENAME)


# ---------------------------------------------------------------
# Konfiguration laden/speichern
# ---------------------------------------------------------------
# Im Speicher gehalten und bei jedem POST /setup ersetzt - kein Neustart
# noetig, damit eine geaenderte Shelly-IP sofort wirkt.
CONFIG = {"shelly_ip": None, "shelly_script_id": None}


def load_config():
    global CONFIG
    try:
        with open(config_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        ip = data.get("shelly_ip")
        sid = data.get("shelly_script_id")
        if isinstance(ip, str) and IP_PATTERN.match(ip) and isinstance(sid, int) and sid >= 0:
            CONFIG = {"shelly_ip": ip, "shelly_script_id": sid}
    except (OSError, ValueError, json.JSONDecodeError):
        pass  # keine oder kaputte Datei - bleibt unkonfiguriert, Setup-Seite greift


def save_config(ip, script_id):
    global CONFIG
    CONFIG = {"shelly_ip": ip, "shelly_script_id": script_id}
    # Erst in eine temporaere Datei schreiben, dann atomar umbenennen -
    # falls der Prozess mitten im Schreiben abbricht (Absturz, Stromausfall),
    # bleibt die alte config.json intakt statt halb geschrieben kaputtzugehen.
    tmp = config_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(CONFIG, f)
    os.replace(tmp, config_path())


def is_configured():
    return CONFIG["shelly_ip"] is not None and CONFIG["shelly_script_id"] is not None


def shelly_base():
    return "http://{}/script/{}/".format(CONFIG["shelly_ip"], CONFIG["shelly_script_id"])


def test_shelly(ip, script_id):
    """Ruft config_api mit den Kandidatenwerten auf. Gibt (True, None) bei
    Erfolg zurueck, sonst (False, <verstaendliche Fehlermeldung>) - damit
    ein Tippfehler in der IP gleich beim Speichern auffaellt statt erst
    beim naechsten Laden des Dashboards."""
    url = "http://{}/script/{}/config_api".format(ip, script_id)
    try:
        with urllib.request.urlopen(url, timeout=SETUP_TEST_TIMEOUT) as resp:
            body = resp.read()
            if resp.status != 200:
                return False, "Shelly antwortet mit Status {}".format(resp.status)
    except urllib.error.HTTPError as e:
        return False, "Shelly antwortet mit Status {} - Script-ID richtig?".format(e.code)
    except urllib.error.URLError as e:
        return False, "Shelly nicht erreichbar unter {}: {}".format(ip, e.reason)
    except Exception as e:
        return False, "Shelly nicht erreichbar: {}".format(e)

    try:
        data = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return False, "Antwort ist kein gueltiges JSON - laeuft unter dieser Script-ID wirklich das API-Script?"
    if not isinstance(data, dict) or "devices" not in data:
        return False, "Antwort sieht nicht nach zendash_api_src.js aus - richtige Script-ID?"
    return True, None


# ---------------------------------------------------------------
# Einrichtungsseite - bewusst als String eingebettet (nicht als eigene
# Datei gebuendelt), damit der PyInstaller-Build nur die Dashboard-HTML
# ueber --add-data mitbekommen muss.
# ---------------------------------------------------------------
def setup_html(message="", ok=None):
    ip = CONFIG["shelly_ip"] or ""
    sid = CONFIG["shelly_script_id"]
    sid = "" if sid is None else str(sid)
    banner = ""
    if not is_configured():
        banner = '<p class="hint">Einmalig einrichten: Shelly-IP und Script-ID des ' \
                 '<code>zendash_api_src.js</code>-Scripts (steht in der Shelly-Scripts-' \
                 '&Uuml;bersicht).</p>'
    msg_class = "ok" if ok else ("err" if ok is False else "")
    return """<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ZenDash Proxy - Einrichtung</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ background:#0B1220; color:#E5E9F0; font-family:system-ui,sans-serif;
          display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0; }}
  .card {{ background:#111a2b; border:1px solid #1f2b42; border-radius:14px;
           padding:28px 32px; max-width:420px; width:calc(100% - 48px); }}
  h1 {{ font-size:1.2rem; margin:0 0 4px; color:#4FD1C5; }}
  p.hint {{ font-size:0.9rem; color:#9AA7BD; line-height:1.4; }}
  label {{ display:block; margin-top:16px; font-size:0.85rem; color:#9AA7BD; }}
  input {{ width:100%; box-sizing:border-box; margin-top:4px; padding:9px 10px;
           border-radius:8px; border:1px solid #2a3750; background:#0B1220;
           color:#E5E9F0; font-size:1rem; }}
  button {{ margin-top:22px; width:100%; padding:11px; border:none; border-radius:8px;
            background:#4FD1C5; color:#0B1220; font-weight:600; font-size:1rem; cursor:pointer; }}
  button:disabled {{ opacity:0.6; cursor:default; }}
  #msg {{ margin-top:14px; font-size:0.9rem; min-height:1.2em; }}
  #msg.ok {{ color:#4FD1C5; }}
  #msg.err {{ color:#F87171; }}
  a {{ color:#4FD1C5; }}
</style></head>
<body>
  <div class="card">
    <h1>ZenDash Proxy</h1>
    {banner}
    <form id="f">
      <label>Shelly-IP<input id="ip" value="{ip}" placeholder="192.168.178.149" required></label>
      <label>Script-ID<input id="sid" value="{sid}" type="number" min="0" placeholder="1" required></label>
      <button id="btn" type="submit">Speichern &amp; testen</button>
    </form>
    <div id="msg" class="{msg_class}">{message}</div>
    {back_link}
  </div>
<script>
document.getElementById('f').addEventListener('submit', async function(e){{
  e.preventDefault();
  var btn = document.getElementById('btn');
  var msg = document.getElementById('msg');
  btn.disabled = true; msg.className = ''; msg.textContent = 'Pruefe Verbindung...';
  try {{
    var r = await fetch('/setup', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{
        shelly_ip: document.getElementById('ip').value.trim(),
        shelly_script_id: Number(document.getElementById('sid').value)
      }})
    }});
    var data = await r.json();
    if (data.ok) {{
      msg.className = 'ok';
      msg.textContent = 'Gespeichert. Weiter zum Dashboard...';
      setTimeout(function(){{ location.href = '/'; }}, 900);
    }} else {{
      msg.className = 'err';
      msg.textContent = data.error || 'Unbekannter Fehler';
      btn.disabled = false;
    }}
  }} catch (err) {{
    msg.className = 'err';
    msg.textContent = 'Netzwerkfehler: ' + err.message;
    btn.disabled = false;
  }}
}});
</script>
</body></html>""".format(
        banner=banner, ip=ip, sid=sid, msg_class=msg_class, message=message,
        back_link='<p style="margin-top:16px"><a href="/">&larr; zurueck zum Dashboard</a></p>' if is_configured() else ""
    )


class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        if QUIET or SILENT:
            return
        print("[proxy] " + (fmt % args))

    def do_GET(self):
        if "?" in self.path:
            path, query = self.path.split("?", 1)
        else:
            path, query = self.path, ""

        endpoint = path.strip("/")

        if endpoint in ICON_PATHS:
            self.serve_favicon()
            return

        if path == "/setup":
            self.serve_setup()
            return

        if path == "/" or path == "":
            if is_configured():
                self.serve_html()
            else:
                self.serve_setup()
            return

        if endpoint in API_ENDPOINTS:
            self.proxy_to_shelly(endpoint, query)
            return

        self.send_error(404, "Nicht gefunden: " + path)

    def do_POST(self):
        if self.path != "/setup":
            self.send_error(404, "Nicht gefunden: " + self.path)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            ip = str(data.get("shelly_ip") or "").strip()
            sid = data.get("shelly_script_id")

            if not IP_PATTERN.match(ip):
                self._json(200, {"ok": False, "error": "Das sieht nicht nach einer IPv4-Adresse aus."})
                return
            if not isinstance(sid, int) or isinstance(sid, bool) or sid < 0:
                self._json(200, {"ok": False, "error": "Script-ID muss eine Zahl sein (siehe Shelly-Scripts-\u00dcbersicht)."})
                return

            ok, error = test_shelly(ip, sid)
            if not ok:
                self._json(200, {"ok": False, "error": error})
                return

            save_config(ip, sid)
            self._json(200, {"ok": True})
        except Exception as e:
            self._json(500, {"ok": False, "error": "Interner Fehler: {}".format(e)})

    def _json(self, status, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_favicon(self):
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml")
        self.send_header("Content-Length", str(len(FAVICON_SVG)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(FAVICON_SVG)

    def serve_setup(self):
        body = setup_html().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def serve_html(self):
        try:
            with open(resource_path(HTML_FILENAME), "rb") as f:
                body = f.read()
        except OSError as e:
            msg = "Dashboard-HTML nicht lesbar ({}): {}".format(resource_path(HTML_FILENAME), e)
            self.send_error(500, msg)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # Ohne diese Angabe entscheidet der Browser selbst, wie lange er die
        # Seite behaelt - iOS Safari ist dabei sehr grosszuegig, erst recht
        # wenn die Seite als Web-App auf dem Home-Bildschirm liegt. Dann zeigt
        # das Geraet nach einem Update tagelang die alte Fassung. Im LAN kostet
        # das erneute Laden nichts.
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def proxy_to_shelly(self, endpoint, query):
        if not is_configured():
            self._json(503, {"success": False, "error": "Proxy noch nicht eingerichtet - siehe /setup"})
            return

        url = shelly_base() + endpoint
        if query:
            url += "?" + query

        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
                body = resp.read()
                status = resp.status
                content_type = resp.headers.get("Content-Type", "application/json")
        except urllib.error.HTTPError as e:
            # Shelly hat selbst einen Fehlerstatus geliefert (z.B. 400/500) -
            # 1:1 durchreichen, damit die Seite die echte Fehlermeldung sieht.
            body = e.read()
            status = e.code
            content_type = "application/json"
        except Exception as e:
            body = ('{{"success":false,"error":"Shelly nicht erreichbar: {}"}}'.format(str(e))).encode("utf-8")
            status = 502
            content_type = "application/json"

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def get_lan_ip():
    # Ermittelt die LAN-IP dieses Rechners (ohne eine echte Verbindung
    # aufzubauen) - fuer eine hilfreiche Ausgabe, von welcher Adresse aus
    # andere Rechner im Netz diesen Proxy erreichen koennen. Ohne bekannte
    # Shelly-IP wird stattdessen ein oeffentlicher Adressraum als Ziel fuer
    # die (nie tatsaechlich aufgebaute) UDP-"Verbindung" verwendet.
    target = CONFIG["shelly_ip"] or "192.168.1.1"
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((target, 80))
        return s.getsockname()[0]
    except Exception:
        return "<lan-ip-dieses-rechners>"
    finally:
        s.close()


def parse_args():
    global QUIET, SILENT
    for arg in sys.argv[1:]:
        if arg in ("-q", "--quiet"):
            QUIET = True
        elif arg in ("-s", "--silent"):
            SILENT = True
        elif arg in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        else:
            sys.stderr.write("Unbekannte Option: {}  (-h fuer Hilfe)\n".format(arg))
            sys.exit(1)


def say(msg):
    if not SILENT:
        print(msg)


def main():
    parse_args()
    load_config()

    if not os.path.isfile(resource_path(HTML_FILENAME)):
        # Warnung auch im stillen Betrieb - ohne die Datei liefert der Proxy
        # nur 404 aus, und die Ursache waere sonst nirgends zu sehen.
        sys.stderr.write("WARNUNG: HTML-Datei nicht gefunden unter: " + resource_path(HTML_FILENAME) + "\n")
        sys.stderr.write("Lege zendure-dashboard.html in denselben Ordner wie dieses Script,\n")
        sys.stderr.write("oder pruefe --add-data beim exe-Build.\n\n")

    say("Zendure Dashboard Proxy")
    if is_configured():
        say("  Shelly:   " + shelly_base())
    else:
        say("  Shelly:   noch nicht eingerichtet - Einrichtungsseite oeffnet automatisch")
    say("  Konfig:   " + config_path())
    url = "http://localhost:{}/".format(PORT)
    say("  Lokal:    " + url)
    if BIND_ADDRESS == "0.0.0.0":
        say("  Im Netz:  http://{}:{}/  (von jedem Rechner im selben Netzwerk)".format(get_lan_ip(), PORT))
    if QUIET:
        say("  Protokoll: aus (-q)")
    say("(Strg+C zum Beenden)\n")

    try:
        # Mehrere gleichzeitige Anfragen: waehrend der Proxy auf den Shelly
        # wartet (bis zu TIMEOUT Sekunden), blockierte ein einfacher
        # HTTPServer alle anderen Verbindungen. Auf einem Dauerlaeufer mit
        # mehreren offenen Dashboards ist das schnell spuerbar.
        server = http.server.ThreadingHTTPServer((BIND_ADDRESS, PORT), Handler)
    except OSError as e:
        sys.stderr.write("Konnte Port {} nicht oeffnen: {}\n".format(PORT, e))
        sys.stderr.write("Laeuft eventuell schon ein anderer Prozess auf diesem Port?\n")
        sys.exit(1)

    try:
        webbrowser.open(url)
    except Exception as e:
        say("Konnte den Browser nicht automatisch oeffnen ({}) - Adresse manuell aufrufen: {}".format(e, url))

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        say("\nBeendet.")


if __name__ == "__main__":
    main()
