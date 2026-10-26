// generate_charts.js
// Erzeugt aus closed_loop_result.csv einen einzelnen HTML-Report mit SVG-Charts:
// Regelguete (Netzsaldo), Haushaltslast (nur mit Rauschmodell), Leistungskurven
// beider Solarflows, SoC-Verlauf. Keine npm-Pakete noetig, reines SVG.
//
// Aufruf: node generate_charts.js [closed_loop_result.csv] [report.html] [maxPunkte]
//
// Erweiterung Rauschmodell (wirkt nur, wenn die CSV die neuen Spalten hat):
//  - Ereignisfenster (Waschmaschine, Induktion, ...) als farbige Hintergrundflaechen
//  - Netzsaldo als Min/Max-Huelle je Bildpunkt, damit kurze Spitzen beim
//    Ausduennen nicht verschwinden; dazu der gemessene Wert (grid_meas_W)
//  - neuer Chart Haushaltslast (gesamt, Grundprofil, Ereignisse)
//  - Kennzahlen zusaetzlich mit Band ±BAND_W (Default 13 W) und je Zeitfenster
// Alte CSVs ohne diese Spalten ergeben denselben Report wie bisher.
"use strict";

const fs = require("fs");

const csvPath = process.argv[2] || "closed_loop_result.csv";
const outPath = process.argv[3] || "report.html";
const BAND_W = Number(process.env.BAND_W || 13);

function readCsv(path) {
  const lines = fs.readFileSync(path, "utf8").trim().split(/\r?\n/);
  const cols = lines[0].split(";");
  const rows = lines.slice(1).map((line) => {
    const vals = line.split(";");
    const row = {};
    cols.forEach((c, i) => (row[c] = vals[i]));
    return row;
  });
  return { cols, rows };
}

const { cols: csvCols, rows: rowsFull } = readCsv(csvPath);
const has = (c) => csvCols.includes(c);
const NOISE = has("event") && rowsFull.some((r) => r.seed !== undefined && r.seed !== "");

// Downsampling fuer die Anzeige (sonst wird die HTML-Datei bei langen
// Laeufen unnoetig gross/langsam - visuell macht das ab ein paar Tausend
// Punkten ohnehin keinen Unterschied mehr).
const MAX_POINTS = Number(process.argv[4] || 2000);
const step = Math.max(1, Math.ceil(rowsFull.length / MAX_POINTS));
const rows = step === 1 ? rowsFull : rowsFull.filter((_, i) => i % step === 0);

const n = rows.length;
const minutes = rows.map((r) => Number(r.minute));
const tMin = minutes[0], tMax = minutes[n - 1];

// Min/Max je Anzeige-Punkt aus dem VOLLEN Datensatz (fuer Huellkurven)
function envelope(col) {
  const lo = [], hi = [];
  for (let b = 0; b < n; b++) {
    let mn = Infinity, mx = -Infinity;
    for (let i = b * step; i < Math.min((b + 1) * step, rowsFull.length); i++) {
      const v = Number(rowsFull[i][col]);
      if (v < mn) mn = v;
      if (v > mx) mx = v;
    }
    lo.push(mn); hi.push(mx);
  }
  return { lo, hi };
}

// --- Ereignisfenster aus der Spalte "event" (voller Datensatz) ---
const EVENT_COLORS = { waschmaschine: "#cfe3f7", induktion: "#fde2c8", wasserkocher: "#f6d3d3", kaffee: "#e3d3c4", sonstige: "#e6e6e6" };
function eventClass(ev) {
  if (!ev) return "";
  if (ev.includes("waschmaschine")) return "waschmaschine";
  if (ev.includes("induktion")) return "induktion";
  if (ev.includes("wasserkocher")) return "wasserkocher";
  if (ev.includes("kaffee")) return "kaffee";
  return "sonstige";
}
const eventBands = [];
if (NOISE) {
  let cur = null;
  rowsFull.forEach((r) => {
    const c = eventClass(r.event);
    const m = Number(r.minute);
    if (cur && c === cur.cls) { cur.to = m; return; }
    if (cur) eventBands.push(cur);
    cur = c ? { cls: c, from: m, to: m } : null;
  });
  if (cur) eventBands.push(cur);
}
const eventTypesPresent = [...new Set(eventBands.map((b) => b.cls))];

// --- kleine SVG-Line-Chart-Fabrik ---
function lineChart({ width = 900, height = 260, series, yLabel, title, yMin, yMax, zeroLine, hband }) {
  const padL = 55, padR = 20, padT = 30, padB = 30;
  const w = width - padL - padR, h = height - padT - padB;

  const allY = series.flatMap((s) => (s.hi ? s.lo.concat(s.hi) : s.data)).filter((v) => isFinite(v));
  const lo = yMin !== undefined ? yMin : Math.min(...allY);
  const hi = yMax !== undefined ? yMax : Math.max(...allY);
  const range = hi - lo || 1;

  const x = (m) => padL + ((m - tMin) / (tMax - tMin || 1)) * w;
  const y = (v) => padT + h - ((Math.max(lo, Math.min(hi, v)) - lo) / range) * h;

  const colors = ["#1f77b4", "#d62728", "#2ca02c", "#888888"];

  let svg = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg" style="background:#fff">`;
  svg += `<text x="${padL}" y="18" font-size="14" font-family="sans-serif" fill="#222">${title}</text>`;

  // Ereignisfenster als Hintergrund
  eventBands.forEach((b) => {
    const x1 = x(b.from), x2 = Math.max(x(b.to), x1 + 1);
    svg += `<rect x="${x1}" y="${padT}" width="${x2 - x1}" height="${h}" fill="${EVENT_COLORS[b.cls]}"/>`;
  });

  // Toleranzband (z.B. ±13 W)
  if (hband !== undefined && hband <= hi && -hband >= lo) {
    svg += `<rect x="${padL}" y="${y(hband)}" width="${w}" height="${y(-hband) - y(hband)}" fill="#2ca02c" fill-opacity="0.12"/>`;
  }

  // Achsen
  svg += `<line x1="${padL}" y1="${padT}" x2="${padL}" y2="${padT + h}" stroke="#333"/>`;
  svg += `<line x1="${padL}" y1="${padT + h}" x2="${padL + w}" y2="${padT + h}" stroke="#333"/>`;

  // Y-Ticks (5 Stueck)
  for (let i = 0; i <= 4; i++) {
    const v = lo + (range * i) / 4;
    const yy = y(v);
    svg += `<line x1="${padL - 4}" y1="${yy}" x2="${padL}" y2="${yy}" stroke="#333"/>`;
    svg += `<text x="${padL - 8}" y="${yy + 4}" font-size="10" font-family="sans-serif" text-anchor="end" fill="#555">${v.toFixed(0)}</text>`;
    svg += `<line x1="${padL}" y1="${yy}" x2="${padL + w}" y2="${yy}" stroke="#eee"/>`;
  }
  svg += `<text x="14" y="${padT + h / 2}" font-size="11" font-family="sans-serif" fill="#555" transform="rotate(-90 14 ${padT + h / 2})">${yLabel}</text>`;

  // X-Ticks
  const span = tMax - tMin;
  const hourStep = span > 1440 ? 240 : span > 240 ? 120 : span > 60 ? 30 : 10;
  for (let m = Math.ceil(tMin / hourStep) * hourStep; m <= tMax; m += hourStep) {
    const xx = x(m);
    const hh = String(Math.floor((m % 1440) / 60)).padStart(2, "0");
    const mi = String(Math.floor(m % 60)).padStart(2, "0");
    svg += `<line x1="${xx}" y1="${padT + h}" x2="${xx}" y2="${padT + h + 4}" stroke="#333"/>`;
    svg += `<text x="${xx}" y="${padT + h + 16}" font-size="9" font-family="sans-serif" text-anchor="middle" fill="#555">${hh}:${mi}</text>`;
  }

  if (zeroLine !== undefined && zeroLine >= lo && zeroLine <= hi) {
    svg += `<line x1="${padL}" y1="${y(zeroLine)}" x2="${padL + w}" y2="${y(zeroLine)}" stroke="#000" stroke-width="1"/>`;
  }

  // Linien bzw. Huellkurven
  series.forEach((s, idx) => {
    const color = s.color || colors[idx % colors.length];
    if (s.hi) {
      // Huelle: je Anzeige-Punkt eine senkrechte Linie von Min bis Max
      let d = "";
      minutes.forEach((m, i) => { d += `M${x(m)},${y(s.lo[i])}V${y(s.hi[i])}`; });
      svg += `<path d="${d}" stroke="${color}" stroke-width="1" fill="none" ${s.opacity ? `stroke-opacity="${s.opacity}"` : ""}/>`;
    } else {
      const pts = minutes.map((m, i) => `${x(m)},${y(s.data[i])}`).join(" ");
      svg += `<polyline points="${pts}" fill="none" stroke="${color}" stroke-width="${s.width || 1.3}" ${s.opacity ? `stroke-opacity="${s.opacity}"` : ""}/>`;
    }
  });

  // Legende
  let lx = padL + w - 10;
  series.slice().reverse().forEach((s, idx) => {
    const color = s.color || colors[(series.length - 1 - idx) % colors.length];
    svg += `<circle cx="${lx}" cy="${padT + 10 + idx * 14}" r="4" fill="${color}"/>`;
    svg += `<text x="${lx - 8}" y="${padT + 14 + idx * 14}" font-size="10" font-family="sans-serif" text-anchor="end" fill="#333">${s.label}</text>`;
  });

  svg += `</svg>`;
  return svg;
}

// --- Kennzahlen (aus VOLLEM Datensatz, nicht downgesampelt) ---
const gridWFull = rowsFull.map((r) => Number(r.grid_W));
const meanAbsGrid = gridWFull.reduce((a, b) => a + Math.abs(b), 0) / rowsFull.length;
const withinBand = gridWFull.filter((g) => Math.abs(g) <= 30).length / rowsFull.length * 100;
const withinBandH = gridWFull.filter((g) => Math.abs(g) <= BAND_W).length / rowsFull.length * 100;

// Kennzahlen je Zeitfenster (nur mit Rauschmodell)
let windowTable = "";
if (NOISE) {
  const stat = {};
  rowsFull.forEach((r) => {
    const c = eventClass(r.event) || "ruhig";
    const g = Math.abs(Number(r.grid_W));
    const s = stat[c] || (stat[c] = { n: 0, sum: 0, band: 0, big: 0 });
    s.n++; s.sum += g;
    if (g <= BAND_W) s.band++;
    if (g > 50) s.big++;
  });
  const order = ["ruhig", "waschmaschine", "induktion", "wasserkocher", "kaffee", "sonstige"].filter((c) => stat[c]);
  windowTable = `<table style="font-size:12px; border-collapse:collapse; margin:6px 0 14px 0;">
    <tr style="background:#f2f2f2"><th style="text-align:left;padding:3px 8px">Zeitfenster</th><th style="padding:3px 8px">Zyklen</th>
    <th style="padding:3px 8px">mittl. |Netz|</th><th style="padding:3px 8px">im Band ±${BAND_W} W</th><th style="padding:3px 8px">&gt; 50 W</th></tr>` +
    order.map((c) => {
      const s = stat[c];
      return `<tr><td style="padding:3px 8px">${c}</td><td style="text-align:right;padding:3px 8px">${s.n}</td>` +
        `<td style="text-align:right;padding:3px 8px">${(s.sum / s.n).toFixed(1)} W</td>` +
        `<td style="text-align:right;padding:3px 8px">${(100 * s.band / s.n).toFixed(1)} %</td>` +
        `<td style="text-align:right;padding:3px 8px">${(100 * s.big / s.n).toFixed(1)} %</td></tr>`;
    }).join("") + `</table>`;
}

// --- 1) Regelguete: Netzsaldo um 0 ---
const gridW = rows.map((r) => Number(r.grid_W));
const series1 = [];
if (step > 1) {
  const env = envelope("grid_W");
  series1.push({ label: "grid_W (echt, Min/Max)", lo: env.lo, hi: env.hi, color: "#c0392b" });
} else {
  series1.push({ label: "grid_W (echt)", data: gridW, color: "#c0392b" });
}
if (NOISE && has("grid_meas_W")) {
  series1.push({ label: "grid_meas_W (gemessen)", data: rows.map((r) => Number(r.grid_meas_W)), color: "#7f7f7f", width: 0.8, opacity: 0.6 });
}
const chart1 = lineChart({
  title: "1) Regelgüte – Netzsaldo (Soll: 0 W)",
  yLabel: "W",
  zeroLine: 0,
  hband: NOISE ? BAND_W : undefined,
  series: series1,
});

// --- 1b) Haushaltslast (nur mit Rauschmodell) ---
let chartLoad = "";
if (NOISE) {
  const envL = step > 1 ? envelope("haushalt_W") : null;
  chartLoad = lineChart({
    title: "Haushaltslast (echt) – gesamt, Grundprofil, Ereignisse",
    yLabel: "W",
    yMin: 0,
    series: [
      envL ? { label: "gesamt (Min/Max)", lo: envL.lo, hi: envL.hi, color: "#555555" }
           : { label: "gesamt", data: rows.map((r) => Number(r.haushalt_W)), color: "#555555" },
      { label: "Grundprofil", data: rows.map((r) => Number(r.last_basis_W)), color: "#2ca02c", width: 1.6 },
      { label: "Ereignisse", data: rows.map((r) => Number(r.last_events_W)), color: "#9467bd", width: 1 },
    ],
  });
}

// --- 2) Leistungskurven beider Solarflows (signierte AC-Leistung: + Export, - Laden) ---
function signedAc(row, dev) {
  const acMode = Number(row["acMode_" + dev]);
  const out = Number(row["out_" + dev] || 0);
  const inp = Number(row["in_" + dev] || 0);
  return acMode === 2 ? out : -inp;
}
const ac800 = rows.map((r) => signedAc(r, "sf800"));
const ac2400 = rows.map((r) => signedAc(r, "sf2400"));

const chart2 = lineChart({
  title: "2) Leistungskurven Solarflows (AC, signiert: + Export / - Laden vom Netz)",
  yLabel: "W",
  zeroLine: 0,
  series: [
    { label: "SF800 Pro", data: ac800, color: "#1f77b4" },
    { label: "SF2400", data: ac2400, color: "#d62728" },
  ],
});

// --- 3) SoC-Verlauf ---
const soc800 = rows.map((r) => Number(r.soc_sf800));
const soc2400 = rows.map((r) => Number(r.soc_sf2400));

const chart3 = lineChart({
  title: "3) SoC-Verlauf",
  yLabel: "%",
  yMin: 0, yMax: 100,
  series: [
    { label: "SF800 Pro", data: soc800, color: "#1f77b4" },
    { label: "SF2400", data: soc2400, color: "#d62728" },
  ],
});

// Legende der Ereignisfarben
const eventLegend = eventTypesPresent.length
  ? `<p style="font-size:12px; color:#555;">Hintergrund: ` + eventTypesPresent.map((c) =>
      `<span style="display:inline-block;width:12px;height:12px;background:${EVENT_COLORS[c]};border:1px solid #ccc;vertical-align:middle;margin:0 4px 0 10px"></span>${c}`
    ).join("") + `</p>`
  : "";

const seedInfo = NOISE ? ` | Seed ${rowsFull[1] ? rowsFull[1].seed : rowsFull[0].seed}` : "";

const html = `<!DOCTYPE html>
<html lang="de">
<head><meta charset="utf-8"><title>Testlauf-Report</title></head>
<body style="font-family:sans-serif; max-width:960px; margin:20px auto;">
  <h2>Testlauf-Report</h2>
  <p style="color:#555; font-size:13px;">
    Quelle: <code>${csvPath}</code> | ${rowsFull.length} Zyklen | Zeitspanne ${(tMax - tMin).toFixed(0)} simulierte Minuten${seedInfo}
    | Regelguete: mittlere |Netzsaldo| = ${meanAbsGrid.toFixed(1)} W, ${withinBand.toFixed(1)}% der Zeit innerhalb ±30 W,
    ${withinBandH.toFixed(1)}% innerhalb ±${BAND_W} W
  </p>
  ${windowTable}
  ${eventLegend}
  <div>${chart1}</div>
  ${chartLoad ? `<div>${chartLoad}</div>` : ""}
  <div>${chart2}</div>
  <div>${chart3}</div>
</body>
</html>`;

fs.writeFileSync(outPath, html);
console.log("Report geschrieben: " + outPath + " (" + rowsFull.length + " Zyklen)");
console.log("Regelguete: mittlere |grid_W| = " + meanAbsGrid.toFixed(1) + " W, " + withinBand.toFixed(1) +
  "% der Zeit innerhalb ±30 W, " + withinBandH.toFixed(1) + "% innerhalb ±" + BAND_W + " W");
