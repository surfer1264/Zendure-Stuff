// compare_runs.js
// Vergleicht zwei Testlaeufe (Baseline vs. Kandidat) - CSV numerisch,
// Log qualitativ (Ereigniszaehlung + Fehler).
//
// Aufruf:
//   node compare_runs.js baseline.csv kandidat.csv [baseline.log kandidat.log]
"use strict";

const fs = require("fs");

const [, , baseCsvPath, candCsvPath, baseLogPath, candLogPath] = process.argv;

if (!baseCsvPath || !candCsvPath) {
  console.error("Nutzung: node compare_runs.js baseline.csv kandidat.csv [baseline.log kandidat.log]");
  process.exit(1);
}

function readCsv(path) {
  const text = fs.readFileSync(path, "utf8").trim();
  const lines = text.split(/\r?\n/);
  const cols = lines[0].split(";");
  const rows = lines.slice(1).map((line) => {
    const vals = line.split(";");
    const row = {};
    cols.forEach((c, i) => (row[c] = vals[i]));
    return row;
  });
  return { cols, rows };
}

function num(v) { return v === undefined ? NaN : Number(v); }

// --- CSV-Vergleich ---
const base = readCsv(baseCsvPath);
const cand = readCsv(candCsvPath);

console.log("=== CSV-Vergleich ===");
console.log(`Baseline: ${base.rows.length} Zeilen | Kandidat: ${cand.rows.length} Zeilen`);
if (base.rows.length !== cand.rows.length) {
  console.log("WARNUNG: unterschiedliche Zeilenzahl - Szenario/CYCLES nicht identisch? Vergleiche nur den ueberlappenden Bereich.");
}

const n = Math.min(base.rows.length, cand.rows.length);
const numericCols = ["grid_W", "soc_sf800", "soc_sf2400", "out_sf800", "in_sf800",
  "out_sf2400", "in_sf2400", "socLimit_sf800", "socLimit_sf2400",
  "gridReverse_sf800", "gridReverse_sf2400", "acMode_sf800", "acMode_sf2400"]
  .filter((c) => base.cols.includes(c) && cand.cols.includes(c));

const TOLERANCE = { grid_W: 5, soc_sf800: 1, soc_sf2400: 1 }; // kleine numerische Toleranz, Rest exakt

for (const col of numericCols) {
  let maxDiff = 0, diffRows = 0, firstDiffAt = null;
  for (let i = 0; i < n; i++) {
    const a = num(base.rows[i][col]), b = num(cand.rows[i][col]);
    const d = Math.abs(a - b);
    const tol = TOLERANCE[col] || 0;
    if (d > tol) {
      diffRows++;
      if (firstDiffAt === null) firstDiffAt = base.rows[i]["t"] + " (minute " + base.rows[i]["minute"] + ")";
    }
    if (d > maxDiff) maxDiff = d;
  }
  const flag = diffRows > 0 ? "  <-- ABWEICHUNG" : "";
  console.log(`  ${col.padEnd(20)} max|Δ|=${maxDiff.toFixed(1).padStart(8)}  abweichende Zeilen=${String(diffRows).padStart(6)}/${n}` +
    (firstDiffAt ? `  erste bei ${firstDiffAt}` : "") + flag);
}

// --- Uebergangs-Zeitpunkte (socLimit / gridReverse) ---
function transitions(rows, col) {
  const out = [];
  let prev = null;
  for (const r of rows) {
    const v = r[col];
    if (v !== prev) { out.push({ t: r["t"], minute: r["minute"], from: prev, to: v }); prev = v; }
  }
  return out;
}

console.log("\n=== Uebergangs-Zeitpunkte ===");
for (const col of ["socLimit_sf800", "socLimit_sf2400", "gridReverse_sf800", "gridReverse_sf2400"]) {
  if (!base.cols.includes(col)) continue;
  const bt = transitions(base.rows, col);
  const ct = transitions(cand.rows, col);
  console.log(`  ${col}: Baseline ${bt.length} Wechsel, Kandidat ${ct.length} Wechsel` +
    (bt.length !== ct.length ? "  <-- unterschiedliche Anzahl" : ""));
}

// --- Aggregate ---
function aggregate(rows) {
  let importKwh = 0, exportKwh = 0;
  for (let i = 1; i < rows.length; i++) {
    const dtH = (num(rows[i]["minute"]) - num(rows[i - 1]["minute"])) / 60;
    const g = num(rows[i]["grid_W"]);
    if (isNaN(dtH) || isNaN(g)) continue;
    if (g > 0) importKwh += g * dtH / 1000;
    else exportKwh += -g * dtH / 1000;
  }
  const last = rows[rows.length - 1];
  return {
    importKwh, exportKwh,
    endSoc800: last["soc_sf800"], endSoc2400: last["soc_sf2400"],
    minSoc800: Math.min(...rows.map((r) => num(r["soc_sf800"]))),
    minSoc2400: Math.min(...rows.map((r) => num(r["soc_sf2400"]))),
    maxSoc800: Math.max(...rows.map((r) => num(r["soc_sf800"]))),
    maxSoc2400: Math.max(...rows.map((r) => num(r["soc_sf2400"]))),
  };
}

console.log("\n=== Aggregate ===");
const ba = aggregate(base.rows), ca = aggregate(cand.rows);
console.log("  Netzbezug (kWh):    Baseline " + ba.importKwh.toFixed(3) + "  | Kandidat " + ca.importKwh.toFixed(3));
console.log("  Einspeisung (kWh):  Baseline " + ba.exportKwh.toFixed(3) + "  | Kandidat " + ca.exportKwh.toFixed(3));
console.log("  End-SOC SF800:      Baseline " + ba.endSoc800 + "%  | Kandidat " + ca.endSoc800 + "%");
console.log("  End-SOC SF2400:     Baseline " + ba.endSoc2400 + "%  | Kandidat " + ca.endSoc2400 + "%");
console.log("  SOC-Spanne SF800:   Baseline " + ba.minSoc800 + "-" + ba.maxSoc800 + "%  | Kandidat " + ca.minSoc800 + "-" + ca.maxSoc800 + "%");
console.log("  SOC-Spanne SF2400:  Baseline " + ba.minSoc2400 + "-" + ba.maxSoc2400 + "%  | Kandidat " + ca.minSoc2400 + "-" + ca.maxSoc2400 + "%");

// --- Log-Vergleich (optional) ---
if (baseLogPath && candLogPath) {
  console.log("\n=== Log-Vergleich ===");
  const baseLog = fs.readFileSync(baseLogPath, "utf8");
  const candLog = fs.readFileSync(candLogPath, "utf8");

  const patterns = [
    ["Ausgleich (Rebalancing)", /Ausgleich:/g],
    ["Wechsel in Mehrere-Geraete-Modus", /Mehrere-Geraete-Modus/g],
    ["Richtungswechsel blockiert", /Richtungswechsel blockiert/g],
    ["gridReverse gesetzt", /gridReverse=\d+ gesetzt/g],
    ["FEHLER-Zeilen", /FEHLER/g],
  ];

  for (const [label, re] of patterns) {
    const bCount = (baseLog.match(re) || []).length;
    const cCount = (candLog.match(re) || []).length;
    const flag = bCount !== cCount ? "  <-- unterschiedlich" : "";
    console.log(`  ${label.padEnd(32)} Baseline=${String(bCount).padStart(4)}  Kandidat=${String(cCount).padStart(4)}${flag}`);
  }

  const candErrors = candLog.match(/FEHLER[^\n]*/g) || [];
  const baseErrors = baseLog.match(/FEHLER[^\n]*/g) || [];
  const newErrors = candErrors.filter((e) => !baseErrors.includes(e));
  if (newErrors.length > 0) {
    console.log("\n  NEUE Fehlerzeilen im Kandidaten (nicht in der Baseline):");
    newErrors.slice(0, 10).forEach((e) => console.log("    " + e));
  }
} else {
  console.log("\n(Kein Log-Vergleich - Log-Pfade nicht angegeben)");
}

console.log("\n=== Fazit ===");
const hasNumericDiff = numericCols.some((col) => {
  let d = 0;
  for (let i = 0; i < n; i++) {
    const a = num(base.rows[i][col]), b = num(cand.rows[i][col]);
    if (Math.abs(a - b) > (TOLERANCE[col] || 0)) d++;
  }
  return d > 0;
});
console.log(hasNumericDiff
  ? "Verhalten UNTERSCHEIDET sich zwischen Baseline und Kandidat - Details oben pruefen."
  : "Verhalten IDENTISCH innerhalb der Toleranz - keine Regression erkennbar.");
