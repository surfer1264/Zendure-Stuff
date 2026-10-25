"""Statistische Auswertung der Multi-Device-Controller-Logs (ein oder mehrere Zendure-Speicher).

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
    tage.csv           Tageswerte: Energie, SOC-Spanne, Regelgüte, Stellbefehle, Störungen, Sparmodus,
                       Zyklusdauer (ab Controller 5.2.6)
    tagesprofil.csv    Je Uhrzeit-Stunde: Netzsaldo und Speicher-Ausgang (Mittel und Verteilung über die Tage),
                       SOC-Verteilung je Gerät (Min, Perzentile, Max)
    geraete.csv        Ausgewertete Geräte (Name wie im Log, Spaltenschlüssel) – für bericht.py
    bericht.html       Bericht zum Öffnen im Browser, erzeugt von bericht.py
    cache/             Zwischenspeicher, eine Datei je Logdatei

Benötigt: Python 3.9+ und pandas (pip install pandas).
Alle Einstellungen stehen im Block EINSTELLUNGEN direkt unter den Imports.
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

import numpy as np
import pandas as pd

# Version der Auswertung (analyse.py + bericht.py gemeinsam); erscheint in der Ausgabe und im Bericht
VERSION = "1.2.0"

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
# Oder eine Liste mit Namen wie im Log ("  SF2400: SOC ..."), z. B. ["SF2400", "SF800"]:
# dann nur diese Geräte, in dieser Reihenfolge. Ein, zwei, drei oder mehr Geräte gehen.
GERAETE = None

# --- Rechenregeln --------------------------------------------------------------
TAKT_S = None                      # Taktlänge in s; None = automatisch aus dem Log (Median der Abstände).
                                   # Wird nur für den letzten Takt eines Logs gebraucht, sonst zählen die echten Abstände.
MAX_LUECKE_S = 30                  # Lücken zwischen zwei Takten > 30 s zählen nicht als Energie
VOLLER_TAG_H = 22                  # ab so vielen erfassten Stunden gilt ein Tag als voll
LEER_SCHWELLE_W = 30               # Ist-Summe < 30 W  = Speicher liefert nichts (leer/Entladegrenze)
SATT_SCHWELLE_W = 1500             # Ist-Summe >= 1500 W = Speicher am Leistungslimit
BAND_W = 25                        # Regelgüte: Takt gilt als gut bei |Netzsaldo| <= 25 W
PROFIL_PERZENTILE = (10, 25, 50, 75, 90)  # Tagesprofil: Verteilung je Stunde für SOC, Netzsaldo und Speicher-Ausgang.
                                          # Der Bericht zeichnet 10/25/50/75/90 (Bänder 10–90 und 25–75, Linie = 50)
                                          # – diese fünf drin lassen, weitere nur ergänzen
AKTIV_SCHWELLE_W = 10              # Gerät gilt als aktiv, wenn es >= 10 W ins Haus abgibt (Ist > 0 = Abgabe)

# =============================================================================
# Ende der Einstellungen
# =============================================================================

HIER = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HIER, "cache")

TS = r"^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\] \[Script \d+\] "
R_NETZ = re.compile(TS + r"Netzsaldo: (-?\d+) W \| Ist-Summe: (-?\d+) W \| Regelsignal: (-?\d+) W(?: \[FIX\])? \| Ladekorrektur: (-?\d+) W")
R_DEV = re.compile(TS + r"  ([A-Za-z0-9_.-]+): SOC (\d+|n/a)%? \| socL (\S+) \| gridR (\S+) \| Ist (-?\d+) W \| Soll (-?\d+) W \| acMode (\d)")
R_SET = re.compile(TS + r"([A-Za-z0-9_.-]+): Leistung gesetzt")
R_SPAR = re.compile(r"Sparmodus an: (\d+)|setze Polling fuer (\d+) Zyklen")
# Stundenzeile ab Controller 5.2.6
R_ZYK = re.compile(TS + r"Zyklen 1h: n (\d+) \| avg (\d+) ms \| max (\d+) ms")
EREIGNISSE = [
    ("nicht_erreichbar", "Geraet nicht erreichbar"),
    ("watchdog", "Watchdog-Timeout"),
    ("takt_uebersprungen", "Takt uebersprungen"),
    ("neustarts", "Multi-Device Controller gestartet"),
]


# ============================================================================ Hilfen
def argumente():
    ordner = [a for a in sys.argv[1:] if not a.startswith("--")]
    return (ordner[0] if ordner else (LOG_ORDNER or os.path.dirname(HIER))), "--neu" in sys.argv[1:]


def fingerabdruck():
    """Alles, was das Ergebnis eines einzelnen Tages beeinflusst. Ändert es sich, wird neu gerechnet."""
    teile = [VERSION, TAKT_S, MAX_LUECKE_S, LEER_SCHWELLE_W, SATT_SCHWELLE_W, BAND_W, AKTIV_SCHWELLE_W,
             list(GERAETE) if GERAETE else None]
    return hashlib.sha256(json.dumps(teile).encode()).hexdigest()[:16]


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
def lesen(pfad, pause):
    """Liest ein Log. pause = noch offene Sparmodus-Takte vom Vortag. Liefert Rohdaten und offene Pause."""
    netz, dev, ev = [], [], []
    takte, gespart, zyklen = {}, {}, {}
    with oeffnen(pfad) as fh:
        for l in fh:
            m = R_NETZ.match(l)
            if m:
                netz.append((m[1], int(m[2]), int(m[3])))
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
                ev.append((m[1], "stellbefehle_" + m[2].lower()))
                continue
            m = R_ZYK.match(l)
            if m:
                # je Tag: Anzahl, Summe der Dauern, längster Zyklus (Fenster zählt zum Tag seiner Zeile)
                z = zyklen.setdefault(m[1][:10], [0, 0, 0])
                n = int(m[2])
                z[0] += n
                z[1] += n * int(m[3])
                z[2] = max(z[2], int(m[4]))
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
                    if key == "neustarts":
                        pause = 0
                    break
    return netz, dev, ev, takte, gespart, zyklen, pause


def auswerten(pfad, pause):
    """Wertet ein Log aus. Ergebnis enthält nur Summen/Zählungen je Tag, aus denen sich alles exakt zusammensetzen lässt."""
    netz, dev, ev, takte, gespart, zyklen, pause_ende = lesen(pfad, pause)
    erg = {"pause_ende": pause_ende, "geraete": [], "takt": None, "tage": {}, "verlauf": None, "profil": [], "soc_hist": {}}
    if not netz:
        return erg
    n = pd.DataFrame(netz, columns=["t", "netz", "ist"])
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
        r["soc_" + g.lower()] = gi.soc.resample("15min").mean()
        r["ausgang_" + g.lower() + "_w"] = gi.ist.resample("15min").mean()
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
    # Aktivzeit gesamt: Takte, in denen mindestens ein Gerät selbst >= AKTIV_SCHWELLE_W abgibt
    # (nicht über die Ist-Summe: lädt ein anderes Gerät gleichzeitig, wäre die Summe zu klein)
    aktiv_nr = d.nr[d.ist >= AKTIV_SCHWELLE_W].unique()
    n["akt"] = n.dt.where(n.nr.isin(aktiv_nr), 0)
    day = n.groupby("tag").agg(netzbezug_kwh=("bezug", "sum"), einspeisung_kwh=("einsp", "sum"),
                               bezug_speicher_aus_kwh=("b_leer", "sum"), bezug_regelrest_kwh=("b_rest", "sum"),
                               aktiv_gesamt_h=("akt", "sum"), erfasst_h=("dt", "sum"))
    akt = n[(n.ist > LEER_SCHWELLE_W) & (n.ist < SATT_SCHWELLE_W)]
    q = akt.groupby("tag").netz.agg(regel_im_band_pct=lambda s: (s.abs() <= BAND_W).mean() * 100,
                                    regel_median_abw_w=lambda s: s.abs().median())
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
    ergebnisse, gelesen, pause = [], 0, 0
    for f in dateien:
        st, info = stamm(f), quelle_info(f)
        c = cache_lesen(st)
        gueltig = (c is not None and c.get("fingerabdruck") == fa and c.get("pause_start") == pause
                   and c.get("quelle") == info)
        if not gueltig:
            erg = auswerten(f, pause)
            c = {"fingerabdruck": fa, "pause_start": pause, "quelle": info, **erg}
            cache_schreiben(st, c)
            gelesen += 1
        ergebnisse.append((f, c))
        pause = c["pause_ende"]
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
    keys = [g.lower() for g in geraete]
    print("Geräte:", ", ".join(geraete))
    if not TAKT_S:
        print(f"Takt: {float(np.median(takte_s)):.1f} s (aus dem Log)")
    pd.DataFrame({"name": geraete, "key": keys}).to_csv(os.path.join(HIER, "geraete.csv"), index=False)

    # ------------------------------------------------ verlauf_15min.csv
    r = pd.concat(verlauf, ignore_index=True)
    spalten = ["t", "netzsaldo_w", "speicher_w"] + [c for k in keys for c in ("soc_" + k, "ausgang_" + k + "_w")]
    r = r.reindex(columns=spalten)
    r = r.dropna(how="all", subset=spalten[1:]).round(1)
    r.to_csv(os.path.join(HIER, "verlauf_15min.csv"), index=False)

    # ------------------------------------------------ tage.csv
    zaehler = ["stellbefehle_" + k for k in keys] + [k for k, _ in EREIGNISSE]
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
        for c in zaehler:
            z[c] = x["ereignisse"].get(c, 0)
        zy = x.get("zyklen")
        z["zyklus_avg_ms"] = round(zy[1] / zy[0]) if zy and zy[0] else None
        z["zyklus_max_ms"] = zy[2] if zy and zy[0] else None
        z["takte_gesamt"] = x["takte"]
        z["takte_ohne_abfrage"] = x["gespart"]
        zeilen.append(z)
    day = pd.DataFrame(zeilen).set_index("tag")
    day = day.astype(float)
    day = day.fillna({c + k + s: 0 for k in keys for c, s in (("entladung_", "_kwh"), ("aktiv_", "_h"))})
    takte_gesamt, takte_ohne = day.pop("takte_gesamt").astype(int), day.pop("takte_ohne_abfrage").astype(int)
    day["entladung_gesamt_kwh"] = sum(day["entladung_" + k + "_kwh"] for k in keys)
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
    regel = ["regel_im_band_pct", "regel_median_abw_w", "zyklus_avg_ms", "zyklus_max_ms"]
    day = day.drop(columns="erfasst_h")
    day[day.columns.difference(regel)] = day[day.columns.difference(regel)].fillna(0)
    day[zaehler] = day[zaehler].astype(int)
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

    print(day[["tag", "vollstaendig", "netzbezug_kwh", "entladung_gesamt_kwh", "nicht_erreichbar", "spar_anteil_pct"]].to_string(index=False))
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
