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
find_html() findet sie dann im temporaeren Entpack-Ordner
sys._MEIPASS. Im normalen Skriptbetrieb sucht der Proxy die HTML erst im
selben Ordner wie das Script, danach im uebergeordneten Ordner (z.B.
Script in "proxy/", Dashboard eine Ebene hoeher im Repo).
Die Konfigurationsdatei liegt dagegen bewusst NICHT dort, sondern in
app_dir() (siehe unten) - sys._MEIPASS wird bei --onefile bei jedem Start
neu angelegt und danach wieder geloescht, eine dort abgelegte config.json
waere beim naechsten Start unwiderruflich weg.

Start:
    python3 zendure_proxy.py         normal, mit Zugriffsprotokoll
    python3 zendure_proxy.py -q      leise: Startmeldung ja, Zugriffe nein
    python3 zendure_proxy.py -s      still: gar keine Ausgabe (Fehler nach stderr)
    python3 zendure_proxy.py --no-update-check
                                     nie bei GitHub nach neueren Versionen fragen
    python3 zendure_proxy.py --bericht=PFAD
                                     bericht.html der Log-Auswertung (stat/auswertung)
                                     unter /bericht_zendure ausliefern; PFAD = Datei
                                     oder Ordner. Ohne Angabe: Umgebungsvariable
                                     ZENDURE_BERICHT, sonst Suche, siehe
                                     bericht_candidates()

Das Zugriffsprotokoll ist im Normalbetrieb recht gespraechig - die Seite
fragt alle 4 Sekunden an. Zum Einrichten ist es hilfreich, im Dauerbetrieb
eher nicht.

Browser beim Start: auf einem Rechner mit Bildschirm (Windows, macOS,
Linux-Desktop, exe) oeffnet der Proxy http://localhost:8000/ automatisch.
Ohne Bildschirm (Synology-Aufgabe, Docker/Home Assistant, SSH) laesst er
das bleiben - dort wuerde es nichts bringen oder im schlechtesten Fall
einen Konsolenbrowser starten. Erzwingen bzw. abschalten:
    python3 zendure_proxy.py --browser      immer oeffnen
    python3 zendure_proxy.py --no-browser   nie oeffnen

Beenden: Strg+C im Terminal.

Anpassen falls noetig: PORT, BIND_ADDRESS weiter unten. SHELLY_IP und
SHELLY_SCRIPT_ID nicht mehr hier eintragen - das erledigt die
Einrichtungsseite unter /setup.
"""

import base64
import http.server
import json
import os
import socket
import sys
import urllib.error
import urllib.request
import webbrowser
import re
import threading
import time

# ThingSpeak-Upload ist optional: fehlt ts_bridge.py, laeuft der Proxy
# ganz normal weiter, nur ohne /thingspeak, /thingsboard und ohne Mitlesen.
try:
    import ts_bridge
except ImportError:
    ts_bridge = None

# Versionsstand des Proxys. Proxy und Dashboard tragen dieselbe Nummer,
# unabhaengig vom Shelly-Script (ab 5.0.0, siehe CHANGELOG_dashboard.md).
# APP_TYPE ist ein fester Bezeichner fuer versions.json (Manifest-Workflow).
APP_TYPE = "zdmc-proxy"
APP_VERSION = "5.4.1"
APP_CHANGELOG = "CHANGELOG_dashboard.md"

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

# Browser beim Start oeffnen: None = automatisch (nur mit Bildschirm),
# True = immer (--browser), False = nie (--no-browser).
OPEN_BROWSER = None

HTML_FILENAME = "zendure-dashboard.html"
# Ab 4.0.0 ist das neue Design (Geraetekarten, Energiefluss) die Startseite /,
# das klassische Dashboard liegt unter /klassisch. Beide werden an denselben
# Orten gesucht; fehlt die neue Datei, zeigt / das klassische Dashboard.
HTML_FILENAME_NEU = "zendure-dashboard-neu.html"
# Bericht der Log-Auswertung (stat/auswertung/analyse.py), Adresse /bericht_zendure.
# BERICHT_PATH: --bericht=PFAD, sonst Umgebungsvariable ZENDURE_BERICHT.
BERICHT_FILENAME = "bericht.html"
BERICHT_PATH = None
CONFIG_FILENAME = "zendure_proxy_config.json"

# Update-Pruefung: der Proxy holt versions.json (vom GitHub-Workflow
# "Versions-Manifest" erzeugt) beim Start und danach alle 12 Stunden, im
# Hintergrund - keine Anfrage an das Dashboard wartet darauf. Ohne Internet
# bleibt einfach der letzte Stand (auch ueber einen Neustart, Datei in
# data_dir()) bzw. nichts; der Proxy laeuft normal weiter.
# Abschalten: --no-update-check (dann geht keine Anfrage an GitHub).
MANIFEST_URL = "https://raw.githubusercontent.com/surfer1264/Zendure-Stuff/manifest/versions.json"
UPDATE_CHECK = True
VERSIONS_CACHE_FILENAME = "zendure_versions_cache.json"
VERSIONS_TTL_OK = 12 * 3600
VERSIONS_TTL_FEHLER = 1800
VERSIONS_TIMEOUT = 8
# Nur diese Eintraege gibt /versions weiter (Dashboard braucht nicht alles).
VERSIONS_TYPES = ("zdmc-zendash-watch", "zdmc-dashboard", "zdmc-proxy",
                  "zdmc-controller", "zdmc-configurator")
VERSIONS_LOCK = threading.Lock()
VERSIONS = {"manifest": None, "geholt": 0.0, "ok": False, "laeuft": False, "fehler": None}

# Fehlerzaehler fuer Anfragen an den Shelly (nur im Speicher, beginnt um
# Mitternacht und bei jedem Start neu). Das Dashboard liest ihn ueber
# /proxy_fehler und zeigt ihn im Fuss der Seite.
#   timeout        Shelly hat nicht innerhalb von TIMEOUT s geantwortet
#   unreachable    keine Verbindung (aus, WLAN weg, falsche IP ...)
#   shelly         Shelly hat mit einem Fehlerstatus geantwortet
FEHLER_LOCK = threading.Lock()
FEHLER = {"tag": None, "timeout": 0, "unreachable": 0, "shelly": 0, "letzter": None}


def fehler_merken(art, endpoint, grund):
    now = time.localtime()
    tag = time.strftime("%Y-%m-%d", now)
    with FEHLER_LOCK:
        if FEHLER["tag"] != tag:
            FEHLER.update({"tag": tag, "timeout": 0, "unreachable": 0, "shelly": 0, "letzter": None})
        FEHLER[art] += 1
        FEHLER["letzter"] = {"zeit": time.strftime("%H:%M:%S", now), "art": art,
                             "endpoint": endpoint, "grund": grund}
    # Auch mit -q protokollieren (Home-Assistant-App), nur --silent schweigt
    say("[proxy] Fehler bei {}: {} ({})".format(endpoint, art, grund))


# Standort des Dashboard-Shellys fuer Sonnenauf-/-untergang im neuen Design.
# Gelesen ueber die Firmware-RPC Sys.GetConfig (nicht ueber das Script -
# kostet dort keinen Speicher), einmal pro Tag; bei Fehler neuer Versuch
# fruehestens nach 10 Minuten. Behalten werden nur Breite und Laenge.
STANDORT_LOCK = threading.Lock()
STANDORT = {"lat": None, "lon": None, "geholt": 0.0, "ok": False}
STANDORT_TTL_OK = 24 * 3600
STANDORT_TTL_FEHLER = 600


def standort_holen():
    now = time.time()
    with STANDORT_LOCK:
        alter = now - STANDORT["geholt"]
        if STANDORT["geholt"] and alter < (STANDORT_TTL_OK if STANDORT["ok"] else STANDORT_TTL_FEHLER):
            return {"lat": STANDORT["lat"], "lon": STANDORT["lon"]}
        STANDORT["geholt"] = now   # auch bei Fehler: nicht bei jedem Aufruf neu fragen
    lat = lon = None
    ok = False
    if is_configured():
        try:
            url = "http://{}/rpc/Sys.GetConfig".format(CONFIG["shelly_ip"])
            with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
                loc = (json.loads(resp.read().decode("utf-8")) or {}).get("location") or {}
            lat, lon = loc.get("lat"), loc.get("lon")
            if not (isinstance(lat, (int, float)) and isinstance(lon, (int, float))
                    and -90 <= lat <= 90 and -180 <= lon <= 180):
                lat = lon = None
            ok = True   # Antwort da; Standort kann trotzdem fehlen (dann null)
        except Exception as e:
            say("[proxy] Standort nicht lesbar: {}".format(e))
    with STANDORT_LOCK:
        STANDORT.update({"lat": lat, "lon": lon, "ok": ok})
    return {"lat": lat, "lon": lon}


def versions_cache_path():
    return os.path.join(data_dir(), VERSIONS_CACHE_FILENAME)


def version_tuple(v):
    """'4.1.0' -> (4, 1, 0); Nicht-Zahlen am Ende sortieren hinter Zahlen."""
    out = []
    for p in re.split(r"[.\-]", str(v or "")):
        out.append((0, int(p)) if p.isdigit() else (1, p))
    return tuple(out)


def manifest_kurz(m):
    """Nur das Noetige aus versions.json: Version, Aenderungen, Changelog-Link."""
    scripts = (m or {}).get("scripts") or {}
    out = {}
    for t in VERSIONS_TYPES:
        e = scripts.get(t)
        if isinstance(e, dict) and e.get("version"):
            out[t] = {"version": e.get("version"), "changes": e.get("changes") or [],
                      "notice": e.get("notice"), "changelogUrl": e.get("changelogUrl")}
    return {"generated": (m or {}).get("generated"), "scripts": out}


def versions_laden_aus_datei():
    try:
        with open(versions_cache_path(), encoding="utf-8") as fh:
            d = json.load(fh)
        with VERSIONS_LOCK:
            VERSIONS["manifest"] = d.get("manifest")
            VERSIONS["geholt"] = float(d.get("geholt") or 0)
            VERSIONS["ok"] = VERSIONS["manifest"] is not None
    except (OSError, ValueError):
        pass


def versions_holen():
    """Laeuft im Hintergrund-Thread. Fehler werden nur gemerkt, nie geworfen."""
    try:
        req = urllib.request.Request(MANIFEST_URL, headers={
            "User-Agent": "zendure-proxy/" + APP_VERSION, "Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=VERSIONS_TIMEOUT) as resp:
            m = manifest_kurz(json.loads(resp.read().decode("utf-8")))
        now = time.time()
        with VERSIONS_LOCK:
            VERSIONS.update({"manifest": m, "geholt": now, "ok": True, "fehler": None})
        try:
            with open(versions_cache_path(), "w", encoding="utf-8") as fh:
                json.dump({"geholt": now, "manifest": m}, fh)
        except OSError:
            pass
        neu = (m["scripts"].get(APP_TYPE) or {}).get("version")
        if neu and version_tuple(neu) > version_tuple(APP_VERSION):
            say("[proxy] Neuere Version {} verfuegbar (laeuft: {}) - "
                "https://github.com/surfer1264/Zendure-Stuff/releases/latest".format(neu, APP_VERSION))
    except Exception as e:
        with VERSIONS_LOCK:
            VERSIONS.update({"geholt": time.time(), "ok": VERSIONS["manifest"] is not None,
                             "fehler": str(e)[:200]})
        say("[proxy] Update-Pruefung nicht moeglich (offline?): {}".format(e))
    finally:
        with VERSIONS_LOCK:
            VERSIONS["laeuft"] = False


def versions_pruefen_falls_faellig():
    """Startet bei Bedarf einen Abruf im Hintergrund und kehrt sofort zurueck."""
    if not UPDATE_CHECK:
        return
    with VERSIONS_LOCK:
        alter = time.time() - VERSIONS["geholt"]
        ttl = VERSIONS_TTL_OK if VERSIONS["fehler"] is None and VERSIONS["ok"] else VERSIONS_TTL_FEHLER
        if VERSIONS["laeuft"] or (VERSIONS["geholt"] and alter < ttl):
            return
        VERSIONS["laeuft"] = True
    threading.Thread(target=versions_holen, name="versions", daemon=True).start()


def versions_stand():
    """Antwort fuer /versions: eigene Version + letzter bekannter Manifest-Stand."""
    versions_pruefen_falls_faellig()
    with VERSIONS_LOCK:
        m = VERSIONS["manifest"]
        geholt = VERSIONS["geholt"] if m is not None else None
    return {
        "proxy": {"type": APP_TYPE, "version": APP_VERSION},
        "updateCheck": UPDATE_CHECK,
        "manifest": m,
        "fetched": (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(geholt)) if geholt else None),
    }


def fehler_stand():
    tag = time.strftime("%Y-%m-%d")
    with FEHLER_LOCK:
        if FEHLER["tag"] != tag:
            return {"tag": tag, "timeout": 0, "unreachable": 0, "shelly": 0, "gesamt": 0, "letzter": None}
        d = dict(FEHLER)
    d["gesamt"] = d["timeout"] + d["unreachable"] + d["shelly"]
    return d


API_ENDPOINTS = ("config_api", "status_api", "kvs_set_api")
TIMEOUT = 5
# config_api braucht laenger: Das Script wartet bis zu 2 s, falls es gerade die
# Speicher abfragt, und liest dann die KVS - mit eigenem Controller-Shelly
# (kvsHost) per HTTP von dort, mit bis zu 5 s Timeout. Zusammen bis ~7 s;
# mit 5 s gab es hier gelegentlich Zeitueberschreitungen (/proxy_fehler).
CONFIG_TIMEOUT = 10
# kvs_set_api schreibt im Shelly-Script mehrere Keys nacheinander (je bis zu
# 5 s HTTP-Timeout, 0,5 s Pause dazwischen, vorher bis 2 s Warten auf den
# eigenen Poll). Mit 5 s brach der Proxy das Beenden des manuellen Ladens
# regelmaessig ab, obwohl alle Keys geschrieben wurden (Dashboard meldete
# "konnte nicht beendet werden").
KVS_SET_TIMEOUT = 25
SETUP_TEST_TIMEOUT = 4

IP_PATTERN = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")

# Kleines SVG-Icon: Ligatur "ZS" aus dem Designsystem ZendureDashboard
# (Nacht-Farben Teal -> Amber auf dunklem Hintergrund, wie im Kopf des
# Dashboards). Wird fuer favicon.ico,
# favicon.svg und alle gaengigen Apple-Touch-Icon-Pfade ausgeliefert -
# damit hat der Browser-Tab ein Icon UND die vielen 404-Zeilen im Log
# fuer diese automatischen Anfragen verschwinden.
FAVICON_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<rect width="64" height="64" rx="14" fill="#0B1220"/>
<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="106" y1="0" x2="173.5" y2="0"><stop offset="0" stop-color="#4FD1C5"/><stop offset="1" stop-color="#F2A93B"/></linearGradient></defs>
<g transform="translate(32 32) scale(0.25) translate(-125.75 -120)"><path d="M44 64 H112 L44 176 H181.5 C207.5 176 207.5 120 181.5 120 H173.5 C147.5 120 147.5 64 173.5 64 H207.5" stroke="url(#g)" stroke-width="26" stroke-linecap="round" stroke-linejoin="round" fill="none"/></g>
</svg>"""

# iOS kann fuer das Home-Bildschirm-Symbol KEIN SVG verwenden und zeigt
# sonst ein graues Ersatzsymbol mit Buchstaben. Deshalb fuer die Apple-Pfade
# dasselbe Motiv als echtes PNG (180 x 180, volle Flaeche - die runden Ecken
# setzt iOS selbst), hier als Base64 eingebettet, damit keine Zusatzdatei
# noetig ist.
APPLE_TOUCH_ICON_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAALQAAAC0CAIAAACyr5FlAAARrklEQVR42u2de3QUdZbH76+qOp3uvBPSJEBICIFAAFF5rILMHg4yIwwyiivjsDLDjCgOOjM6M+rMzpx193g8q646s+gwiisiqIyvHQVFRGUQ5f0KhEcSXiEJ5NF5d6ffVXf/qO5O54Gmq7o6Vcn9Hk6f0Kn61a9Tn75169a998eSMguAROpLHP0JSAQHieAgERwkgoNEcJAIDhLBQSI4SAQHieAgkQgOEsFBIjhIBAeJ4CARHCSCg0RwkAgOEsFBIhEcJIKDRHCQCA4SwUEiOEgEB4ngIBEcJIKDRCI4SAQHieAgERwkgoNEcJAIDhLBQSI4SINegoZDJ1nTJo9LKcrnTKaB/ZAMkCFyIHGIktvdVlnVUn4p4PXFcw6ZKXz+MKEgWxidxZl4BoAALPRLJT/7AlhW4z9ywdfhlowEx6gf3Jy35HtJo0fo5BvAEAUQeRQFkHgpIL+2n6s+vuHj2kNntDvumNzExTem31RiKcoRUkwogMhLogASAMbwKGfr/K/u6nx9d2fs/26xbW9tzsqY/MfVGdeW6OzaiTyK8j9BfpVZQen8p/v3vbTF7/bG8HAZqaYFs7K+f0NGSZ65xxHl/2rxGXeXe3+1obW+XdQpHNZROTNfekJIsurt2slQEkDqYTkEkDgpYAKps87+3oNrfK7Y8LFgju2P94wNjy+AxGPXEeU5AKIWH7PDjbf8V+NFeyBWA/IJlvTYnADGrvvv31lybTp0rBgDDpAD5FDiABlKHAMGEg/AQLIkJ6YMS7mw97Ra+8SxXywvuu+O0ZHjc/IrIseQA+QBOdTKRTCb2LRC8+Y9nag3OMbc/YPc+Tfp0+tmGIIDkAPkGXAYJEN+tY0Zbq+oabvSovgQqcmmJ397zdyZwzhEngELj8+AocQx5BA5QAao6f1hTjrv8cPB8z593crm/+hW/d6TsS4vHwAQERhDQAYMARgwQJix9DuKh09I4J/+w7Qpxeny5QIRGYPg+Bgcn4VvNQA1/ayr5iXrK85hHZUjWC36hSN0jWeMBV9RPnMYvKdkkF2UyyJOYFR6ZPWUglHJ8sgYHB8YMAQEAAQEBhj2M5QepZ8alsLlZfE6giOtpEjX0Zzw+UDsZjnkcwmACCazKbswR8HYS24tvGH6cAyNz7pbJgCUWZHnwCJI1U7TxiToCI6UcWN0DQd2o6TLckDQ/gMDRMgZF3Vg5rqpth/fNQEwdOFiQfuEXeMzRAQWnANixEVOM10zWk9w+NsdBjEcYcvRh08Q8PmjGna4LenhX1wfGbr8dp+Dae5zAEC7S9IRHI5zl3RtOPrwOaCHz4EIbXWtUQ27+ufXWy1C8LJ0lfHj73MAwIkan67gqDKszyF7CeBu72w4e6X/Q06eYptQnBn0YRnDnpYpOD7Inkd8fY6yar+O4PA2tTZ+fdgAPkf4+x32CeR7CgalH+4XA1HEnn941yRgQdsg+6FhCHv6HBDhc4DmPseHh91NDklfcY4zz6zztbQZNM7hae888fHB/o93/bQRYwszAREirEK/fA6N4xwN7eKjb7XpLp/D7+g8/cw6g8Y59r62w9vp6f943104HoOOKPbwOQY2zrF6fWsMn+DHMpjbdOB46e+f9bV2GCvO0VhefWbHkf4PlpqWWDIpWx4uHMMY8DhHk0O6+y/Neyu9+s0Ea9p/bN+KR+p37jNKnAMl/HLN36MabPoNeeGARjiGMbBxjg8Pu2c/3vDFSQ/oPNnH3+E8+cSLlS9sTJs0Lm3y+JSifM6kYb5ZxtSJ/TIc2CvOgciAndrydUtVfVRHnHnj6NA9SNjniDz3IZ8De/kcCMDgZLXP4YmB5ff68WSt/8gF3+ELvlh5oHFKE/S1ddj3HLHvOaKpRciaObU/cHSLcyAwxkACBszV0nFk46dRHTHBLIyfkM1AQvmEy1ZB6nv8bnEOCe0d4vI/15Vf9gMM+RzSOGjCQz/tr8+BvXwOxEPrtvjd0cWLRhdkhK0CYITPgb3iHMHfdsU5lj5bd7HBD5R9HgcVrrjDkputOM5hP111YdexaA9aUJQl+w2y5eh/nOPjQw5jkWFgOCy5toJlixXHOSRR2vvcZgXHLSjMYgx6+RzfHufYvLsDqG4lPip59N4o/NxecY4z733RUduoBI6xmXLcLKo4R7Xdv7/CTXDEQ7Y5M6JLcO8e5+hsbDn55naFh85NDZ/1/sc59pzuBKp4i8eMzQnFD61QE+c4tvZd0avk8m82C1zQz4guznG52U9wxMkPNWemK87nqD906vKe48oObU1OkPOD+ohzfKPPQXDEQ9a83Pw7F4DSfA70B47+6Q3lR08yywSEnuX24XP0mc9xuYng0F6THlvFeF7xs5WKt7a57a0q4EgIhr4gIs7Rj3yOy80BgkNb5dw8O23SOFD6bKXzSmPFpq2q/lg8Y8F4V3RxDodbJDg0FG9NLH5wOajI5zjx3AaVc/C4/VfxOb4lzpGdJhAcGqronqWmtBRQms9Rv/tQc2m5yjm4Xf5QL4To4hzD0wkOzZRcmJd3+3cV7y75/KfXbFI/DbfLF3nW+x/nsBEcoGE8dJWaBKrzr73vbWmPBRx+pijOQXBopZGL5qYWKy+a6qypu/TuJzGZScAvOp1eBXGOmeOtBEfsJSRbi1b9CNRlPqMUs1yY6ostCuIc865NzkjmCY4Ya9z9y0zJSYp3r9vxddvJyhjOp/ZSq4I4BwNYelMqwRFLpRYXjvz+XMW7i25P5do3Yjul2kttyvI5lv0zwRE7MY4refQ+NSOcXfe3mBfx1la3KcvnGJVleuz2TKBWkzHRqNvmJxfmKd69o/Ji7QefxXxW1RdbnE5fepLQLc4RkUOKkTmk0C2H9Oe3pI21ce/tczo9GDmmy4uXmgKtnRLB0S8lZKYXrVyqZoTy59drNLfD+2vmzSvoinNIXTmk3eIcGFG3IgXzWBdeZ731WjNcpTT+UpNYZQ+cawhsP+6OVb0r6KEnWGw18dc/Sy0uVLz75Y92Xt66U6O5+f3iTd8p4EDiIvp98XLDMfnnb+gJhlftCZZoYsPT+OIRphvHmZfPSVo8zZKSyFU3iU4vAvkcEFGKknPzbDXNQs6t+5t20ztd1uBweKOKcyjozzE+1/Rvt6Ueeypn/f2ZaRaO4AAAYAI/8Tf3qPJDX97sd2iblnf4QG1UcQ41tbILplo++0N28QgTwQH5dy605uUq90MrLlz55EutJ7l9W2VUcQ6VtbJ5WcL2x7LnT0kc0j5Hoi1ryn/+ihMUBhNRlEp/90wcKrmdDl/uiJT80akMJbn3LR/scIoa9SEVeHbbdAvHsX1nvUPUcox/cDlvVt7srOaDHc4LNfGZ6jtvn0Iprv05GGO/Xpjy8MKUoQhH1oxrbHNmKN7d19J+/tV34zbbxsbOf+yqjn9/jkcWpf5TkXlowcGZTBMe/qmaESrXviG6PfGc8+ubyuobXPHvz7Hu3oz43L/oBY6Cf12spql+28nK+i/2xnnOHk/gqecOen1inPtz2FL5v/wsY6jAYcm1Ff5kiarYwwB1nKq97HzxlRPx70M6b3Li0husQwKOiY/cq2b3qre2umrqBmryX+2r+/iz6vj3IX1scapJYIP8VtY2Z0bBMuUrLngam0/8x/+gOJC5/0fLmq0WoaQoeGcbn/VWUiycvUMsveQftJaDMyf0twHLVVTxwkYpvkv59ZYk4bo3K5966XRAxHj2IX1oQYrZxAYtHGNX3JGQmQYq+hfaddMcd+fehl8+UdrU5otbH1JbGr94mmVwwmHNy837l1uUf1/9/vLnXwU9qeKiY+W/l5ZXdcatD+mSGdbB6XNMffI3lpxsxbtf3PiBfe9R0Jk8Xumj3Y1HK5yBgDRqWILFBDzTcI23vCx+09edLm0e6w8YHDk3zx6twmy4rzSeePzPADrttF7X5P3qePuGTxpPVbntbYE2ZwAlTElkJhbjNd44xmpbxGNV/sGTCcZbE4sfWK5mhPI/rQcjaPcJx+4TjsgF+vKyeBPf7coyIoNfOTd5ar7Ch/K3z7Cu39U5eOAoWvlDU7ryB0gNXx5oPlwGBlR9m1jf1sdd99aj7rceHDZrvJKHjtMLE6xmpsWVhRuYwtfb5iv3Q72+ijUbYXDJ68fV61skped3gjapQNxAFL7ep6rwdcP7+l27A1SthrHjhMKOgxMHBxwjF81VkznsqqmrfmcbDFJt+sql0HKMFAwPh5BsHbdqmZoRTj39cgwLX/Wmf5z21LaIim5ojQ/HuPuXCclWNYWv7afOwuAVIhxQlAWYZmHGhkNl4WvA5Y554asO1ahocYz0JN7AcKgvfD3/yts6X702NnC0K7mspFmNbDlUFr46L9bUfPg5DAHZFVoOzqhwJGSkFd2zVG2iF+KQgEOR5bCYDGs5xj9wN29VXpBzeevOjvILMDRkNTOlD1kMCEf6pPE582Yp90OdrrPrNsOQUU66EtfS4ZEkNBocTOAnPqoqP7Tyr28GnK6hA0euIjg63Gi8y0r+nQuTRo8ANYWv23bBUJIyy9HhkgwGR6Itq3DFHaAiM1O/S1yT5VBd+PpjLkH5A6Hqv8ev8FUnSk5k0wuVPLWv0WZVBq3gyLiuxDZnuuLdvS1t59e/O9TMxl2zkiwJSu46ymr8hoGDM5lKfqvKDz279k3R5RlSZDAGK+cq7LiqUQMxTeAoWHarZYTywtfW0tPxL3wdcC2Zac0fpvDhalmNzxhwWHJtqvxQgDPPrx9qZCy63vLiCoW10RftgR69K0G3OaQqK9gCTpfcEyxYayrXrav7GVDiQeKCryIPyKEoYM93eJA4KfyOxId/i6HfRm4vydtE7Cv/Vop8R+QB+Yjt5XcAQ/3EgAHiyCxhdJbyx6q7z3iN0YfUNmdG1sxrVCYEZUydGOPLOaCAIo+i/MqjKIDEY0BAKfymACIviQKENkCRB6lr+27bSDwG5DcFkHhJ5CG4TV/jB8LbhDeI7af7v0MuA1S8KVnxFeJVSRJRbSavZR+qZQ1XpEHwNdRkAyL6mge3RFC23kps+3NEqq5NPHjOZwA4FKz4GrcbAejZ7e+b+2cEQQh2vw9ep0LrQka/3krM+3OE9f4BlwFqZa2jcgruWgQ6Tb+7ap/Q4JWfRWQEBLuLBq1L5IoIoXMf9Xor2tXKvvZlpwHgyFvyPV3HECK+2pF9QhHkLl6h1TC6bwPdeowGv/YK1luJbU+wsF7Z6bzSKuodDibwOfNn6xcO7NmzscvnCNqALqsgn0HW0+eAUNs3pmy9lZj353D58PltDgO0fcqeNU3NekraW45ukER2+0Po5hOwHj4Hhn0O+EafIx59SHvo5c+dbRqvwhEbOJILRoLOc/57+gTYy+fAiG92yOdgffkc0a8rG3Of41x94IVPHcZoGCd6vKDz5xZX9TnCVoGF7kjDbmcvnyMIQ9TrysbW53B5cfnaZrcPDQLHQHflGlJxjlWvtlTZA2CUPqTeplaDGA7DxznWbHd8XuYxUnvrpv2lHnuLjl2OQRLn2H/O9/SWDjBWY3wUxZr3PqE4h6Zxji1H3MteaJLQgIvx1H60M8596YdOnMPllR7a2Lrqf1vi4IRqAofo8pT+/lmdpm8ZOc5RccU/70n72/tcxl7Gq/X4mYMPPO5raac4h/o4hy+A20rdP/lr87wnG+NzbwJat5r0t3XUf7GHM5mSx4ziBEE/LgcnL+3Zqzc5A+QBGYZW4ALkILgyFxfai0Fw1c/QNsDkbUAK9xhlVxk/cpv+9CFtcohlNYGXPnf+8vXWd/a5zjcEBrBGmCVlFmgxrpBkSZ9cbLZlJqSnMZ4b6KsKBs9Z5PkDZCjxXT+HsOhry257gcQjynz0tSVyIPUeLfJYELY6wADQ5YUqe6C6OXC+IRBnr2Jg4CANAnH0JyARHCSCg0RwkAgOEsFBIjhIBAeJ4CARHCSCg0QiOEgEB4ngIBEcJIKDRHCQCA4SwUEiOEgEB4lEcJAIDhLBQSI4SAQHieAgERwkgoNEcJAIDhKJ4CARHCSCg0RwkAgOEsFBIjhIBAeJ4CANev0/1QWZN9djojcAAAAASUVORK5CYII="
)

ICON_PATHS = (
    "favicon.ico",
    "favicon.svg",
)
APPLE_ICON_PATHS = (
    "apple-touch-icon.png",
    "apple-touch-icon-precomposed.png",
    "apple-touch-icon-120x120.png",
    "apple-touch-icon-120x120-precomposed.png",
    "apple-touch-icon-180x180.png",
    "apple-touch-icon-180x180-precomposed.png",
)


# ---------------------------------------------------------------
# Pfade - zwei bewusst getrennte Vorstellungen von "hier":
#   find_html()     = mitgelieferte, GEBUENDELTE Datei (Dashboard-HTML).
#                      Bei --onefile im temporaeren sys._MEIPASS, sonst
#                      neben diesem Script oder eine Ebene hoeher. Nur
#                      zum LESEN.
#   app_dir()       = Ordner der exe bzw. des Scripts selbst. Hier landet
#                      die Konfiguration - muss exe-Neustarts ueberleben,
#                      sys._MEIPASS tut das nicht.
#   data_dir()      = app_dir(), ausser ZENDURE_DATA_DIR ist gesetzt
#                      (Home-Assistant-App: /data). Ablage fuer Shelly-
#                      Config und ThingSpeak-Keys.
# ---------------------------------------------------------------
def html_candidates(filename=HTML_FILENAME):
    """Alle Orte, an denen die Dashboard-HTML gesucht wird - in dieser
    Reihenfolge, die erste vorhandene gewinnt."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dirs = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        dirs.append(meipass)                       # in die exe eingebettet
    if getattr(sys, "frozen", False):
        dirs.append(app_dir())                     # neben der exe
    dirs.append(script_dir)                        # neben dem Script
    dirs.append(os.path.dirname(script_dir))       # eine Ebene hoeher
    seen, result = set(), []
    for d in dirs:
        path = os.path.normpath(os.path.join(d, filename))
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result


def find_html(filename=HTML_FILENAME):
    """Pfad der ersten gefundenen Dashboard-HTML, sonst None. Wird bei jedem
    Seitenaufruf neu ermittelt - eine nachtraeglich abgelegte oder
    verschobene HTML wirkt also ohne Neustart."""
    for path in html_candidates(filename):
        if os.path.isfile(path):
            return path
    return None


def bericht_candidates():
    """Orte fuer bericht.html, die erste vorhandene gewinnt. Mit --bericht
    bzw. ZENDURE_BERICHT nur dieser Ort (Datei oder Ordner). Sonst neben der
    Dashboard-HTML, neben der Konfiguration, neben exe/Script und im
    Repo-Ordner stat/auswertung."""
    fest = BERICHT_PATH or os.environ.get("ZENDURE_BERICHT")
    if fest:
        if os.path.isdir(fest):
            fest = os.path.join(fest, BERICHT_FILENAME)
        return [os.path.normpath(fest)]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dirs = []
    html = find_html()
    meipass = getattr(sys, "_MEIPASS", None)
    if html and not (meipass and html.startswith(os.path.abspath(meipass))):
        dirs.append(os.path.dirname(html))         # neben der Dashboard-HTML (nicht im exe-Entpackordner)
    dirs += [data_dir(), app_dir(),
            os.path.join(os.path.dirname(script_dir), "stat", "auswertung"),                      # Repo
            os.path.join(os.path.dirname(os.path.dirname(script_dir)), "stat", "auswertung")]     # Repo, local_helper/
    seen, result = set(), []
    for d in dirs:
        path = os.path.normpath(os.path.join(d, BERICHT_FILENAME))
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result


def find_bericht():
    """Wie find_html(): bei jedem Aufruf neu, ein frisch erzeugter Bericht wirkt sofort."""
    for path in bericht_candidates():
        if os.path.isfile(path):
            return path
    return None


def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def data_dir():
    """Ablage fuer die Konfigurationsdateien (Shelly-IP, ThingSpeak-Keys).
    Normal der Ordner neben exe bzw. Script. Die Home-Assistant-App setzt
    ZENDURE_DATA_DIR=/data, weil nur /data Updates der App uebersteht.
    Kein automatisches Erkennen von /data: auf einem NAS oder Raspberry Pi
    kann es zufaellig einen solchen Ordner geben."""
    d = os.environ.get("ZENDURE_DATA_DIR")
    if d and os.path.isdir(d):
        return d
    return app_dir()


def config_path():
    return os.path.join(data_dir(), CONFIG_FILENAME)


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
    var r = await fetch('setup', {{
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
      setTimeout(function(){{ location.href = './'; }}, 900);
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
        back_link='<p style="margin-top:16px"><a href="./">&larr; zurueck zum Dashboard</a></p>' if is_configured() else ""
    )


class Handler(http.server.BaseHTTPRequestHandler):

    def handle(self):
        # Browser hat die Verbindung waehrend der Antwort geschlossen (Tab zu,
        # Reload, Seitenwechsel). Harmlos - kein Traceback ins Log.
        try:
            super().handle()
        except ConnectionError:
            pass

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

        if endpoint in APPLE_ICON_PATHS:
            self.serve_apple_icon()
            return

        if path == "/setup":
            self.serve_setup()
            return

        if path in ("/thingspeak", "/thingsboard"):
            if ts_bridge is None:
                self.send_error(404, "Cloud-Upload nicht verfuegbar: ts_bridge.py fehlt neben dem Proxy")
                return
            if path == "/thingspeak":
                self._html(ts_bridge.page_html())
            else:
                self._html(ts_bridge.page_html_tb())
            return

        if path in ("/bericht_zendure", "/bericht_zendure/"):
            self.serve_bericht()
            return

        if path == "/standort":
            # Breite/Laenge des Dashboard-Shellys (oder null) fuer die Sonnenzeiten
            self._json(200, standort_holen())
            return

        if path == "/versions":
            # Eigene Version + zuletzt geholtes versions.json fuer die Fusszeile
            self._json(200, versions_stand())
            return

        if path == "/proxy_fehler":
            # Fehlerzaehler des Tages fuer die Fusszeile des Dashboards
            self._json(200, fehler_stand())
            return

        if path == "/bericht_vorhanden":
            # Abfrage des Dashboards, ob es den Link zum Bericht zeigen soll. Als GET,
            # weil Home-Assistant-Ingress HEAD-Anfragen nicht durchreicht.
            body = json.dumps({"vorhanden": find_bericht() is not None}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(body)
            return

        # Startseite: neues Design (ab 4.0.0), ohne dessen Datei das klassische
        if path == "/" or path == "":
            if not is_configured():
                self.serve_setup()
            elif find_html(HTML_FILENAME_NEU):
                self.serve_html(HTML_FILENAME_NEU)
            else:
                self.serve_html()
            return

        # Klassisches Dashboard. Relative Links und API-Aufrufe der Seite
        # ("./", "status_api") stimmen nur ohne Schraegstrich am Ende -
        # /klassisch/ leitet deshalb relativ weiter (auch hinter Ingress).
        if path == "/klassisch":
            if is_configured():
                self.serve_html()
            else:
                self.serve_setup()
            return
        if path == "/klassisch/":
            self._redirect("../klassisch")
            return

        # Alte Adresse des neuen Designs (3.5.12): Lesezeichen landen auf der
        # Startseite. Relativ, damit es auch hinter Ingress stimmt.
        if path == "/neu":
            self._redirect("./")
            return
        if path == "/neu/":
            self._redirect("../")
            return

        # Das bisherige Layout unter /b ist entfernt (3.5.12) - alte
        # Lesezeichen landen auf dem Dashboard. Relative Weiterleitung, damit
        # sie auch hinter einem Pfad-Praefix (z. B. Ingress) stimmt.
        if path == "/b" or path == "/b/":
            self.send_response(301)
            self.send_header("Location", "./" if path == "/b" else "../")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if endpoint in API_ENDPOINTS:
            self.proxy_to_shelly(endpoint, query)
            return

        self.send_error(404, "Nicht gefunden: " + path)

    def do_HEAD(self):
        # Nur fuer den Bericht: das Dashboard fragt so ab, ob es den Link zeigen soll
        path = self.path.split("?", 1)[0]
        if path in ("/bericht_zendure", "/bericht_zendure/") and find_bericht():
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store, must-revalidate")
            self.end_headers()
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_POST(self):
        if self.path in ("/thingspeak", "/thingsboard"):
            self.post_cloud(self.path)
            return
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

    def post_cloud(self, path):
        if ts_bridge is None:
            self._json(404, {"ok": False, "error": "ts_bridge.py fehlt neben dem Proxy"})
            return
        # Nur echtes JSON annehmen: erzwingt beim Browser einen CORS-Preflight,
        # den dieser Proxy nicht beantwortet - fremde Seiten koennen so keine
        # Keys unterschieben.
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            self._json(415, {"ok": False, "error": "JSON erwartet"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            if path == "/thingspeak":
                ok, error = ts_bridge.handle_post(data)
            else:
                ok, error = ts_bridge.handle_post_tb(data)
            self._json(200, {"ok": ok, "error": error})
        except Exception as e:
            self._json(500, {"ok": False, "error": "Interner Fehler: {}".format(e)})

    def _html(self, text):
        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location):
        self.send_response(301)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

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

    def serve_apple_icon(self):
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(APPLE_TOUCH_ICON_PNG)))
        self.send_header("Cache-Control", "public, max-age=86400")
        self.end_headers()
        self.wfile.write(APPLE_TOUCH_ICON_PNG)

    def serve_setup(self):
        body = setup_html().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def serve_bericht(self):
        path = find_bericht()
        if path is None:
            self.send_error(404, BERICHT_FILENAME + " nicht gefunden. Gesucht in: " + " | ".join(bericht_candidates()))
            return
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError as e:
            self.send_error(500, "Bericht nicht lesbar ({}): {}".format(path, e))
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # Bericht wird regelmaessig neu erzeugt - immer die aktuelle Fassung laden
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def serve_html(self, filename=HTML_FILENAME):
        path = find_html(filename)
        if path is None:
            self.send_error(404, filename + " nicht gefunden. Gesucht in: " + " | ".join(html_candidates(filename)))
            return
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError as e:
            msg = "Dashboard-HTML nicht lesbar ({}): {}".format(path, e)
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
            wait = (KVS_SET_TIMEOUT if endpoint == "kvs_set_api" else
                    CONFIG_TIMEOUT if endpoint == "config_api" else TIMEOUT)
            with urllib.request.urlopen(url, timeout=wait) as resp:
                body = resp.read()
                status = resp.status
                content_type = resp.headers.get("Content-Type", "application/json")
            if ts_bridge is not None and endpoint == "status_api" and status == 200:
                ts_bridge.feed(body)   # mitlesen; tut nichts, wenn ThingSpeak inaktiv
        except urllib.error.HTTPError as e:
            # Shelly hat selbst einen Fehlerstatus geliefert (z.B. 400/500) -
            # 1:1 durchreichen, damit die Seite die echte Fehlermeldung sieht.
            body = e.read()
            status = e.code
            content_type = "application/json"
            fehler_merken("shelly", endpoint, "HTTP {}".format(e.code))
        except Exception as e:
            # Zeitueberschreitung oder keine Verbindung. "art" liest das Dashboard.
            reason = getattr(e, "reason", e)
            art = "timeout" if isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in str(reason) else "unreachable"
            grund = str(reason)
            body = json.dumps({"success": False, "art": art,
                               "error": "Shelly nicht erreichbar: " + grund}).encode("utf-8")
            status = 502
            content_type = "application/json"
            fehler_merken(art, endpoint, grund)

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def fetch_status_for_bridge(query=""):
    """Wird von ts_bridge nur aufgerufen, wenn ein Cloud-Upload aktiv ist.
    query: "bg=wake" (ein Poll im Script anstossen) oder "bg=read" (nur
    lesen) - beide ohne den schnellen 8-s-Takt des Scripts (ab 3.5.11)."""
    if not is_configured():
        raise RuntimeError("Proxy noch nicht eingerichtet")
    url = shelly_base() + "status_api" + ("?" + query if query else "")
    with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
        return resp.read()


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
    global QUIET, SILENT, OPEN_BROWSER, BERICHT_PATH, UPDATE_CHECK
    for arg in sys.argv[1:]:
        if arg in ("-q", "--quiet"):
            QUIET = True
        elif arg in ("-s", "--silent"):
            SILENT = True
        elif arg == "--browser":
            OPEN_BROWSER = True
        elif arg == "--no-browser":
            OPEN_BROWSER = False
        elif arg == "--no-update-check":
            UPDATE_CHECK = False
        elif arg.startswith("--bericht="):
            BERICHT_PATH = arg.split("=", 1)[1] or None
        elif arg in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        else:
            sys.stderr.write("Unbekannte Option: {}  (-h fuer Hilfe)\n".format(arg))
            sys.exit(1)


def has_display():
    """Grobe Schaetzung, ob hier jemand vor einem Bildschirm sitzt.
    Windows/macOS: ja (auch die exe). Linux: nur mit X11/Wayland - eine
    Synology-Aufgabe, ein Docker-Container (Home Assistant) oder eine
    SSH-Sitzung haben beides nicht."""
    if sys.platform.startswith("win") or sys.platform == "darwin":
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def say(msg):
    if not SILENT:
        print(msg)


def main():
    parse_args()
    load_config()

    html = find_html()
    if html is None:
        # Warnung auch im stillen Betrieb - ohne die Datei liefert der Proxy
        # nur 404 aus, und die Ursache waere sonst nirgends zu sehen.
        sys.stderr.write("WARNUNG: " + HTML_FILENAME + " nicht gefunden. Gesucht in:\n")
        for path in html_candidates():
            sys.stderr.write("  " + path + "\n")
        sys.stderr.write("Lege die Datei in den Ordner dieses Scripts oder eine Ebene hoeher,\n")
        sys.stderr.write("oder pruefe --add-data beim exe-Build.\n\n")

    say("Zendure Dashboard Proxy " + APP_VERSION)
    if is_configured():
        say("  Shelly:   " + shelly_base())
    else:
        say("  Shelly:   noch nicht eingerichtet - Einrichtungsseite oeffnet automatisch")
    html_neu = find_html(HTML_FILENAME_NEU)
    say("  HTML:     " + (html_neu or (HTML_FILENAME_NEU + " nicht gefunden - Startseite zeigt das klassische Dashboard")))
    say("  Klassisch: http://localhost:{}/klassisch  ({})".format(PORT, html or "NICHT GEFUNDEN"))
    say("  Konfig:   " + config_path())
    bericht = find_bericht()
    say("  Bericht:  " + ("http://localhost:{}/bericht_zendure  ({})".format(PORT, bericht) if bericht
                          else "keiner gefunden (optional, --bericht=PFAD)"))
    url = "http://localhost:{}/".format(PORT)
    say("  Lokal:    " + url)
    if BIND_ADDRESS == "0.0.0.0":
        say("  Im Netz:  http://{}:{}/  (von jedem Rechner im selben Netzwerk)".format(get_lan_ip(), PORT))
    if QUIET:
        say("  Protokoll: aus (-q)")
    if ts_bridge is not None:
        say("  ThingSpeak:  http://localhost:{}/thingspeak".format(PORT))
        say("  ThingsBoard: http://localhost:{}/thingsboard".format(PORT))
    else:
        say("  Cloud-Upload: nicht verfuegbar (ts_bridge.py fehlt)")
    say("(Strg+C zum Beenden)\n")

    if UPDATE_CHECK:
        versions_laden_aus_datei()
        # Beim Start immer einmal frisch fragen (Hinweis auf neuere Version
        # in der Konsole), egal wie alt der gespeicherte Stand ist.
        with VERSIONS_LOCK:
            VERSIONS["geholt"] = 0.0
        versions_pruefen_falls_faellig()
    else:
        say("  Update-Pruefung: aus (--no-update-check)")

    if ts_bridge is not None:
        ts_bridge.LOG = not (QUIET or SILENT)
        ts_bridge.start(data_dir(), fetch_status_for_bridge)

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

    open_browser = OPEN_BROWSER if OPEN_BROWSER is not None else has_display()
    if open_browser:
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
