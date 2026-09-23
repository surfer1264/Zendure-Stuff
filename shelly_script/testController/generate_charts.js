// generate_charts.js
// Erzeugt aus closed_loop_result.csv einen einzelnen HTML-Report mit drei
// SVG-Charts: Regelguete (Netzsaldo), Leistungskurven beider Solarflows,
// SoC-Verlauf. Keine npm-Pakete noetig, reines SVG.
//
// Aufruf: node generate_charts.js [closed_loop_result.csv] [report.html]
"use strict";

const fs = require("fs");

const csvPath = process.argv[2] || "closed_loop_result.csv";
const outPath = process.argv[3] || "report.html";

function readCsv(path) {
  const lines = fs.readFileSync(path, "utf8").trim().split(/\r?\n/);
  const cols = lines[0].split(";");
  return lines.slice(1).map((line) => {
    const vals = line.split(";");
    const row = {};
    cols.forEach((c, i) => (row[c] = vals[i]));
    return row;
  });
}

const rowsFull = readCsv(csvPath);

// Downsampling fuer die Anzeige (sonst wird die HTML-Datei bei langen
// Laeufen unnoetig gross/langsam - visuell macht das ab ein paar Tausend
// Punkten ohnehin keinen Unterschied mehr).
const MAX_POINTS = Number(process.argv[4] || 2000);
const step = Math.max(1, Math.ceil(rowsFull.length / MAX_POINTS));
const rows = step === 1 ? rowsFull : rowsFull.filter((_, i) => i % step === 0);

const n = rows.length;
const minutes = rows.map((r) => Number(r.minute));
const tMin = minutes[0], tMax = minutes[n - 1];

// --- kleine SVG-Line-Chart-Fabrik ---
function lineChart({ width = 900, height = 260, series, yLabel, title, yMin, yMax, zeroLine }) {
  const padL = 55, padR = 20, padT = 30, padB = 30;
  const w = width - padL - padR, h = height - padT - padB;

  const allY = series.flatMap((s) => s.data);
  const lo = yMin !== undefined ? yMin : Math.min(...allY);
  const hi = yMax !== undefined ? yMax : Math.max(...allY);
  const range = hi - lo || 1;

  const x = (m) => padL + ((m - tMin) / (tMax - tMin || 1)) * w;
  const y = (v) => padT + h - ((v - lo) / range) * h;

  const colors = ["#1f77b4", "#d62728", "#2ca02c", "#888888"];

  let svg = `<svg width="${width}" height="${height}" xmlns="http://www.w3.org/2000/svg" style="background:#fff">`;
  svg += `<text x="${padL}" y="18" font-size="14" font-family="sans-serif" fill="#222">${title}</text>`;

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

  // X-Ticks (stündlich, falls Zeitspanne <= 1 Tag)
  const hourStep = (tMax - tMin) > 1440 ? 240 : 120; // grobere Ticks bei Mehrtageslaeufen
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

  // Linien
  series.forEach((s, idx) => {
    const color = s.color || colors[idx % colors.length];
    const pts = minutes.map((m, i) => `${x(m)},${y(s.data[i])}`).join(" ");
    svg += `<polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.3"/>`;
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

// --- 1) Regelguete: Netzsaldo um 0 (Kennzahlen aus VOLLEM Datensatz, nicht downgesampelt) ---
const gridWFull = rowsFull.map((r) => Number(r.grid_W));
const meanAbsGrid = gridWFull.reduce((a, b) => a + Math.abs(b), 0) / rowsFull.length;
const withinBand = gridWFull.filter((g) => Math.abs(g) <= 30).length / rowsFull.length * 100;

const gridW = rows.map((r) => Number(r.grid_W));

const chart1 = lineChart({
  title: "1) Regelgüte – Netzsaldo (Soll: 0 W)",
  yLabel: "W",
  zeroLine: 0,
  series: [{ label: "grid_W", data: gridW, color: "#c0392b" }],
});

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

const html = `<!DOCTYPE html>
<html lang="de">
<head><meta charset="utf-8"><title>Testlauf-Report</title></head>
<body style="font-family:sans-serif; max-width:960px; margin:20px auto;">
  <h2>Testlauf-Report</h2>
  <p style="color:#555; font-size:13px;">
    Quelle: <code>${csvPath}</code> | ${n} Zyklen | Zeitspanne ${(tMax - tMin).toFixed(0)} simulierte Minuten
    | Regelguete: mittlere |Netzsaldo| = ${meanAbsGrid.toFixed(1)} W, ${withinBand.toFixed(1)}% der Zeit innerhalb ±30 W
  </p>
  <div>${chart1}</div>
  <div>${chart2}</div>
  <div>${chart3}</div>
</body>
</html>`;

fs.writeFileSync(outPath, html);
console.log("Report geschrieben: " + outPath + " (" + n + " Zyklen)");
console.log("Regelguete: mittlere |grid_W| = " + meanAbsGrid.toFixed(1) + " W, " + withinBand.toFixed(1) + "% der Zeit innerhalb ±30 W");
