"""Erzeugt bericht.html aus den CSV-Dateien von analyse.py.

Eine einzelne HTML-Datei, die ohne Internetverbindung funktioniert: Daten, Schriften und
das Zeichen-Skript sind eingebettet. Design wie Dashboard/Konfigurator (ZENDURE // …),
mit Tag/Nacht-Umschalter. Alle Grafiken folgen einem gemeinsamen, zoombaren Zeitraum.

Aufruf:  python bericht.py     (wird auch am Ende von analyse.py aufgerufen)

Hier gibt es nichts einzustellen. Zeitraum, Geräte und Schwellwerte kommen aus analyse.py:
der Zeitraum steckt bereits in den CSV-Dateien, Geräte und Schwellwerte werden für die
Beschriftungen aus analyse.py gelesen. Tageswerte = alle vollen Tage aus tage.csv.

Schriften: liegt zendure_fonts.css (IBM Plex, aus dem Dashboard) neben diesem Skript,
wird sie eingebettet; sonst nutzt der Bericht die Systemschrift.
"""
import datetime as dt
import html
import json
import math
import os
import sys

import pandas as pd

HIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HIER)
import analyse as cfg  # noqa: E402  nur Einstellungen; die Auswertung startet dabei nicht

SCHRIFTEN = "zendure_fonts.css"
# Gerätefarben in Reihenfolge; ab dem fünften Gerät wiederholen sie sich
FARBEN_GERAETE = ["var(--s1)", "var(--s2)", "var(--s6)", "var(--s7)"]


def _sauber(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return None
    if isinstance(x, float) and x.is_integer():
        return int(x)
    return x


def _liste(serie, nk=None):
    out = []
    for x in serie:
        x = _sauber(float(x)) if pd.notna(x) else None
        if nk is not None and isinstance(x, float):
            x = round(x, nk)
        out.append(x)
    return out


def geraeteliste(hier, verlauf):
    """[(Name, Spaltenschlüssel)] – aus geraete.csv (von analyse.py), sonst aus den CSV-Spalten."""
    pfad = os.path.join(hier, "geraete.csv")
    if os.path.exists(pfad):
        g = pd.read_csv(pfad, dtype=str)
        return list(zip(g.name, g.key))
    keys = [c[4:] for c in verlauf.columns if c.startswith("soc_")]
    return [(k.upper(), k) for k in keys]


def daten(hier):
    v = pd.read_csv(os.path.join(hier, "verlauf_15min.csv"))
    t = pd.read_csv(os.path.join(hier, "tage.csv"))
    p = pd.read_csv(os.path.join(hier, "tagesprofil.csv"))
    voll = t[t.vollstaendig == 1].reset_index(drop=True)
    if voll.empty:
        sys.exit("Keine vollen Tage in tage.csv – Zeitraum in analyse.py prüfen")
    # Takt: Einstellung aus analyse.py oder gemessen (Median der Takte je vollem Tag)
    takte_tag = int(voll.takte_gesamt.median())
    takt = cfg.TAKT_S or round(86400 / takte_tag, 1)
    geraete = [{"name": g, "key": k, "farbe": FARBEN_GERAETE[i % len(FARBEN_GERAETE)]}
               for i, (g, k) in enumerate(geraeteliste(hier, v))]
    # Zeit als Minuten seit 1970 ohne Zeitzone (Logzeit = Ortszeit, keine Sommerzeit-Sprünge)
    minuten = ((pd.to_datetime(v.t) - pd.Timestamp("1970-01-01")) // pd.Timedelta(minutes=1)).astype(int)
    verlauf = {"t": [int(x) for x in minuten], "netz": _liste(v.netzsaldo_w), "speicher": _liste(v.speicher_w)}
    for g in geraete:
        verlauf["soc_" + g["key"]] = _liste(v["soc_" + g["key"]])
    tage = {c: (list(voll[c]) if c == "tag" else _liste(voll[c], 3)) for c in voll.columns if c != "vollstaendig"}
    profil = {c: _liste(p[c]) for c in p.columns}
    return {
        "geraete": geraete,
        "cfg": {"band": cfg.BAND_W, "leer": cfg.LEER_SCHWELLE_W, "aktiv": cfg.AKTIV_SCHWELLE_W,
                "takt": takt, "takteTag": takte_tag, "luecke": cfg.MAX_LUECKE_S, "vollH": cfg.VOLLER_TAG_H},
        "mehr": len(geraete) > 1,
        "verlauf": verlauf, "tage": tage, "profil": profil,
        "profilVon": voll.tag.iloc[0], "profilBis": voll.tag.iloc[-1],
    }


def schriften(hier):
    pfad = os.path.join(hier, SCHRIFTEN)
    if os.path.exists(pfad):
        with open(pfad, encoding="utf-8") as fh:
            return fh.read()
    return "/* zendure_fonts.css nicht gefunden – Systemschrift */"


def erzeugen(hier=HIER):
    d = daten(hier)
    stand = dt.datetime.now().strftime("%d.%m.%Y %H:%M")
    geraete_txt = " + ".join(g["name"] for g in d["geraete"])
    chips = "".join(f'<span class="chip"><i style="background:{g["farbe"]}"></i>{html.escape(g["name"])}</span>'
                    for g in d["geraete"])
    c = d["cfg"]
    methode = (
        f"Grundlage sind die Debug-Logs des Multi-Device-Controllers (ein Takt etwa alle {str(c['takt']).replace('.', ',').removesuffix(',0')} s). "
        f"Energie ist Leistung × Zeit bis zum nächsten Takt, Lücken über {c['luecke']} s zählen nicht. "
        f"„Netzbezug bei {'leeren Speichern' if d['mehr'] else 'leerem Speicher'}“: Netzsaldo &gt; 0, während "
        f"{'die Ist-Summe aller Geräte' if d['mehr'] else 'der Ist-Wert des Geräts'} unter {c['leer']} W lag. "
        f"„Aktiv“: Ein Gerät gilt als aktiv, solange es mindestens {c['aktiv']} W ins Haus abgibt. Tageswerte und Kennzahlen zeigen nur volle Tage "
        f"(mindestens {c['vollH']} h erfasst). PV-Ladung steht nicht im Log und ist nur am SOC-Anstieg zu sehen."
    )
    seite = (VORLAGE
             .replace("__SCHRIFTEN__", schriften(hier))
             .replace("__TITEL__", html.escape(geraete_txt))
             .replace("__CHIPS__", chips)
             .replace("__STAND__", stand)
             .replace("__METHODE__", methode)
             .replace("__DATEN__", json.dumps(d, ensure_ascii=False, separators=(",", ":"))))
    ziel = os.path.join(hier, "bericht.html")
    with open(ziel, "w", encoding="utf-8") as fh:
        fh.write(seite)
    print("Bericht geschrieben:", ziel)
    return ziel


# ---------------------------------------------------------------- HTML-Vorlage
VORLAGE = r"""<!DOCTYPE html>
<html lang="de" data-theme="dark">
<script>(function(){var d=document.documentElement,s=null;
  try{s=localStorage.getItem('zendure_stat_theme');}catch(e){}
  try{if(s!=='dark'&&s!=='light')s=(window.matchMedia&&!window.matchMedia('(prefers-color-scheme: dark)').matches)?'light':'dark';}catch(e){s='dark';}
  d.setAttribute('data-theme',s);})();</script>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Zendure · Tagesstatistik</title>
<style>
__SCHRIFTEN__
</style>
<style>
  :root{
    --amber:#F2A93B; --amber-deep:#C97C1D; --teal:#4FD1C5; --teal-deep:#1FA394; --alert:#E2574C;
    --radius-lg:1.25rem; --radius-md:.875rem; --radius-sm:.625rem; --tap:2.5rem;
    --mono:'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
    --sans:'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  }
  html[data-theme="dark"]{
    color-scheme:dark;
    --bg:#0B1220;
    --bg-glow:radial-gradient(circle at 15% -10%, rgba(79,209,197,0.14), transparent 42%),
              radial-gradient(circle at 92% 6%, rgba(242,169,59,0.11), transparent 38%);
    --surface:#141E33; --surface-2:#1B2740; --border:rgba(255,255,255,0.08);
    --text:#EAF0F6; --text-muted:#8B9BB4;
    --shadow:0 10px 30px rgba(0,0,0,0.35), 0 2px 8px rgba(0,0,0,0.25);
    --teal-text:#4FD1C5; --amber-text:#F2A93B; --alert-text:#E2574C;
    --grid:rgba(255,255,255,0.06); --axis:rgba(255,255,255,0.22); --ref:#5B6B85;
    --s1:#4FD1C5; --s2:#F2A93B; --s3:#E2574C; --s4:#8F9BFF; --s5:#5CCB76; --s6:#E77BD0; --s7:#6CB6FF; --muted-series:#34445F;
    --sel:rgba(79,209,197,0.16);
  }
  html[data-theme="light"]{
    color-scheme:light;
    --bg:#EEF3F1;
    --bg-glow:radial-gradient(circle at 12% -10%, rgba(79,209,197,0.20), transparent 42%),
              radial-gradient(circle at 92% 4%, rgba(242,169,59,0.18), transparent 38%);
    --surface:#FFFFFF; --surface-2:#F3F7F6; --border:rgba(15,23,32,0.08);
    --text:#10192B; --text-muted:#5A6B82;
    --shadow:0 10px 24px rgba(20,30,45,0.10), 0 2px 6px rgba(20,30,45,0.06);
    --teal-text:#207B73; --amber-text:#99600A; --alert-text:#CF2E22;
    --grid:rgba(15,23,32,0.07); --axis:rgba(15,23,32,0.25); --ref:#8A97A8;
    --s1:#1FA394; --s2:#D08418; --s3:#CF2E22; --s4:#5B63D6; --s5:#2F8A46; --s6:#B4479C; --s7:#2F6FC4; --muted-series:#C9D3DD;
    --sel:rgba(31,163,148,0.14);
  }
  *{box-sizing:border-box;}
  html,body{margin:0;padding:0;}
  html{background:var(--bg);}
  body{font-family:var(--sans); color:var(--text); background:var(--bg); font-size:15px; line-height:1.45;}
  .app{min-height:100vh; background-image:var(--bg-glow); padding:1.25rem 16px 3.75rem;
       padding-top:calc(1.25rem + env(safe-area-inset-top, 0px));}
  .shell{max-width:1180px; margin:0 auto; display:flex; flex-direction:column; gap:1.75rem;}
  .mono, .num{font-family:var(--mono); font-feature-settings:'ss04' 1; font-variant-numeric:tabular-nums;}
  h1,h2,h3{margin:0; font:inherit;}
  :focus-visible{outline:2px solid var(--teal-text); outline-offset:3px;}

  /* Kopfzeile */
  header{display:flex; align-items:flex-start; justify-content:space-between; flex-wrap:wrap; gap:.75rem 1rem; padding:.25rem .25rem 0;}
  .brand{display:flex; flex-direction:column; gap:.5rem; min-width:0;}
  .brand .word{font-family:var(--mono); font-feature-settings:'ss04' 1; font-weight:600; letter-spacing:.14em;
               text-transform:uppercase; font-size:clamp(1.05rem, 1.6vw, 1.3rem);}
  .brand .word span{color:var(--teal-text);}
  .chips{display:flex; flex-wrap:wrap; gap:.375rem; align-items:center;}
  .chip{display:inline-flex; align-items:center; gap:.4rem; font-family:var(--mono); font-feature-settings:'ss04' 1;
        font-size:.78rem; font-weight:600; padding:.25rem .625rem; border-radius:999px;
        background:var(--surface); border:1px solid var(--border); box-shadow:var(--shadow);}
  .chip i{width:.55rem; height:.55rem; border-radius:50%; display:inline-block;}
  .brand .sub{font-size:.8rem; color:var(--text-muted);}
  .head-right{display:flex; align-items:center; gap:.625rem; flex-wrap:wrap; justify-content:flex-end;}
  .pill{display:flex; align-items:center; gap:.5rem; min-height:var(--tap); background:var(--surface);
        border:1px solid var(--border); border-radius:999px; padding:.375rem .875rem; box-shadow:var(--shadow);
        font-size:.8rem; color:var(--text-muted);}
  .pill b{font-family:var(--mono); color:var(--text); font-weight:600;}
  .icon-btn{min-width:var(--tap); height:var(--tap); padding:0 .7rem; display:inline-flex; align-items:center;
            justify-content:center; gap:.35rem; cursor:pointer; border-radius:999px; background:var(--surface);
            border:1px solid var(--border); color:var(--text); font-family:inherit; font-size:.95rem; box-shadow:var(--shadow);}
  .icon-btn:active{transform:scale(.95);}

  /* Zeitraum-Leiste */
  .zoombar{position:sticky; top:.5rem; z-index:30; padding:.5rem .625rem; border-radius:var(--radius-lg);
           background:color-mix(in srgb, var(--surface) 90%, transparent); border:1px solid var(--border);
           box-shadow:var(--shadow); backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px);}
  .zoombar .in{display:flex; flex-wrap:wrap; align-items:center; gap:.5rem .75rem;}
  .zoombar .seg{box-shadow:none; background:var(--surface-2);}
  .seg{display:inline-flex; background:var(--surface); border:1px solid var(--border); border-radius:999px;
       padding:.1875rem; box-shadow:var(--shadow);}
  .seg button{min-height:2.125rem; min-width:2.375rem; padding:0 .7rem; border:0; background:none; color:var(--text);
              font-family:var(--mono); font-feature-settings:'ss04' 1; font-weight:600; font-size:.8rem;
              border-radius:999px; cursor:pointer;}
  .seg button:hover{background:var(--surface-2);}
  .seg button.on{background:var(--teal-deep); color:#fff;}
  .seg button:disabled{opacity:.35; cursor:default; background:none;}
  .range-lbl{font-family:var(--mono); font-feature-settings:'ss04' 1; font-size:.85rem; font-weight:600;}
  .range-lbl small{display:block; font-family:var(--sans); font-weight:400; font-size:.72rem; color:var(--text-muted);}

  .take{color:var(--text-muted); max-width:75ch; margin:0 .25rem; font-size:.92rem;}
  .take b{color:var(--text); font-family:var(--mono); font-feature-settings:'ss04' 1; font-weight:600;}

  .kpis{display:grid; grid-template-columns:repeat(auto-fit, minmax(min(100%, 10.5rem), 1fr)); gap:1rem;}
  .card{background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg); box-shadow:var(--shadow);}
  .kpi{padding:1rem 1.125rem; display:flex; flex-direction:column; gap:.25rem; min-width:0;}
  .kpi .lbl{font-size:.8rem; color:var(--text-muted); line-height:1.3;}
  .kpi .val{font-family:var(--mono); font-feature-settings:'ss04' 1; font-weight:600; font-size:clamp(1.5rem, 3vw, 2rem); line-height:1.1;}
  .kpi .unit{font-size:.9rem; font-weight:500; color:var(--text-muted); margin-left:.3em;}
  .kpi .note{font-size:.72rem; color:var(--text-muted);}

  section{display:flex; flex-direction:column; gap:.75rem;}
  .section-title{font-size:.8rem; color:var(--text-muted); letter-spacing:.08em; text-transform:uppercase; margin:0 .25rem;}
  .grid{display:grid; grid-template-columns:repeat(auto-fit, minmax(min(100%, 26rem), 1fr)); gap:1rem;}
  .chart{padding:1.125rem 1.25rem 1rem; display:flex; flex-direction:column; gap:.5rem; min-width:0;}
  .chart.wide{grid-column:1 / -1; overflow-x:auto;}
  @media (max-width:720px){ .chart.wide svg{min-width:680px;} }
  .chart h3{font-weight:600; font-size:1rem;}
  .chart p{font-size:.8rem; color:var(--text-muted); margin:0;}
  .legend{display:flex; flex-wrap:wrap; gap:.875rem; font-size:.76rem; color:var(--text-muted);}
  .legend span{display:inline-flex; align-items:center; gap:.4em;}
  .legend i{width:14px; height:3px; border-radius:2px; display:inline-block;}
  .leer{font-size:.85rem; color:var(--text-muted); padding:2rem 0; text-align:center;}

  svg{display:block; overflow:visible; user-select:none; -webkit-user-select:none;}
  svg .gl{stroke:var(--grid); stroke-width:1;}
  svg .ax{stroke:var(--axis); stroke-width:1;}
  svg .ref{stroke:var(--ref); stroke-dasharray:4 3;}
  svg .tk{fill:var(--text-muted); font-size:11px; font-family:var(--mono); font-feature-settings:'ss04' 1;}
  svg .hit{fill:transparent; cursor:crosshair;}
  svg .hit.day{cursor:zoom-in;}
  svg .hl{fill:var(--text); fill-opacity:.06;}
  svg .hv{stroke:var(--text-muted); stroke-width:1; stroke-dasharray:3 3;}
  svg .selr{fill:var(--sel); stroke:var(--teal-text); stroke-width:1;}

  .tip{position:fixed; z-index:50; pointer-events:none; opacity:0; transition:opacity .12s ease;
       background:var(--surface-2); color:var(--text); border:1px solid var(--border); border-radius:var(--radius-sm);
       box-shadow:var(--shadow); padding:.5rem .7rem; font-size:.78rem; line-height:1.45; max-width:18rem;}
  .tip.show{opacity:1;}
  .tip .h{font-weight:600; margin-bottom:.15rem;}
  .tip .r{display:flex; align-items:center; gap:.45rem; justify-content:space-between;}
  .tip .r span:first-child{display:inline-flex; align-items:center; gap:.4rem; color:var(--text-muted);}
  .tip .r i{width:.5rem; height:.5rem; border-radius:50%; display:inline-block;}
  .tip .r b{font-family:var(--mono); font-feature-settings:'ss04' 1; font-weight:600;}

  .method{font-size:.8rem; color:var(--text-muted); max-width:80ch; margin:0 .25rem;}
  .method p{margin:0 0 .4rem;}
  footer{text-align:center; color:var(--text-muted); font-size:.74rem;}
  @media (max-width:640px){ .head-right{width:100%; justify-content:flex-start;} }
  @media (prefers-reduced-motion: reduce){ *{transition-duration:0s !important;} }
</style>
</head>
<body>
<div class="app">
<div class="shell">
  <header>
    <div class="brand">
      <h1 class="word">ZENDURE <span>// TAGESSTATISTIK</span></h1>
      <div class="chips" aria-label="Geräte">__CHIPS__</div>
      <div class="sub">Auswertung der Debug-Logs des Multi-Device-Controllers</div>
    </div>
    <div class="head-right">
      <div class="pill">Stand <b>__STAND__</b></div>
      <button type="button" class="icon-btn" id="themeBtn" aria-label="Tag/Nacht umschalten" title="Tag/Nacht umschalten">☾</button>
    </div>
  </header>

  <div class="zoombar" role="toolbar" aria-label="Zeitraum">
    <div class="in">
      <div class="seg" id="presets">
        <button type="button" data-w="0">Alles</button>
        <button type="button" data-w="10080">7 T</button>
        <button type="button" data-w="4320">3 T</button>
      </div>
      <div class="seg">
        <button type="button" id="pL" aria-label="Früher" title="Früher">‹</button>
        <button type="button" id="zOut" aria-label="Herauszoomen" title="Herauszoomen">−</button>
        <button type="button" id="zIn" aria-label="Hineinzoomen" title="Hineinzoomen">+</button>
        <button type="button" id="pR" aria-label="Später" title="Später">›</button>
      </div>
      <div class="range-lbl" id="rangeLbl" aria-live="polite"></div>
    </div>
  </div>

  <p class="take" id="take"></p>
  <div class="kpis" id="kpis"></div>

  <section>
    <h2 class="section-title">Verlauf über die Zeit</h2>
    <div class="grid">
      <div class="card chart wide"><h3>Ladezustand (SOC)</h3>
        <p>15-Minuten-Mittel je Gerät. Bereich mit der Maus aufziehen = hineinzoomen, Doppelklick = alles.</p>
        <div class="legend" id="lg-soc"></div><div id="c-soc"></div></div>
      <div class="card chart wide"><h3>Netzsaldo und Speicher-Ausgang</h3>
        <p>15-Minuten-Mittel in Watt. Netzsaldo &gt; 0 heißt Bezug. Speicher-Ausgang bei 0 und hoher Netzsaldo: Speicher leer.</p>
        <div class="legend" id="lg-leistung"></div><div id="c-leistung"></div></div>
    </div>
  </section>

  <section>
    <h2 class="section-title">Pro Tag · volle Tage im Ausschnitt</h2>
    <div class="grid">
      <div class="card chart wide"><h3>Energie pro Tag, nach Herkunft</h3>
        <p>kWh je Tag, gestapelt. Die Gesamthöhe ist der Verbrauch, der nicht direkt aus PV kam. Klick auf einen Tag zoomt dorthin.</p>
        <div class="legend" id="lg-energie"></div><div id="c-energie"></div></div>
      <div class="card chart wide"><h3>Aktivzeit pro Tag</h3>
        <p id="txt-aktiv"></p>
        <div class="legend" id="lg-aktiv"></div><div id="c-aktiv"></div></div>
      <div class="card chart"><h3>Deckung durch Speicher</h3>
        <p>Prozent: Entladung ÷ (Entladung + Netzbezug).</p><div id="c-deckung"></div></div>
      <div class="card chart"><h3>Regelgüte</h3>
        <p id="txt-regel"></p><div id="c-regel"></div></div>
      <div class="card chart"><h3>Stellbefehle je Gerät</h3>
        <p>Gesendete „Leistung gesetzt“-Befehle pro Tag.</p>
        <div class="legend" id="lg-befehle"></div><div id="c-befehle"></div></div>
      <div class="card chart"><h3>Störungen pro Tag</h3>
        <p>Gerät nicht erreichbar, übersprungene Takte, Watchdog-Timeouts.</p>
        <div class="legend" id="lg-fehler"></div><div id="c-fehler"></div></div>
    </div>
  </section>

  <section>
    <h2 class="section-title">Sparmodus · eingesparte Takte</h2>
    <div class="grid">
      <div class="card chart"><h3>Takte mit und ohne Geräteabfrage</h3>
        <p id="txt-takte"></p>
        <div class="legend" id="lg-takte"></div><div id="c-takte"></div></div>
      <div class="card chart"><h3>Anteil Takte ohne Geräteabfrage</h3>
        <p>Prozent der Takte pro Tag. Bei 12 ausgesetzten Takten je Pause liegt die Obergrenze bei gut 90 %.</p>
        <div id="c-spar"></div></div>
    </div>
  </section>

  <section>
    <h2 class="section-title">Typischer Tagesverlauf · alle vollen Tage</h2>
    <div class="grid">
      <div class="card chart"><h3>Netzsaldo nach Uhrzeit</h3>
        <p class="txt-pband"></p>
        <div class="legend" id="lg-pnetz"></div><div id="c-pnetz"></div></div>
      <div class="card chart"><h3 id="h-pspeicher">Speicher-Ausgang nach Uhrzeit</h3>
        <p class="txt-pband"></p>
        <div class="legend" id="lg-pspeicher"></div><div id="c-pspeicher"></div></div>
    </div>
    <div class="grid" id="profilsoc"></div>
  </section>

  <section class="method">
    <h2 class="section-title" style="margin:0 0 .5rem">Wie gerechnet</h2>
    <p>__METHODE__</p>
    <p>Der Zeitraum oben gilt für Kennzahlen, Verlauf und Tageswerte. Das Tagesprofil zeigt immer alle vollen Tage.</p>
  </section>
  <footer>Eigenständige Datei · funktioniert ohne Internetverbindung · erzeugt von bericht.py</footer>
</div>
</div>
<div class="tip" id="tip" role="tooltip"></div>

<script id="daten" type="application/json">__DATEN__</script>
<script>
(function(){
'use strict';
var D = JSON.parse(document.getElementById('daten').textContent);
var NS = 'http://www.w3.org/2000/svg';
var W = 960, WH = 560, H = 260, HT = 320, ML = 52, MR = 16, MT = 14, MB = 30;
var TAG = 1440, MIN_SPAN = 120;
var WT = ['So','Mo','Di','Mi','Do','Fr','Sa'];
var G = D.geraete, V = D.verlauf, T = D.tage, MEHR = D.mehr;
var LEER_TXT = MEHR ? 'Netzbezug bei leeren Speichern' : 'Netzbezug bei leerem Speicher';
var NT = V.t.length;
var LO = Math.floor(V.t[0] / TAG) * TAG, HI = Math.ceil((V.t[NT - 1] + 15) / TAG) * TAG;
var range = {a: LO, b: HI};

/* ---------------- Formate ---------------- */
function de(v, nk){
  if (v === null || v === undefined || isNaN(v)) return '–';
  return Number(v).toLocaleString('de-DE', {minimumFractionDigits: nk, maximumFractionDigits: nk});
}
function f0(v){ return de(v, 0); }
function f1(v){ return de(v, 1); }
function esc(s){ return String(s).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
function pad(n){ return (n < 10 ? '0' : '') + n; }
function dOf(min){ return new Date(min * 60000); }            /* UTC = Logzeit */
function dKurz(min){ var d = dOf(min); return pad(d.getUTCDate()) + '.' + pad(d.getUTCMonth() + 1) + '.'; }
function dLang(min){ return WT[dOf(min).getUTCDay()] + ' ' + dKurz(min); }
function hm(min){ var d = dOf(min); return pad(d.getUTCHours()) + ':' + pad(d.getUTCMinutes()); }
function tagMin(s){ return Date.UTC(+s.slice(0,4), +s.slice(5,7) - 1, +s.slice(8,10)) / 60000; }
var TMIN = T.tag.map(tagMin);

/* ---------------- Achsen ---------------- */
function niceTicks(lo, hi, n){
  n = n || 5; if (hi <= lo) hi = lo + 1;
  var raw = (hi - lo) / n, mag = Math.pow(10, Math.floor(Math.log10(raw))), step = 10 * mag;
  [1, 2, 2.5, 5, 10].some(function(m){ if (m * mag >= raw){ step = m * mag; return true; } });
  var a = Math.floor(lo / step) * step, b = Math.ceil(hi / step) * step, t = [];
  for (var v = a; v <= b + step / 1000; v += step) t.push(Math.round(v * 1e6) / 1e6);
  return {lo: a, hi: b, t: t};
}
function yAchse(werte, o){
  var alle = werte.filter(function(v){ return v !== null && !isNaN(v); });
  var lo = o.ymin !== undefined ? o.ymin : Math.min(0, Math.min.apply(null, alle.length ? alle : [0]));
  var hi = o.ymax !== undefined ? o.ymax : Math.max.apply(null, alle.length ? alle : [1]);
  var n = niceTicks(lo, hi);
  if (o.ymin !== undefined){ n.lo = o.ymin; n.t = n.t.filter(function(t){ return t >= o.ymin; }); }
  if (o.ymax !== undefined){ n.hi = o.ymax; n.t = n.t.filter(function(t){ return t <= o.ymax; }); }
  if (o.yticks) n.t = o.yticks;
  return n;
}
function rahmen(w, h, ya, yfmt, xticks){
  var sy = function(v){ return MT + (h - MT - MB) * (1 - (v - ya.lo) / (ya.hi - ya.lo)); };
  var o = [];
  ya.t.forEach(function(t){
    var y = sy(t).toFixed(1);
    o.push('<line x1="' + ML + '" x2="' + (w - MR) + '" y1="' + y + '" y2="' + y + '" class="gl"/>');
    o.push('<text x="' + (ML - 8) + '" y="' + y + '" dy="0.32em" text-anchor="end" class="tk">' + esc(yfmt(t)) + '</text>');
  });
  o.push('<line x1="' + ML + '" x2="' + (w - MR) + '" y1="' + (h - MB) + '" y2="' + (h - MB) + '" class="ax"/>');
  xticks.forEach(function(xt){
    var x = xt[0], anchor = x < ML + 24 ? 'start' : (x > w - MR - 24 ? 'end' : 'middle');
    o.push('<text x="' + x.toFixed(1) + '" y="' + (h - MB + 18) + '" text-anchor="' + anchor + '" class="tk">' + esc(xt[1]) + '</text>');
  });
  return {sy: sy, out: o};
}
function svgOpen(w, h, aria){
  return '<svg viewBox="0 0 ' + w + ' ' + h + '" width="100%" role="img" aria-label="' + esc(aria) + '" preserveAspectRatio="xMinYMin meet">';
}
function svgX(svg, w, ev){ var r = svg.getBoundingClientRect(); return (ev.clientX - r.left) * w / r.width; }

/* ---------------- Hinweis-Box ---------------- */
var tip = document.getElementById('tip');
function zeigeTip(ev, kopf, zeilen){
  tip.innerHTML = '<div class="h">' + esc(kopf) + '</div>' + zeilen.map(function(z){
    return '<div class="r"><span>' + (z[2] ? '<i style="background:' + z[2] + '"></i>' : '') + esc(z[0]) +
           '</span><b>' + esc(z[1]) + '</b></div>';
  }).join('');
  tip.classList.add('show');
  var r = tip.getBoundingClientRect(), x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + r.width > window.innerWidth - 8) x = ev.clientX - r.width - 14;
  if (y + r.height > window.innerHeight - 8) y = ev.clientY - r.height - 14;
  tip.style.left = Math.max(8, x) + 'px'; tip.style.top = Math.max(8, y) + 'px';
}
function versteckeTip(){ tip.classList.remove('show'); }

function legende(id, eintraege){
  var el = document.getElementById(id); if (!el) return;
  el.innerHTML = eintraege.map(function(e){
    var bg = e[2] ? 'repeating-linear-gradient(90deg,' + e[1] + ' 0 4px,transparent 4px 7px)' : e[1];
    return '<span><i style="background:' + bg + '"></i>' + esc(e[0]) + '</span>';
  }).join('');
}

/* ---------------- Zeit-Liniengrafik (zoombar) ---------------- */
function suche(t){ var lo = 0, hi = NT; while (lo < hi){ var m = (lo + hi) >> 1; if (V.t[m] < t) lo = m + 1; else hi = m; } return lo; }
function zeitTicks(a, b, w){
  var span = b - a, maxN = Math.max(3, Math.floor((w - ML - MR) / 74));
  var schritte = [30, 60, 120, 180, 360, 720, 1440, 2880, 4320, 10080, 20160];
  var st = schritte[schritte.length - 1];
  for (var i = 0; i < schritte.length; i++){ if (span / schritte[i] <= maxN){ st = schritte[i]; break; } }
  var out = [];
  for (var t = Math.ceil(a / st) * st; t <= b; t += st){
    out.push([t, st >= TAG || t % TAG === 0 ? dKurz(t) : hm(t)]);
  }
  return out;
}
function zeitLinien(id, o){
  var el = document.getElementById(id), w = W, h = o.h || H, a = range.a, b = range.b;
  var i0 = Math.max(0, suche(a) - 1), i1 = Math.min(NT, suche(b) + 1);
  var sx = function(t){ return ML + (w - ML - MR) * (t - a) / (b - a); };
  var sichtbar = [];
  o.serien.forEach(function(s){ for (var i = i0; i < i1; i++) if (V.t[i] >= a && V.t[i] <= b) sichtbar.push(s.werte[i]); });
  var ya = yAchse(sichtbar, o);
  var xt = zeitTicks(a, b, w).map(function(x){ return [sx(x[0]), x[1]]; });
  var r = rahmen(w, h, ya, o.yfmt, xt), sy = r.sy, out = r.out;
  var cid = 'cl-' + id;
  out.push('<defs><clipPath id="' + cid + '"><rect x="' + ML + '" y="0" width="' + (w - ML - MR) + '" height="' + h + '"/></clipPath></defs>');
  if (o.ref !== undefined && ya.lo <= o.ref && o.ref <= ya.hi)
    out.push('<line x1="' + ML + '" x2="' + (w - MR) + '" y1="' + sy(o.ref).toFixed(1) + '" y2="' + sy(o.ref).toFixed(1) + '" class="ref"/>');
  out.push('<g clip-path="url(#' + cid + ')">');
  o.serien.forEach(function(s){
    var teile = [], akt = [], vor = null;
    for (var i = i0; i < i1; i++){
      var v = s.werte[i], ok = v !== null && !isNaN(v), bruch = vor !== null && V.t[i] - vor > 60;
      if (!ok || bruch){ if (akt.length > 1) teile.push(akt); akt = []; }
      if (ok) akt.push(sx(V.t[i]).toFixed(1) + ',' + sy(Math.max(ya.lo, Math.min(ya.hi, v))).toFixed(1));
      vor = V.t[i];
    }
    if (akt.length > 1) teile.push(akt);
    teile.forEach(function(t){
      out.push('<polyline points="' + t.join(' ') + '" fill="none" style="stroke:' + s.farbe + '" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>');
    });
  });
  out.push('</g><g class="hov"></g><rect class="selr" x="0" y="' + MT + '" width="0" height="' + (h - MT - MB) + '" style="display:none"/>');
  out.push('<rect class="hit" x="' + ML + '" y="' + MT + '" width="' + (w - ML - MR) + '" height="' + (h - MT - MB) + '"/>');
  el.innerHTML = svgOpen(w, h, o.aria) + out.join('') + '</svg>';

  var svg = el.firstChild, hov = svg.querySelector('.hov'), sel = svg.querySelector('.selr'), hit = svg.querySelector('.hit');
  var zuT = function(x){ return a + (x - ML) * (b - a) / (w - ML - MR); };
  var start = null;
  function hover(ev){
    var x = svgX(svg, w, ev), t = zuT(x), i = suche(t);
    if (i > 0 && (i >= NT || Math.abs(V.t[i - 1] - t) < Math.abs(V.t[i] - t))) i--;
    if (i < 0 || i >= NT || Math.abs(V.t[i] - t) > 45){ hov.innerHTML = ''; versteckeTip(); return; }
    var px = sx(V.t[i]).toFixed(1), g = '<line class="hv" x1="' + px + '" x2="' + px + '" y1="' + MT + '" y2="' + (h - MB) + '"/>';
    var zeilen = [];
    o.serien.forEach(function(s){
      var v = s.werte[i];
      if (v !== null && !isNaN(v)) g += '<circle cx="' + px + '" cy="' + sy(v).toFixed(1) + '" r="3.5" style="fill:' + s.farbe + '"/>';
      zeilen.push([s.name, o.yfmt(v) + o.einheit, s.farbe]);
    });
    hov.innerHTML = g;
    zeigeTip(ev, dLang(V.t[i]) + ' ' + hm(V.t[i]) + '–' + hm(V.t[i] + 15), zeilen);
  }
  hit.addEventListener('pointermove', function(ev){
    if (start !== null){
      var x = Math.max(ML, Math.min(w - MR, svgX(svg, w, ev)));
      sel.setAttribute('x', Math.min(start, x)); sel.setAttribute('width', Math.abs(x - start)); sel.style.display = '';
      versteckeTip(); hov.innerHTML = ''; return;
    }
    hover(ev);
  });
  hit.addEventListener('pointerleave', function(){ if (start === null){ hov.innerHTML = ''; versteckeTip(); } });
  hit.addEventListener('pointerdown', function(ev){
    if (ev.pointerType !== 'mouse'){ hover(ev); return; }
    if (ev.button !== 0) return;
    start = svgX(svg, w, ev); hit.setPointerCapture(ev.pointerId);
  });
  hit.addEventListener('pointerup', function(ev){
    if (start === null) return;
    var x = Math.max(ML, Math.min(w - MR, svgX(svg, w, ev))), s0 = start;
    start = null; sel.style.display = 'none';
    if (Math.abs(x - s0) > 6) setze(zuT(Math.min(s0, x)), zuT(Math.max(s0, x)));
  });
  hit.addEventListener('dblclick', function(){ setze(LO, HI); });
}

/* ---------------- Kategorie-Grafiken (Tage, Stunden) ---------------- */
function katRahmen(id, o, werte){
  var w = o.w || W, h = o.h || H, n = o.kat.length, band = (w - ML - MR) / n;
  var ya = yAchse(werte, o);
  var schritt = o.tickSchritt || Math.max(1, Math.ceil(64 / band)), xt = [];
  for (var i = 0; i < n; i += schritt) xt.push([ML + band * (i + 0.5), o.katLabel(o.kat[i], i)]);
  var r = rahmen(w, h, ya, o.yfmt, xt);
  return {w: w, h: h, n: n, band: band, ya: ya, sy: r.sy, out: r.out};
}
function katFertig(id, o, f, tipZeilen){
  var el = document.getElementById(id);
  f.out.push('<rect class="hl" x="0" y="' + MT + '" width="0" height="' + (f.h - MT - MB) + '" style="display:none"/>');
  f.out.push('<rect class="hit' + (o.klick ? ' day' : '') + '" x="' + ML + '" y="' + MT + '" width="' + (f.w - ML - MR) + '" height="' + (f.h - MT - MB) + '"/>');
  el.innerHTML = svgOpen(f.w, f.h, o.aria) + f.out.join('') + '</svg>';
  var svg = el.firstChild, hl = svg.querySelector('.hl'), hit = svg.querySelector('.hit');
  function idx(ev){ return Math.max(0, Math.min(f.n - 1, Math.floor((svgX(svg, f.w, ev) - ML) / f.band))); }
  function hover(ev){
    var i = idx(ev);
    hl.setAttribute('x', ML + f.band * i); hl.setAttribute('width', f.band); hl.style.display = '';
    zeigeTip(ev, o.tipLabel(o.kat[i], i), tipZeilen(i));
  }
  hit.addEventListener('pointermove', hover);
  hit.addEventListener('pointerdown', function(ev){ if (ev.pointerType !== 'mouse') hover(ev); });
  hit.addEventListener('pointerleave', function(){ hl.style.display = 'none'; versteckeTip(); });
  if (o.klick) hit.addEventListener('click', function(ev){ if (ev.pointerType !== 'touch') o.klick(idx(ev)); });
}
function leer(id, text){ document.getElementById(id).innerHTML = '<div class="leer">' + esc(text) + '</div>'; }

function stapel(id, o){
  if (!o.kat.length) return leer(id, 'Keine vollen Tage im gewählten Zeitraum.');
  var summen = o.kat.map(function(_, i){ return o.serien.reduce(function(s, r){ return s + (r.werte[i] || 0); }, 0); });
  o.ymin = 0;
  var f = katRahmen(id, o, summen.concat([0])), bw = f.band * 0.72;
  for (var i = 0; i < f.n; i++){
    var basis = 0, x = ML + f.band * i + (f.band - bw) / 2;
    o.serien.forEach(function(s){
      var v = s.werte[i] || 0;
      if (v > 0) f.out.push('<rect x="' + x.toFixed(1) + '" y="' + f.sy(basis + v).toFixed(1) + '" width="' + bw.toFixed(1) +
                            '" height="' + Math.max(0, f.sy(basis) - f.sy(basis + v)).toFixed(1) + '" rx="2" style="fill:' + s.farbe + '"/>');
      basis += v;
    });
  }
  katFertig(id, o, f, function(i){
    var z = o.serien.slice().reverse().map(function(s){ return [s.name, o.yfmt(s.werte[i]) + o.einheit, s.farbe]; });
    z.push(['Summe', o.yfmt(summen[i]) + o.einheit]);
    return z;
  });
}
function gruppe(id, o){
  if (!o.kat.length) return leer(id, 'Keine vollen Tage im gewählten Zeitraum.');
  var alle = [0]; o.serien.forEach(function(s){ alle = alle.concat(s.werte); });
  o.ymin = 0;
  var f = katRahmen(id, o, alle), m = o.serien.length, bw = Math.min(f.band * 0.78 / m, 44), gw = bw * m;
  for (var i = 0; i < f.n; i++){
    var x0 = ML + f.band * i + (f.band - gw) / 2;
    o.serien.forEach(function(s, j){
      var v = s.werte[i] || 0;
      if (v > 0) f.out.push('<rect x="' + (x0 + j * bw + 0.5).toFixed(1) + '" y="' + f.sy(v).toFixed(1) + '" width="' + Math.max(0.5, bw - 1).toFixed(1) +
                            '" height="' + Math.max(0, f.sy(0) - f.sy(v)).toFixed(1) + '" rx="2" style="fill:' + s.farbe + '"/>');
    });
  }
  katFertig(id, o, f, function(i){ return o.serien.map(function(s){ return [s.name, o.yfmt(s.werte[i]) + o.einheit, s.farbe]; }); });
}
function katLinie(id, o){
  if (!o.kat.length) return leer(id, 'Keine vollen Tage im gewählten Zeitraum.');
  var alle = []; o.serien.forEach(function(s){ alle = alle.concat(s.werte); });
  var f = katRahmen(id, o, alle), sx = function(i){ return ML + f.band * (i + 0.5); };
  if (o.ref !== undefined && f.ya.lo <= o.ref && o.ref <= f.ya.hi)
    f.out.push('<line x1="' + ML + '" x2="' + (f.w - MR) + '" y1="' + f.sy(o.ref).toFixed(1) + '" y2="' + f.sy(o.ref).toFixed(1) + '" class="ref"/>');
  o.serien.forEach(function(s){
    var pts = [];
    s.werte.forEach(function(v, i){ if (v !== null && !isNaN(v)) pts.push(sx(i).toFixed(1) + ',' + f.sy(v).toFixed(1)); });
    if (pts.length > 1) f.out.push('<polyline points="' + pts.join(' ') + '" fill="none" style="stroke:' + s.farbe + '" stroke-width="2" stroke-linejoin="round"' +
                                   (s.strich ? ' stroke-dasharray="5 4"' : ' stroke-linecap="round"') + '/>');
    if (f.n <= 62) s.werte.forEach(function(v, i){
      if (v !== null && !isNaN(v)) f.out.push('<circle cx="' + sx(i).toFixed(1) + '" cy="' + f.sy(v).toFixed(1) + '" r="3" style="fill:' + s.farbe + '"/>');
    });
  });
  katFertig(id, o, f, function(i){ return o.serien.map(function(s){ return [s.name, o.yfmt(s.werte[i]) + o.einheit, s.farbe]; }); });
}

/* ---------------- Zeitraum ---------------- */
function setze(a, b){
  var span = Math.max(MIN_SPAN, b - a), voll = HI - LO;
  if (span >= voll){ a = LO; b = HI; }
  else {
    var m = (a + b) / 2; a = m - span / 2; b = m + span / 2;
    if (a < LO){ b += LO - a; a = LO; }
    if (b > HI){ a -= b - HI; b = HI; }
  }
  range.a = Math.round(a); range.b = Math.round(b);
  zeichne();
}
function preset(w){
  if (!w) return setze(LO, HI);
  var m = (range.a + range.b) / 2, a = Math.round((m - w / 2) / TAG) * TAG;
  setze(a, a + w);
}
function tageImAusschnitt(){
  var idx = [];
  TMIN.forEach(function(t, i){ if (t + TAG > range.a && t < range.b) idx.push(i); });
  return idx;
}

/* ---------------- Zeichnen ---------------- */
var S = {s1:'var(--s1)', s2:'var(--s2)', s3:'var(--s3)', s4:'var(--s4)', s5:'var(--s5)', mut:'var(--muted-series)'};
function spalte(name, idx){ var c = T[name] || []; return idx.map(function(i){ var v = c[i]; return v === undefined ? null : v; }); }
function summe(name, idx){ return spalte(name, idx).reduce(function(s, v){ return s + (v || 0); }, 0); }

function kennzahlen(idx){
  var el = document.getElementById('kpis'), take = document.getElementById('take');
  if (!idx.length){
    el.innerHTML = '';
    take.textContent = 'Im gewählten Ausschnitt liegt kein voller Tag – Kennzahlen und Tageswerte brauchen mindestens einen vollen Tag.';
    return;
  }
  var ent = summe('entladung_gesamt_kwh', idx), bez = summe('netzbezug_kwh', idx), leerB = summe('bezug_speicher_aus_kwh', idx);
  var band = summe('regel_im_band_pct', idx) / idx.length, deck = 100 * ent / (ent + bez), anteil = bez ? 100 * leerB / bez : null;
  var spar = 100 * summe('takte_ohne_abfrage', idx) / summe('takte_gesamt', idx), akt = summe('aktiv_gesamt_h', idx) / idx.length;
  var von = dKurz(TMIN[idx[0]]), bis = dKurz(TMIN[idx[idx.length - 1]]), zr = von === bis ? von : von + '–' + bis;
  var k = [
    [MEHR ? 'Aus Speichern entladen' : 'Aus Speicher entladen', f1(ent), 'kWh', zr + (MEHR ? ', alle Geräte' : ', ' + G[0].name)],
    ['Netzbezug', f1(bez), 'kWh', zr + ', Netzsaldo > 0'],
    ['Deckung durch Speicher', f0(deck), '%', 'Entladung ÷ (Entladung + Bezug)'],
    ['Regelung im ±' + D.cfg.band + '-W-Band', f1(band), '%', 'solange ein Speicher einspeist'],
    ['Aktiv je Tag', f1(akt), 'h', MEHR ? 'mindestens ein Gerät gibt ab' : G[0].name + ' gibt ab'],
    ['Takte ohne Geräteabfrage', f0(spar), '%', 'durch Sparmodus eingespart']
  ];
  el.innerHTML = k.map(function(x){
    return '<div class="card kpi"><span class="lbl">' + esc(x[0]) + '</span><span class="val">' + x[1] + '<span class="unit">' + x[2] +
           '</span></span><span class="note">' + esc(x[3]) + '</span></div>';
  }).join('');
  take.innerHTML = 'In <b>' + idx.length + '</b> ' + (idx.length === 1 ? 'vollen Tag' : 'vollen Tagen') + ' (' + zr + ') kamen <b>' + f1(ent) +
    ' kWh</b> aus ' + (MEHR ? 'den Speichern' : 'dem Speicher') + ' und <b>' + f1(bez) + ' kWh</b> aus dem Netz. <b>' + f0(anteil) +
    ' %</b> des Netzbezugs fielen an, während ' + (MEHR ? 'kein Speicher etwas lieferte' : 'der Speicher nichts lieferte') +
    ' (leer bzw. an der Entladegrenze).';
}

function zeichne(){
  versteckeTip();
  var span = range.b - range.a, alles = range.a <= LO && range.b >= HI;
  document.getElementById('rangeLbl').innerHTML =
    esc(dLang(range.a) + ' ' + hm(range.a) + ' – ' + dLang(range.b) + ' ' + hm(range.b)) +
    '<small>' + (span >= TAG ? f1(span / TAG) + ' Tage' : f1(span / 60) + ' Stunden') + (alles ? ' · alles' : '') + '</small>';
  [].forEach.call(document.querySelectorAll('#presets button'), function(btn){
    var w = +btn.dataset.w; btn.classList.toggle('on', w ? span === w : alles);
    btn.disabled = w > 0 && w >= HI - LO;
  });
  document.getElementById('zIn').disabled = span <= MIN_SPAN;
  document.getElementById('zOut').disabled = alles;
  document.getElementById('pL').disabled = range.a <= LO;
  document.getElementById('pR').disabled = range.b >= HI;

  zeitLinien('c-soc', {serien: G.map(function(g){ return {name: g.name, werte: V['soc_' + g.key], farbe: g.farbe}; }),
    yfmt: f0, einheit: ' %', ymin: 0, ymax: 100, aria: 'Ladezustand über die Zeit'});
  zeitLinien('c-leistung', {serien: [{name: 'Netzsaldo', werte: V.netz, farbe: S.s3}, {name: MEHR ? 'Speicher-Ausgang (Summe)' : 'Speicher-Ausgang', werte: V.speicher, farbe: S.s1}],
    yfmt: f0, einheit: ' W', ref: 0, h: HT, aria: 'Netzsaldo und Speicher-Ausgang'});

  var idx = tageImAusschnitt(), kat = idx.map(function(i){ return TMIN[i]; });
  kennzahlen(idx);
  var basis = {kat: kat, katLabel: function(t){ return dKurz(t); }, tipLabel: function(t){ return dLang(t); },
               klick: function(i){ setze(kat[i], kat[i] + TAG); }};
  function mit(o){ var r = {}; Object.keys(basis).forEach(function(k){ r[k] = basis[k]; }); Object.keys(o).forEach(function(k){ r[k] = o[k]; }); return r; }

  stapel('c-energie', mit({serien: G.map(function(g){ return {name: 'Entladung ' + g.name, werte: spalte('entladung_' + g.key + '_kwh', idx), farbe: g.farbe}; })
      .concat([{name: LEER_TXT, werte: spalte('bezug_speicher_aus_kwh', idx), farbe: S.s3},
               {name: 'Übriger Netzbezug', werte: spalte('bezug_regelrest_kwh', idx), farbe: S.s4}]),
    yfmt: f1, einheit: ' kWh', h: HT, aria: 'Energie pro Tag gestapelt'}));
  gruppe('c-aktiv', mit({serien: G.map(function(g){ return {name: g.name, werte: spalte('aktiv_' + g.key + '_h', idx), farbe: g.farbe}; })
      .concat(MEHR ? [{name: 'Mindestens ein Gerät', werte: spalte('aktiv_gesamt_h', idx), farbe: S.mut}] : []),
    yfmt: f1, einheit: ' h', ymax: 24, yticks: [0, 6, 12, 18, 24], aria: 'Aktivzeit pro Tag'}));
  katLinie('c-deckung', mit({serien: [{name: 'Deckung', werte: spalte('deckung_pct', idx), farbe: S.s1}],
    yfmt: f0, einheit: ' %', ymin: 0, ymax: 100, w: WH, aria: 'Deckung pro Tag'}));
  var rg = spalte('regel_im_band_pct', idx), rmin = Math.min.apply(null, rg.filter(function(v){ return v !== null; }).concat([80]));
  katLinie('c-regel', mit({serien: [{name: 'Im ±' + D.cfg.band + '-W-Band', werte: rg, farbe: S.s1}],
    yfmt: f0, einheit: ' %', ymin: Math.floor(rmin / 10) * 10, ymax: 100, w: WH, aria: 'Regelgüte pro Tag'}));
  katLinie('c-befehle', mit({serien: G.map(function(g){ return {name: g.name, werte: spalte('stellbefehle_' + g.key, idx), farbe: g.farbe}; }),
    yfmt: f0, einheit: '', w: WH, aria: 'Stellbefehle pro Tag'}));
  katLinie('c-fehler', mit({serien: [{name: 'Nicht erreichbar', werte: spalte('nicht_erreichbar', idx), farbe: S.s3},
      {name: 'Takt übersprungen', werte: spalte('takt_uebersprungen', idx), farbe: S.s4},
      {name: 'Watchdog', werte: spalte('watchdog', idx), farbe: S.s5}],
    yfmt: f0, einheit: '', w: WH, aria: 'Störungen pro Tag'}));
  stapel('c-takte', mit({serien: [{name: 'Ohne Geräteabfrage', werte: spalte('takte_ohne_abfrage', idx), farbe: S.s1},
      {name: 'Mit Geräteabfrage', werte: spalte('takte_mit_abfrage', idx), farbe: S.mut}],
    yfmt: f0, einheit: '', w: WH, aria: 'Takte pro Tag'}));
  katLinie('c-spar', mit({serien: [{name: 'Ohne Abfrage', werte: spalte('spar_anteil_pct', idx), farbe: S.s1}],
    yfmt: f0, einheit: ' %', ymin: 50, ymax: 100, w: WH, aria: 'Anteil eingesparter Takte'}));
}

function profil(){
  var P = D.profil, std = P.stunde;
  var o = {kat: std, katLabel: function(h){ return h + ' Uhr'; }, tipLabel: function(h){ return h + ':00–' + h + ':59 Uhr'; },
           tickSchritt: 4, w: WH};
  function bandLegende(id, farbe){
    legende(id, [['Median', farbe], ['25–75 %', 'color-mix(in srgb, ' + farbe + ' 45%, transparent)'],
                 ['10–90 %', 'color-mix(in srgb, ' + farbe + ' 30%, transparent)']]);
  }
  [['netzsaldo', 'c-pnetz', 'lg-pnetz', S.s3, 'Netzsaldo'], ['speicher', 'c-pspeicher', 'lg-pspeicher', S.s1, 'Speicher-Ausgang']].forEach(function(x){
    var p = function(q){ return P[x[0] + '_p' + q + '_w']; }, mittel = P[x[0] + '_w'];
    if (!p(50)) return leer(x[1], 'Keine Perzentile in tagesprofil.csv – analyse.py neu laufen lassen.');
    bandLegende(x[2], x[3]);
    katBand(x[1], Object.assign({}, o, {farbe: x[3], mitte: p(50), ref: 0,
      baender: [[p(10), p(90), 0.16], [p(25), p(75), 0.38]],
      tip: function(i){ return [['Median', f0(p(50)[i]) + ' W', x[3]], ['25–75 %', f0(p(25)[i]) + ' bis ' + f0(p(75)[i]) + ' W'],
        ['10–90 %', f0(p(10)[i]) + ' bis ' + f0(p(90)[i]) + ' W'], ['Mittel', f0(mittel[i]) + ' W'],
        ['Tage', f0(P.tage ? P.tage[i] : null)]]; },
      yfmt: f0, aria: x[4] + ' nach Uhrzeit, Verteilung über die Tage'}));
  });
  [].forEach.call(document.querySelectorAll('.txt-pband'), function(el){
    el.textContent = 'Stundenmittel je Tag, verteilt über ' + dKurz(tagMin(D.profilVon)) + '–' + dKurz(tagMin(D.profilBis)) +
      ': Linie = Median, kräftiges Band = mittlere Hälfte der Tage, blasses Band = 10–90 %.';
  });
  if (MEHR) document.getElementById('h-pspeicher').textContent = 'Speicher-Ausgang (Summe) nach Uhrzeit';
  var box = document.getElementById('profilsoc');
  box.innerHTML = G.map(function(g){
    return '<div class="card chart' + (MEHR ? '' : ' wide') + '"><h3>SOC nach Uhrzeit · ' + esc(g.name) + '</h3>' +
      '<p>Verteilung über alle vollen Tage: Linie = Median, kräftiges Band = mittlere Hälfte der Tage (25–75 %), ' +
      'blasses Band = 10–90 %.</p><div class="legend" id="lg-band-' + g.key + '"></div><div id="c-band-' + g.key + '"></div></div>';
  }).join('');
  G.forEach(function(g){
    var k = g.key, p = function(q){ return P['soc_p' + q + '_' + k]; };
    if (!p(50)) return leer('c-band-' + k, 'Keine Perzentile in tagesprofil.csv – analyse.py neu laufen lassen.');
    bandLegende('lg-band-' + k, g.farbe);
    katBand('c-band-' + k, Object.assign({}, o, {w: MEHR ? WH : W, tickSchritt: MEHR ? 4 : 2, farbe: g.farbe, mitte: p(50),
      baender: [[p(10), p(90), 0.16], [p(25), p(75), 0.38]],
      tip: function(i){ return [['Median', f0(p(50)[i]) + ' %', g.farbe], ['25–75 %', f0(p(25)[i]) + '–' + f0(p(75)[i]) + ' %'],
        ['10–90 %', f0(p(10)[i]) + '–' + f0(p(90)[i]) + ' %'],
        ['Min–Max', f0(P['soc_min_' + k][i]) + '–' + f0(P['soc_max_' + k][i]) + ' %']]; },
      ymin: 0, ymax: 100, yfmt: f0, aria: 'SOC-Verteilung nach Uhrzeit ' + g.name}));
  });
}
function katBand(id, o){
  var werte = [];
  o.baender.forEach(function(b){ werte = werte.concat(b[0], b[1]); });
  var f = katRahmen(id, o, werte.concat(o.mitte)), sx = function(i){ return (ML + f.band * (i + 0.5)).toFixed(1); };
  if (o.ref !== undefined && f.ya.lo <= o.ref && o.ref <= f.ya.hi)
    f.out.push('<line x1="' + ML + '" x2="' + (f.w - MR) + '" y1="' + f.sy(o.ref).toFixed(1) + '" y2="' + f.sy(o.ref).toFixed(1) + '" class="ref"/>');
  o.baender.forEach(function(b){
    var oben = [], unten = [];
    b[1].forEach(function(v, i){ if (v !== null) oben.push(sx(i) + ',' + f.sy(v).toFixed(1)); });
    b[0].forEach(function(v, i){ if (v !== null) unten.unshift(sx(i) + ',' + f.sy(v).toFixed(1)); });
    f.out.push('<polygon points="' + oben.concat(unten).join(' ') + '" style="fill:' + o.farbe + ';fill-opacity:' + b[2] + '"/>');
  });
  var pts = [];
  o.mitte.forEach(function(v, i){ if (v !== null) pts.push(sx(i) + ',' + f.sy(v).toFixed(1)); });
  f.out.push('<polyline points="' + pts.join(' ') + '" fill="none" style="stroke:' + o.farbe + '" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>');
  o.mitte.forEach(function(v, i){ if (v !== null) f.out.push('<circle cx="' + sx(i) + '" cy="' + f.sy(v).toFixed(1) + '" r="2.6" style="fill:' + o.farbe + '"/>'); });
  katFertig(id, o, f, o.tip);
}

/* ---------------- Start ---------------- */
legende('lg-soc', G.map(function(g){ return [g.name, g.farbe]; }));
legende('lg-leistung', [['Netzsaldo', S.s3], [MEHR ? 'Speicher-Ausgang (Summe aller Geräte)' : 'Speicher-Ausgang', S.s1]]);
legende('lg-energie', G.map(function(g){ return ['Entladung ' + g.name, g.farbe]; })
  .concat([[LEER_TXT, S.s3], ['Übriger Netzbezug', S.s4]]));
legende('lg-aktiv', G.map(function(g){ return [g.name, g.farbe]; }).concat(MEHR ? [['Mindestens ein Gerät', S.mut]] : []));
legende('lg-befehle', G.map(function(g){ return [g.name, g.farbe]; }));
legende('lg-fehler', [['Nicht erreichbar', S.s3], ['Takt übersprungen', S.s4], ['Watchdog', S.s5]]);
legende('lg-takte', [['Ohne Geräteabfrage (eingespart)', S.s1], ['Mit Geräteabfrage', S.mut]]);
document.getElementById('txt-aktiv').textContent = 'Stunden je Tag, in denen ' + (MEHR ? 'ein Gerät' : 'das Gerät') + ' mindestens ' +
  D.cfg.aktiv + ' W ins Haus abgegeben hat.' + (MEHR ? ' „Mindestens ein Gerät“ zählt jede Stunde nur einmal, auch wenn mehrere gleichzeitig liefern.' : '');
document.getElementById('txt-regel').textContent = 'Anteil der Takte mit |Netzsaldo| ≤ ' + D.cfg.band + ' W, solange ein Speicher einspeist und nicht am Limit ist.';
document.getElementById('txt-takte').textContent = 'Regeltakte pro Tag (typisch ' + f0(D.cfg.takteTag) + ', also etwa alle ' + de(D.cfg.takt, D.cfg.takt % 1 ? 1 : 0) +
  ' s). Ohne Abfrage: Der Sparmodus hat das Polling ausgesetzt.';

[].forEach.call(document.querySelectorAll('#presets button'), function(btn){ btn.addEventListener('click', function(){ preset(+btn.dataset.w); }); });
document.getElementById('zIn').addEventListener('click', function(){ var m = (range.a + range.b) / 2, s = (range.b - range.a) / 4; setze(m - s, m + s); });
document.getElementById('zOut').addEventListener('click', function(){ var m = (range.a + range.b) / 2, s = range.b - range.a; setze(m - s, m + s); });
document.getElementById('pL').addEventListener('click', function(){ var s = (range.b - range.a) / 2; setze(range.a - s, range.b - s); });
document.getElementById('pR').addEventListener('click', function(){ var s = (range.b - range.a) / 2; setze(range.a + s, range.b + s); });

var themeBtn = document.getElementById('themeBtn');
function themeIcon(){ themeBtn.textContent = document.documentElement.getAttribute('data-theme') === 'dark' ? '☾' : '☀'; }
themeBtn.addEventListener('click', function(){
  var n = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', n);
  try{ localStorage.setItem('zendure_stat_theme', n); }catch(e){}
  themeIcon();
});
themeIcon();
window.addEventListener('scroll', versteckeTip, {passive: true});

zeichne();
profil();
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    erzeugen()
