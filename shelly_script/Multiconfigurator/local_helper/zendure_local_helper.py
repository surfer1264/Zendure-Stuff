#!/usr/bin/env python3
"""
zendure_local_helper.py - lokaler Ein-Klick-Upload-Helfer fuer den
Zendure-Multi-Configurator (zendure-multi-configurator_multilang.html).

Loest drei Probleme, die ein reiner Browser nicht loesen kann:

  1. CORS: die Shelly-Firmware sendet keine CORS-Header, ein direkter
     fetch() vom Configurator zum Shelly wuerde vom Browser blockiert.
     Dieser Helfer laeuft lokal auf 127.0.0.1 und spricht das Shelly
     stattdessen serverseitig per RPC an - dort gelten keine
     Browser-CORS-Regeln.
  2. Chunked Upload: Shellys RPC hat ein Groessenlimit pro Aufruf, der
     Code muss daher in mehreren Script.PutCode-Aufrufen uebertragen
     werden (siehe upload_script()). Vorher wird der Bestand geprueft:
     pro Shelly ist genau EIN Script erlaubt. Ein Update ueberschreibt
     das vorhandene Script auf derselben ID; fremde, vertauschte oder
     mehrere Scripte werden nur nach Bestaetigung im Browser entfernt.
     Nach jedem erfolgreichen Upload merkt sich der Helfer die IP in
     zendure_helper_config.json (siehe save_settings()); der Configurator
     liest sie beim Start ueber GET /api/settings.
  3. Start-Komfort: der Helfer liefert die Configurator-Seite gleich
     selbst aus (genau wie zendure_proxy.py es heute fuers Dashboard
     macht) und oeffnet sie beim Start automatisch im Standardbrowser -
     kein manuelles Suchen der HTML-Datei noetig. Als Nebeneffekt laufen
     Seite und Helfer dann auf demselben Origin, das CORS-Thema aus
     Punkt 1 betrifft nur noch den Sonderfall "Configurator woanders
     geoeffnet" (z.B. die ueber GitHub Pages gehostete Version).

Kein "pip install" noetig, nur Python-Standardbibliothek.

Start:
    python3 zendure_local_helper.py

Der Browser oeffnet sich automatisch auf http://127.0.0.1:8787/ - dort
liegt der komplette Configurator, inklusive Erkennung des Helfers und
der Ziel-IP-Felder pro Script. Klappt der Auto-Open nicht (z.B. auf
einem Rechner ohne Standardbrowser-Registrierung), die Adresse manuell
in einen Browser eintragen.

WICHTIG - anders als zendure_proxy.py: es gibt hier bewusst KEINE feste
SHELLY_IP. Jeder Upload-Aufruf (POST /api/upload) traegt seine eigene
Ziel-IP im Request-Body mit ("ip"). Controller-, Watchdog- und
zenDash-API-Script koennen so ohne weitere Konfiguration auf drei
verschiedene Shellys gehen.

Fuers Bauen als exe (PyInstaller) muss die HTML-Datei mitgegeben werden,
siehe --add-data im build-and-release.yml-Workflow.

Beenden: Strg+C im Terminal.
"""

import http.server
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

# ---------------------------------------------------------------
# Konfiguration - hier anpassen
# ---------------------------------------------------------------
PORT = 8787
BIND_ADDRESS = "127.0.0.1"   # bewusst NUR dieser Rechner, nicht das ganze Netz
CHUNK_SIZE = 1024            # Zeichen pro Script.PutCode-Aufruf
HTML_FILENAME = "zendure-multi-configurator_multilang.html"
HELPER_VERSION = "1.1"
SETTINGS_FILENAME = "zendure_helper_config.json"


def resource_path(filename):
    """Findet eine mitgelieferte Datei - im normalen Skriptbetrieb neben
    diesem Skript, in einer mit PyInstaller --onefile gebauten exe
    stattdessen im temporaeren Entpack-Ordner sys._MEIPASS."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, filename)


# ---------------------------------------------------------------
# Gemerkte Shelly-IPs (zendure_helper_config.json)
#
# Vorbild: zendure_proxy_config.json des Dashboard-Proxys. Gespeichert
# werden NUR die beiden IPs (runtime-Rollen ctr_kvs / apidash_watch),
# keine Config, keine Zugangsdaten. Geschrieben wird nach jedem
# erfolgreichen Upload fuer die Rolle des hochgeladenen Scripts.
#
# Ablageort: neben der exe bzw. diesem Script (app_dir) - NICHT in
# sys._MEIPASS, das wird bei --onefile nach jedem Start geloescht. Ist
# app_dir nicht beschreibbar (z.B. C:\Programme, schreibgeschuetzter
# Ordner auf macOS), weicht der Helfer in den Benutzerordner aus. Beim
# Lesen werden beide Orte geprueft.
# ---------------------------------------------------------------
RUNTIME_KEYS = ("ctr_kvs", "apidash_watch")
KEY_TO_ROLE = {"ctrl": "ctr_kvs", "zdw": "apidash_watch"}
TYPE_TO_ROLE = {"zdmc-controller": "ctr_kvs", "zdmc-zendash-watch": "apidash_watch"}
RE_IP = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
_settings_lock = threading.Lock()


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def user_dir():
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "ZendureHelper")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/ZendureHelper")
    return os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
                        "zendure-helper")


def settings_candidates():
    return [os.path.join(app_dir(), SETTINGS_FILENAME),
            os.path.join(user_dir(), SETTINGS_FILENAME)]


def load_settings():
    """Liefert (settings, pfad). settings enthaelt nur gueltige IPs."""
    for path in settings_candidates():
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        clean = {k: data[k].strip() for k in RUNTIME_KEYS
                 if isinstance(data.get(k), str) and RE_IP.match(data[k].strip())}
        return clean, path
    return {}, None


def save_settings(updates):
    """Uebernimmt gueltige IPs aus updates in die Datei (atomar ueber eine
    Temp-Datei). Gibt den Pfad zurueck oder None, wenn nirgends
    geschrieben werden konnte - das ist nie ein Fehler fuer den Upload."""
    updates = {k: v.strip() for k, v in updates.items()
               if k in RUNTIME_KEYS and isinstance(v, str) and RE_IP.match(v.strip())}
    if not updates:
        return None
    with _settings_lock:
        current, current_path = load_settings()
        merged = dict(current, **updates)
        if merged == current and current_path:
            return current_path
        targets = settings_candidates()
        if current_path in targets:       # zuerst dort, wo die Datei schon liegt
            targets.remove(current_path)
            targets.insert(0, current_path)
        for path in targets:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                tmp = path + ".tmp"
                with open(tmp, "w", encoding="utf-8") as fh:
                    json.dump(merged, fh, indent=2)
                    fh.write("\n")
                os.replace(tmp, path)
                return path
            except OSError:
                continue
    return None


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


# ---------------------------------------------------------------
# Script-Erkennung und Upload
#
# Regel: pro Shelly genau EIN Script (Speicher). Vor jedem Upload wird
# der Bestand geprueft:
#   - kein Script                      -> neu anlegen
#   - genau eins, gleicher Script-Typ  -> auf derselben ID ueberschreiben
#                                         (Update; Script-ID bleibt, z.B.
#                                         fuer den Dashboard-Proxy)
#   - sonst (fremdes Script, anderer   -> NICHTS veraendern, sondern
#     Typ = vermutlich IP vertauscht,     needs_confirm an den Browser;
#     mehrere Scripte)                    erst nach Bestaetigung (force +
#                                         confirm_ids) werden alle
#                                         Scripte entfernt und neu angelegt
# ---------------------------------------------------------------
KEY_TO_TYPE = {"ctrl": "zdmc-controller", "zdw": "zdmc-zendash-watch"}
READ_CHUNK = 2048            # Zeichen pro Script.GetCode-Aufruf
RE_SCRIPT_TYPE = re.compile(r"""\bSCRIPT_TYPE\s*=\s*["']([^"']+)["']""")
RE_VERSION = re.compile(r"""\bVERSION\s*=\s*["']([^"']+)["']""")
RE_LEGACY_VERSION = re.compile(r"""CONFIG\.version\s*=\s*["']([^"']+)["']""")


class UploadIncomplete(RpcError):
    """Upload nach dem ersten Block abgebrochen - auf dem Shelly liegt
    jetzt ein unvollstaendiges Script."""


def read_code(ip, sid, full=True):
    """Liest den Code eines Scripts per Script.GetCode. full=False liest
    nur den ersten Block (reicht fuer SCRIPT_TYPE, das in der Mini-
    Version ganz vorne steht)."""
    parts, offset = [], 0
    while True:
        res = rpc(ip, "Script.GetCode", {"id": sid, "offset": offset, "len": READ_CHUNK})
        data = res.get("data") or ""
        parts.append(data)
        offset += len(data)
        if not full or not data or not res.get("left"):
            break
    return "".join(parts)


def detect_type(code):
    """Ermittelt (script_type, version, legacy) aus dem Code.
    legacy=True: Stand vor Einfuehrung von SCRIPT_TYPE, erkannt an
    typischen Merkmalen."""
    m = RE_SCRIPT_TYPE.search(code)
    if m:
        v = RE_VERSION.search(code)
        return m.group(1), (v.group(1) if v else None), False
    if "zdmc_" in code:
        if "kvs_set_api" in code or "status_api" in code:
            v = RE_VERSION.search(code)
            return "zdmc-zendash-watch", (v.group(1) if v else None), True
        if "zdmc_setpoint" in code:
            v = RE_LEGACY_VERSION.search(code)
            return "zdmc-controller", (v.group(1) if v else None), True
    return None, None, False


def inspect_scripts(ip):
    """Bestand eines Shelly: Liste aller Scripte mit erkanntem Typ."""
    result = []
    for s in rpc(ip, "Script.List").get("scripts", []):
        entry = {"id": s.get("id"), "name": s.get("name") or "",
                 "running": bool(s.get("running")),
                 "type": None, "version": None, "legacy": False}
        try:
            code = read_code(ip, s["id"], full=False)
            stype, ver, legacy = detect_type(code)
            if not stype:
                # SCRIPT_TYPE steht in der Mini-Version vorne; fuer
                # aeltere Staende den ganzen Code lesen.
                code = read_code(ip, s["id"], full=True)
                stype, ver, legacy = detect_type(code)
            entry.update(type=stype, version=ver, legacy=legacy)
        except RpcError:
            pass  # Code nicht lesbar -> Typ bleibt unbekannt
        result.append(entry)
    return result


def _put_code(ip, sid, code, first_append):
    for n, i in enumerate(range(0, len(code), CHUNK_SIZE)):
        chunk = code[i:i + CHUNK_SIZE]
        for attempt in range(3):
            try:
                rpc(ip, "Script.PutCode",
                    {"id": sid, "code": chunk, "append": first_append or n > 0})
                break
            except RpcError as err:
                if attempt == 2:
                    if n > 0:
                        raise UploadIncomplete(str(err))
                    raise
                time.sleep(1)


def _start(ip, sid, name):
    rpc(ip, "Script.SetConfig", {"id": sid, "config": {"name": name, "enable": True}})
    rpc(ip, "Script.Start", {"id": sid})
    time.sleep(1.5)
    return bool(rpc(ip, "Script.GetStatus", {"id": sid}).get("running", False))


def upload_script(ip, name, code, key=None, force=False, confirm_ids=None):
    """Laedt code auf den Shelly (siehe Regel oben). Rueckgabe:
      {"action": "installed"|"updated"|"replaced", "id", "running"}
    oder, wenn eine Bestaetigung noetig ist:
      {"needs_confirm": True, "reason": "foreign"|"wrong_type"|"multiple",
       "expected_type", "scripts": [...]}
    Wirft RpcError / UploadIncomplete bei Fehlern."""
    if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
        raise RpcError("Ungueltige IP-Adresse: %r" % ip)
    name = name[:20]

    stype, _, _ = detect_type(code)
    expected = stype or KEY_TO_TYPE.get(key)
    if not expected:
        raise RpcError("Script-Typ des hochzuladenden Codes unbekannt")

    scripts = inspect_scripts(ip)

    # Fall 1: leer -> neu anlegen
    if not scripts:
        sid = rpc(ip, "Script.Create", {"name": name})["id"]
        _put_code(ip, sid, code, first_append=False)
        return {"action": "installed", "id": sid, "running": _start(ip, sid, name)}

    # Fall 2: genau ein Script vom gleichen Typ -> auf derselben ID ueberschreiben
    if len(scripts) == 1 and scripts[0]["type"] == expected:
        sid = scripts[0]["id"]
        was_running = scripts[0]["running"]
        if was_running:
            rpc(ip, "Script.Stop", {"id": sid})
        try:
            _put_code(ip, sid, code, first_append=False)
        except UploadIncomplete:
            raise
        except RpcError:
            # Schon der erste Block kam nicht an -> der alte Code ist noch
            # vollstaendig; wieder starten, damit die Regelung weiterlaeuft.
            if was_running:
                try:
                    rpc(ip, "Script.Start", {"id": sid})
                except RpcError:
                    pass
            raise
        return {"action": "updated", "id": sid, "running": _start(ip, sid, name)}

    # Fall 3: alles andere -> nur nach ausdruecklicher Bestaetigung
    current_ids = sorted(s["id"] for s in scripts)
    if not force or sorted(confirm_ids or []) != current_ids:
        if len(scripts) > 1:
            reason = "multiple"
        elif scripts[0]["type"]:
            reason = "wrong_type"
        else:
            reason = "foreign"
        return {"needs_confirm": True, "reason": reason,
                "expected_type": expected, "scripts": scripts}

    for s in scripts:
        if s["running"]:
            try:
                rpc(ip, "Script.Stop", {"id": s["id"]})
            except RpcError:
                pass  # wird gleich sowieso geloescht
        rpc(ip, "Script.Delete", {"id": s["id"]})
    sid = rpc(ip, "Script.Create", {"name": name})["id"]
    _put_code(ip, sid, code, first_append=False)
    return {"action": "replaced", "id": sid, "running": _start(ip, sid, name)}


def check_memory(ip):
    """Ermittelt den freien mJS-Skriptspeicher (mem_free) eines Shelly.
    Script.GetStatus liefert das nur fuer eine existierende Script-ID -
    bei einem Geraet ganz ohne Scripte wird deshalb kurz ein leeres
    Testscript angelegt, ausgelesen und danach wieder geloescht, damit
    auch ein jungfraeulicher Shelly geprueft werden kann. Referenzwert
    laut Zendure-Stuff-Wiki: mem_free 25200 = voller Standard-Heap, alles
    darunter deutet auf bereits belegten Speicher (z.B. durch andere
    Scripte) hin."""
    if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
        raise RpcError("Ungueltige IP-Adresse: %r" % ip)

    scripts = rpc(ip, "Script.List").get("scripts", [])
    if scripts:
        status = rpc(ip, "Script.GetStatus", {"id": scripts[0]["id"]})
        return {
            "mem_free": status.get("mem_free"),
            "mem_used": status.get("mem_used"),
            "script_count": len(scripts),
            "created_temp": False,
        }

    sid = rpc(ip, "Script.Create", {"name": "memcheck-tmp"})["id"]
    try:
        status = rpc(ip, "Script.GetStatus", {"id": sid})
        return {
            "mem_free": status.get("mem_free"),
            "mem_used": status.get("mem_used"),
            "script_count": 0,
            "created_temp": True,
        }
    finally:
        try:
            rpc(ip, "Script.Delete", {"id": sid})
        except RpcError:
            pass  # Aufraeumen ist nicht kritisch fuers eigentliche Ergebnis


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
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/api/health":
            self._json(200, {"ok": True, "helper": "zendure-local-helper", "version": HELPER_VERSION})
        elif parsed.path == "/api/memcheck":
            self._handle_memcheck(parsed.query)
        elif parsed.path == "/api/settings":
            settings, path = load_settings()
            self._json(200, dict({"ok": True, "path": path}, **settings))
        elif parsed.path in ("/", "/index.html"):
            self._serve_html()
        else:
            self._json(404, {"ok": False, "error": "not found"})

    def _handle_memcheck(self, query):
        params = urllib.parse.parse_qs(query)
        ip = (params.get("ip") or [""])[0].strip()
        try:
            if not ip:
                raise RpcError("ip fehlt")
            result = check_memory(ip)
            self._json(200, dict({"ok": True}, **result))
        except RpcError as err:
            self._json(200, {"ok": False, "error": str(err)})
        except Exception as err:
            self._json(500, {"ok": False, "error": str(err)})

    def _serve_html(self):
        try:
            with open(resource_path(HTML_FILENAME), "rb") as fh:
                body = fh.read()
        except OSError as err:
            self._json(
                500,
                {"ok": False, "error": "Configurator-HTML nicht gefunden (%s): %s" % (HTML_FILENAME, err)},
            )
            return
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

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
            key = data.get("key")
            force = bool(data.get("force"))
            confirm_ids = data.get("confirm_ids") or []
            if not ip or not code:
                raise RpcError("ip und code sind Pflichtfelder")
            print("Upload: %d Zeichen -> %s (Name: %s%s)"
                  % (len(code), ip, name, ", bestaetigt" if force else ""))
            result = upload_script(ip, name, code, key=key, force=force,
                                   confirm_ids=confirm_ids)
            if result.get("needs_confirm"):
                print("  -> Bestaetigung noetig (%s), nichts veraendert" % result["reason"])
                self._json(200, dict({"ok": False}, **result))
            else:
                print("  -> %s, Script-ID %s, laeuft: %s"
                      % (result["action"], result["id"], result["running"]))
                stype, _, _ = detect_type(code)
                role = TYPE_TO_ROLE.get(stype) or KEY_TO_ROLE.get(key)
                if role:
                    saved = save_settings({role: ip})
                    if saved:
                        print("  -> IP gemerkt in %s" % saved)
                self._json(200, dict({"ok": True}, **result))
        except UploadIncomplete as err:
            self._json(200, {"ok": False, "error_code": "incomplete", "error": str(err)})
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

    url = "http://%s:%s/" % (BIND_ADDRESS, PORT)
    print("Lokaler Helfer laeuft auf %s" % url)
    print("Oeffne den Configurator automatisch im Browser...")
    try:
        webbrowser.open(url)
    except Exception as err:
        print("Konnte den Browser nicht automatisch oeffnen (%s) - Adresse manuell aufrufen: %s"
              % (err, url))
    print("Dieses Fenster offen lassen, solange hochgeladen wird. Beenden mit Strg+C.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
