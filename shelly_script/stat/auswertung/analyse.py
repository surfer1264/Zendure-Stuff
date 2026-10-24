"""Statistische Auswertung der Multi-Device-Controller-Logs (SF2400 + SF800).

Aufruf (aus beliebigem Verzeichnis):
    python analyse.py              # Logs aus LOG_ORDNER (Standard: Ordner über diesem Skript)
    python analyse.py <logordner>  # anderer Log-Ordner (überschreibt LOG_ORDNER)

Erzeugt im Ordner dieses Skripts:
    verlauf_15min.csv  15-Minuten-Mittel: Netzsaldo, Speicher-Ausgang, SOC und Ausgang je Gerät
    tage.csv           Tageswerte: Energie, SOC-Spanne, Regelgüte, Stellbefehle, Störungen, Sparmodus
    tagesprofil.csv    Je Uhrzeit-Stunde: mittlerer Netzsaldo/Speicher-Ausgang, SOC-Min/-Max je Gerät
    bericht.html       Statischer Bericht (fertige SVG-Grafiken, kein JavaScript), erzeugt von bericht.py

Benötigt: Python 3.9+ und pandas (pip install pandas).
Alle Einstellungen stehen im Block EINSTELLUNGEN direkt unter den Imports.
bericht.py hat keine eigenen Einstellungen, es übernimmt alles von hier.
"""
import glob
import os
import re
import sys

import pandas as pd

# =============================================================================
# EINSTELLUNGEN – nur hier anpassen
# =============================================================================

# --- Logdateien --------------------------------------------------------------
# Ordner mit den Logs. None = Ordner über diesem Skript (also ../).
# Ein Ordner als Aufrufparameter hat Vorrang.
LOG_ORDNER = None
# Muster der Logdateinamen (glob: * = beliebige Zeichen, ? = ein Zeichen).
# Die Dateien werden nach Namen sortiert eingelesen.
LOG_MUSTER = "shelly_debug_*.log"

# --- Auswertungszeitraum (gilt für alle CSV-Dateien und den Bericht) ---------
# Format "JJJJ-MM-TT", jeweils einschließlich. None = keine Grenze.
# Tageswerte, Kennzahlen und Tagesprofil im Bericht nutzen nur volle Tage
# (siehe VOLLER_TAG_H) – angebrochene Tage am Rand fallen also automatisch weg.
# Bei neuen Logs muss hier nichts geändert werden, solange ZEITRAUM_BIS = None ist.
ZEITRAUM_VON = "2026-10-06"        # 20.09. ist ein Einzeltag 16 Tage davor und bleibt außen vor
ZEITRAUM_BIS = None                # None = bis zum Ende der Logs

# --- Geräte ------------------------------------------------------------------
# Gerätenamen wie im Log ("  SF2400: SOC ..."). Reihenfolge = Reihenfolge im Bericht.
GERAETE = ["SF2400", "SF800"]

# --- Rechenregeln --------------------------------------------------------------
TAKT_S = 4                         # übliche Taktlänge in s (für den letzten Takt einer Reihe)
MAX_LUECKE_S = 30                  # Lücken zwischen zwei Takten > 30 s zählen nicht als Energie
VOLLER_TAG_H = 22                  # ab so vielen erfassten Stunden gilt ein Tag als voll
LEER_SCHWELLE_W = 30               # Ist-Summe < 30 W  = Speicher liefert nichts (leer/Entladegrenze)
SATT_SCHWELLE_W = 1500             # Ist-Summe >= 1500 W = Speicher am Leistungslimit
BAND_W = 25                        # Regelgüte: Takt gilt als gut bei |Netzsaldo| <= 25 W

# =============================================================================
# Ende der Einstellungen
# =============================================================================

HIER = os.path.dirname(os.path.abspath(__file__))

TS = r"^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\] \[Script \d+\] "
R_NETZ = re.compile(TS + r"Netzsaldo: (-?\d+) W \| Ist-Summe: (-?\d+) W \| Regelsignal: (-?\d+) W(?: \[FIX\])? \| Ladekorrektur: (-?\d+) W")
R_DEV = re.compile(TS + r"  (SF\d+): SOC (\d+|n/a)%? \| socL (\S+) \| gridR (\S+) \| Ist (-?\d+) W \| Soll (-?\d+) W \| acMode (\d)")
R_SET = re.compile(TS + r"(SF\d+): Leistung gesetzt")
R_SPAR = re.compile(r"Sparmodus an: (\d+)|setze Polling fuer (\d+) Zyklen")
EREIGNISSE = [
    ("nicht_erreichbar", "Geraet nicht erreichbar"),
    ("watchdog", "Watchdog-Timeout"),
    ("takt_uebersprungen", "Takt uebersprungen"),
    ("neustarts", "Multi-Device Controller gestartet"),
]


def log_ordner():
    if len(sys.argv) > 1:
        return sys.argv[1]
    return LOG_ORDNER or os.path.dirname(HIER)


def zeitgrenzen():
    """Start (einschließlich) und Ende (ausschließlich) als Timestamp oder None."""
    ab = pd.Timestamp(ZEITRAUM_VON) if ZEITRAUM_VON else None
    bis = pd.Timestamp(ZEITRAUM_BIS) + pd.Timedelta(days=1) if ZEITRAUM_BIS else None
    return ab, bis


def einlesen(logdir):
    netz, dev, ev = [], [], []
    takte, gespart = {}, {}
    pause = 0
    dateien = sorted(glob.glob(os.path.join(logdir, LOG_MUSTER)))
    if not dateien:
        sys.exit(f"Keine Logs nach Muster {LOG_MUSTER} gefunden in {logdir}")
    for f in dateien:
        with open(f, encoding="utf-8", errors="replace") as fh:
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
                    dev.append((m[1], m[2], None if m[3] == "n/a" else int(m[3]), int(m[6])))
                    continue
                m = R_SET.match(l)
                if m:
                    ev.append((m[1], "stellbefehle_" + m[2].lower()))
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
    print(f"{len(dateien)} Logs ({LOG_MUSTER}), {len(netz)} Takte gelesen")
    n = pd.DataFrame(netz, columns=["t", "netz", "ist"])
    n["t"] = pd.to_datetime(n.t)
    d = pd.DataFrame(dev, columns=["t", "dev", "soc", "ist"])
    d["t"] = pd.to_datetime(d.t)
    e = pd.DataFrame(ev, columns=["t", "ev"])
    e["t"] = pd.to_datetime(e.t)
    return n.sort_values("t"), d.sort_values("t"), e, takte, gespart


def dauer_h(t):
    """Stunden bis zum nächsten Takt, Lücken gekappt."""
    return t.diff().shift(-1).dt.total_seconds().clip(upper=MAX_LUECKE_S).fillna(TAKT_S) / 3600


def im_zeitraum(df):
    ab, bis = zeitgrenzen()
    if ab is not None:
        df = df[df.t >= ab]
    if bis is not None:
        df = df[df.t < bis]
    return df.copy()


def main():
    n, d, e, takte, gespart = einlesen(log_ordner())
    n, d, e = im_zeitraum(n), im_zeitraum(d), im_zeitraum(e)
    if n.empty:
        sys.exit(f"Keine Takte im Zeitraum {ZEITRAUM_VON or 'Anfang'} bis {ZEITRAUM_BIS or 'Ende'}")
    keys = [g.lower() for g in GERAETE]

    # ------------------------------------------------ verlauf_15min.csv
    ni = n.set_index("t")
    r = pd.DataFrame({"netzsaldo_w": ni.netz.resample("15min").mean(),
                      "speicher_w": ni.ist.resample("15min").mean()})
    for g, k in zip(GERAETE, keys):
        gi = d[d.dev == g].set_index("t")
        r["soc_" + k] = gi.soc.resample("15min").mean()
        r["ausgang_" + k + "_w"] = gi.ist.resample("15min").mean()
    r = r.dropna(how="all").round(1).reset_index()
    r["t"] = r.t.dt.strftime("%Y-%m-%dT%H:%M")
    r.to_csv(os.path.join(HIER, "verlauf_15min.csv"), index=False)

    # ------------------------------------------------ tage.csv
    n["dt"] = dauer_h(n.t)
    n["tag"] = n.t.dt.strftime("%Y-%m-%d")
    bezug = n.netz.clip(lower=0) * n.dt / 1000
    n["bezug"] = bezug
    n["einsp"] = (-n.netz).clip(lower=0) * n.dt / 1000
    n["b_leer"] = bezug.where(n.ist < LEER_SCHWELLE_W, 0)
    n["b_rest"] = bezug - n.b_leer
    day = n.groupby("tag").agg(netzbezug_kwh=("bezug", "sum"), einspeisung_kwh=("einsp", "sum"),
                               bezug_speicher_aus_kwh=("b_leer", "sum"), bezug_regelrest_kwh=("b_rest", "sum"),
                               erfasst_h=("dt", "sum"))
    lad = 0
    for g, k in zip(GERAETE, keys):
        x = d[d.dev == g].copy()
        x["dt"] = dauer_h(x.t)
        x["tag"] = x.t.dt.strftime("%Y-%m-%d")
        x["ent"] = x.ist.clip(lower=0) * x.dt / 1000
        x["lad"] = (-x.ist).clip(lower=0) * x.dt / 1000
        a = x.groupby("tag").agg(ent=("ent", "sum"), lad=("lad", "sum"), smin=("soc", "min"), smax=("soc", "max"))
        day["entladung_" + k + "_kwh"] = a.ent
        day["soc_min_" + k] = a.smin
        day["soc_max_" + k] = a.smax
        lad = lad + a.lad.reindex(day.index, fill_value=0)
    day["netzladen_kwh"] = lad
    akt = n[(n.ist > LEER_SCHWELLE_W) & (n.ist < SATT_SCHWELLE_W)]
    q = akt.groupby("tag").netz.agg(regel_im_band_pct=lambda s: (s.abs() <= BAND_W).mean() * 100,
                                    regel_median_abw_w=lambda s: s.abs().median())
    day = day.join(q)
    ec = e.assign(tag=e.t.dt.strftime("%Y-%m-%d")).groupby(["tag", "ev"]).size().unstack(fill_value=0)
    zaehler = ["stellbefehle_" + k for k in keys] + [k for k, _ in EREIGNISSE]
    for c in zaehler:
        day[c] = ec[c] if c in ec else 0
    day = day.fillna({"entladung_" + k + "_kwh": 0 for k in keys})
    day["entladung_gesamt_kwh"] = sum(day["entladung_" + k + "_kwh"] for k in keys)
    day["deckung_pct"] = 100 * day.entladung_gesamt_kwh / (day.entladung_gesamt_kwh + day.netzbezug_kwh)
    day["takte_gesamt"] = pd.Series(takte).reindex(day.index).fillna(0).astype(int)
    day["takte_ohne_abfrage"] = pd.Series(gespart).reindex(day.index).fillna(0).astype(int)
    day["takte_mit_abfrage"] = day.takte_gesamt - day.takte_ohne_abfrage
    day["spar_anteil_pct"] = (100 * day.takte_ohne_abfrage / day.takte_gesamt).round(1)
    # voller Tag = mindestens VOLLER_TAG_H Stunden erfasst (kurze Ausfälle zählen nicht)
    day["vollstaendig"] = (day.erfasst_h >= VOLLER_TAG_H).astype(int)
    voll_tage = set(day.index[day.vollstaendig == 1])
    day = day.drop(columns="erfasst_h").fillna(0)
    day[zaehler] = day[zaehler].astype(int)
    cols = ["vollstaendig"] + [c for c in day.columns if c != "vollstaendig"]
    day = day[cols].round(2).reset_index()
    day.to_csv(os.path.join(HIER, "tage.csv"), index=False)

    # ------------------------------------------------ tagesprofil.csv (nur volle Tage)
    h = n[n.tag.isin(voll_tage)].copy()
    h["stunde"] = h.t.dt.hour
    H = h.groupby("stunde").agg(netzsaldo_w=("netz", "mean"), speicher_w=("ist", "mean")).round(1)
    dd = d[d.t.dt.strftime("%Y-%m-%d").isin(voll_tage)].copy()
    dd["stunde"] = dd.t.dt.hour
    for g, k in zip(GERAETE, keys):
        s = dd[dd.dev == g].groupby("stunde").soc
        H["soc_min_" + k] = s.min()
        H["soc_max_" + k] = s.max()
    H.reset_index().to_csv(os.path.join(HIER, "tagesprofil.csv"), index=False)

    print(day[["tag", "vollstaendig", "netzbezug_kwh", "entladung_gesamt_kwh", "nicht_erreichbar", "spar_anteil_pct"]].to_string(index=False))
    if voll_tage:
        print(f"Volle Tage im Zeitraum: {min(voll_tage)} bis {max(voll_tage)} ({len(voll_tage)})")
    print("Geschrieben nach", HIER)

    # ------------------------------------------------ bericht.html
    sys.path.insert(0, HIER)
    import bericht
    bericht.erzeugen(HIER)


if __name__ == "__main__":
    main()
