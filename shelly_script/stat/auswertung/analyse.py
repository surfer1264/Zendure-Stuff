"""Statistische Auswertung der Multi-Device-Controller-Logs (ein oder mehrere Zendure-Speicher).
Die Logs schreibt Script_poller/shelly_log_grabber.py mit (show_script_prefix und daily_log_rotation an).

Aufruf (aus beliebigem Verzeichnis):
    python analyse.py              # Logs aus LOG_ORDNER (Standard: Ordner über diesem Skript)
    python analyse.py <logordner>  # anderer Log-Ordner (überschreibt LOG_ORDNER)
    python analyse.py --neu        # Zwischenspeicher verwerfen, alle Logs neu auswerten

Arbeitsweise: Jede Logdatei (ein Tag) wird einmal ausgewertet; das Ergebnis landet im Ordner cache/.
Spätere Läufe lesen nur neue oder geänderte Logs und setzen den Rest aus dem Zwischenspeicher zusammen.
Abgeschlossene Tage werden auf Wunsch gepackt (.log -> .log.gz, etwa 25-mal kleiner); gepackte Logs
werden genauso gelesen. Ändern sich Einstellungen oder Version, wird automatisch neu gerechnet.

Erzeugt im Ordner dieses Skripts:
    verlauf_15min.csv  15-Minuten-Mittel: Netzsaldo, Speicher-Ausgang, SOC und Ausgang je Gerät
    tage.csv           Tageswerte: Energie, SOC-Spanne, Regelgüte (gegen den jeweils gültigen Sollwert),
                       Sollwert, Stellbefehle, Störungen, Sparmodus, Zyklusdauer (ab Controller 5.2.6),
                       Klassen der Zyklusdauer zyklus_k0..k6 (ab Controller 5.3.6)
    tagesprofil.csv    Je Uhrzeit-Stunde: Netzsaldo und Speicher-Ausgang (Mittel und Verteilung über die Tage),
                       SOC-Verteilung je Gerät (Min, Perzentile, Max)
    geraete.csv        Ausgewertete Geräte (Name wie im Log, Spaltenschlüssel) – für bericht.py
    bericht.html       Bericht zum Öffnen im Browser, erzeugt von bericht.py
    cache/             Zwischenspeicher, eine Datei je Logdatei

Benötigt: Python 3.8+ und pandas (pip install pandas).
Alle Einstellungen stehen im Block EINSTELLUNGEN direkt unter den Imports (Standardwerte).
Eigene Werte gehören in analyse_config.json neben diesem Skript – die bleibt bei Updates erhalten.
bericht.py hat keine eigenen Einstellungen, es übernimmt alles von hier.
"""
import glob
import gzip
import hashlib
import json
import os
import re
import shutil
import sys
import time
import unicodedata

import numpy as np
import pandas as pd

# Version der Auswertung (analyse.py + bericht.py gemeinsam); erscheint in der Ausgabe und im Bericht
VERSION = "1.7.0"

# =============================================================================
# EINSTELLUNGEN – nur hier anpassen
# =============================================================================

# --- Logdateien --------------------------------------------------------------
# Ordner mit den Logs. None = Ordner über diesem Skript (also ../).
# Ein Ordner als Aufrufparameter hat Vorrang.
LOG_ORDNER = None
# Muster der Logdateinamen (glob: * = beliebige Zeichen, ? = ein Zeichen).
# Gepackte Logs (Muster + ".gz") werden automatisch mitgelesen. Sortierung nach Namen.
LOG_MUSTER = "shelly_debug_*.log"
# Abgeschlossene Logs nach der Auswertung packen (.log -> .log.gz). Das Original wird erst
# gelöscht, wenn die gepackte Datei geprüft ist. Das jüngste Log bleibt immer ungepackt.
LOGS_PACKEN = True

# --- Auswertungszeitraum (gilt für alle CSV-Dateien und den Bericht) ---------
# Format "JJJJ-MM-TT", jeweils einschließlich. None = keine Grenze.
# Tageswerte, Kennzahlen und Tagesprofil im Bericht nutzen nur volle Tage
# (siehe VOLLER_TAG_H) – angebrochene Tage am Rand fallen also automatisch weg.
# Bei neuen Logs muss hier nichts geändert werden, solange ZEITRAUM_BIS = None ist.
ZEITRAUM_VON = "2026-10-06"        # 20.09. ist ein Einzeltag 16 Tage davor und bleibt außen vor
ZEITRAUM_BIS = None                # None = bis zum Ende der Logs

# --- Geräte ------------------------------------------------------------------
# None = alle Geräte, die im Log vorkommen, in der Reihenfolge ihres ersten Auftretens.
# Oder eine Liste mit Namen wie im Log ("  SF2400: SOC ..."), z. B. ["SF2400", "SF800"] oder ["Keller Süd", "SF800"]:
# Leerzeichen und Umlaute im Namen sind erlaubt, genau so schreiben wie im Log.
# dann nur diese Geräte, in dieser Reihenfolge. Ein, zwei, drei oder mehr Geräte gehen.
GERAETE = None

# --- Rechenregeln --------------------------------------------------------------
TAKT_S = None                      # Taktlänge in s; None = automatisch aus dem Log (Median der Abstände).
                                   # Wird nur für den letzten Takt eines Logs gebraucht, sonst zählen die echten Abstände.
MAX_LUECKE_S = 30                  # Lücken zwischen zwei Takten > 30 s zählen nicht als Energie
VOLLER_TAG_H = 22                  # ab so vielen erfassten Stunden gilt ein Tag als voll
LEER_SCHWELLE_W = 15               # Ist-Summe < 15 W  = Speicher liefert nichts (leer/Entladegrenze)
SATT_SCHWELLE_W = 1580             # Ist-Summe >= 1580 W = Speicher am Leistungslimit
BAND_W = 25                        # Regelgüte: Takt gilt als gut bei |Netzsaldo| <= 25 W
PROFIL_PERZENTILE = (10, 25, 50, 75, 90)  # Tagesprofil: Verteilung je Stunde für SOC, Netzsaldo und Speicher-Ausgang.
                                          # Der Bericht zeichnet 10/25/50/75/90 (Bänder 10–90 und 25–75, Linie = 50)
                                          # – diese fünf drin lassen, weitere nur ergänzen
AKTIV_SCHWELLE_W = 10              # Gerät gilt als aktiv, wenn es >= 10 W ins Haus abgibt (Ist > 0 = Abgabe)
SOLLWERT_START_W = 0               # Sollwert, bis das Log einen meldet ("Setpoint   : N W" beim Start oder
                                   # "KVS zdmc_setpoint: Wert uebernommen (a -> b)"). Danach gilt der Wert aus dem Log,
                                   # auch über Mitternacht ins nächste Log hinein.
NEUSTART_ABSTAND_S = 10            # Startzeilen, die näher als 10 s beieinander liegen, gehören zu einem Neustart
                                   # (ein Startblock dauert etwa 2 s; echte Neustarts lagen schon 21 s auseinander)

# =============================================================================
# Ende der Einstellungen
# =============================================================================

HIER = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HIER, "cache")

# Eigene Einstellungen: analyse_config.json neben diesem Skript (wird nicht ins Git übernommen,
# übersteht also jedes Update). Fehlt die Datei, gelten die Standardwerte oben. In der Datei stehen
# nur die Werte, die abweichen sollen, Schlüssel wie die Variablen oben, null = None:
#     {"ZEITRAUM_VON": "2026-10-06", "GERAETE": ["SF2400", "SF800"], "BAND_W": 30}
CONFIG = os.path.join(HIER, "analyse_config.json")
EINSTELLUNGEN = ["LOG_ORDNER", "LOG_MUSTER", "LOGS_PACKEN", "ZEITRAUM_VON", "ZEITRAUM_BIS", "GERAETE",
                 "TAKT_S", "MAX_LUECKE_S", "VOLLER_TAG_H", "LEER_SCHWELLE_W", "SATT_SCHWELLE_W", "BAND_W",
                 "PROFIL_PERZENTILE", "AKTIV_SCHWELLE_W", "SOLLWERT_START_W", "NEUSTART_ABSTAND_S"]


def config_laden():
    if not os.path.exists(CONFIG):
        return
    try:
        with open(CONFIG, encoding="utf-8-sig") as f:
            werte = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit(f"Fehler in {os.path.basename(CONFIG)}: {e}")
    if not isinstance(werte, dict):
        sys.exit(f"Fehler in {os.path.basename(CONFIG)}: erwartet wird ein Objekt {{\"NAME\": Wert, ...}}")
    melden = __name__ == "__main__"                      # beim Import durch bericht.py nicht doppelt ausgeben
    for k, v in werte.items():
        if k not in EINSTELLUNGEN:
            if melden:
                print(f"Warnung: unbekannte Einstellung {k!r} in {os.path.basename(CONFIG)} – ignoriert")
            continue
        globals()[k] = tuple(v) if k == "PROFIL_PERZENTILE" else v
    if melden:
        print(f"Einstellungen aus {os.path.basename(CONFIG)}: {', '.join(k for k in werte if k in EINSTELLUNGEN) or '–'}")


config_laden()

TS = r"^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\] \[Script \d+\] "
R_NETZ = re.compile(TS + r"Netzsaldo: (-?\d+) W \| Ist-Summe: (-?\d+) W \| Regelsignal: (-?\d+) W(?: \[FIX\])? \| Ladekorrektur: (-?\d+) W")
# Gerätename: alles bis zum Doppelpunkt (auch Leerzeichen, Umlaute), aber ohne | [ ] und ohne führendes Leerzeichen
NAME = r"([^\s:|\[\]][^:|\[\]]*?)"
R_DEV = re.compile(TS + r"  " + NAME + r": SOC (\d+|n/a)%? \| socL (\S+) \| gridR (\S+) \| Ist (-?\d+) W \| Soll (-?\d+) W \| acMode (\d)")
R_SET = re.compile(TS + NAME + r": Leistung gesetzt")
R_SPAR = re.compile(r"Sparmodus an: (\d+)|setze Polling fuer (\d+) Zyklen")
# Stundenzeile ab Controller 5.2.6
# Klassen "| s a/b/c/d/e/f/g" ab Controller 5.3.6: Zyklen je Viertel des Intervalls (0-25 % ... über 150 %)
R_ZYK = re.compile(TS + r"Zyklen 1h: n (\d+) \| avg (\d+) ms \| max (\d+) ms(?: \| uebersprungen \d+ \| interval (\d+) ms)?"
                   r"(?: \| s (\d+(?:/\d+){6}))?")
ZYK_KLASSEN = 7
# Sollwert: Startblock und Änderung per KVS
R_SOLL_START = re.compile(r"\] Setpoint   : (-?\d+) W")
R_SOLL_KVS = re.compile(r"KVS zdmc_setpoint: Wert uebernommen \((-?\d+) -> (-?\d+)\)")
# Neustart: jede Zeile des Startblocks zählt – so wird ein Neustart auch erkannt, wenn einzelne
# Zeilen (z. B. "gestartet") im Log fehlen. Zeilen innerhalb NEUSTART_ABSTAND_S = ein Neustart.
R_START = re.compile(r"\] (Multi-Device Controller gestartet|Version \d|Geraete    :|Interval   :|Watchdog   :|Setpoint   :)")
EREIGNISSE = [
    ("nicht_erreichbar", "Geraet nicht erreichbar"),
    ("watchdog", "Watchdog-Timeout"),
    ("takt_uebersprungen", "Takt uebersprungen"),
]
EREIGNIS_SPALTEN = ["nicht_erreichbar", "watchdog", "takt_uebersprungen", "neustarts"]


# ============================================================================ Hilfen
def argumente():
    ordner = [a for a in sys.argv[1:] if not a.startswith("--")]
    return (ordner[0] if ordner else (LOG_ORDNER or os.path.dirname(HIER))), "--neu" in sys.argv[1:]


def fingerabdruck():
    """Alles, was das Ergebnis eines einzelnen Tages beeinflusst. Ändert es sich, wird neu gerechnet."""
    teile = [VERSION, TAKT_S, MAX_LUECKE_S, LEER_SCHWELLE_W, SATT_SCHWELLE_W, BAND_W, AKTIV_SCHWELLE_W,
             SOLLWERT_START_W, NEUSTART_ABSTAND_S, list(GERAETE) if GERAETE else None]
    return hashlib.sha256(json.dumps(teile).encode()).hexdigest()[:16]


def schluessel(namen):
    """Spaltenschlüssel je Gerätename: klein, Umlaute umschrieben, sonst nur a–z, 0–9 und _.
    "Keller Süd" -> "keller_sued". Gleiche Schlüssel bekommen eine Nummer (_2, _3 ...)."""
    keys = []
    for name in namen:
        k = name.lower()
        for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
            k = k.replace(a, b)
        k = unicodedata.normalize("NFKD", k).encode("ascii", "ignore").decode()
        k = re.sub(r"[^a-z0-9]+", "_", k).strip("_") or "geraet"
        basis, i = k, 2
        while k in keys:
            k, i = f"{basis}_{i}", i + 1
        keys.append(k)
    return keys


def stamm(pfad):
    name = os.path.basename(pfad)
    return name[:-3] if name.endswith(".gz") else name


def oeffnen(pfad):
    if pfad.endswith(".gz"):
        return gzip.open(pfad, "rt", encoding="utf-8", errors="replace")
    return open(pfad, encoding="utf-8", errors="replace")


def json_wert(x):
    if x is None:
        return None
    if isinstance(x, (np.integer,)):
        return int(x)
    x = float(x)
    return None if np.isnan(x) else x


def taktlaenge(t):
    """TAKT_S oder, wenn None, der übliche Abstand zweier Takte (Median, Lücken ausgenommen)."""
    if TAKT_S:
        return TAKT_S
    d = t.diff().dt.total_seconds()
    d = d[(d > 0) & (d <= MAX_LUECKE_S)]
    return round(float(d.median()), 1) if len(d) else 4.0


def dauer_h(t, takt):
    """Stunden bis zum nächsten Takt, Lücken gekappt; der letzte Takt eines Logs zählt mit der Taktlänge."""
    return t.diff().shift(-1).dt.total_seconds().clip(upper=MAX_LUECKE_S).fillna(takt) / 3600


def im_zeitraum(tag):
    return (not ZEITRAUM_VON or tag >= ZEITRAUM_VON) and (not ZEITRAUM_BIS or tag <= ZEITRAUM_BIS)


# ============================================================================ Ein Log auswerten
def zustand_anfang():
    """Zustand, der von einem Log ins nächste weiterläuft."""
    return {"pause": 0, "soll": SOLLWERT_START_W, "start": None}


def lesen(pfad, zustand):
    """Liest ein Log. zustand = vom Vortag offene Sparmodus-Takte, gültiger Sollwert, letzte Startzeile.
    Liefert Rohdaten und den Zustand am Ende des Logs."""
    netz, dev, ev = [], [], []
    takte, gespart, zyklen = {}, {}, {}
    pause, soll, start = zustand["pause"], zustand["soll"], zustand["start"]
    start_t = pd.Timestamp(start) if start else None
    with oeffnen(pfad) as fh:
        for l in fh:
            m = R_NETZ.match(l)
            if m:
                netz.append((m[1], int(m[2]), int(m[3]), soll))
                tag = m[1][:10]
                takte[tag] = takte.get(tag, 0) + 1
                if pause > 0:
                    gespart[tag] = gespart.get(tag, 0) + 1
                    pause -= 1
                continue
            m = R_DEV.match(l)
            if m:
                dev.append((m[1], m[2], None if m[3] == "n/a" else int(m[3]), int(m[6]), len(netz) - 1))  # letzte Zahl = Takt-Nr.
                continue
            m = R_SET.match(l)
            if m:
                ev.append((m[1], "stell:" + m[2]))     # Gerätename unverändert; Spaltenschlüssel erst beim Zusammensetzen
                continue
            m = R_ZYK.match(l)
            if m:
                # je Tag: Anzahl, Summe der Dauern, längster Zyklus, größtes Intervall, Klassen (oder None)
                # (Fenster zählt zum Tag seiner Zeile)
                z = zyklen.setdefault(m[1][:10], [0, 0, 0, None, None])
                n = int(m[2])
                z[0] += n
                z[1] += n * int(m[3])
                z[2] = max(z[2], int(m[4]))
                if m[5]:
                    z[3] = max(z[3] or 0, int(m[5]))
                if m[6]:
                    k = [int(x) for x in m[6].split("/")]
                    z[4] = [a + b for a, b in zip(z[4], k)] if z[4] else k
                continue
            m = R_START.search(l)
            if m:
                t = pd.Timestamp(l[1:20])
                if start_t is None or abs((t - start_t).total_seconds()) > NEUSTART_ABSTAND_S:
                    ev.append((l[1:20], "neustarts"))
                    pause = 0
                start_t = t
                s = R_SOLL_START.search(l)
                if s:
                    soll = int(s[1])
                continue
            m = R_SOLL_KVS.search(l)
            if m:
                soll = int(m[2])
                continue
            if "Sparmodus" in l:
                s = R_SPAR.search(l)
                if s:
                    pause = int(s[1] or s[2])
                elif "Sparmodus aus" in l or "Sparmodus beendet" in l:
                    pause = 0
            for key, text in EREIGNISSE:
                if text in l:
                    ev.append((l[1:20], key))
                    break
    ende = {"pause": pause, "soll": soll, "start": start_t.strftime("%Y-%m-%d %H:%M:%S") if start_t is not None else None}
    return netz, dev, ev, takte, gespart, zyklen, ende


def auswerten(pfad, zustand):
    """Wertet ein Log aus. Ergebnis enthält nur Summen/Zählungen je Tag, aus denen sich alles exakt zusammensetzen lässt."""
    netz, dev, ev, takte, gespart, zyklen, zustand_ende = lesen(pfad, zustand)
    erg = {"zustand_ende": zustand_ende, "geraete": [], "takt": None, "tage": {}, "verlauf": None, "profil": [], "soc_hist": {}}
    if not netz:
        return erg
    n = pd.DataFrame(netz, columns=["t", "netz", "ist", "soll"])
    n["nr"] = range(len(n))
    n["t"] = pd.to_datetime(n.t)
    n = n.sort_values("t", kind="stable")
    d = pd.DataFrame(dev, columns=["t", "dev", "soc", "ist", "nr"])
    d["t"] = pd.to_datetime(d.t)
    d = d.sort_values("t", kind="stable")
    e = pd.DataFrame(ev, columns=["t", "ev"])
    e["t"] = pd.to_datetime(e.t)

    im_log = list(pd.unique(d.dev))
    geraete = [g for g in GERAETE if g in im_log] if GERAETE else im_log
    d = d[d.dev.isin(geraete)]
    erg["geraete"] = im_log if not GERAETE else geraete

    # 15-Minuten-Verlauf (alle Geräte dieses Logs; Auswahl beim Zusammensetzen)
    ni = n.set_index("t")
    r = pd.DataFrame({"netzsaldo_w": ni.netz.resample("15min").mean(), "speicher_w": ni.ist.resample("15min").mean()})
    for g in geraete:
        gi = d[d.dev == g].set_index("t")
        r["soc:" + g] = gi.soc.resample("15min").mean()          # Gerätename unverändert, siehe oben
        r["ausgang:" + g] = gi.ist.resample("15min").mean()
    r = r.dropna(how="all")
    erg["verlauf"] = {"t": list(r.index.strftime("%Y-%m-%dT%H:%M"))}
    erg["verlauf"].update({c: [json_wert(x) for x in r[c]] for c in r.columns})

    # Tageswerte
    takt = taktlaenge(n.t)
    erg["takt"] = takt
    n["dt"] = dauer_h(n.t, takt)
    n["tag"] = n.t.dt.strftime("%Y-%m-%d")
    bezug = n.netz.clip(lower=0) * n.dt / 1000
    n["bezug"] = bezug
    n["einsp"] = (-n.netz).clip(lower=0) * n.dt / 1000
    n["b_leer"] = bezug.where(n.ist < LEER_SCHWELLE_W, 0)
    n["b_rest"] = bezug - n.b_leer
    n["abw"] = n.netz - n.soll                       # Abweichung vom gültigen Sollwert
    # Aktivzeit gesamt: Takte, in denen mindestens ein Gerät selbst >= AKTIV_SCHWELLE_W abgibt
    # (nicht über die Ist-Summe: lädt ein anderes Gerät gleichzeitig, wäre die Summe zu klein)
    aktiv_nr = d.nr[d.ist >= AKTIV_SCHWELLE_W].unique()
    n["akt"] = n.dt.where(n.nr.isin(aktiv_nr), 0)
    day = n.groupby("tag").agg(netzbezug_kwh=("bezug", "sum"), einspeisung_kwh=("einsp", "sum"),
                               bezug_speicher_aus_kwh=("b_leer", "sum"), bezug_regelrest_kwh=("b_rest", "sum"),
                               aktiv_gesamt_h=("akt", "sum"), erfasst_h=("dt", "sum"),
                               sollwert_min_w=("soll", "min"), sollwert_max_w=("soll", "max"))
    # Regelgüte gegen den in jedem Takt gültigen Sollwert
    akt = n[(n.ist > LEER_SCHWELLE_W) & (n.ist < SATT_SCHWELLE_W)]
    q = akt.groupby("tag").abw.agg(regel_im_band_pct=lambda s: (s.abs() <= BAND_W).mean() * 100,
                                   regel_median_abw_w=lambda s: s.abs().median(),
                                   regel_versatz_w="median")
    day = day.join(q)
    geraet_tag = {}
    for g in geraete:
        x = d[d.dev == g].copy()
        x["dt"] = dauer_h(x.t, takt)
        x["tag"] = x.t.dt.strftime("%Y-%m-%d")
        x["ent"] = x.ist.clip(lower=0) * x.dt / 1000
        x["lad"] = (-x.ist).clip(lower=0) * x.dt / 1000
        x["akt"] = x.dt.where(x.ist >= AKTIV_SCHWELLE_W, 0)
        geraet_tag[g] = x.groupby("tag").agg(ent=("ent", "sum"), lad=("lad", "sum"), akt=("akt", "sum"),
                                              smin=("soc", "min"), smax=("soc", "max"))
    ec = e.assign(tag=e.t.dt.strftime("%Y-%m-%d")).groupby(["tag", "ev"]).size()
    for tag, z in day.iterrows():
        eintrag = {c: json_wert(z[c]) for c in day.columns}
        eintrag["takte"] = takte.get(tag, 0)
        eintrag["gespart"] = gespart.get(tag, 0)
        eintrag["zyklen"] = zyklen.get(tag)
        eintrag["ereignisse"] = {k: int(v) for (t, k), v in ec.items() if t == tag}
        eintrag["geraete"] = {}
        for g, a in geraet_tag.items():
            if tag in a.index:
                eintrag["geraete"][g] = {c: json_wert(a.at[tag, c]) for c in a.columns}
        erg["tage"][tag] = eintrag

    # Tagesprofil-Bausteine: Summen je Tag und Stunde, SOC-Häufigkeiten je Tag/Gerät/Stunde
    n["stunde"] = n.t.dt.hour
    p = n.groupby(["tag", "stunde"]).agg(s_netz=("netz", "sum"), s_ist=("ist", "sum"), anzahl=("netz", "size"))
    erg["profil"] = [[t, int(h), int(z.s_netz), int(z.s_ist), int(z.anzahl)] for (t, h), z in p.iterrows()]
    dd = d.dropna(subset=["soc"]).copy()
    dd["tag"] = dd.t.dt.strftime("%Y-%m-%d")
    dd["stunde"] = dd.t.dt.hour
    hist = dd.groupby(["tag", "dev", "stunde", "soc"]).size()
    for (tag, g, h, soc), anz in hist.items():
        erg["soc_hist"].setdefault(tag, {}).setdefault(g, {}).setdefault(str(int(h)), {})[str(int(soc))] = int(anz)
    return erg


# ============================================================================ Zwischenspeicher
def cache_pfad(st):
    return os.path.join(CACHE, st + ".json")


def cache_lesen(st):
    try:
        with open(cache_pfad(st), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def cache_schreiben(st, inhalt):
    os.makedirs(CACHE, exist_ok=True)
    tmp = cache_pfad(st) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(inhalt, fh, separators=(",", ":"))
    os.replace(tmp, cache_pfad(st))


def quelle_info(pfad):
    s = os.stat(pfad)
    return {"datei": os.path.basename(pfad), "groesse": s.st_size, "mtime": s.st_mtime}


def logs_finden(logdir):
    """Je Stamm genau eine Quelle; liegen .log und .log.gz nebeneinander, gilt das ungepackte."""
    quellen = {}
    for f in glob.glob(os.path.join(logdir, LOG_MUSTER + ".gz")) + glob.glob(os.path.join(logdir, LOG_MUSTER)):
        quellen[stamm(f)] = f            # .log überschreibt .log.gz
    return [quellen[k] for k in sorted(quellen)]


def alle_auswerten(dateien, neu):
    fa = fingerabdruck()
    if neu and os.path.isdir(CACHE):
        shutil.rmtree(CACHE)
        print("Zwischenspeicher verworfen – alles wird neu ausgewertet")
    ergebnisse, gelesen, zustand = [], 0, zustand_anfang()
    for f in dateien:
        st, info = stamm(f), quelle_info(f)
        c = cache_lesen(st)
        gueltig = (c is not None and c.get("fingerabdruck") == fa and c.get("zustand_start") == zustand
                   and c.get("quelle") == info)
        if not gueltig:
            erg = auswerten(f, zustand)
            c = {"fingerabdruck": fa, "zustand_start": zustand, "quelle": info, **erg}
            cache_schreiben(st, c)
            gelesen += 1
        ergebnisse.append((f, c))
        zustand = c["zustand_ende"]
    print(f"{len(dateien)} Logs: {gelesen} neu ausgewertet, {len(dateien) - gelesen} aus dem Zwischenspeicher")
    return ergebnisse


# ============================================================================ Packen
def packen(pfad):
    """pfad.log -> pfad.log.gz; Original erst löschen, wenn der Inhalt der gepackten Datei geprüft ist."""
    ziel, tmp = pfad + ".gz", pfad + ".gz.tmp"
    h1 = hashlib.sha256()
    with open(pfad, "rb") as src, gzip.open(tmp, "wb", compresslevel=9) as dst:
        for block in iter(lambda: src.read(1 << 20), b""):
            h1.update(block)
            dst.write(block)
    h2 = hashlib.sha256()
    with gzip.open(tmp, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h2.update(block)
    if h1.digest() != h2.digest():
        os.remove(tmp)
        return None
    s = os.stat(pfad)
    os.replace(tmp, ziel)
    os.utime(ziel, (s.st_atime, s.st_mtime))
    os.remove(pfad)
    return ziel


def alte_logs_packen(ergebnisse):
    if not LOGS_PACKEN:
        return
    jetzt, gepackt, vorher, nachher = time.time(), 0, 0, 0
    for f, c in ergebnisse[:-1]:                         # das jüngste Log bleibt ungepackt
        if f.endswith(".gz") or jetzt - os.path.getmtime(f) < 600:
            continue                                     # schon gepackt oder vor < 10 min noch beschrieben
        groesse = os.path.getsize(f)
        ziel = packen(f)
        if ziel is None:
            print("Warnung: Prüfung beim Packen fehlgeschlagen, Original bleibt:", os.path.basename(f))
            continue
        c["quelle"] = quelle_info(ziel)                  # Zwischenspeicher bleibt gültig
        cache_schreiben(stamm(f), c)
        gepackt += 1
        vorher += groesse
        nachher += os.path.getsize(ziel)
    if gepackt:
        print(f"{gepackt} Logs gepackt: {vorher / 1e6:.1f} MB -> {nachher / 1e6:.1f} MB")


# ============================================================================ Zusammensetzen
def zusammensetzen(ergebnisse):
    tage_roh, verlauf, profil, soc_hist, im_log, takte_s = {}, [], [], {}, [], []
    for _, c in ergebnisse:
        tage_im = [t for t in c["tage"] if im_zeitraum(t)]
        if not tage_im:
            continue
        for t in tage_im:
            if t in tage_roh:
                print("Warnung: Tag", t, "kommt in mehreren Logs vor – es zählt das spätere")
            tage_roh[t] = c["tage"][t]
        im_log += [g for g in c["geraete"] if g not in im_log]
        takte_s.append(c["takt"])
        v = pd.DataFrame(c["verlauf"])
        verlauf.append(v[v.t.str[:10].map(im_zeitraum)])
        profil += [z for z in c["profil"] if im_zeitraum(z[0])]
        for t in tage_im:
            if t in c["soc_hist"]:
                soc_hist[t] = c["soc_hist"][t]
    if not tage_roh:
        sys.exit(f"Keine Takte im Zeitraum {ZEITRAUM_VON or 'Anfang'} bis {ZEITRAUM_BIS or 'Ende'}")
    if GERAETE:
        fehlt = [g for g in GERAETE if g not in im_log]
        if fehlt:
            print("Hinweis: nicht im Log/Zeitraum gefunden:", ", ".join(fehlt))
        geraete = list(GERAETE)
    else:
        geraete = im_log
    if not geraete:
        sys.exit("Keine Gerätezeilen im Log gefunden")
    keys = schluessel(geraete)
    print("Geräte:", ", ".join(f"{g} ({k})" if g != k else g for g, k in zip(geraete, keys)))
    if not TAKT_S:
        print(f"Takt: {float(np.median(takte_s)):.1f} s (aus dem Log)")
    # Zeitraum je Gerät: erster und letzter Tag mit Gerätezeilen (für den Hinweis im Bericht)
    da = {g: sorted(t for t, x in tage_roh.items() if g in x["geraete"]) for g in geraete}
    pd.DataFrame({"name": geraete, "key": keys,
                  "von": [da[g][0] if da[g] else "" for g in geraete],
                  "bis": [da[g][-1] if da[g] else "" for g in geraete]}).to_csv(os.path.join(HIER, "geraete.csv"), index=False)
    alle_tage = sorted(tage_roh)
    for g in geraete:
        if da[g] and (da[g][0] != alle_tage[0] or da[g][-1] != alle_tage[-1]):
            print(f"Hinweis: {g} kommt nur von {da[g][0]} bis {da[g][-1]} im Log vor – an den anderen Tagen bleiben seine Spalten leer")

    # ------------------------------------------------ verlauf_15min.csv
    r = pd.concat(verlauf, ignore_index=True)
    r = r.rename(columns={**{"soc:" + g: "soc_" + k for g, k in zip(geraete, keys)},
                          **{"ausgang:" + g: "ausgang_" + k + "_w" for g, k in zip(geraete, keys)}})
    spalten = ["t", "netzsaldo_w", "speicher_w"] + [c for k in keys for c in ("soc_" + k, "ausgang_" + k + "_w")]
    r = r.reindex(columns=spalten)
    r = r.dropna(how="all", subset=spalten[1:]).round(1)
    r.to_csv(os.path.join(HIER, "verlauf_15min.csv"), index=False)

    # ------------------------------------------------ tage.csv
    zaehler = ["stellbefehle_" + k for k in keys] + EREIGNIS_SPALTEN
    zeilen = []
    for t in sorted(tage_roh):
        x = tage_roh[t]
        z = {"tag": t}
        for c in ("netzbezug_kwh", "einspeisung_kwh", "bezug_speicher_aus_kwh", "bezug_regelrest_kwh",
                  "aktiv_gesamt_h", "erfasst_h"):
            z[c] = x[c]
        lad = 0
        for g, k in zip(geraete, keys):
            a = x["geraete"].get(g)
            z["entladung_" + k + "_kwh"] = a["ent"] if a else None
            z["soc_min_" + k] = a["smin"] if a else None
            z["soc_max_" + k] = a["smax"] if a else None
            z["aktiv_" + k + "_h"] = a["akt"] if a else None
            lad += a["lad"] if a else 0
        z["netzladen_kwh"] = lad
        z["regel_im_band_pct"] = x.get("regel_im_band_pct")
        z["regel_median_abw_w"] = x.get("regel_median_abw_w")
        z["regel_versatz_w"] = x.get("regel_versatz_w")
        z["sollwert_min_w"] = x.get("sollwert_min_w")
        z["sollwert_max_w"] = x.get("sollwert_max_w")
        for g, k in zip(geraete, keys):
            # Gerät an diesem Tag nicht im Log (noch nicht oder nicht mehr da): leer statt 0
            z["stellbefehle_" + k] = x["ereignisse"].get("stell:" + g, 0) if g in x["geraete"] else None
        for c in EREIGNIS_SPALTEN:
            z[c] = x["ereignisse"].get(c, 0)
        zy = x.get("zyklen")
        z["zyklus_avg_ms"] = round(zy[1] / zy[0]) if zy and zy[0] else None
        z["zyklus_max_ms"] = zy[2] if zy and zy[0] else None
        z["zyklus_interval_ms"] = zy[3] if zy and zy[0] and len(zy) > 3 else None
        kl = zy[4] if zy and len(zy) > 4 else None
        for i in range(ZYK_KLASSEN):
            z[f"zyklus_k{i}"] = kl[i] if kl else None   # leer bei Logs vor Controller 5.3.6
        z["takte_gesamt"] = x["takte"]
        z["takte_ohne_abfrage"] = x["gespart"]
        zeilen.append(z)
    day = pd.DataFrame(zeilen).set_index("tag")
    day = day.astype(float)
    # Spalten der Einzelgeräte bleiben leer, wenn das Gerät an dem Tag nicht im Log war
    geraet_spalten = [c for k in keys for c in ("entladung_" + k + "_kwh", "soc_min_" + k, "soc_max_" + k,
                                                 "aktiv_" + k + "_h", "stellbefehle_" + k)]
    takte_gesamt, takte_ohne = day.pop("takte_gesamt").astype(int), day.pop("takte_ohne_abfrage").astype(int)
    day["entladung_gesamt_kwh"] = sum(day["entladung_" + k + "_kwh"].fillna(0) for k in keys)   # nur vorhandene Geräte
    day["deckung_pct"] = 100 * day.entladung_gesamt_kwh / (day.entladung_gesamt_kwh + day.netzbezug_kwh)
    day["takte_gesamt"] = takte_gesamt
    day["takte_ohne_abfrage"] = takte_ohne
    day["takte_mit_abfrage"] = day.takte_gesamt - day.takte_ohne_abfrage
    day["spar_anteil_pct"] = (100 * day.takte_ohne_abfrage / day.takte_gesamt).round(1)
    # voller Tag = mindestens VOLLER_TAG_H Stunden erfasst (kurze Ausfälle zählen nicht)
    day["vollstaendig"] = (day.erfasst_h >= VOLLER_TAG_H).astype(int)
    voll_tage = set(day.index[day.vollstaendig == 1])
    # Regelgüte bleibt leer, wenn an dem Tag kein Speicher im Regelbereich war (sonst sähe es nach 0 % aus);
    # Zyklusdauer bleibt leer bei Logs ohne Stundenzeile (Controller vor 5.2.6)
    regel = ["regel_im_band_pct", "regel_median_abw_w", "regel_versatz_w", "zyklus_avg_ms", "zyklus_max_ms",
             "zyklus_interval_ms"] + [f"zyklus_k{i}" for i in range(ZYK_KLASSEN)]
    day = day.drop(columns="erfasst_h")
    offen = regel + geraet_spalten                     # diese Spalten dürfen leer bleiben
    day[day.columns.difference(offen)] = day[day.columns.difference(offen)].fillna(0)
    day[EREIGNIS_SPALTEN] = day[EREIGNIS_SPALTEN].astype(int)
    stell = ["stellbefehle_" + k for k in keys]
    day[stell] = day[stell].astype("Int64")            # ganze Zahl, leer wenn das Gerät fehlt
    kl = [f"zyklus_k{i}" for i in range(ZYK_KLASSEN)]
    day[kl] = day[kl].astype("Int64")                  # ganze Zahl, leer ohne Klassen in der Stundenzeile
    cols = ["vollstaendig"] + [c for c in day.columns if c != "vollstaendig"]
    day = day[cols].round(2)
    day.index.name = "tag"
    day = day.reset_index()
    day.to_csv(os.path.join(HIER, "tage.csv"), index=False)

    # ------------------------------------------------ tagesprofil.csv (nur volle Tage)
    p = pd.DataFrame(profil, columns=["tag", "stunde", "s_netz", "s_ist", "anzahl"])
    p = p[p.tag.isin(voll_tage)]
    g = p.groupby("stunde")
    H = pd.DataFrame({"netzsaldo_w": g.s_netz.sum() / g.anzahl.sum(), "speicher_w": g.s_ist.sum() / g.anzahl.sum()}).round(1)
    # Leistung: erst Stundenmittel je Tag, dann Verteilung über die Tage (Rohwerte wären von kurzen Lastspitzen geprägt)
    p = p.assign(m_netz=p.s_netz / p.anzahl, m_ist=p.s_ist / p.anzahl)
    for spalte, name in (("m_netz", "netzsaldo"), ("m_ist", "speicher")):
        gg = p.groupby("stunde")[spalte]
        for q in PROFIL_PERZENTILE:
            H[f"{name}_p{q}_w"] = gg.quantile(q / 100).round(1)
    H["tage"] = p.groupby("stunde").size()
    # SOC: Verteilung über alle Takte dieser Stunde an allen vollen Tagen – exakt aus den Häufigkeiten
    for gname, k in zip(geraete, keys):
        werte = {}
        for t in voll_tage:
            for h, zaehl in soc_hist.get(t, {}).get(gname, {}).items():
                ziel = werte.setdefault(int(h), {})
                for soc, anz in zaehl.items():
                    ziel[int(soc)] = ziel.get(int(soc), 0) + anz
        smin, smax, perz = {}, {}, {q: {} for q in PROFIL_PERZENTILE}
        for h, zaehl in werte.items():
            soc = sorted(zaehl)
            s = pd.Series(np.repeat(np.array(soc, dtype=float), [zaehl[v] for v in soc]))
            smin[h], smax[h] = float(soc[0]), float(soc[-1])
            for q in PROFIL_PERZENTILE:
                perz[q][h] = round(s.quantile(q / 100), 1)
        H["soc_min_" + k] = pd.Series(smin, dtype=float)
        H["soc_max_" + k] = pd.Series(smax, dtype=float)
        for q in PROFIL_PERZENTILE:
            H[f"soc_p{q}_" + k] = pd.Series(perz[q], dtype=float)
    H.index.name = "stunde"
    H.reset_index().to_csv(os.path.join(HIER, "tagesprofil.csv"), index=False)

    print(day[["tag", "vollstaendig", "netzbezug_kwh", "entladung_gesamt_kwh", "sollwert_max_w", "regel_im_band_pct",
               "nicht_erreichbar", "neustarts", "spar_anteil_pct"]].to_string(index=False))
    # Plausibilität: Im Regelbetrieb sollte der Netzsaldo im Median nahe am Sollwert liegen.
    # Weicht er stark ab, wurde womöglich eine Sollwert-Änderung im Log verschluckt.
    auff = day[day.regel_versatz_w.abs() > BAND_W / 2]
    for _, z in auff.iterrows():
        print(f"Hinweis {z.tag}: Netzsaldo liegt im Regelbetrieb im Median {z.regel_versatz_w:+.0f} W neben dem Sollwert "
              f"({z.sollwert_min_w:.0f}–{z.sollwert_max_w:.0f} W) – Sollwert-Änderung im Log verschluckt?")
    if voll_tage:
        print(f"Volle Tage im Zeitraum: {min(voll_tage)} bis {max(voll_tage)} ({len(voll_tage)})")
    print("Geschrieben nach", HIER)


def main():
    print(f"Auswertung Zendure-Speicher v{VERSION}")
    logdir, neu = argumente()
    dateien = logs_finden(logdir)
    if not dateien:
        sys.exit(f"Keine Logs nach Muster {LOG_MUSTER} (auch .gz) gefunden in {logdir}")
    ergebnisse = alle_auswerten(dateien, neu)
    zusammensetzen(ergebnisse)
    alte_logs_packen(ergebnisse)

    # ------------------------------------------------ bericht.html
    sys.path.insert(0, HIER)
    import bericht
    bericht.erzeugen(HIER)


if __name__ == "__main__":
    main()
