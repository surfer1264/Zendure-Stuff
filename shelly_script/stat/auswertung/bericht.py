"""Erzeugt bericht.html: einen statischen Bericht aus den CSV-Dateien von analyse.py.

Kein JavaScript, keine Nachlade-Inhalte: alle Grafiken sind fertige SVGs in der Datei.
Werte zu einzelnen Punkten/Balken erscheinen beim Darüberfahren (SVG-<title>).

Aufruf:  python bericht.py     (wird auch am Ende von analyse.py aufgerufen)

Hier gibt es nichts einzustellen. Zeitraum, Geräte und Schwellwerte kommen aus analyse.py:
der Zeitraum steckt bereits in den CSV-Dateien, Geräte und Schwellwerte werden für die
Beschriftungen aus analyse.py gelesen. Bericht = alle vollen Tage aus tage.csv.
"""
import datetime as dt
import html
import math
import os

import sys

import pandas as pd

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import analyse as cfg  # noqa: E402  nur Einstellungen; die Auswertung startet dabei nicht

# Layout der Grafiken (Pixel im SVG-Koordinatensystem), keine fachlichen Einstellungen
W, W_HALB, H_STD, H_HOCH = 960, 560, 260, 320
ML, MR, MT, MB = 52, 16, 14, 30
WOCHENTAG = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


# ---------------------------------------------------------------- Formate
def de(v, nk=1):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    s = f"{v:,.{nk}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def esc(s):
    return html.escape(str(s), quote=True)


def tag_lang(s):
    d = dt.date.fromisoformat(s)
    return f"{WOCHENTAG[d.weekday()]} {d.day:02d}.{d.month:02d}."


def tag_kurz(s):
    d = dt.date.fromisoformat(s)
    return f"{d.day:02d}.{d.month:02d}."


def nice_ticks(lo, hi, n=5):
    if hi <= lo:
        hi = lo + 1
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=10 * mag)
    a = math.floor(lo / step) * step
    b = math.ceil(hi / step) * step
    ticks, v = [], a
    while v <= b + step / 1000:
        ticks.append(round(v, 10))
        v += step
    return a, b, ticks


# ---------------------------------------------------------------- SVG-Bausteine
def _rahmen(h, y0, y1, yticks, yfmt, xticks, xpos, W=W):
    sy = lambda v: MT + (h - MT - MB) * (1 - (v - y0) / (y1 - y0))
    out = []
    for t in yticks:
        y = sy(t)
        out.append(f'<line x1="{ML}" x2="{W - MR}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        out.append(f'<text x="{ML - 8}" y="{y:.1f}" dy="0.32em" text-anchor="end" class="tick">{esc(yfmt(t))}</text>')
    out.append(f'<line x1="{ML}" x2="{W - MR}" y1="{h - MB}" y2="{h - MB}" class="axis"/>')
    for v, lab in xticks:
        x = xpos(v)
        anchor = "start" if x < ML + 24 else ("end" if x > W - MR - 24 else "middle")
        out.append(f'<text x="{x:.1f}" y="{h - MB + 18}" text-anchor="{anchor}" class="tick">{esc(lab)}</text>')
    return sy, out


def linien(x, serien, xticks, yfmt, einheit="", h=H_STD, ymin=None, ymax=None,
           ref=None, punkte=False, xlabel=None, luecke=None, aria="", W=W):
    """x: Zahlen; serien: [(name, werte, farbe, gestrichelt)]; luecke: max. x-Abstand ohne Linienbruch."""
    alle = [v for _, ws, _, _ in serien for v in ws if v is not None and not math.isnan(v)]
    lo = min(alle) if ymin is None else ymin
    hi = max(alle) if ymax is None else ymax
    if ymin is None:
        lo = min(0, lo)
    y0, y1, yt = nice_ticks(lo, hi)
    if ymin is not None:
        y0, yt = ymin, [t for t in yt if t >= ymin]
    if ymax is not None:
        y1, yt = ymax, [t for t in yt if t <= ymax]
    x0, x1 = min(x), max(x)
    sx = lambda v: ML + (W - ML - MR) * (v - x0) / ((x1 - x0) or 1)
    sy, out = _rahmen(h, y0, y1, yt, yfmt, xticks, sx, W)
    if ref is not None and y0 <= ref <= y1:
        out.append(f'<line x1="{ML}" x2="{W - MR}" y1="{sy(ref):.1f}" y2="{sy(ref):.1f}" class="ref"/>')
    for name, ws, farbe, strich in serien:
        teile, akt, vorx = [], [], None
        for xv, wv in zip(x, ws):
            ok = wv is not None and not (isinstance(wv, float) and math.isnan(wv))
            bruch = luecke is not None and vorx is not None and xv - vorx > luecke
            if not ok or bruch:
                if len(akt) > 1:
                    teile.append(akt)
                akt = []
            if ok:
                akt.append(f"{sx(xv):.1f},{sy(wv):.1f}")
            vorx = xv
        if len(akt) > 1:
            teile.append(akt)
        dash = ' stroke-dasharray="5 4"' if strich else ""
        cap = "butt" if strich else "round"
        for t in teile:
            out.append(f'<polyline points="{" ".join(t)}" fill="none" style="stroke:{farbe}" stroke-width="2" '
                       f'stroke-linecap="{cap}" stroke-linejoin="round"{dash}/>')
        if punkte:
            for xv, wv in zip(x, ws):
                if wv is None or (isinstance(wv, float) and math.isnan(wv)):
                    continue
                lab = xlabel(xv) if xlabel else xv
                out.append(f'<circle cx="{sx(xv):.1f}" cy="{sy(wv):.1f}" r="3" style="fill:{farbe}">'
                           f'<title>{esc(lab)} · {esc(name)}: {esc(yfmt(wv))}{esc(einheit)}</title></circle>')
    return (f'<svg viewBox="0 0 {W} {h}" width="100%" role="img" aria-label="{esc(aria)}" '
            f'preserveAspectRatio="xMinYMin meet">{"".join(out)}</svg>')


def balken(kat, schichten, yfmt, einheit="", h=H_STD, aria="", katlabel=tag_kurz, tiplabel=tag_lang, W=W):
    """kat: Kategorien (Tage); schichten: [(name, werte, farbe)] von unten nach oben."""
    summen = [sum(s[1][i] for s in schichten) for i in range(len(kat))]
    y0, y1, yt = nice_ticks(0, max(summen))
    n = len(kat)
    band = (W - ML - MR) / n
    bw = band * 0.72
    sx = lambda i: ML + band * i + (band - bw) / 2
    schritt = max(1, math.ceil(46 / band))
    xticks = [(i, katlabel(kat[i])) for i in range(0, n, schritt)]
    sy, out = _rahmen(h, y0, y1, yt, yfmt, xticks, lambda i: sx(i) + bw / 2, W)
    for i in range(n):
        basis = 0
        tip = [tiplabel(kat[i])]
        for name, ws, farbe in schichten:
            v = ws[i]
            if v > 0:
                out.append(f'<rect x="{sx(i):.1f}" y="{sy(basis + v):.1f}" width="{bw:.1f}" '
                           f'height="{max(0, sy(basis) - sy(basis + v)):.1f}" style="fill:{farbe}"/>')
            basis += v
        for name, ws, _ in reversed(schichten):
            tip.append(f"{name}: {yfmt(ws[i])}{einheit}")
        tip.append(f"Summe: {yfmt(summen[i])}{einheit}")
        out.append(f'<rect x="{ML + band * i:.1f}" y="{MT}" width="{band:.1f}" height="{h - MT - MB}" class="hit">'
                   f'<title>{esc(chr(10).join(tip))}</title></rect>')
    return (f'<svg viewBox="0 0 {W} {h}" width="100%" role="img" aria-label="{esc(aria)}" '
            f'preserveAspectRatio="xMinYMin meet">{"".join(out)}</svg>')


def legende(eintraege):
    teile = []
    for name, farbe, strich in eintraege:
        bg = (f"repeating-linear-gradient(90deg,{farbe} 0 4px,transparent 4px 7px)" if strich else farbe)
        teile.append(f'<span><i style="background:{bg}"></i>{esc(name)}</span>')
    return f'<div class="legend">{"".join(teile)}</div>'


def karte(titel, text, inhalt, breit=False, kid=""):
    return (f'<div class="card{" wide" if breit else ""}" id="{kid}"><h3>{esc(titel)}</h3>'
            f'<p>{text}</p>{inhalt}</div>')


# ---------------------------------------------------------------- Bericht
def erzeugen(hier=HIER):
    v = pd.read_csv(os.path.join(hier, "verlauf_15min.csv"))
    t = pd.read_csv(os.path.join(hier, "tage.csv"))
    p = pd.read_csv(os.path.join(hier, "tagesprofil.csv"))
    voll = t[t.vollstaendig == 1].reset_index(drop=True)
    tage = list(voll.tag)
    if not tage:
        sys.exit("Keine vollen Tage in tage.csv – Zeitraum in analyse.py prüfen")
    von_s, bis_s = tag_kurz(tage[0]), tag_kurz(tage[-1])

    S1, S2, S3, S4, S5, MUT = "var(--s1)", "var(--s2)", "var(--s3)", "var(--s4)", "var(--s5)", "var(--muted-series)"
    f0 = lambda x: de(x, 0)
    f1 = lambda x: de(x, 1)
    geraete = [(g, g.lower(), farbe) for g, farbe in zip(cfg.GERAETE, [S1, S2, S5, S4, MUT])]
    geraete_txt = " + ".join(cfg.GERAETE)

    # Kennzahlen
    ent = voll.entladung_gesamt_kwh.sum()
    bez = voll.netzbezug_kwh.sum()
    leer = voll.bezug_speicher_aus_kwh.sum()
    band = voll.regel_im_band_pct.mean()
    deck = 100 * ent / (ent + bez)
    anteil_leer = 100 * leer / bez
    spar = 100 * voll.takte_ohne_abfrage.sum() / voll.takte_gesamt.sum()

    # Zeitachse 15 min (Minuten seit Start)
    vt = pd.to_datetime(v.t)
    start = vt.min().normalize()
    vx = list(((vt - start).dt.total_seconds() / 60).round(1))
    tage_v = pd.date_range(start, vt.max().normalize(), freq="D")
    schritt = max(1, math.ceil(len(tage_v) * 64 / (W - ML - MR)))
    vticks = [((d - start).total_seconds() / 60, f"{d.day:02d}.{d.month:02d}.") for d in tage_v[::schritt]]
    werte = lambda col: [None if pd.isna(x) else float(x) for x in v[col]]

    # Tagesachse
    tx = list(range(len(tage)))
    schritt_t = max(1, math.ceil(len(tage) * 52 / (W_HALB - ML - MR)))
    tticks = [(i, tag_kurz(tage[i])) for i in range(0, len(tage), schritt_t)]
    tlab = lambda i: tag_lang(tage[int(i)])
    schritt_b = max(1, math.ceil(len(tage) * 52 / (W - ML - MR)))
    tticks_breit = [(i, tag_kurz(tage[i])) for i in range(0, len(tage), schritt_b)]
    tw = lambda col: [float(x) for x in voll[col]]

    # Tagesprofil
    px = list(p.stunde)
    pticks = [(hh, f"{hh} Uhr") for hh in range(0, 24, 4)]
    plab = lambda hh: f"{int(hh)}:00–{int(hh)}:59 Uhr"
    pw = lambda col: [float(x) for x in p[col]]

    karten_verlauf = [
        karte("Ladezustand (SOC)",
              "15-Minuten-Mittel je Gerät. Steigt tagsüber durch PV, fällt abends durch Entladung; Boden an der Entladegrenze.",
              legende([(g, f, False) for g, _, f in geraete]) +
              linien(vx, [(g, werte("soc_" + k), f, False) for g, k, f in geraete],
                     vticks, f0, " %", ymin=0, ymax=100, luecke=60, aria="Ladezustand über die Zeit"), True, "soc"),
        karte("Netzsaldo und Speicher-Ausgang",
              "15-Minuten-Mittel in Watt. Netzsaldo &gt; 0 heißt Bezug. Speicher-Ausgang bei 0 und hoher Netzsaldo: Speicher leer.",
              legende([("Netzsaldo", S3, False), ("Speicher-Ausgang (Summe)", S1, False)]) +
              linien(vx, [("Netzsaldo", werte("netzsaldo_w"), S3, False), ("Speicher-Ausgang", werte("speicher_w"), S1, False)],
                     vticks, f0, " W", h=H_HOCH, ref=0, luecke=60, aria="Netzsaldo und Speicher-Ausgang"), True, "leistung"),
    ]
    karten_tage = [
        karte("Energie pro Tag, nach Herkunft",
              "kWh je vollem Tag, gestapelt. Die Gesamthöhe ist der Verbrauch, der nicht direkt aus PV kam.",
              legende([("Entladung " + g, f, False) for g, _, f in geraete] +
                      [("Netzbezug bei leerem Speicher", S3, False), ("Übriger Netzbezug", S4, False)]) +
              balken(tage, [("Entladung " + g, tw("entladung_" + k + "_kwh"), f) for g, k, f in geraete] +
                           [("Netzbezug bei leerem Speicher", tw("bezug_speicher_aus_kwh"), S3),
                            ("Übriger Netzbezug", tw("bezug_regelrest_kwh"), S4)], f1, " kWh", h=H_HOCH,
                     aria="Energie pro Tag gestapelt"), True, "energie"),
        karte("Deckung durch Speicher", "Prozent: Entladung ÷ (Entladung + Netzbezug).",
              linien(tx, [("Deckung", tw("deckung_pct"), S1, False)], tticks, f0, " %", ymin=0, ymax=100,
                     punkte=True, xlabel=tlab, W=W_HALB, aria="Deckung pro Tag"), kid="deckung"),
        karte("Regelgüte", f"Anteil der Takte mit |Netzsaldo| ≤ {cfg.BAND_W} W, solange ein Speicher einspeist und nicht am Limit ist.",
              linien(tx, [(f"Im ±{cfg.BAND_W}-W-Band", tw("regel_im_band_pct"), S1, False)], tticks, f0, " %", ymin=80, ymax=100,
                     punkte=True, xlabel=tlab, W=W_HALB, aria="Regelgüte pro Tag"), kid="regel"),
        karte("Stellbefehle je Gerät", "Gesendete „Leistung gesetzt“-Befehle pro Tag.",
              legende([(g, f, False) for g, _, f in geraete]) +
              linien(tx, [(g, tw("stellbefehle_" + k), f, False) for g, k, f in geraete],
                     tticks, f0, punkte=True, xlabel=tlab, W=W_HALB, aria="Stellbefehle pro Tag"), kid="befehle"),
    ]
    karten_stoer = [
        karte("Störungen pro Tag",
              "Gerät nicht erreichbar, übersprungene Takte, Watchdog-Timeouts.",
              legende([("Nicht erreichbar", S3, False), ("Takt übersprungen", S4, False), ("Watchdog", S5, False)]) +
              linien(tx, [("Nicht erreichbar", tw("nicht_erreichbar"), S3, False),
                          ("Takt übersprungen", tw("takt_uebersprungen"), S4, False),
                          ("Watchdog", tw("watchdog"), S5, False)], tticks_breit, f0, punkte=True, xlabel=tlab,
                     aria="Störungen pro Tag"), True, "fehler"),
    ]
    karten_spar = [
        karte("Takte mit und ohne Geräteabfrage",
              f"Regeltakte pro vollem Tag (etwa {de(86400 / cfg.TAKT_S, 0)} bei {cfg.TAKT_S} s). Ohne Abfrage: Der Sparmodus hat das Polling ausgesetzt.",
              legende([("Ohne Geräteabfrage (eingespart)", S1, False), ("Mit Geräteabfrage", MUT, False)]) +
              balken(tage, [("Ohne Geräteabfrage", tw("takte_ohne_abfrage"), S1),
                            ("Mit Geräteabfrage", tw("takte_mit_abfrage"), MUT)], f0, aria="Takte pro Tag", W=W_HALB), kid="spartakte"),
        karte("Anteil Takte ohne Geräteabfrage",
              "Prozent der Takte pro Tag. Bei 12 ausgesetzten Takten je Pause liegt die Obergrenze bei gut 90 %.",
              linien(tx, [("Ohne Abfrage", tw("spar_anteil_pct"), S1, False)], tticks, f0, " %", ymin=50, ymax=100,
                     punkte=True, xlabel=tlab, W=W_HALB, aria="Anteil eingesparter Takte"), kid="sparanteil"),
    ]
    karten_profil = [
        karte("Leistung nach Uhrzeit", f"Mittel je Stunde über {tag_kurz(tage[0])}–{tag_kurz(tage[-1])}, in Watt.",
              legende([("Netzsaldo", S3, False), ("Speicher-Ausgang", S1, False)]) +
              linien(px, [("Netzsaldo", pw("netzsaldo_w"), S3, False), ("Speicher-Ausgang", pw("speicher_w"), S1, False)],
                     pticks, f0, " W", punkte=True, xlabel=plab, W=W_HALB, aria="Leistung nach Uhrzeit"), kid="profil"),
        karte("SOC nach Uhrzeit", "Niedrigster und höchster SOC, der in dieser Stunde an einem der Tage auftrat.",
              legende([(g + m, f, st) for g, _, f in geraete for m, st in ((" Max", False), (" Min", True))]) +
              linien(px, [(g + m, pw(c + k), f, st) for g, k, f in geraete
                          for m, c, st in ((" Max", "soc_max_", False), (" Min", "soc_min_", True))],
                     pticks, f0, " %", ymin=0, ymax=100, punkte=True, xlabel=plab, W=W_HALB, aria="SOC Min und Max nach Uhrzeit"),
              kid="profilsoc"),
    ]

    def abschnitt(titel, karten, sid):
        return f'<section id="{sid}"><h2>{esc(titel)}</h2><div class="grid">{"".join(karten)}</div></section>'

    kpis = [
        ("Aus Speicher entladen", f1(ent), "kWh", f"{von_s}–{bis_s}, beide Geräte"),
        ("Netzbezug", f1(bez), "kWh", f"{von_s}–{bis_s}, Netzsaldo &gt; 0"),
        ("Deckung durch Speicher", f0(deck), "%", "Entladung ÷ (Entladung + Bezug)"),
        (f"Regelung im ±{cfg.BAND_W}-W-Band", f1(band), "%", "solange ein Speicher einspeist"),
        ("Takte ohne Geräteabfrage", f0(spar), "%", "durch Sparmodus eingespart"),
    ]
    kpi_html = "".join(f'<div class="kpi"><span class="lbl">{a}</span><span class="val">{b}<span class="unit">{c}</span></span>'
                       f'<span class="note">{d}</span></div>' for a, b, c, d in kpis)
    stand = dt.datetime.now().strftime("%d.%m.%Y %H:%M")

    seite = f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Speicher-Statistik {esc(geraete_txt)}</title>
<style>
:root {{
  --bg: #f6f7f9; --panel: #ffffff; --fg: #1d2330; --muted: #5d6676; --line: #dde1e8;
  --grid: #e9ecf1; --axis: #b9c0cc; --ref: #8d96a6; --ok: #1f7a4d; --bad: #b3261e;
  --s1: #2f6fdf; --s2: #e07b1f; --s3: #c2414d; --s4: #8a5cc7; --s5: #2a9d8f; --muted-series: #c9ced8;
  --serif: Georgia, "Times New Roman", serif;
  --sans: "Segoe UI", system-ui, -apple-system, Roboto, Arial, sans-serif;
  color-scheme: light;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #14171d; --panel: #1c2028; --fg: #e8ebf0; --muted: #9aa3b2; --line: #2e3440;
    --grid: #262b35; --axis: #4a5262; --ref: #737d8f; --ok: #5cc98f; --bad: #f2867d;
    --s1: #6f9dff; --s2: #f3a259; --s3: #f07a84; --s4: #b393ea; --s5: #5cc9bb; --muted-series: #3d4452;
    color-scheme: dark;
  }}
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--fg); font-family: var(--sans); font-size: 15px; line-height: 1.45; }}
.wrap {{ max-width: 82rem; margin: 0 auto; padding: 28px 16px 48px; display: flex; flex-direction: column; gap: 32px; }}
h1 {{ font-family: var(--serif); font-weight: 400; font-size: 2rem; margin: 0; text-wrap: balance; }}
.take {{ color: var(--muted); max-width: 72ch; margin: 8px 0 0; }}
.take b {{ color: var(--fg); }}
.stand {{ color: var(--muted); font-size: 12px; margin-top: 6px; }}
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 11rem), 1fr)); gap: 12px; }}
.kpi, .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 16px; }}
.kpi {{ display: flex; flex-direction: column; gap: 4px; }}
.kpi .lbl, .kpi .note {{ font-size: 12px; color: var(--muted); }}
.kpi .val {{ font-family: var(--serif); font-size: 1.9rem; font-variant-numeric: tabular-nums; }}
.kpi .unit {{ font-family: var(--sans); font-size: 14px; color: var(--muted); margin-left: .3em; }}
section {{ display: flex; flex-direction: column; gap: 12px; }}
h2 {{ font-size: 1.15rem; font-weight: 600; margin: 0; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 26rem), 1fr)); gap: 12px; }}
.card {{ display: flex; flex-direction: column; gap: 8px; min-width: 0; }}
.card.wide {{ grid-column: 1 / -1; overflow-x: auto; }}
@media (max-width: 720px) {{ .card.wide svg {{ min-width: 680px; }} }}
.card h3 {{ font-size: 1rem; font-weight: 600; margin: 0; }}
.card p {{ font-size: 12.5px; color: var(--muted); margin: 0; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 14px; font-size: 12px; color: var(--muted); }}
.legend span {{ display: inline-flex; align-items: center; gap: .4em; }}
.legend i {{ width: 14px; height: 3px; border-radius: 2px; display: inline-block; }}
svg {{ display: block; overflow: visible; }}
svg .grid {{ stroke: var(--grid); stroke-width: 1; }}
svg .axis {{ stroke: var(--axis); stroke-width: 1; }}
svg .ref {{ stroke: var(--ref); stroke-dasharray: 4 3; }}
svg .tick {{ fill: var(--muted); font-size: 11px; font-family: var(--sans); font-variant-numeric: tabular-nums; }}
svg .hit {{ fill: transparent; }}
svg .hit:hover {{ fill: var(--fg); fill-opacity: .06; }}
.tablewrap {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }}
th {{ text-align: left; font-size: 12px; color: var(--muted); font-weight: 600; padding: 6px 8px; border-bottom: 1px solid var(--line); }}
td {{ padding: 8px; border-bottom: 1px solid var(--line); }}
.n {{ text-align: right; }}
td.good {{ color: var(--ok); font-weight: 600; }}
td.bad {{ color: var(--bad); font-weight: 600; }}
.method {{ font-size: 12.5px; color: var(--muted); max-width: 80ch; }}
.method p {{ margin: 0 0 6px; }}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>Speicher-Statistik {esc(geraete_txt)}</h1>
  <p class="take">In <b>{len(tage)}</b> vollen Tagen ({von_s}–{bis_s}) kamen <b>{f1(ent)} kWh</b> aus den Speichern und
  <b>{f1(bez)} kWh</b> aus dem Netz. Die Regelung sitzt gut; <b>{f0(anteil_leer)} %</b> des Netzbezugs fielen an,
  während beide Speicher nichts lieferten (leer bzw. an der Entladegrenze).</p>
  <div class="stand">Erstellt am {stand} aus den Debug-Logs des Multi-Device-Controllers.</div>
</header>
<div class="kpis">{kpi_html}</div>
{abschnitt("Verlauf über die Zeit", karten_verlauf, "verlauf")}
{abschnitt("Pro Tag", karten_tage, "tage")}
{abschnitt("Störungen", karten_stoer, "stoerungen")}
{abschnitt("Sparmodus: eingesparte Takte", karten_spar, "sparmodus")}
{abschnitt("Typischer Tagesverlauf", karten_profil, "tagesprofil")}
<section class="method" id="methode">
  <h2 style="color: var(--fg)">Wie gerechnet</h2>
  <p>Grundlage sind die Debug-Logs des Multi-Device-Controllers (ein Takt etwa alle {cfg.TAKT_S} s). Energie ist Leistung × Zeit bis zum
  nächsten Takt, Lücken über {cfg.MAX_LUECKE_S} s zählen nicht. „Bezug bei leerem Speicher“: Netzsaldo &gt; 0, während die Ist-Summe aller
  Geräte unter {cfg.LEER_SCHWELLE_W} W lag. Tageswerte, Kennzahlen und Tagesprofil zeigen nur volle Tage (mindestens {cfg.VOLLER_TAG_H} h erfasst). PV-Ladung steht nicht im Log und ist nur
  am SOC-Anstieg zu sehen.</p>
  <p>Werte zu einzelnen Tagen und Stunden erscheinen beim Darüberfahren über Punkte und Balken.</p>
</section>
</div>
</body>
</html>
"""
    ziel = os.path.join(hier, "bericht.html")
    with open(ziel, "w", encoding="utf-8") as fh:
        fh.write(seite)
    print("Bericht geschrieben:", ziel)
    return ziel


if __name__ == "__main__":
    erzeugen()
