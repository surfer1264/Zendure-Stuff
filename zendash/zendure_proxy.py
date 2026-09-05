#!/usr/bin/env python3
"""
Zendure Dashboard Proxy
=======================
Kleiner lokaler Proxy, nur Python-Standardbibliothek (kein "pip install"
noetig). Loest das Origin/CORS-Problem der Shelly-Firmware, indem der
Browser nur noch mit DIESEM Proxy spricht (gleicher Ursprung) - der Proxy
selbst holt die Daten serverseitig vom Shelly (dort gelten keine
Browser-CORS-Regeln).

Start:
    python3 zendure_proxy.py         normal, mit Zugriffsprotokoll
    python3 zendure_proxy.py -q      leise: Startmeldung ja, Zugriffe nein
    python3 zendure_proxy.py -s      still: gar keine Ausgabe (Fehler nach stderr)

Das Zugriffsprotokoll ist im Normalbetrieb recht gespraechig - die Seite
fragt alle 4 Sekunden an. Zum Einrichten ist es hilfreich, im Dauerbetrieb
eher nicht.

Danach im Browser oeffnen:
    http://localhost:8000/

Beenden: Strg+C im Terminal.

Anpassen falls noetig: SHELLY_IP, SHELLY_SCRIPT_ID, PORT, HTML_FILE
"""

import http.server
import urllib.request
import urllib.error
import os
import socket
import sys

# ---------------------------------------------------------------
# Konfiguration - hier anpassen
# ---------------------------------------------------------------
SHELLY_IP = "192.168.178.149"
SHELLY_SCRIPT_ID = 1
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

# Erwartet die HTML-Datei im selben Ordner wie dieses Script.
# Falls sie woanders liegt oder anders heisst, hier den Pfad anpassen.
HTML_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zendure-dashboard.html")

API_ENDPOINTS = ("config_api", "status_api", "kvs_set_api")
SHELLY_BASE = "http://{}/script/{}/".format(SHELLY_IP, SHELLY_SCRIPT_ID)
TIMEOUT = 5

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

        if path == "/" or path == "":
            self.serve_html()
            return

        if endpoint in ICON_PATHS:
            self.serve_favicon()
            return

        if endpoint in API_ENDPOINTS:
            self.proxy_to_shelly(endpoint, query)
            return

        self.send_error(404, "Nicht gefunden: " + path)

    def serve_favicon(self):
        self.send_response(200)
        self.send_header("Content-Type", "image/svg+xml")
        self.send_header("Content-Length", str(len(FAVICON_SVG)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(FAVICON_SVG)

    def serve_html(self):
        try:
            with open(HTML_FILE, "rb") as f:
                body = f.read()
        except OSError as e:
            msg = "HTML-Datei nicht lesbar ({}): {}".format(HTML_FILE, e)
            self.send_error(500, msg)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def proxy_to_shelly(self, endpoint, query):
        url = SHELLY_BASE + endpoint
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
    # andere Rechner im Netz diesen Proxy erreichen koennen.
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((SHELLY_IP, 80))
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

    if not os.path.isfile(HTML_FILE):
        # Warnung auch im stillen Betrieb - ohne die Datei liefert der Proxy
        # nur 404 aus, und die Ursache waere sonst nirgends zu sehen.
        sys.stderr.write("WARNUNG: HTML-Datei nicht gefunden unter: " + HTML_FILE + "\n")
        sys.stderr.write("Lege zendure-dashboard.html in denselben Ordner wie dieses Script,\n")
        sys.stderr.write("oder passe HTML_FILE oben im Script an.\n\n")

    say("Zendure Dashboard Proxy")
    say("  Shelly:   " + SHELLY_BASE)
    say("  HTML:     " + HTML_FILE)
    say("  Lokal:    http://localhost:{}/".format(PORT))
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
        server.serve_forever()
    except KeyboardInterrupt:
        say("\nBeendet.")


if __name__ == "__main__":
    main()