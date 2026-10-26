// Testmatrix: mehrere dampingFactor-Werte x mehrere Seeds, je Lauf ein eigener
// Prozess (run_test.js) mit eigenem Mock-Port und eigenem Ausgabeordner.
// Am Ende: matrix_laeufe.csv (je Lauf) + matrix_ergebnis.md (je Damping, Median ueber Seeds).
//
// Steuerung per Umgebungsvariablen (alle anderen, z.B. CYCLES, STEP_MIN,
// START_MIN, START_SOC, SPEED_FACTOR, LOAD_SCALE, SCENARIO, werden durchgereicht):
//   DAMPINGS   Liste, Default "0.4,0.5,0.65,0.8,1.0"
//   SEEDS      Liste, Default "1,2,3"
//   PARALLEL   gleichzeitige Laeufe, Default 2
//   BASE_PORT  erster Mock-Port, Default 3901
//   BAND_W     Hystereseband fuer die Auswertung, Default 13
//   MATRIX_DIR Zielordner, Default Matrix-<Datum-Uhrzeit>
//   SAT_TOL_W  Toleranz fuer "Geraet am Maximum" in der Saettigung, Default = BAND_W.
//              Ein Geraet, das weniger als die Hysterese unter seinem Maximum steht,
//              kann praktisch nicht mehr nachlegen (der Controller aendert erst ab
//              der Hysterese).
//   NUR_AUSWERTEN=1  keine Laeufe starten, nur die vorhandenen Ordner in
//              MATRIX_DIR neu auswerten (gleiche DAMPINGS/SEEDS/CYCLES setzen)
"use strict";

const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const list = (s, d) => String(s || d).split(",").map((x) => x.trim()).filter(Boolean);
const DAMPINGS = list(process.env.DAMPINGS, "0.4,0.5,0.65,0.8,1.0");
const SEEDS = list(process.env.SEEDS, "1,2,3");
const PARALLEL = Math.max(1, Number(process.env.PARALLEL || 2));
const BASE_PORT = Number(process.env.BASE_PORT || 3901);
const BAND = Number(process.env.BAND_W || 13);
const STEP_MIN = Number(process.env.STEP_MIN || 15);
const SAT_TOL = Number(process.env.SAT_TOL_W || BAND);
const NUR_AUSWERTEN = process.env.NUR_AUSWERTEN === "1";

// Geraetegrenzen in CSV-Reihenfolge (Mock dev0 = CSV "sf800", dev1 = CSV "sf2400").
// Werte aus zdmc_test.js lesen, damit sie zu den CONFIG-Werten passen.
function deviceLimits() {
  const code = fs.readFileSync(path.join(__dirname, "zdmc_test.js"), "utf8");
  const out = [...code.matchAll(/maxOutput:\s*([0-9]+)/g)].map((m) => Number(m[1]));
  const inp = [...code.matchAll(/maxInputPower:\s*([0-9]+)/g)].map((m) => Number(m[1]));
  const minS = [...code.matchAll(/minSoc:\s*([0-9]+)/g)].map((m) => Number(m[1]));
  const maxS = [...code.matchAll(/maxSoc:\s*([0-9]+)/g)].map((m) => Number(m[1]));
  return { out: out.slice(0, 2), inp: inp.slice(0, 2), minSoc: minS.slice(0, 2), maxSoc: maxS.slice(0, 2) };
}
const LIM = deviceLimits();

function ts() {
  const d = new Date(), p = (n) => String(n).padStart(2, "0");
  return String(d.getFullYear()).slice(2) + p(d.getMonth() + 1) + p(d.getDate()) + "-" +
    p(d.getHours()) + p(d.getMinutes()) + p(d.getSeconds());
}
const MATRIX_DIR = path.resolve(process.env.MATRIX_DIR || ("Matrix-" + ts()));
fs.mkdirSync(MATRIX_DIR, { recursive: true });

// ---------------------------------------------------------------
// Laeufe ausfuehren
// ---------------------------------------------------------------
const jobs = [];
for (const seed of SEEDS) for (const d of DAMPINGS) jobs.push({ seed, damping: d });

function runJob(job, port) {
  return new Promise((resolve) => {
    const dir = path.join(MATRIX_DIR, "seed" + job.seed + "_damp" + job.damping);
    fs.mkdirSync(dir, { recursive: true });
    const env = Object.assign({}, process.env, {
      NOISE_SEED: String(job.seed), DAMPING: String(job.damping),
      MOCK_PORT: String(port), OUT_DIR: dir,
    });
    const logPath = path.join(dir, "lauf.log");
    const logStream = fs.createWriteStream(logPath);
    const t0 = Date.now();
    console.log("[matrix] Start  seed " + job.seed + " damping " + job.damping + " (Port " + port + ")");
    const p = spawn(process.execPath, [path.join(__dirname, "run_test.js")], { cwd: __dirname, env });
    p.stdout.pipe(logStream);
    p.stderr.pipe(logStream);
    p.on("close", (code) => {
      logStream.end();
      const sec = Math.round((Date.now() - t0) / 1000);
      console.log("[matrix] Fertig seed " + job.seed + " damping " + job.damping +
        " nach " + sec + " s (Exit " + code + ")");
      // optional: Bericht wie bisher
      const gc = path.join(__dirname, "generate_charts.js");
      const csv = path.join(dir, "closed_loop_result.csv");
      if (fs.existsSync(gc) && fs.existsSync(csv)) {
        const g = spawn(process.execPath, [gc, csv, path.join(dir, "report.html")], { cwd: __dirname });
        g.on("close", () => resolve(Object.assign({ dir, exit: code }, job)));
      } else {
        resolve(Object.assign({ dir, exit: code }, job));
      }
    });
  });
}

async function runAll() {
  const results = [];
  let next = 0;
  async function worker(slot) {
    while (next < jobs.length) {
      const job = jobs[next++];
      results.push(await runJob(job, BASE_PORT + slot));
    }
  }
  await Promise.all(Array.from({ length: Math.min(PARALLEL, jobs.length) }, (_, i) => worker(i)));
  return results;
}

// ---------------------------------------------------------------
// Auswertung je Lauf
// ---------------------------------------------------------------
function readCsv(file) {
  const lines = fs.readFileSync(file, "utf8").split(/\r?\n/).filter(Boolean);
  const head = lines[0].split(";");
  return lines.slice(1).map((l) => {
    const v = l.split(";"), r = {};
    head.forEach((h, i) => { const n = Number(v[i]); r[h] = v[i] === "" || isNaN(n) ? v[i] : n; });
    return r;
  });
}
const median = (a) => {
  if (!a.length) return NaN;
  const s = a.slice().sort((x, y) => x - y), m = s.length >> 1;
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};

function classify(ev) {
  if (!ev) return "ruhig";
  if (String(ev).includes("waschmaschine")) return "waschmaschine";
  if (String(ev).includes("induktion")) return "induktion";
  return "sonstige";
}

function evaluate(res) {
  const csv = path.join(res.dir, "closed_loop_result.csv");
  if (!fs.existsSync(csv)) return Object.assign({ fehler: "keine CSV" }, res);
  // Zeile 0 = Startzustand. Auf genau CYCLES Zeilen kuerzen: der Runner stoppt
  // erst beim naechsten Pruefzeitpunkt, die Laeufe sind sonst unterschiedlich lang.
  const cyc = Number(process.env.CYCLES || 0);
  const all = readCsv(csv);
  const rows = cyc > 0 ? all.slice(1, cyc + 1) : all.slice(1);
  const dtH = STEP_MIN / 60;

  let sat = 0, inB = 0, mid = 0, big = 0, imp = 0, exp = 0;
  const devs = [];
  const win = {};
  for (const r of rows) {
    const g = r.grid_W;
    devs.push(g);
    const gm = typeof r.grid_mittel_W === "number" ? r.grid_mittel_W : g;
    if (gm > 0) imp += gm * dtH; else exp += -gm * dtH;

    // Saettigung: kein Geraet kann in die noetige Richtung noch mehr tun
    const s = [r.socLimit_sf800, r.socLimit_sf2400];
    const o = [r.out_sf800, r.out_sf2400];
    const i = [r.in_sf800, r.in_sf2400];
    const soc = [r.soc_sf800, r.soc_sf2400];
    // Entlade-Hysterese des Controllers (Freigabe erst ab minSoc + 3) ist in der
    // CSV nicht sichtbar -> naeherungsweise: steht still und SoC unter minSoc + 3
    const cantDeliver = (k) => s[k] === 2 || o[k] >= LIM.out[k] - SAT_TOL ||
                               (o[k] === 0 && soc[k] < LIM.minSoc[k] + 3);
    // voll: socLimit 1, am Maximum, oder SoC bereits bei maxSoc (Mock meldet
    // socLimit 1 erst bei exakt 100 %, die CSV zeigt gerundet schon 100)
    const cantAbsorb = (k) => s[k] === 1 || i[k] >= LIM.inp[k] - SAT_TOL || soc[k] >= LIM.maxSoc[k];
    const saturated = (g > BAND && cantDeliver(0) && cantDeliver(1)) ||
                      (g < -BAND && cantAbsorb(0) && cantAbsorb(1));
    if (saturated) { sat++; continue; }

    const a = Math.abs(g);
    const cls = classify(r.event);
    win[cls] = win[cls] || { n: 0, inB: 0, big: 0 };
    win[cls].n++;
    if (a <= BAND) { inB++; win[cls].inB++; }
    else if (a <= 50) mid++;
    else { big++; win[cls].big++; }
  }
  const nAll = rows.length, nUns = nAll - sat;
  const pct = (x, n) => (n ? (100 * x) / n : NaN);

  let writes = 0;
  const logPath = path.join(res.dir, "lauf.log");
  if (fs.existsSync(logPath)) {
    writes = (fs.readFileSync(logPath, "utf8").match(/Leistung gesetzt/g) || []).length;
  }

  const out = Object.assign({}, res, {
    zyklen: nAll,
    median_W: median(devs),
    band_pct: pct(inB, nUns),
    mittel_pct: pct(mid, nUns),
    gross_pct: pct(big, nUns),
    saettigung_pct: pct(sat, nAll),
    bezug_kWh: imp / 1000,
    export_kWh: exp / 1000,
    schreibvorgaenge: writes,
  });
  for (const c of ["ruhig", "waschmaschine", "induktion"]) {
    const w = win[c];
    out[c + "_band_pct"] = w ? pct(w.inB, w.n) : NaN;
    out[c + "_gross_pct"] = w ? pct(w.big, w.n) : NaN;
  }
  return out;
}

// ---------------------------------------------------------------
// Ausgabe
// ---------------------------------------------------------------
const f1 = (x) => (isNaN(x) ? "–" : x.toFixed(1).replace(".", ","));
const f2 = (x) => (isNaN(x) ? "–" : x.toFixed(2).replace(".", ","));

function writeOutputs(evals) {
  const cols = ["seed", "damping", "exit", "zyklen", "median_W", "band_pct", "mittel_pct", "gross_pct",
    "saettigung_pct", "bezug_kWh", "export_kWh", "schreibvorgaenge",
    "ruhig_band_pct", "ruhig_gross_pct", "waschmaschine_band_pct", "waschmaschine_gross_pct",
    "induktion_band_pct", "induktion_gross_pct"];
  const csv = [cols.join(";")].concat(evals.map((e) =>
    cols.map((c) => (typeof e[c] === "number" ? String(Math.round(e[c] * 100) / 100).replace(".", ",") : (e[c] ?? ""))).join(";")
  )).join("\n");
  fs.writeFileSync(path.join(MATRIX_DIR, "matrix_laeufe.csv"), csv);

  const lines = [];
  lines.push("# Testmatrix dampingFactor");
  lines.push("");
  lines.push("Szenario: " + (process.env.SCENARIO || "keins (ohne Rauschen)") +
    " | Seeds: " + SEEDS.join(", ") + " | Zyklen je Lauf: " + (process.env.CYCLES || "?") +
    " | Hystereseband: ±" + BAND + " W");
  lines.push("");
  lines.push("Werte = Median über die Seeds. Bänder ohne gesättigte Zyklen.");
  lines.push("");
  lines.push("| Damping | Median | im Band | 13–50 W | > 50 W | Sättigung | Bezug kWh | Export kWh | Schreibvorg. | Band ruhig | Band Waschm. | Band Induktion |");
  lines.push("|---|---|---|---|---|---|---|---|---|---|---|---|");
  for (const d of DAMPINGS) {
    const es = evals.filter((e) => String(e.damping) === String(d) && !e.fehler);
    const m = (k) => median(es.map((e) => e[k]).filter((x) => !isNaN(x)));
    lines.push("| " + d + " | " + f1(m("median_W")) + " W | " + f1(m("band_pct")) + " % | " +
      f1(m("mittel_pct")) + " % | " + f1(m("gross_pct")) + " % | " + f1(m("saettigung_pct")) + " % | " +
      f2(m("bezug_kWh")) + " | " + f2(m("export_kWh")) + " | " + Math.round(m("schreibvorgaenge")) + " | " +
      f1(m("ruhig_band_pct")) + " % | " + f1(m("waschmaschine_band_pct")) + " % | " +
      f1(m("induktion_band_pct")) + " % |");
  }
  lines.push("");
  lines.push("Legende:");
  lines.push("- Median: mittlere echte Netzabweichung (grid_W), nahe 0 W = gut.");
  lines.push("- im Band / 13–50 W / > 50 W: Anteil der Zyklen nach Betrag der Abweichung, ohne gesättigte Zyklen.");
  lines.push("- Sättigung: Bezug, obwohl kein Gerät mehr liefern kann (socLimit 2, weniger als " + SAT_TOL + " W unter dem Maximum oder Entlade-Hysterese unter minSoc + 3 %), bzw. Export, obwohl kein Gerät mehr laden kann (socLimit 1, voll oder weniger als " + SAT_TOL + " W unter dem Maximum).");
  lines.push("- Bezug/Export: Energie über den Lauf aus grid_mittel_W.");
  lines.push("- Band ruhig/Waschm./Induktion: Anteil im Band nur in diesen Zeitfenstern.");
  const bad = evals.filter((e) => e.fehler || e.exit !== 0);
  if (bad.length) {
    lines.push("");
    lines.push("Achtung, unvollständige Läufe: " + bad.map((e) => "seed " + e.seed + "/damp " + e.damping).join(", "));
  }
  fs.writeFileSync(path.join(MATRIX_DIR, "matrix_ergebnis.md"), lines.join("\n") + "\n");
  console.log("\n" + lines.join("\n"));
}

(async () => {
  if (NUR_AUSWERTEN) console.log("[matrix] nur Auswertung der vorhandenen Ordner (Exit wird als 0 angenommen)");
  console.log("[matrix] " + jobs.length + " Laeufe (Damping " + DAMPINGS.join("/") + " x Seeds " +
    SEEDS.join("/") + "), parallel " + PARALLEL + " -> " + MATRIX_DIR);
  const results = NUR_AUSWERTEN
    ? jobs.map((j) => Object.assign({ dir: path.join(MATRIX_DIR, "seed" + j.seed + "_damp" + j.damping), exit: 0 }, j))
    : await runAll();
  const order = (e) => SEEDS.indexOf(String(e.seed)) * 100 + DAMPINGS.indexOf(String(e.damping));
  const evals = results.map(evaluate).sort((a, b) => order(a) - order(b));
  writeOutputs(evals);
  console.log("\n[matrix] Ergebnisse: " + MATRIX_DIR);
})();
