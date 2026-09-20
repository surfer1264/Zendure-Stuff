#!/usr/bin/env python3
"""
zendure_local_helper.py - lokaler Ein-Klick-Upload-Helfer fuer den
Zendure-Multi-Configurator (zendure-multi-configurator_multilang.html).

Loest zwei Probleme, die ein reiner Browser nicht loesen kann:

  1. CORS: die Shelly-Firmware sendet keine CORS-Header, ein direkter
     fetch() vom Configurator zum Shelly wuerde vom Browser blockiert.
     Dieser Helfer laeuft lokal auf 127.0.0.1 und spricht das Shelly
     stattdessen serverseitig per RPC an - dort gelten keine
     Browser-CORS-Regeln (dasselbe Prinzip wie zendure_proxy.py fuers
     Dashboard).
  2. Chunked Upload: Shellys RPC hat ein Groessenlimit pro Aufruf, der
     Code muss daher in mehreren Script.PutCode-Aufrufen uebertragen
     werden (siehe upload_script()) - identisch zu upload_shelly.py.

Kein "pip install" noetig, nur Python-Standardbibliothek.

Start:
    python3 zendure_local_helper.py

Danach den Configurator im Browser offen lassen (egal ob als lokale
Datei oder z.B. ueber GitHub Pages gehostet) - er erkennt den Helfer
automatisch per GET /api/health und zeigt pro Script ein Eingabefeld
fuer die Ziel-IP plus einen "Direkt hochladen"-Button.

WICHTIG - anders als zendure_proxy.py: es gibt hier bewusst KEINE feste
SHELLY_IP. Jeder Upload-Aufruf (POST /api/upload) traegt seine eigene
Ziel-IP im Request-Body mit ("ip"). Controller-, Watchdog- und
zenDash-API-Script koennen so ohne weitere Konfiguration auf drei
verschiedene Shellys gehen.

Beenden: Strg+C im Terminal.
"""

import http.server
import json
import re
import sys
import time
import urllib.error
import urllib.request

# ---------------------------------------------------------------
# Konfiguration - hier anpassen
# ---------------------------------------------------------------
PORT = 8787
BIND_ADDRESS = "127.0.0.1"   # bewusst NUR dieser Rechner, nicht das ganze Netz
CHUNK_SIZE = 1024            # Zeichen pro Script.PutCode-Aufruf


class RpcError(Exception):
    pass


def rpc(ip, method, params=None, timeout=15):
    # ensure_ascii=False, siehe upload_shelly.py: sonst kodiert json.dumps
    # Emojis als \uXXXX-Surrogatpaare, die der Shelly-JSON-Parser ablehnt.
    payload = json.dumps(
        {"id": 1, "method": method, "params": params or {}},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        "http://%s/rpc" % ip,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", "replace")[:200]
        if err.code == 401:
            raise RpcError(
                "Der Shelly %s verlangt ein Passwort - Passwortschutz "
                "voruebergehend deaktivieren." % ip
            )
        raise RpcError("%s: HTTP %s %s" % (method, err.code, detail))
    except urllib.error.URLError as err:
        raise RpcError("%s: Shelly %s nicht erreichbar (%s)" % (method, ip, err.reason))

    if "error" in body:
        raise RpcError("%s: %s" % (method, body["error"]))
    return body.get("result", {})


def find_script(ip, name):
    for s in rpc(ip, "Script.List").get("scripts", []):
        if s.get("name") == name:
            return s
    return None


def upload_script(ip, name, code):
    """Ersetzt ein gleichnamiges Script komplett (stoppen, loeschen, neu
    anlegen), laedt den Code in Bloecken hoch und startet es mit
    Autostart. Wirft RpcError bei jedem Fehlschlag - der Aufrufer
    (do_POST) faengt das ab und meldet es dem Browser."""
    if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
        raise RpcError("Ungueltige IP-Adresse: %r" % ip)
    name = name[:20]

    old = find_script(ip, name)
    if old:
        if old.get("running"):
            try:
                rpc(ip, "Script.Stop", {"id": old["id"]})
            except RpcError:
                pass  # egal, wird gleich sowieso geloescht
        rpc(ip, "Script.Delete", {"id": old["id"]})

    sid = rpc(ip, "Script.Create", {"name": name})["id"]

    for i in range(0, len(code), CHUNK_SIZE):
        chunk = code[i:i + CHUNK_SIZE]
        for attempt in range(3):
            try:
                rpc(ip, "Script.PutCode", {"id": sid, "code": chunk, "append": i > 0})
                break
            except RpcError:
                if attempt == 2:
                    raise
                time.sleep(1)

    rpc(ip, "Script.SetConfig", {"id": sid, "config": {"enable": True}})
    rpc(ip, "Script.Start", {"id": sid})
    time.sleep(1.5)
    status = rpc(ip, "Script.GetStatus", {"id": sid})
    return {"id": sid, "running": status.get("running", False)}


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _cors(self):
        origin = self.headers.get("Origin", "*")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        # Chromes "Private Network Access": erlaubt einer von aussen (auch
        # https, z.B. GitHub Pages) geladenen Seite, dieses 127.0.0.1
        # anzusprechen - ohne diesen Header blockt neueres Chrome sonst
        # den Preflight-Request.
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _json(self, status, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/health":
            self._json(200, {"ok": True, "helper": "zendure-local-helper", "version": "1.0"})
        else:
            self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if self.path != "/api/upload":
            self._json(404, {"ok": False, "error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            ip = (data.get("ip") or "").strip()
            name = (data.get("name") or "script").strip()
            code = data.get("code") or ""
            if not ip or not code:
                raise RpcError("ip und code sind Pflichtfelder")
            print("Upload: %d Zeichen -> %s (Name: %s)" % (len(code), ip, name))
            result = upload_script(ip, name, code)
            self._json(200, {"ok": True, "id": result["id"], "running": result["running"]})
        except RpcError as err:
            # Kein Serverfehler, sondern ein erwartbarer Fall (falsche IP,
            # Shelly nicht erreichbar etc.) - der Browser zeigt err als
            # normale Fehlermeldung an, kein HTTP-500 noetig.
            self._json(200, {"ok": False, "error": str(err)})
        except Exception as err:
            self._json(500, {"ok": False, "error": str(err)})


def main():
    try:
        httpd = http.server.ThreadingHTTPServer((BIND_ADDRESS, PORT), Handler)
    except OSError as err:
        print("Fehler: konnte nicht auf %s:%s lauschen (%s)" % (BIND_ADDRESS, PORT, err),
              file=sys.stderr)
        return 1

    print("Lokaler Helfer laeuft auf http://%s:%s" % (BIND_ADDRESS, PORT))
    print("Configurator-Tab offen lassen - er erkennt den Helfer automatisch.")
    print("Beenden mit Strg+C.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
