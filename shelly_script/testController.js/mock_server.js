// Stateful Mock-Server: simuliert Netzzaehler (http_json) + 2 Zendure-Geraete
// Reagiert geschlossen auf das, was der echte Controller (zdmc_test.js) schreibt.
"use strict";

const http = require("http");
const url = require("url");

// ---------------------------------------------------------------
// Zeit- und Lastmodell (wiederverwendet aus dem Testdatenprofil)
// ---------------------------------------------------------------

const STEP_MIN = Number(process.env.STEP_MIN || 8); // simulierte Minuten pro Zyklus
let simMinute = Number(process.env.START_MIN || 0);  // Start-Uhrzeit (Minute des Tages)

function hhmm(m) {
  m = ((m % 1440) + 1440) % 1440;
  const h = Math.floor(m / 60), mi = m % 60;
  return String(h).padStart(2, "0") + ":" + String(mi).padStart(2, "0");
}

function gauss(h, mu, sig, amp) {
  return amp * Math.exp(-0.5 * Math.pow((h - mu) / sig, 2));
}
function sigmoid(x) { return 1 / (1 + Math.exp(-x)); }

const LOAD_SCALE = Number(process.env.LOAD_SCALE || 1.0);

function householdLoad(minuteOfDay) {
  const hour = (((minuteOfDay % 1440) + 1440) % 1440) / 60; // immer auf einen Tag (0-24h) zurueckgesetzt
  const dayW = sigmoid((hour - 6) * 4) * sigmoid((22 - hour) * 4);
  const lower = 150 + dayW * (300 - 150);
  const upper = 300 + dayW * (3000 - 300);
  const base = lower + 0.30 * (upper - lower);
  const peaks = (gauss(hour, 7.2, 0.8, 700) + gauss(hour, 12.5, 1.0, 550) + gauss(hour, 19.0, 1.3, 1900)) * dayW;
  let v = (base + peaks) * LOAD_SCALE;
  v = Math.max(lower * Math.min(1, LOAD_SCALE), Math.min(upper, v));
  return v;
}

function pvCurve(minuteOfDay, start, end, peak, maxPower) {
  const m = ((minuteOfDay % 1440) + 1440) % 1440; // immer auf einen Tag (0-1440) zurueckgesetzt
  if (m < start || m > end) return 0;
  let v;
  if (m <= peak) {
    const frac = (m - start) / (peak - start);
    v = maxPower * Math.sin(frac * Math.PI / 2);
  } else {
    const frac = (m - peak) / (end - peak);
    v = maxPower * Math.cos(frac * Math.PI / 2);
  }
  return Math.max(0, v);
}

const WIN_START = 8 * 60, WIN_END = 18 * 60;
function pv800(m) { return pvCurve(m, WIN_START, WIN_END, 10 * 60, 1600); }
function pv2400(m) { return pvCurve(m, WIN_START, WIN_END, 15 * 60, 2000); }

// ---------------------------------------------------------------
// Geraete-Zustand
// ---------------------------------------------------------------

function makeDevice(sn, capacityKWh, startSoc, pvFn) {
  return {
    sn: sn,
    capacityKWh: capacityKWh,
    soc: startSoc,          // %
    pvFn: pvFn,
    minSocX10: 0,            // wird von syncSocLimitsDevice ueberschrieben (vorher: keine Sperre)
    socSetX10: 1000,         // "
    acMode: 1,               // 1=Idle/Laden, 2=Export
    outputLimit: 0,
    inputLimit: 0,
    smartMode: 1,
    gridReverse: 1,
    lastPv: 0,
    lastAcPower: 0,          // signiert: + Export, - Laden vom Netz (tatsaechlich geliefert)
  };
}

const START_SOC = Number(process.env.START_SOC || 50);
const dev0 = makeDevice("MOCKSN-SF800", 2.0, START_SOC, pv800);
const dev1 = makeDevice("MOCKSN-SF2400", 4.0, START_SOC, pv2400);

function socLimitOf(dev) {
  const maxSoc = dev.socSetX10 / 10;
  const minSoc = dev.minSocX10 / 10;
  if (dev.soc >= maxSoc) return 1;
  if (dev.soc <= minSoc) return 2;
  return 0;
}

// Fuehrt STEP_MIN simulierte Minuten fuer ein Geraet aus: PV-Ladung (autonom)
// + AC-Wirkung des zuletzt geschriebenen Kommandos.
function advanceDevice(dev, elapsedMin) {
  const dtH = elapsedMin / 60;
  const pv = dev.pvFn(simMinute);
  dev.lastPv = pv;

  // Firmware-Grenzen: das Geraet haelt SEINE EIGENEN minSoc/socSet-Werte
  // hart ein (genau dafuer schreibt syncSocLimitsDevice sie ja hin) -
  // unabhaengig davon, wie grob STEP_MIN zwischen zwei Reglerzyklen ist.
  const maxSoc = dev.socSetX10 / 10;
  const minSoc = dev.minSocX10 / 10;

  // --- PV laedt Akku (DC-seitig, unabhaengig vom Controller) ---
  let pvSurplus = pv;
  if (dev.soc < maxSoc) {
    const headroomKwh = dev.capacityKWh * (maxSoc - dev.soc) / 100;
    const maxByHeadroomW = headroomKwh * 1000 / dtH;
    const chg = Math.min(pv, maxByHeadroomW);
    dev.soc += (chg * dtH / 1000 / dev.capacityKWh) * 100;
    pvSurplus = pv - chg;
  }

  // --- AC-Kommando des Controllers wirkt auf den Akku ---
  let acPower = 0; // signiert: + Export/Entladen, - Laden vom Netz
  if (dev.acMode === 2) acPower = dev.outputLimit;
  else if (dev.acMode === 1 && dev.inputLimit > 0) acPower = -dev.inputLimit;

  let delivered = 0;
  if (acPower > 0) {
    const maxDeliverableW = Math.max(0, (dev.soc - minSoc) / 100) * dev.capacityKWh * 1000 / dtH;
    delivered = Math.min(acPower, maxDeliverableW);
    dev.soc -= (delivered * dtH / 1000 / dev.capacityKWh) * 100;
  } else if (acPower < 0) {
    const maxAcceptableW = Math.max(0, (maxSoc - dev.soc) / 100) * dev.capacityKWh * 1000 / dtH;
    const chg = Math.min(-acPower, maxAcceptableW);
    dev.soc += (chg * dtH / 1000 / dev.capacityKWh) * 100;
    delivered = -chg;
  }

  dev.soc = Math.max(0, Math.min(100, dev.soc));
  dev.lastAcPower = delivered;
  return pvSurplus;
}

let lastGridPollAt = null;

function reportJson(dev) {
  const acMode = dev.acMode;
  const props = {
    electricLevel: Math.round(dev.soc),
    socLimit: socLimitOf(dev),
    gridReverse: dev.gridReverse,
    acMode: acMode,
    outputLimit: dev.outputLimit,
    inputLimit: dev.inputLimit,
    smartMode: dev.smartMode,
    minSoc: dev.minSocX10,
    socSet: dev.socSetX10,
  };
  if (acMode === 2) {
    props.outputHomePower = Math.max(0, Math.round(dev.lastAcPower));
    props.gridInputPower = 0;
  } else {
    props.outputHomePower = 0;
    props.gridInputPower = Math.max(0, Math.round(-dev.lastAcPower));
  }
  return JSON.stringify({ sn: dev.sn, properties: props });
}

function currentAcContribution(dev) {
  if (dev.acMode === 2) return dev.outputLimit;
  if (dev.acMode === 1 && dev.inputLimit > 0) return -dev.inputLimit;
  return 0;
}

// ---------------------------------------------------------------
// Log-Puffer (fuer die Auswertung nach dem Testlauf)
// ---------------------------------------------------------------
const log = [];

function readBody(req, cb) {
  let chunks = [];
  req.on("data", (c) => chunks.push(c));
  req.on("end", () => cb(Buffer.concat(chunks).toString("utf8")));
}

const server = http.createServer((req, res) => {
  const parsed = url.parse(req.url, true);
  const path = parsed.pathname;

  // ---------------- Netzzaehler ----------------
  if (path === "/grid/properties/report" && req.method === "GET") {
    const elapsed = lastGridPollAt === null ? 0 : STEP_MIN;
    if (elapsed > 0) simMinute += STEP_MIN;

    if (elapsed > 0) {
      advanceDevice(dev0, elapsed);
      advanceDevice(dev1, elapsed);
    }
    lastGridPollAt = Date.now();

    const load = householdLoad(simMinute);
    const acSum = currentAcContribution(dev0) + currentAcContribution(dev1);
    const grid = load - acSum;

    log.push({
      t: hhmm(simMinute), minute: simMinute,
      haushalt_W: Math.round(load),
      grid_W: Math.round(grid),
      soc_sf800: Math.round(dev0.soc), soc_sf2400: Math.round(dev1.soc),
      pv_sf800: Math.round(dev0.lastPv), pv_sf2400: Math.round(dev1.lastPv),
      acMode_sf800: dev0.acMode, out_sf800: dev0.outputLimit, in_sf800: dev0.inputLimit,
      acMode_sf2400: dev1.acMode, out_sf2400: dev1.outputLimit, in_sf2400: dev1.inputLimit,
      socLimit_sf800: socLimitOf(dev0), socLimit_sf2400: socLimitOf(dev1),
      gridReverse_sf800: dev0.gridReverse, gridReverse_sf2400: dev1.gridReverse,
    });

    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ total_power: Math.round(grid) }));
    return;
  }

  // ---------------- Geraete lesen ----------------
  if ((path === "/dev0/properties/report" || path === "/dev1/properties/report") && req.method === "GET") {
    const dev = path === "/dev0/properties/report" ? dev0 : dev1;
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(reportJson(dev));
    return;
  }

  // ---------------- Geraete schreiben ----------------
  if ((path === "/dev0/properties/write" || path === "/dev1/properties/write") && req.method === "POST") {
    const dev = path === "/dev0/properties/write" ? dev0 : dev1;
    readBody(req, (bodyStr) => {
      let body;
      try { body = JSON.parse(bodyStr); } catch (e) { res.writeHead(400); res.end("{}"); return; }
      const p = (body && body.properties) || {};

      if (p.acMode !== undefined) dev.acMode = p.acMode;
      if (p.outputLimit !== undefined) dev.outputLimit = p.outputLimit;
      if (p.inputLimit !== undefined) dev.inputLimit = p.inputLimit;
      if (p.smartMode !== undefined) dev.smartMode = p.smartMode;
      if (p.minSoc !== undefined) dev.minSocX10 = p.minSoc;
      if (p.socSet !== undefined) dev.socSetX10 = p.socSet;
      if (p.gridReverse !== undefined) dev.gridReverse = p.gridReverse;

      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ writeRsp: 0 }));
    });
    return;
  }

  res.writeHead(404);
  res.end("not found");
});

const PORT = Number(process.env.MOCK_PORT || 3900);
server.listen(PORT, () => {
  console.log("[mock] laeuft auf Port " + PORT + " (STEP_MIN=" + STEP_MIN + ", Start " + hhmm(simMinute) + ")");
});

// Fuer den Runner: Log als JSON auf Signal ausgeben
process.on("SIGUSR2", () => {
  console.log("###LOG_START###");
  console.log(JSON.stringify(log));
  console.log("###LOG_END###");
});

module.exports = { server, log };
