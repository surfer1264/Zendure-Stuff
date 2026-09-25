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
     pro Shelly wird genau EIN Script empfohlen. Ein Update ueberschreibt
     das vorhandene Script auf derselben ID; fremde, vertauschte oder
     mehrere Scripte fuehren zu einer Rueckfrage im Browser - der Nutzer
     entscheidet, ob die anderen Scripte geloescht oder behalten werden.
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
# Gemeinsame Version von Helfer und Configurator: steht NUR in der
# Configurator-HTML (const APP_VERSION = "..."), der Helfer liest sie beim
# Start von dort. So gibt es genau eine Stelle zum Hochzaehlen.
# Faehigkeiten DIESES Helfer-Codes. Wichtig, weil die Seite bei jedem
# Aufruf frisch von der Platte gelesen wird, der Python-Code aber nur beim
# Start: laeuft noch ein alter Helfer-Prozess (oder eine alte exe mit dem
# Configurator per githack), kennt er neue Optionen nicht. Der Configurator
# bietet eine Funktion nur an, wenn sie hier aufgefuehrt ist.
HELPER_FEATURES = ["script_check", "keep_others", "read_config", "settings"]
RE_APP_VERSION = re.compile(r"""\bAPP_VERSION\s*=\s*["']([^"']+)["']""")

# Herkunftspruefung: nur diese Seiten duerfen den Helfer aus dem Browser
# ansprechen. Der Browser setzt den Origin-Header selbst, eine Webseite
# kann ihn nicht faelschen. Anfragen OHNE Origin (curl, upload_shelly.py,
# andere lokale Programme) bleiben erlaubt - wer lokal Programme startet,
# hat ohnehin vollen Zugriff.
# githack ist bewusst zugelassen (Configurator per githack-Link + Helfer).
# Hinweis: githack liefert ALLE oeffentlichen GitHub-Repos unter derselben
# Adresse aus - diese Freigabe gilt damit auch fuer fremde Repos dort.
ALLOWED_ORIGINS = {
    "http://127.0.0.1:%d" % PORT,
    "http://localhost:%d" % PORT,
    "https://raw.githack.com",
    "https://rawcdn.githack.com",
}
SETTINGS_FILENAME = "zendure_helper_config.json"


def resource_path(filename):
    """Findet eine mitgelieferte Datei - im normalen Skriptbetrieb neben
    diesem Skript oder im Ordner darueber, in einer mit PyInstaller
    --onefile gebauten exe stattdessen im temporaeren Entpack-Ordner
    sys._MEIPASS."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, filename)
    # Skriptbetrieb: erst neben diesem Skript, sonst eine Ebene hoeher
    # (Repo-Layout: local_helper/ liegt unter Multiconfigurator/, wo auch
    # die HTML liegt) - so ist keine Kopie der HTML im Repo noetig.
    here = os.path.dirname(os.path.abspath(__file__))
    for base in (here, os.path.dirname(here)):
        path = os.path.join(base, filename)
        if os.path.isfile(path):
            return path
    return os.path.join(here, filename)


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


def app_version():
    try:
        with open(resource_path(HTML_FILENAME), "r", encoding="utf-8") as fh:
            m = RE_APP_VERSION.search(fh.read())
        return m.group(1) if m else "?"
    except OSError:
        return "?"


class RpcError(Exception):
    pass


def rpc(ip, method, params=None, timeout=15, lenient=False):
    # lenient=True (nur Script.GetCode): Antwort mit "surrogateescape"
    # dekodieren. Der Shelly teilt den Code nach BYTES in Bloecke - ein
    # Umlaut oder Gedankenstrich (2-3 Byte) kann dabei mitten durchgeschnitten
    # werden. So bleiben die Rohbytes erhalten und werden in read_code()
    # wieder korrekt zusammengesetzt.
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
            body = json.loads(resp.read().decode("utf-8", "surrogateescape" if lenient else "strict"))
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
#     mehrere Scripte)                    der Nutzer entscheidet Ja/Nein,
#                                         ob die anderen Scripte geloescht
#                                         werden (force + confirm_ids +
#                                         delete_others)
# ---------------------------------------------------------------
KEY_TO_TYPE = {"ctrl": "zdmc-controller", "zdw": "zdmc-zendash-watch"}
READ_CHUNK = 2048            # Zeichen pro Script.GetCode-Aufruf
RE_SCRIPT_TYPE = re.compile(r"""\bSCRIPT_TYPE\s*=\s*["']([^"']+)["']""")
RE_VERSION = re.compile(r"""\bVERSION\s*=\s*["']([^"']+)["']""")
RE_LEGACY_VERSION = re.compile(r"""CONFIG\.version\s*=\s*["']([^"']+)["']""")
RE_SCHEMA = re.compile(r"""\bCONFIG_SCHEMA\s*=\s*(\d+)""")
RE_CONFIG_START = re.compile(r"^let CONFIG\s*=\s*\{", re.MULTILINE)


def find_config_block(text):
    """(start, ende) des Blocks 'let CONFIG = {...};' - beachtet Strings
    und Kommentare (gleiche Logik wie .github/scripts/build_manifest.py)."""
    m = RE_CONFIG_START.search(text)
    if not m:
        return None
    i, depth, n = m.end() - 1, 0, len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        if c in "\"'":
            i += 1
            while i < n and text[i] != c:
                if text[i] == "\\":
                    i += 1
                i += 1
            i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                if end < n and text[end] == ";":
                    end += 1
                return m.start(), end
        i += 1
    return None


class UploadIncomplete(RpcError):
    """Upload nach dem ersten Block abgebrochen - auf dem Shelly liegt
    jetzt ein unvollstaendiges Script."""


def read_code(ip, sid, full=True):
    """Liest den Code eines Scripts per Script.GetCode. full=False liest
    nur den ersten Block (reicht fuer SCRIPT_TYPE, das in der Mini-
    Version ganz vorne steht).

    Wichtig: offset und left zaehlt der Shelly in BYTES, nicht in
    Zeichen. Enthaelt der Code Umlaute oder Sonderzeichen (z.B. "—" in
    den Kommentaren der Config), liefen Zeichen- und Bytezaehlung
    auseinander und Teile wurden doppelt gelesen. Deshalb: Rohbytes
    sammeln, den naechsten offset aus der Gesamtlaenge (erste Antwort:
    gelieferte Bytes + left) minus left berechnen und erst am Ende als
    UTF-8 dekodieren."""
    chunks, offset, total = [], 0, None
    while True:
        res = rpc(ip, "Script.GetCode", {"id": sid, "offset": offset, "len": READ_CHUNK},
                  lenient=True)
        raw = (res.get("data") or "").encode("utf-8", "surrogateescape")
        left = res.get("left") or 0
        chunks.append(raw)
        if total is None:
            total = offset + len(raw) + left
        next_offset = total - left
        if not full or not raw or left <= 0 or next_offset <= offset:
            break
        offset = next_offset
    return b"".join(chunks).decode("utf-8", "replace")


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
                 "type": None, "version": None, "schema": None, "legacy": False}
        try:
            code = read_code(ip, s["id"], full=False)
            stype, ver, legacy = detect_type(code)
            if not stype:
                # SCRIPT_TYPE steht in der Mini-Version vorne; fuer
                # aeltere Staende den ganzen Code lesen.
                code = read_code(ip, s["id"], full=True)
                stype, ver, legacy = detect_type(code)
            m_schema = RE_SCHEMA.search(code)
            entry.update(type=stype, version=ver, legacy=legacy,
                         schema=int(m_schema.group(1)) if m_schema else None)
        except RpcError:
            pass  # Code nicht lesbar -> Typ bleibt unbekannt
        result.append(entry)
    return result


def read_config(ip, key):
    """Liest den CONFIG-Block des installierten Scripts (fuer den
    Update-Weg im Configurator). Erwartet genau ein Script vom Typ zu key
    auf dem Shelly - sonst Fehler (dann bitte 'Neu konfigurieren').
    Weitere, fremde Scripte stoeren hier nicht: sie fuehren erst beim
    Hochladen zur Rueckfrage "Alle entfernen und installieren"."""
    expected = KEY_TO_TYPE.get(key)
    if not expected:
        raise RpcError("Unbekannter Script-Schluessel: %r" % key)
    matching = [s for s in inspect_scripts(ip) if s["type"] == expected]
    if len(matching) != 1:
        raise RpcError("Auf %s liegt nicht genau ein passendes Script "
                       "- bitte 'Neu konfigurieren' waehlen." % ip)
    code = read_code(ip, matching[0]["id"], full=True)
    rng = find_config_block(code.replace("\r\n", "\n"))
    if rng is None:
        raise RpcError("CONFIG-Block im Script auf %s nicht gefunden." % ip)
    return dict(matching[0], config=code.replace("\r\n", "\n")[rng[0]:rng[1]])


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


def _update_in_place(ip, script, code, name):
    """Ueberschreibt ein vorhandenes Script auf derselben ID (Update)."""
    sid = script["id"]
    was_running = script["running"]
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


def _install_new(ip, code, name, action="installed"):
    sid = rpc(ip, "Script.Create", {"name": name})["id"]
    _put_code(ip, sid, code, first_append=False)
    return {"action": action, "id": sid, "running": _start(ip, sid, name)}


def _delete(ip, script):
    if script["running"]:
        try:
            rpc(ip, "Script.Stop", {"id": script["id"]})
        except RpcError:
            pass  # wird gleich sowieso geloescht
    rpc(ip, "Script.Delete", {"id": script["id"]})


def upload_script(ip, name, code, key=None, force=False, confirm_ids=None,
                  delete_others=True):
    """Laedt code auf den Shelly (siehe Regel oben). Rueckgabe:
      {"action": "installed"|"updated"|"replaced", "id", "running",
       "kept_others": n}
    oder, wenn eine Bestaetigung noetig ist:
      {"needs_confirm": True, "reason": "foreign"|"wrong_type"|"multiple",
       "expected_type", "scripts": [...], "target_id", "keep_possible"}
    Nach der Rueckfrage entscheidet der Nutzer (delete_others):
      True  -> alle anderen Scripte loeschen
      False -> andere Scripte behalten, nur das eigene installieren bzw.
               aktualisieren
    Ein vorhandenes Script vom gleichen Typ wird in beiden Faellen auf
    seiner ID aktualisiert (Script-ID bleibt, z.B. fuer den Dashboard-Proxy).
    Wirft RpcError / UploadIncomplete bei Fehlern."""
    if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
        raise RpcError("Ungueltige IP-Adresse: %r" % ip)
    name = name[:20]

    stype, _, _ = detect_type(code)
    expected = stype or KEY_TO_TYPE.get(key)
    if not expected:
        raise RpcError("Script-Typ des hochzuladenden Codes unbekannt")

    scripts = inspect_scripts(ip)
    matching = [s for s in scripts if s["type"] == expected]
    others = [s for s in scripts if s["type"] != expected]

    # Fall 1: leer -> neu anlegen
    if not scripts:
        return _install_new(ip, code, name)

    # Fall 2: genau ein Script vom gleichen Typ -> auf derselben ID ueberschreiben
    if len(scripts) == 1 and matching:
        return _update_in_place(ip, matching[0], code, name)

    # Fall 3: alles andere -> erst Rueckfrage, dann entscheidet der Nutzer
    current_ids = sorted(s["id"] for s in scripts)
    if not force or sorted(confirm_ids or []) != current_ids:
        if len(scripts) > 1:
            reason = "multiple"
        elif scripts[0]["type"]:
            reason = "wrong_type"
        else:
            reason = "foreign"
        return {"needs_confirm": True, "reason": reason,
                "expected_type": expected, "scripts": scripts,
                "target_id": matching[0]["id"] if len(matching) == 1 else None,
                # Mehrere Scripte vom gleichen Typ: unklar, welches
                # aktualisiert werden soll -> "Behalten" nicht moeglich
                "keep_possible": len(matching) <= 1}

    if not delete_others:
        if len(matching) > 1:
            raise RpcError("Mehrere Scripte vom gleichen Typ auf %s - "
                           "bitte andere Scripte entfernen lassen." % ip)
        if matching:
            result = _update_in_place(ip, matching[0], code, name)
        else:
            result = _install_new(ip, code, name)
        result["kept_others"] = len(others)
        return result

    if len(matching) == 1:
        for s in others:
            _delete(ip, s)
        result = _update_in_place(ip, matching[0], code, name)
        result["action"] = "replaced"
        return result
    for s in scripts:
        _delete(ip, s)
    return _install_new(ip, code, name, action="replaced")


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

    def _origin_ok(self):
        origin = self.headers.get("Origin")
        return origin is None or origin in ALLOWED_ORIGINS

    def _reject(self):
        body = b'{"ok": false, "error": "origin not allowed"}'
        self.send_response(403)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        sys.stderr.write("Abgelehnt: Anfrage von %s\n" % self.headers.get("Origin"))

    def _cors(self):
        origin = self.headers.get("Origin")
        if origin not in ALLOWED_ORIGINS:
            return
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        # Chromes "Private Network Access": erlaubt einer von aussen (auch
        # https, z.B. githack) geladenen Seite, dieses 127.0.0.1
        # anzusprechen - ohne diesen Header blockt neueres Chrome sonst
        # den Preflight-Request.
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def do_OPTIONS(self):
        if not self._origin_ok():
            self._reject()
            return
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
        if not self._origin_ok():
            self._reject()
            return
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.path == "/api/health":
            self._json(200, {"ok": True, "helper": "zendure-local-helper", "version": APP_VERSION,
                             "features": HELPER_FEATURES})
        elif parsed.path == "/api/inspect":
            self._handle_ip_call(parsed.query, lambda ip, q: {"scripts": inspect_scripts(ip)})
        elif parsed.path == "/api/config":
            self._handle_ip_call(parsed.query, lambda ip, q: read_config(ip, (q.get("key") or [""])[0]))
        elif parsed.path == "/api/memcheck":
            self._handle_memcheck(parsed.query)
        elif parsed.path == "/api/settings":
            settings, path = load_settings()
            self._json(200, dict({"ok": True, "path": path}, **settings))
        elif parsed.path in ("/", "/index.html"):
            self._serve_html()
        else:
            self._json(404, {"ok": False, "error": "not found"})

    def _handle_ip_call(self, query, func):
        params = urllib.parse.parse_qs(query)
        ip = (params.get("ip") or [""])[0].strip()
        try:
            if not RE_IP.match(ip):
                raise RpcError("ungueltige oder fehlende IP")
            self._json(200, dict({"ok": True}, **func(ip, params)))
        except RpcError as err:
            self._json(200, {"ok": False, "error": str(err)})
        except Exception as err:
            self._json(500, {"ok": False, "error": str(err)})

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
        if not self._origin_ok():
            self._reject()
            return
        if self.path != "/api/upload":
            self._json(404, {"ok": False, "error": "not found"})
            return
        # Nur JSON: verhindert, dass eine Seite den Upload als "einfache"
        # Anfrage (text/plain, ohne Preflight) ausloest.
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            self._json(415, {"ok": False, "error": "Content-Type application/json erwartet"})
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
            delete_others = data.get("delete_others", True) is not False
            if not ip or not code:
                raise RpcError("ip und code sind Pflichtfelder")
            print("Upload: %d Zeichen -> %s (Name: %s%s)"
                  % (len(code), ip, name,
                     "" if not force else (", andere Scripte loeschen" if delete_others
                                           else ", andere Scripte behalten")))
            result = upload_script(ip, name, code, key=key, force=force,
                                   confirm_ids=confirm_ids, delete_others=delete_others)
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


APP_VERSION = app_version()


def main():
    try:
        httpd = http.server.ThreadingHTTPServer((BIND_ADDRESS, PORT), Handler)
    except OSError as err:
        print("Fehler: konnte nicht auf %s:%s lauschen (%s)" % (BIND_ADDRESS, PORT, err),
              file=sys.stderr)
        return 1

    url = "http://%s:%s/" % (BIND_ADDRESS, PORT)
    print("Zendure Multi-Configurator %s - lokaler Helfer laeuft auf %s" % (APP_VERSION, url))
    print("Oeffne den Configurator automatisch im Browser...")
    try:
        webbrowser.open(url)
    except Exception as err:
        print("Konnte den Browser nicht automatisch oeffnen (%s) - Adresse manuell aufrufen: %s"
              % (err, url))
    print("Dieses Fenster offen lassen, solange hochgeladen wird.")
    print("Nach Konfiguration bzw. Update bitte dieses Fenster schliessen (Strg+C).")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nBeendet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())