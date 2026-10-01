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

  4. Log-Aufzeichnung (POST /api/logcapture startet einen Hintergrund-Job,
     GET /api/logcapture?job=... liefert Stand und Ergebnis): stoppt ein Script, liest den
     Debug-Log-Stream des Shelly per WebSocket, startet das Script wieder
     und liefert das Log an den Browser (siehe capture_log()).

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

import base64
import datetime
import hashlib
import http.server
import json
import os
import re
import socket
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
HELPER_FEATURES = ["script_check", "keep_others", "read_config", "settings", "log_capture", "shelly_auth"]
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


class AuthRequired(RpcError):
    """Shelly verlangt ein Passwort (HTTP 401). wrong=True: das gemerkte
    Passwort wurde abgelehnt."""

    def __init__(self, ip, wrong=False):
        self.ip = ip
        self.wrong = wrong
        RpcError.__init__(self, (
            "Das Passwort fuer den Shelly %s ist falsch." if wrong else
            "Der Shelly %s ist passwortgeschuetzt - bitte Passwort eingeben.") % ip)


# ---------------------------------------------------------------
# Passwortgeschuetzte Shellys (Gen2+/Gen3): HTTP-Digest mit SHA-256,
# Benutzer immer "admin". Passwoerter liegen NUR im Arbeitsspeicher des
# Helfers (je IP), nie in einer Datei - nach dem Beenden sind sie weg.
# ---------------------------------------------------------------
SHELLY_USER = "admin"
SHELLY_PASSWORDS = {}      # ip -> Passwort
_DIGEST = {}               # ip -> {"realm", "nonce", "algorithm", "nc"}
_DIGEST_LOCK = threading.Lock()


def set_shelly_password(ip, password):
    with _DIGEST_LOCK:
        _DIGEST.pop(ip, None)
        if password:
            SHELLY_PASSWORDS[ip] = password
        else:
            SHELLY_PASSWORDS.pop(ip, None)


def _parse_challenge(header):
    if not header or not header.lower().startswith("digest"):
        return None
    fields = dict((k.lower(), v1 or v2) for k, v1, v2 in
                  re.findall(r'(\w+)\s*=\s*(?:"([^"]*)"|([^\s,]+))', header[6:]))
    if "nonce" not in fields:
        return None
    return {"realm": fields.get("realm", ""), "nonce": fields["nonce"],
            "algorithm": (fields.get("algorithm") or "SHA-256").upper(), "nc": 0}


def _remember_challenge(ip, header):
    ch = _parse_challenge(header)
    if ch:
        with _DIGEST_LOCK:
            _DIGEST[ip] = ch
    return ch


def _digest_header(ip, method, uri):
    """Authorization-Header aus der zuletzt gesehenen Challenge, oder None."""
    with _DIGEST_LOCK:
        pw = SHELLY_PASSWORDS.get(ip)
        ch = _DIGEST.get(ip)
        if not pw or not ch:
            return None
        ch["nc"] += 1
        nc = "%08x" % ch["nc"]
        realm, nonce, algo = ch["realm"], ch["nonce"], ch["algorithm"]
    h = (lambda x: hashlib.md5(x.encode("utf-8")).hexdigest()) if algo == "MD5" else \
        (lambda x: hashlib.sha256(x.encode("utf-8")).hexdigest())
    cnonce = base64.b16encode(os.urandom(8)).decode("ascii").lower()
    ha1 = h("%s:%s:%s" % (SHELLY_USER, realm, pw))
    ha2 = h("%s:%s" % (method, uri))
    response = h("%s:%s:%s:%s:auth:%s" % (ha1, nonce, nc, cnonce, ha2))
    return ('Digest username="%s", realm="%s", nonce="%s", uri="%s", algorithm=%s, '
            'response="%s", qop=auth, nc=%s, cnonce="%s"'
            % (SHELLY_USER, realm, nonce, uri, algo, response, nc, cnonce))


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
    body = None
    for attempt in range(3):
        headers = {"Content-Type": "application/json"}
        auth = _digest_header(ip, "POST", "/rpc")
        if auth:
            headers["Authorization"] = auth
        req = urllib.request.Request("http://%s/rpc" % ip, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = json.loads(resp.read().decode("utf-8", "surrogateescape" if lenient else "strict"))
            break
        except urllib.error.HTTPError as err:
            detail = err.read().decode("utf-8", "replace")[:200]
            if err.code == 401:
                ch = _remember_challenge(ip, err.headers.get("WWW-Authenticate"))
                if ip not in SHELLY_PASSWORDS or not ch:
                    raise AuthRequired(ip)
                # 1. Versuch ohne/mit veralteter Nonce -> mit neuer Nonce
                # wiederholen; wird auch das abgelehnt, ist das Passwort falsch.
                if attempt == 0 and not auth:
                    continue
                if attempt < 2 and 'stale=true' in (err.headers.get("WWW-Authenticate") or "").lower():
                    continue
                if attempt == 0:
                    continue
                raise AuthRequired(ip, wrong=True)
            raise RpcError("%s: HTTP %s %s" % (method, err.code, detail))
        except urllib.error.URLError as err:
            raise RpcError("%s: Shelly %s nicht erreichbar (%s)" % (method, ip, err.reason))
    if body is None:
        raise AuthRequired(ip, wrong=True)

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


# ---------------------------------------------------------------
# Log-Aufzeichnung (POST /api/logcapture)
#
# Stoppt ein Script, liest den Debug-Log-Stream des Shelly per WebSocket
# (ws://<IP>/debug/log, wie Script_poller/shelly_log_grabber.py), startet
# das Script wieder und zeichnet eine feste Zeit lang auf. So ist der
# komplette Script-Start im Log - inklusive Fehlermeldungen, die als
# Systemmeldung kommen (z.B. "Uncaught ..." oder zu wenig Speicher).
#
# Eigener kleiner WebSocket-Client, damit der Helfer weiterhin ohne
# "pip install" auskommt (nur Standardbibliothek).
# ---------------------------------------------------------------
LOG_DEFAULT_SECONDS = 140
LOG_MIN_SECONDS = 10
LOG_MAX_SECONDS = 600
LOG_MAX_LINES = 50000
SCRIPT_FD_BASE = 100         # fd = 100 + Script-ID, siehe shelly_log_grabber.py


class WsLogStream:
    """Minimaler WebSocket-Client (RFC 6455), nur Lesen von Textframes."""

    def __init__(self, ip, timeout=5):
        self.buf = b""
        self.frag = b""
        for attempt in range(2):
            head = self._handshake(ip, timeout)
            status = head.split(b"\r\n", 1)[0]
            if b" 101" in status:
                self.buf = head.split(b"\r\n\r\n", 1)[1]
                return
            self.close()
            if b" 401" in status:
                m = re.search(rb"(?im)^www-authenticate:\s*(.+?)\r?$", head)
                ch = _remember_challenge(ip, m.group(1).decode("latin-1") if m else "")
                if ip in SHELLY_PASSWORDS and ch and attempt == 0:
                    continue
                raise AuthRequired(ip, wrong=ip in SHELLY_PASSWORDS)
            raise RpcError("Log-Stream von %s nicht verfuegbar (%s)"
                           % (ip, status.decode("latin-1", "replace") or "keine Antwort"))

    def _handshake(self, ip, timeout):
        self.sock = socket.create_connection((ip, 80), timeout=timeout)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        auth = _digest_header(ip, "GET", "/debug/log")
        req = ("GET /debug/log HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\n"
               "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
               "Sec-WebSocket-Version: 13\r\n%s\r\n"
               % (ip, key, ("Authorization: %s\r\n" % auth) if auth else ""))
        self.sock.sendall(req.encode("ascii"))
        head = b""
        while b"\r\n\r\n" not in head:
            chunk = self.sock.recv(1024)
            if not chunk:
                break
            head += chunk
            if len(head) > 16384:
                break
        return head

    def _need(self, n, deadline):
        while len(self.buf) < n:
            left = deadline - time.time()
            if left <= 0:
                return False
            self.sock.settimeout(min(left, 1.0))
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                continue
            if not chunk:
                raise RpcError("Log-Stream wurde vom Shelly beendet")
            self.buf += chunk
        return True

    def _take(self, n):
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def _send(self, opcode, payload=b""):
        mask = os.urandom(4)
        header = bytes([0x80 | opcode, 0x80 | len(payload)]) + mask
        body = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        try:
            self.sock.sendall(header + body)
        except OSError:
            pass

    def read_message(self, deadline):
        """Naechste Textnachricht oder None, wenn die Zeit abgelaufen ist."""
        while True:
            if not self._need(2, deadline):
                return None
            b0, b1 = self.buf[0], self.buf[1]
            length = b1 & 0x7F
            hdr = 2
            if length == 126:
                if not self._need(4, deadline):
                    return None
                length = int.from_bytes(self.buf[2:4], "big")
                hdr = 4
            elif length == 127:
                if not self._need(10, deadline):
                    return None
                length = int.from_bytes(self.buf[2:10], "big")
                hdr = 10
            masked = bool(b1 & 0x80)
            total = hdr + (4 if masked else 0) + length
            if not self._need(total, deadline):
                return None
            frame = self._take(total)
            payload = frame[hdr + (4 if masked else 0):]
            if masked:
                m = frame[hdr:hdr + 4]
                payload = bytes(b ^ m[i % 4] for i, b in enumerate(payload))
            opcode, fin = b0 & 0x0F, bool(b0 & 0x80)
            if opcode == 0x9:                       # Ping -> Pong
                self._send(0xA, payload[:125])
                continue
            if opcode == 0x8:                       # Close
                raise RpcError("Log-Stream wurde vom Shelly beendet")
            if opcode in (0x1, 0x0):
                self.frag += payload
                if fin:
                    text, self.frag = self.frag.decode("utf-8", "replace"), b""
                    return text
            # Binaer-/Pong-Frames ignorieren

    def close(self):
        try:
            self._send(0x8)
            self.sock.close()
        except (OSError, AttributeError):
            pass


# Maskierung: Logs werden gern in Issues/Foren geteilt. Geheimnisse und
# Kennungen kommen deshalb gar nicht erst in die Datei. IP-Adressen bleiben
# stehen (fuer die Fehlersuche noetig, im Heimnetz unkritisch).
# Der Shelly schreibt JSON teils mehrfach escaped (\"sn\\\":\\\"...),
# deshalb erlauben die Muster Backslashes vor den Anfuehrungszeichen.
_Q = r'\\*"'                   # optional escaptes Anfuehrungszeichen
_SECRET_NAMES = r'(?:api_?key|apikey|token|access_token|auth|authorization|password|passwd|pwd|pass|secret|phone|chat_?id)'
LOG_MASKS = [
    # Home-Assistant-Webhook-ID
    (re.compile(r'(/api/webhook/)[^\s"\\/?&]+'), r'\1***'),
    # ntfy-Topic, Telegram-Bot-Token
    (re.compile(r'(ntfy\.sh/)[^\s"\\/?&]+'), r'\1***'),
    (re.compile(r'(/bot)\d+:[A-Za-z0-9_-]+'), r'\1***'),
    # Zugangsdaten in URLs: http://user:pass@host
    (re.compile(r'(\w+://)[^/\s:@"\\]+:[^/\s@"\\]+@'), r'\1***:***@'),
    # URL-/Formular-Parameter: apikey=..., token=..., phone=...
    (re.compile(r'(\b' + _SECRET_NAMES + r'=)[^&\s"\\]+', re.IGNORECASE), r'\1***'),
    # JSON-Felder: "apikey":"...", "password":"..."
    (re.compile(r'(' + _Q + _SECRET_NAMES + _Q + r'\s*:\s*' + _Q + r')[^"\\]+', re.IGNORECASE), r'\1***'),
]
# Seriennummern: nur die letzten 4 Zeichen stehen lassen
RE_MASK_SN = re.compile(r'(' + _Q + r'(?:sn|serial|serialNumber|deviceSn)' + _Q + r'\s*:\s*' + _Q + r')([A-Za-z0-9]+)',
                        re.IGNORECASE)


def mask_secrets(text):
    for pattern, repl in LOG_MASKS:
        text = pattern.sub(repl, text)
    return RE_MASK_SN.sub(lambda m: m.group(1) + "***" + m.group(2)[-4:], text)


def _log_line(message, sid, only_script):
    """Wandelt eine Log-Nachricht in Textzeilen um (oder [] wenn gefiltert)."""
    try:
        data = json.loads(message)
    except ValueError:
        data = {"data": message}
    if not isinstance(data, dict):
        data = {"data": str(data)}
    text = str(data.get("data") or data.get("msg") or data.get("text") or "").rstrip("\r\n")
    fd = data.get("fd")
    script_id = fd - SCRIPT_FD_BASE if isinstance(fd, int) and fd >= SCRIPT_FD_BASE else None
    if only_script and script_id != sid:
        return []
    ts = data.get("ts")
    if isinstance(ts, (int, float)) and ts > 1e9:
        stamp = datetime.datetime.fromtimestamp(ts)
    else:
        stamp = datetime.datetime.now()
    prefix = "[%s] " % stamp.strftime("%H:%M:%S.%f")[:-3]
    if script_id is not None and not only_script:
        prefix += "[Script %d] " % script_id
    return [prefix + mask_secrets(part) for part in (text.split("\n") if text else [""])]


def capture_log(ip, sid, seconds=LOG_DEFAULT_SECONDS, only_script=True, progress=None):
    """Script stoppen, Log-Stream oeffnen, Script starten, aufzeichnen.
    Das Script wird in jedem Fall wieder gestartet (finally)."""
    seconds = max(LOG_MIN_SECONDS, min(LOG_MAX_SECONDS, int(seconds)))
    scripts = {s.get("id"): s for s in rpc(ip, "Script.List").get("scripts", [])}
    if sid not in scripts:
        raise RpcError("Script %s gibt es auf %s nicht" % (sid, ip))
    name = scripts[sid].get("name") or ""
    was_running = bool(scripts[sid].get("running"))

    # Debug-Log per WebSocket muss eingeschaltet sein; nur fuer die
    # Aufzeichnung einschalten und danach den alten Zustand wiederherstellen.
    debug_ws = ((rpc(ip, "Sys.GetConfig").get("debug") or {}).get("websocket") or {})
    switched_on = False
    if not debug_ws.get("enable"):
        res = rpc(ip, "Sys.SetConfig", {"config": {"debug": {"websocket": {"enable": True}}}})
        if res.get("restart_required"):
            raise RpcError("Auf %s wurde das Debug-Log eingeschaltet, dafuer ist ein Neustart "
                           "des Shelly noetig. Bitte den Shelly einmal neu starten und die "
                           "Aufzeichnung erneut starten." % ip)
        switched_on = True
        time.sleep(0.5)

    started = datetime.datetime.now()
    lines = ["# Log-Aufzeichnung Zendure Multi-Configurator %s" % APP_VERSION,
             "# Shelly %s, Script %s \"%s\", %d s, %s" % (
                 ip, sid, name, seconds,
                 "nur Script-Ausgaben" if only_script else "alle Meldungen (ungefiltert)"),
             "# Sensible Daten (Webhook-IDs, Tokens, API-Keys, Passwoerter, Telefonnummern) sind "
             "maskiert, Seriennummern bis auf die letzten 4 Zeichen",
             "# Beginn %s" % started.strftime("%Y-%m-%d %H:%M:%S"), ""]
    ws = None
    running_after = None
    try:
        ws = WsLogStream(ip)
        lines.append("# --- Script %s wird gestoppt ---" % sid)
        if was_running:
            rpc(ip, "Script.Stop", {"id": sid})
        time.sleep(1.0)
        lines.append("# --- Script %s wird gestartet ---" % sid)
        rpc(ip, "Script.Start", {"id": sid})
        deadline = time.time() + seconds
        if progress:
            progress(len(lines), deadline)
        while len(lines) < LOG_MAX_LINES:
            msg = ws.read_message(deadline)
            if msg is None:
                break
            lines.extend(_log_line(msg, sid, only_script))
            if progress:
                progress(len(lines))
        lines.append("")
        lines.append("# Ende %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    finally:
        if ws:
            ws.close()
        try:
            running_after = bool(rpc(ip, "Script.GetStatus", {"id": sid}).get("running"))
            if not running_after:
                rpc(ip, "Script.Start", {"id": sid})
                time.sleep(1.5)
                running_after = bool(rpc(ip, "Script.GetStatus", {"id": sid}).get("running"))
        except RpcError:
            pass
        if switched_on:
            try:
                rpc(ip, "Sys.SetConfig", {"config": {"debug": {"websocket": {"enable": False}}}})
            except RpcError:
                pass
    lines.append("# Script laeuft nach der Aufzeichnung: %s"
                 % ("ja" if running_after else ("NEIN" if running_after is False else "unbekannt")))
    return {"log": "\n".join(lines) + "\n", "lines": len(lines), "name": name,
            "running": running_after, "seconds": seconds}


# Aufzeichnungen laufen als Hintergrund-Job: bis zu 10 Minuten sind zu
# lang fuer einen einzelnen HTTP-Aufruf (Firefox bricht nach 300 s ab).
# Der Browser startet den Job per POST und fragt den Stand per GET ab.
LOG_JOBS = {}
LOG_JOBS_LOCK = threading.Lock()
LOG_JOB_KEEP = 3600          # fertige Jobs nach 1 Stunde verwerfen


def start_log_job(ip, sid, seconds, only_script):
    now = time.time()
    with LOG_JOBS_LOCK:
        for jid in [j for j, v in LOG_JOBS.items()
                    if v["state"] != "running" and now - v["created"] > LOG_JOB_KEEP]:
            del LOG_JOBS[jid]
        if any(v["state"] == "running" and v["ip"] == ip for v in LOG_JOBS.values()):
            raise RpcError("Auf %s laeuft bereits eine Log-Aufzeichnung" % ip)
        jid = base64.urlsafe_b64encode(os.urandom(9)).decode("ascii")
        job = {"ip": ip, "sid": sid, "state": "running", "created": now,
               "lines": 0, "deadline": None, "result": None, "error": None}
        LOG_JOBS[jid] = job

    def progress(n, deadline=None):
        job["lines"] = n
        if deadline:
            job["deadline"] = deadline

    def run():
        try:
            job["result"] = capture_log(ip, sid, seconds, only_script, progress)
            job["state"] = "done"
            print("Log-Aufzeichnung %s Script %s fertig: %d Zeilen, Script laeuft: %s"
                  % (ip, sid, job["result"]["lines"], job["result"]["running"]))
        except Exception as err:   # alles an den Browser melden
            job["error"] = str(err)
            job["auth_required"] = isinstance(err, AuthRequired)
            job["state"] = "error"
            print("Log-Aufzeichnung %s Script %s fehlgeschlagen: %s" % (ip, sid, err))

    threading.Thread(target=run, daemon=True).start()
    return jid


def log_job_status(jid):
    job = LOG_JOBS.get(jid)
    if not job:
        raise RpcError("Aufzeichnung nicht gefunden (Helfer neu gestartet?)")
    out = {"state": job["state"], "lines": job["lines"]}
    if job["deadline"]:
        out["remaining"] = max(0, int(round(job["deadline"] - time.time())))
    if job["state"] == "done":
        out.update(job["result"])
    elif job["state"] == "error":
        out["error"] = job["error"]
        if job.get("auth_required"):
            out.update(auth_required=True, ip=job["ip"])
    return out


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

    def _err(self, err):
        out = {"ok": False, "error": str(err)}
        if isinstance(err, AuthRequired):
            out.update(auth_required=True, ip=err.ip, wrong_password=err.wrong)
        self._json(200, out)

    def _handle_auth(self):
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            self._json(415, {"ok": False, "error": "Content-Type application/json erwartet"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            ip = (data.get("ip") or "").strip()
            if not RE_IP.match(ip):
                raise RpcError("ungueltige oder fehlende IP")
            password = data.get("password") or ""
            set_shelly_password(ip, password)
            if password:
                try:
                    rpc(ip, "Script.List")        # Passwort sofort pruefen
                except AuthRequired:
                    set_shelly_password(ip, "")
                    raise AuthRequired(ip, wrong=True)
                print("Passwort fuer %s gesetzt (nur im Arbeitsspeicher)" % ip)
            self._json(200, {"ok": True})
        except RpcError as err:
            self._err(err)
        except Exception as err:
            self._json(500, {"ok": False, "error": str(err)})

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
        elif parsed.path == "/api/logcapture":
            params = urllib.parse.parse_qs(parsed.query)
            try:
                st = log_job_status((params.get("job") or [""])[0])
                if st["state"] == "error":
                    self._json(200, dict(st, ok=False))
                else:
                    self._json(200, dict({"ok": True}, **st))
            except RpcError as err:
                self._err(err)
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
            self._err(err)
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
            self._err(err)
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
        if self.path == "/api/logcapture":
            self._handle_logcapture()
            return
        if self.path == "/api/auth":
            self._handle_auth()
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
            self._err(err)
        except Exception as err:
            self._json(500, {"ok": False, "error": str(err)})


    def _handle_logcapture(self):
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            self._json(415, {"ok": False, "error": "Content-Type application/json erwartet"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            ip = (data.get("ip") or "").strip()
            if not RE_IP.match(ip):
                raise RpcError("ungueltige oder fehlende IP")
            sid = data.get("id")
            if not isinstance(sid, int):
                raise RpcError("Script-ID fehlt")
            seconds = data.get("seconds") or LOG_DEFAULT_SECONDS
            only_script = data.get("only_script", True) is not False   # Standard: gefiltert
            print("Log-Aufzeichnung: %s Script %s, %s s%s"
                  % (ip, sid, seconds, ", nur Script-Ausgaben" if only_script else ", ungefiltert"))
            rpc(ip, "Script.List")   # Erreichbarkeit/Passwort vorab pruefen
            self._json(200, {"ok": True, "job": start_log_job(ip, sid, seconds, only_script)})
        except RpcError as err:
            self._err(err)
        except (OSError, ValueError) as err:
            self._json(200, {"ok": False, "error": "Log-Aufzeichnung fehlgeschlagen: %s" % err})
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