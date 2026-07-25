#!/usr/bin/env python3
"""
Lokaler Server fuer das Zendure-Grid-Dashboard.

Dient drei Zwecken:
  1. Liefert die Dashboard-HTML-Datei (wie "python -m http.server").
  2. Stellt unter /hubproxy?ip=<hub-ip> einen kleinen Proxy fuer die
     Zendure-Hub-Abfrage (/properties/report) bereit.
  3. Stellt unter /shellyrpc?ip=<ip>&method=<Methode>&<weitere Parameter>
     einen generischen Proxy fuer die native Shelly-RPC-Schnittstelle
     bereit (KVS.Set, KVS.GetMany, EM.GetStatus, ...).

Grund fuer beide Proxies: weder die Zendure- noch (bei diesem Geraet/dieser
Firmware) die Shelly-RPC-Antworten enthalten einen
Access-Control-Allow-Origin-Header, daher blockt der Browser einen direkten
fetch() aus dem Dashboard heraus (CORS). Eine Anfrage von diesem
Python-Skript aus ist dagegen keine Browser-Anfrage und unterliegt keiner
CORS-Pruefung - das Skript holt die Daten also stellvertretend fuer den
Browser und reicht sie same-origin weiter.

Nutzung:
    python3 zendure_proxy.py [port]
    # Default-Port: 8000

Dann im Browser oeffnen:
    http://localhost:8000/zendure-grid-dashboard.html

Die HTML-Datei muss im selben Ordner liegen wie dieses Skript.
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

TIMEOUT_SECONDS = 5


class ProxyHandler(SimpleHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/hubproxy":
            self._handle_hub_proxy(parsed)
            return

        if parsed.path == "/shellyrpc":
            self._handle_shelly_rpc(parsed)
            return

        # alles andere (die Dashboard-Datei, etc.) normal als statische Datei ausliefern
        super().do_GET()

    def _handle_shelly_rpc(self, parsed):
        query = parse_qs(parsed.query)
        ip = (query.get("ip") or [""])[0].strip()
        method = (query.get("method") or [""])[0].strip()

        if not ip or not method:
            self._send_json(400, {"error": "Parameter 'ip' und 'method' erforderlich, z.B. /shellyrpc?ip=...&method=KVS.GetMany&match=zdmc_*"})
            return

        # restliche Query-Parameter 1:1 an die Shelly-RPC-Methode weiterreichen
        extra = []
        for key, values in query.items():
            if key in ("ip", "method"):
                continue
            for value in values:
                extra.append(urllib.parse.quote(key) + "=" + urllib.parse.quote(value))
        qs = "&".join(extra)
        target_url = "http://" + ip + "/rpc/" + method + (("?" + qs) if qs else "")

        try:
            request = urllib.request.Request(target_url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as resp:
                body = resp.read()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        except urllib.error.HTTPError as e:
            body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except urllib.error.URLError as e:
            self._send_json(502, {"error": "Shelly " + ip + " nicht erreichbar: " + str(e.reason)})
        except Exception as e:
            self._send_json(502, {"error": "Fehler bei RPC " + method + " auf " + ip + ": " + str(e)})

    def _handle_hub_proxy(self, parsed):
        query = parse_qs(parsed.query)
        ip = (query.get("ip") or [""])[0].strip()

        if not ip:
            self._send_json(400, {"error": "Parameter 'ip' fehlt, z.B. /hubproxy?ip=192.168.178.143"})
            return

        target_url = "http://" + ip + "/properties/report"

        try:
            request = urllib.request.Request(target_url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as resp:
                body = resp.read()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        except urllib.error.URLError as e:
            self._send_json(502, {"error": "Hub " + ip + " nicht erreichbar: " + str(e.reason)})
        except Exception as e:
            self._send_json(502, {"error": "Fehler beim Abfragen von " + ip + ": " + str(e)})

    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ruhigeres Log: nur Fehler, keine Zeile pro Request (bei Bedarf entfernen)
    def log_message(self, fmt, *args):
        if args and str(args[0]).startswith(("4", "5")):
            super().log_message(fmt, *args)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    server = ThreadingHTTPServer(("0.0.0.0", port), ProxyHandler)
    print("Server laeuft: http://localhost:%d/zendure-grid-dashboard.html" % port)
    print("Hub-Proxy unter: http://localhost:%d/hubproxy?ip=<hub-ip>" % port)
    print("Shelly-RPC-Proxy unter: http://localhost:%d/shellyrpc?ip=<ip>&method=<Methode>" % port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")