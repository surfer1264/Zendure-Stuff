"use strict";
process.env.STEP_MIN = process.env.STEP_MIN || "15";
process.env.START_MIN = process.env.START_MIN || "0";

const path = require("path");
const fs = require("fs");

const mock = require("./mock_server.js");
const { runScript } = require("./shelly_shim.js");

const CYCLES = Number(process.env.CYCLES || 20);
const INTERVAL_MS = Number(process.env.INTERVAL_MS || 3000);
const SPEED_FACTOR = Number(process.env.SPEED_FACTOR || 1);
const MIN_REAL_MS = Number(process.env.MIN_REAL_MS || 15);
const effectiveMs = Math.max(MIN_REAL_MS, Math.round(INTERVAL_MS / SPEED_FACTOR));

// Sicherheits-Obergrenze, falls das Skript haengen bleibt (z.B. Watchdog-Stall):
// grosszuegiger Faktor auf die geschaetzte Zeit, damit ein normal langsamerer
// realer Durchlauf (z.B. auf Windows ohne Keep-Alive-Vorteil) NICHT abgebrochen wird.
const MAX_WAIT_MS = Number(process.env.MAX_WAIT_MS || (CYCLES * effectiveMs * 6 + 30000));

console.log("[runner] SPEED_FACTOR=" + SPEED_FACTOR + " -> nominaler Zyklusabstand ~" + effectiveMs + " ms " +
  "(Hold-/Cooldown-Zaehler im Skript bleiben unveraendert, da sie nur Zyklen zaehlen)");
console.log("[runner] Ziel: " + CYCLES + " Zyklen. Warte auf tatsaechliche Fertigstellung " +
  "(kein fester Zeit-Abbruch mehr) - Sicherheitslimit " + MAX_WAIT_MS + " ms.");

// ---------------------------------------------------------------
// Erweiterung fuer Testmatrix (alles optional, ohne Variablen wie bisher):
//   DAMPING   = dampingFactor fuer diesen Lauf (ersetzt den Wert in zdmc_test.js)
//   MOCK_PORT = Port des Mocks; wird auch in die URLs von zdmc_test.js eingesetzt
//   OUT_DIR   = Ordner fuer closed_loop_result.csv und die angepasste Skriptkopie
// Die Original-Datei zdmc_test.js wird NIE veraendert - angepasst wird eine Kopie.
// ---------------------------------------------------------------
const OUT_DIR = process.env.OUT_DIR ? path.resolve(process.env.OUT_DIR) : __dirname;
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

function prepareScript() {
  const src = path.join(__dirname, "zdmc_test.js");
  const damping = process.env.DAMPING;
  const port = process.env.MOCK_PORT;
  if (damping === undefined && (port === undefined || port === "3900")) return src;

  let code = fs.readFileSync(src, "utf8");
  if (damping !== undefined) {
    const re = /dampingFactor:\s*[0-9.]+/;
    if (!re.test(code)) throw new Error("dampingFactor in zdmc_test.js nicht gefunden");
    code = code.replace(re, "dampingFactor: " + Number(damping));
    console.log("[runner] dampingFactor fuer diesen Lauf: " + Number(damping));
  }
  if (port !== undefined && port !== "3900") {
    code = code.split("localhost:3900").join("localhost:" + port);
    console.log("[runner] Mock-Port fuer diesen Lauf: " + port);
  }
  const dst = path.join(OUT_DIR, "zdmc_run.js");
  fs.writeFileSync(dst, code);
  return dst;
}

setTimeout(() => {
  runScript(prepareScript(), "zdmc");
}, 500);

const startedAt = Date.now();
let lastCount = -1;
let lastProgressAt = Date.now();

const checkInterval = setInterval(() => {
  const n = mock.log.length;

  if (n !== lastCount) {
    lastCount = n;
    lastProgressAt = Date.now();
  }

  const elapsed = Date.now() - startedAt;

  // Fertig: Zielzahl erreicht
  if (n >= CYCLES) {
    finish("Zielzahl erreicht");
    return;
  }

  // Sicherheitsabbruch 1: absolute Obergrenze ueberschritten
  if (elapsed > MAX_WAIT_MS) {
    console.log("[runner] WARNUNG: Sicherheitslimit (" + MAX_WAIT_MS + " ms) erreicht, " +
      "aber erst " + n + "/" + CYCLES + " Zyklen fertig. Breche ab - vermutlich haengt " +
      "ein Zyklus (Watchdog?) oder die Umgebung ist ungewoehnlich langsam.");
    finish("Sicherheitslimit erreicht (unvollstaendig)");
    return;
  }

  // Sicherheitsabbruch 2: seit 20s keinerlei Fortschritt mehr -> haengt wirklich
  if (Date.now() - lastProgressAt > 20000) {
    console.log("[runner] WARNUNG: seit 20s kein neuer Zyklus mehr (aktuell " + n + "/" + CYCLES +
      "). Skript haengt vermutlich fest. Breche ab.");
    finish("Kein Fortschritt mehr (unvollstaendig)");
    return;
  }
}, 200);

function finish(reason) {
  clearInterval(checkInterval);
  const outPath = path.join(OUT_DIR, "closed_loop_result.csv");
  const rows = mock.log;
  if (rows.length === 0) {
    console.log("[runner] KEINE Log-Zeilen - Skript ist vermutlich nicht durchgelaufen.");
    process.exit(1);
  }
  const cols = Object.keys(rows[0]);
  const csv = [cols.join(";")].concat(
    rows.map((r) => cols.map((c) => r[c]).join(";"))
  ).join("\n");
  fs.writeFileSync(outPath, csv);
  const realMs = Date.now() - startedAt;
  console.log("[runner] fertig (" + reason + "). " + rows.length + " Zyklen geloggt in " +
    Math.round(realMs / 1000) + "s (~" + Math.round(realMs / Math.max(1, rows.length)) +
    " ms/Zyklus real) -> " + outPath);
  process.exit(rows.length >= CYCLES ? 0 : 2);
}
