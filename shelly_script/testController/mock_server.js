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
  const totalMin = Math.round(m); // erst auf ganze Minute runden...
  const wrapped = ((totalMin % 1440) + 1440) % 1440; // ...DANN auf einen Tag wrappen
  const h = Math.floor(wrapped / 60), mi = wrapped % 60;
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
function pv800(m) { return pvCurve(m, WIN_START-60, WIN_END-60, 10 * 60, 1400); }
function pv2400(m) { return pvCurve(m, WIN_START, WIN_END+60, 15 * 60, 920); }

// ===============================================================
// RAUSCH- UND SZENARIO-MODELL (deterministisch)
// ---------------------------------------------------------------
// Aktiv nur, wenn NOISE_SEED oder SCENARIO gesetzt ist. Sonst verhaelt
// sich der Mock exakt wie vorher (gleiche Werte, gleiche CSV-Spalten
// plus leere Zusatzspalten).
//
// Grundsatz: Jeder Zufallswert haengt NUR von (Seed, Zeitindex, Kanal)
// ab - nie von der Anzahl der Aufrufe. Ein Controller, der oefter
// schreibt oder liest, sieht deshalb exakt dieselbe Last. Damit sind
// Laeufe mit verschiedenen dampingFactor-Werten direkt vergleichbar.
//
// Umgebungsvariablen:
//   NOISE_SEED        ganze Zahl (Default 1, wenn SCENARIO gesetzt)
//   SCENARIO          Pfad zur Szenario-JSON (ohne: nur Grund-/Messrauschen)
//   METER_NOISE_W     ueberschreibt "messrauschenW" aus dem Szenario
//   SUBSTEP_S         Teilschritt in Sekunden fuer schnelle Lasten (Default 1)
// ===============================================================

const NOISE_ON = process.env.NOISE_SEED !== undefined || process.env.SCENARIO !== undefined;
const NOISE_SEED = NOISE_ON ? (Number(process.env.NOISE_SEED || 1) | 0) : 0;

const DEFAULT_SCENARIO = {
  name: "nur-rauschen",
  grundrauschenW: 30,          // sigma der langsamen Lastschwankung (echte Last)
  grundrauschenPeriodeS: 60,   // Stuetzstellenabstand der langsamen Schwankung
  lastzitternW: 5,             // sigma schnelles Zittern der echten Last (je Teilschritt)
  messrauschenW: 8,            // sigma Zaehler-Messfehler (nur Messwert, keine Energie)
  geraeteMessrauschenW: 3,     // sigma Messfehler im Geraete-Report (nur wenn Leistung > 0)
  kuehlschrank: { leistungW: 100, anMin: 15, ausMin: 30 },
  events: [],
  zufallsEvents: []
};

function loadScenario() {
  if (!NOISE_ON) return null;
  let sc = Object.assign({}, DEFAULT_SCENARIO);
  if (process.env.SCENARIO) {
    const fs = require("fs");
    const fileSc = JSON.parse(fs.readFileSync(process.env.SCENARIO, "utf8"));
    sc = Object.assign(sc, fileSc);
  }
  if (process.env.METER_NOISE_W !== undefined) sc.messrauschenW = Number(process.env.METER_NOISE_W);
  return sc;
}
const SCEN = loadScenario();

// --- zaehlerbasierter Zufall: rnd(seed, index, kanal) -> [0,1) ----
function mix32(h) {
  h ^= h >>> 16; h = Math.imul(h, 0x85ebca6b);
  h ^= h >>> 13; h = Math.imul(h, 0xc2b2ae35);
  h ^= h >>> 16; return h >>> 0;
}
const chCache = {};
function chHash(ch) {
  if (chCache[ch] !== undefined) return chCache[ch];
  let h = 0x811c9dc5;
  for (let i = 0; i < ch.length; i++) { h ^= ch.charCodeAt(i); h = Math.imul(h, 0x01000193); }
  return (chCache[ch] = h >>> 0);
}
function rnd(seed, idx, ch) {
  let h = mix32((seed ^ 0x9e3779b9) >>> 0);
  h = mix32(h ^ (idx >>> 0));
  h = mix32(h ^ (Math.floor(idx / 4294967296) >>> 0));
  h = mix32(h ^ chHash(ch));
  return (h + 0.5) / 4294967296;
}
function gaussN(seed, idx, ch) { // Standardnormalverteilt (Box-Muller)
  const u1 = rnd(seed, idx, ch + "#a"), u2 = rnd(seed, idx, ch + "#b");
  return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
}

// --- Zeitbasis -----------------------------------------------------
// Ganzzahliger Teilschritt-Index g (kein Aufsummieren von Fliesskomma).
const START_MIN = Number(process.env.START_MIN || 0);
const STEP_SEC = STEP_MIN * 60;
const SUBS = NOISE_ON ? Math.max(1, Math.round(STEP_SEC / Number(process.env.SUBSTEP_S || 1))) : 1;
const SUB_SEC = STEP_SEC / SUBS;
function tMinOf(g) { return START_MIN + (g * SUB_SEC) / 60; } // absolute Simulationsminute

function hm2min(s) {
  if (typeof s === "number") return s;
  const p = String(s).split(":");
  return Number(p[0]) * 60 + Number(p[1] || 0);
}

// --- langsame Lastschwankung: Stuetzstellen + Cosinus-Interpolation --
function slowNoise(tMin) {
  const per = SCEN.grundrauschenPeriodeS / 60;
  const x = tMin / per + 1e-9;
  const k = Math.floor(x), f = x - k;
  const a = gaussN(NOISE_SEED, k, "slow"), b = gaussN(NOISE_SEED, k + 1, "slow");
  const w = (1 - Math.cos(f * Math.PI)) / 2;
  return SCEN.grundrauschenW * (a + (b - a) * w);
}

// --- Kuehlschrank: fester Takt, Phase aus dem Seed -----------------
function fridge(tMin) {
  const k = SCEN.kuehlschrank;
  if (!k) return 0;
  const per = k.anMin + k.ausMin;
  const phase = rnd(NOISE_SEED, 0, "fridgePhase") * per;
  const pos = (((tMin + phase) % per) + per) % per;
  return pos < k.anMin ? k.leistungW : 0;
}

// --- Ereignis-Lastprofile -------------------------------------------
// tIn = Minuten seit Ereignisbeginn, uid = eindeutige Ereignis-Kennung
function pWaschmaschine(ev, tIn, uid) {
  const dauer = ev.dauer, p = tIn / dauer, sec = tIn * 60;
  const heizW = ev.heizW || 2000;
  if (p < 0.03) return 30;                                   // Wasser einlassen
  const zyk = Math.floor(sec / 20), inZyk = sec - zyk * 20;  // Trommel: 12 s an / 8 s aus
  const trommel = inZyk < 12 ? 150 + 150 * rnd(NOISE_SEED, zyk, uid + "trommel") : 0;
  if (p < 0.30) return heizW + 0.5 * trommel;                // Heizen
  if (p < 0.83) return 15 + trommel;                         // Waschen
  if (p < 0.97) {                                            // Schleudern, steigend
    const s = (p - 0.83) / 0.14;
    const k = Math.floor(sec / 30);
    return 40 + 300 + 300 * s + 60 * (rnd(NOISE_SEED, k, uid + "schleu") - 0.5);
  }
  return 5;                                                  // Ende/Abpumpen
}

function pInduktion(ev, tIn, uid) {
  // optionale Stufen: [{abMin, stufe, periodeS}]; stufe 1.0 = Dauerleistung
  let stufe = ev.stufe !== undefined ? ev.stufe : 0.6;
  let per = ev.periodeS || 12;
  if (Array.isArray(ev.stufen)) {
    for (const st of ev.stufen) if (tIn >= st.abMin) { stufe = st.stufe; if (st.periodeS) per = st.periodeS; }
  }
  const leistung = ev.leistungW || 1900;
  const luefter = 25;
  if (stufe >= 1) return leistung + luefter;
  const sec = tIn * 60;
  const zyk = Math.floor(sec / per);
  const phase = rnd(NOISE_SEED, 0, uid + "phase") * per;
  const pos = (((sec + phase) % per) + per) % per;
  const an = pos < stufe * per;
  const jitter = 1 + 0.05 * (rnd(NOISE_SEED, zyk, uid + "jit") - 0.5) * 2;
  return (an ? leistung * jitter : 0) + luefter;
}

function eventPower(ev, tIn, uid) {
  switch (ev.typ) {
    case "waschmaschine": return pWaschmaschine(ev, tIn, uid);
    case "induktion":     return pInduktion(ev, tIn, uid);
    case "wasserkocher":  return ev.leistungW || 2000;
    default:              return ev.leistungW || 0;     // "block": konstante Leistung
  }
}

// --- Ereignisplan: feste (taeglich) + zufaellig platzierte ----------
// Zufallsereignisse: {typ, anzahlProTag, von, bis, dauer, ...}
const dayPlanCache = {};
function eventsOfDay(day) {
  if (dayPlanCache[day]) return dayPlanCache[day];
  const list = [];
  (SCEN.events || []).forEach((ev, i) => {
    const e = Object.assign({}, ev, { dauer: ev.dauer || 30 });
    list.push({ ev: e, start: day * 1440 + hm2min(ev.start), uid: "f" + i + "d" + day + ":" });
  });
  (SCEN.zufallsEvents || []).forEach((zr, i) => {
    const von = hm2min(zr.von || "00:00"), bis = hm2min(zr.bis || "24:00");
    const dauer = zr.dauer || 30;
    for (let n = 0; n < (zr.anzahlProTag || 1); n++) {
      const r = rnd(NOISE_SEED, day * 1000 + n, "zev" + i);
      const start = von + r * Math.max(0, bis - von - dauer);
      const e = Object.assign({}, zr, { dauer: dauer });
      list.push({ ev: e, start: day * 1440 + start, uid: "z" + i + "n" + n + "d" + day + ":" });
    }
  });
  return (dayPlanCache[day] = list);
}

// liefert {watt, namen} aller aktiven Ereignisse zur Minute tMin
function eventsAt(tMin) {
  const day = Math.floor(tMin / 1440);
  let watt = 0; const namen = [];
  for (const d of [day - 1, day]) {
    for (const it of eventsOfDay(d)) {
      const tIn = tMin - it.start;
      if (tIn >= 0 && tIn < it.ev.dauer) {
        watt += eventPower(it.ev, tIn, it.uid);
        namen.push(it.ev.typ);
      }
    }
  }
  return { watt: watt, namen: namen };
}

// Echte Haushaltslast zum Teilschritt g, in Bestandteilen
function loadParts(g) {
  const tMin = tMinOf(g);
  const basis = householdLoad(tMin);
  const rausch = slowNoise(tMin) + SCEN.lastzitternW * gaussN(NOISE_SEED, g, "zittern");
  const kuehl = fridge(tMin);
  const evs = eventsAt(tMin);
  const total = Math.max(0, basis + rausch + kuehl + evs.watt);
  return { total, basis, rausch, kuehl, events: evs.watt, namen: evs.namen };
}

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
    lastPassThrough: 0,      // Bypass: PV-Ueberschuss, der zusaetzlich AC-seitig ins Haus/Netz ging
  };
}

const START_SOC = Number(process.env.START_SOC || 50);
// Optional getrennte Start-SOCs, z.B. ein Geraet voll (Bypass), eines halb leer
const START_SOC_SF800 = Number(process.env.START_SOC_SF800 || START_SOC);
const START_SOC_SF2400 = Number(process.env.START_SOC_SF2400 || START_SOC);
const dev0 = makeDevice("MOCKSN-SF800", 4.0, START_SOC_SF800, pv800);
const dev1 = makeDevice("MOCKSN-SF2400", 4.0, START_SOC_SF2400, pv2400);

function socLimitOf(dev) {
  const maxSoc = dev.socSetX10 / 10;
  const minSoc = dev.minSocX10 / 10;
  if (dev.soc >= maxSoc) return 1;
  if (dev.soc <= minSoc) return 2;
  return 0;
}

// Fuehrt STEP_MIN simulierte Minuten fuer ein Geraet aus: PV-Ladung (autonom)
// + AC-Wirkung des zuletzt geschriebenen Kommandos.
// ===============================================================
// GERAETE-VERZOEGERUNG (optional)
// ---------------------------------------------------------------
//   DEVICE_DELAY_S  Sekunden, bis ein Geraet eine neue Vorgabe erreicht
//                   (Default 0 = sofort, wie bisher)
//   DEVICE_RAMP     "linear" (Default): gleitet in DEVICE_DELAY_S auf den
//                   neuen Wert; "step": haelt den alten Wert DEVICE_DELAY_S
//                   lang und springt dann (Totzeit)
//   WRITE_LAG_S     Sekunden zwischen Messung und Ankunft des Schreibbefehls
//                   am Geraet (Default 0). Im echten Betrieb liegen zwischen
//                   dem Messen und dem Schreiben die HTTP-Laufzeiten.
//   DEVICE_RATE_WPS Steigung der Rampe in W/s (Default 0 = aus). Wenn gesetzt,
//                   dauert die Rampe |neu - alt| / DEVICE_RATE_WPS Sekunden und
//                   ersetzt die feste Dauer DEVICE_DELAY_S. Gemessenes Modell
//                   aus echten Logs: WRITE_LAG_S=1.25, DEVICE_RATE_WPS=350,
//                   START_DELAY_S=3.25 (Standby-Start gesamt 4,5 s Totzeit).
//                   Gilt fuer jede Richtung (Abgabe, Laden, Wechsel).
//   START_DELAY_S   zusaetzliche Sekunden, bevor ein Geraet aus dem Standby
//                   (|Leistung| <= START_THRESH_W) mit der Abgabe beginnt
//                   (Default 0 = aus). Echtes Log 15.10.: Start aus 0 W
//                   meist erst im uebernaechsten Takt sichtbar (~4 s mehr).
//                   Gilt nur fuer den Start der Abgabe; der Start des Ladens
//                   ist im Log nicht gemessen und wird nicht verzoegert.
//                   Kommt waehrend der Anlaufzeit ein neuer Befehl, laeuft
//                   die Anlaufzeit weiter (sie beginnt nicht von vorn).
//   START_THRESH_W  Grenze fuer "Standby" in W (Default 5)
// Gerechnet wird in 1-s-Abschnitten (bzw. den Teilschritten des
// Rauschmodells). Gemeldet und vom Zaehler gesehen wird die Leistung am
// Ende des Schritts, fuer SoC und grid_mittel_W zaehlt der Verlauf.
// ===============================================================
const DEV_DELAY_S = Number(process.env.DEVICE_DELAY_S || 0);
const DEV_RAMP = String(process.env.DEVICE_RAMP || "linear").toLowerCase();
const WRITE_LAG_S = Number(process.env.WRITE_LAG_S || 0);
const START_DELAY_S = Number(process.env.START_DELAY_S || 0);
const DEV_RATE = Number(process.env.DEVICE_RATE_WPS || 0);
// REPORT_AGE_S: Das Geraet meldet seine Ist-Leistung (outputHomePower /
// gridInputPower, acMode) mit dieser Verspaetung in Sekunden. Der Zaehler
// zeigt dagegen den aktuellen Stand. SoC, socLimit und alle anderen Felder
// bleiben aktuell. Default 0 = aus (Verhalten wie bisher).
const REPORT_AGE_S = Number(process.env.REPORT_AGE_S || 0);
const START_THRESH_W = Number(process.env.START_THRESH_W || 5);
const DELAY_ON = DEV_DELAY_S > 0 || WRITE_LAG_S > 0 || START_DELAY_S > 0 || DEV_RATE > 0;

// signierte Soll-Leistung aus den geschriebenen Werten (+ Export, - Laden)
function cmdPower(acMode, out, inp) {
  if (acMode === 2) return out || 0;
  if (acMode === 1 && inp > 0) return -inp;
  return 0;
}
// tatsaechlich wirkende Vorgabe zur Simulationssekunde t
function cmdAt(dev, t) {
  const now = cmdPower(dev.acMode, dev.outputLimit, dev.inputLimit);
  const tr = dev.trans;
  if (!tr) return now;
  if (t <= tr.t0) return tr.from;
  if (t >= tr.t1) return tr.to;
  if (DEV_RAMP === "step") return tr.from;
  return tr.from + (tr.to - tr.from) * (t - tr.t0) / (tr.t1 - tr.t0);
}

function advanceDevice(dev, elapsedMin) {
  if (DELAY_ON) return advanceDeviceDelayed(dev, elapsedMin);
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
    // Hybrid-Wechselrichter: ein vorhandener PV-Ueberschuss (Akku voll)
    // deckt das Export-Kommando zuerst, nur der Rest kommt aus dem Akku.
    // Was an PV-Ueberschuss danach noch uebrig ist, geht als Bypass
    // zusaetzlich raus (siehe Grid-Handler) - das Geraet ist im Bypass
    // nicht steuerbar, es liefert mindestens seinen PV-Ueberschuss.
    const fromPv = Math.min(acPower, pvSurplus);
    pvSurplus -= fromPv;
    const maxDeliverableW = Math.max(0, (dev.soc - minSoc) / 100) * dev.capacityKWh * 1000 / dtH;
    const fromBat = Math.min(acPower - fromPv, maxDeliverableW);
    dev.soc -= (fromBat * dtH / 1000 / dev.capacityKWh) * 100;
    delivered = fromPv + fromBat;
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

// Wie advanceDevice, aber die AC-Vorgabe wirkt mit Verzoegerung und wird in
// Abschnitten gerechnet. PV-Ladung wie bisher fuer den ganzen Schritt.
function advanceDeviceDelayed(dev, elapsedMin) {
  const stepSec = elapsedMin * 60;
  const pv = dev.pvFn(simMinute);
  dev.lastPv = pv;
  const maxSoc = dev.socSetX10 / 10;
  const minSoc = dev.minSocX10 / 10;

  let pvSurplus = pv;
  if (dev.soc < maxSoc) {
    const dtHall = elapsedMin / 60;
    const headroomKwh = dev.capacityKWh * (maxSoc - dev.soc) / 100;
    const chg = Math.min(pv, headroomKwh * 1000 / dtHall);
    dev.soc += (chg * dtHall / 1000 / dev.capacityKWh) * 100;
    pvSurplus = pv - chg;
  }

  const nseg = Math.max(SUBS, Math.round(stepSec));
  const segSec = stepSec / nseg;
  const dtH = segSec / 3600;
  const tStart = (stepNo - 1) * STEP_SEC; // stepNo ist bereits erhoeht
  const trace = [];
  let surplusEnd = pvSurplus;

  for (let i = 0; i < nseg; i++) {
    const acPower = cmdAt(dev, tStart + (i + 0.5) * segSec);
    let delivered = 0, rest = pvSurplus;
    if (acPower > 0) {
      const fromPv = Math.min(acPower, pvSurplus);
      rest = pvSurplus - fromPv;
      const maxDeliverableW = Math.max(0, (dev.soc - minSoc) / 100) * dev.capacityKWh * 1000 / dtH;
      const fromBat = Math.min(acPower - fromPv, maxDeliverableW);
      dev.soc -= (fromBat * dtH / 1000 / dev.capacityKWh) * 100;
      delivered = fromPv + fromBat;
    } else if (acPower < 0) {
      const maxAcceptableW = Math.max(0, (maxSoc - dev.soc) / 100) * dev.capacityKWh * 1000 / dtH;
      const chg = Math.min(-acPower, maxAcceptableW);
      dev.soc += (chg * dtH / 1000 / dev.capacityKWh) * 100;
      delivered = -chg;
    }
    dev.soc = Math.max(0, Math.min(100, dev.soc));
    trace.push(delivered);
    surplusEnd = rest;
  }

  if (dev.trans && dev.trans.t1 <= tStart + stepSec) dev.trans = null; // Uebergang abgeschlossen
  dev.acTrace = trace;
  dev.acTraceT0 = tStart;
  dev.acTraceSeg = segSec;
  dev.lastAcPower = trace[nseg - 1];
  return surplusEnd;
}

// AC-Beitrag eines Geraets im Teilschritt j (0..SUBS-1) des aktuellen Schritts
function acAtSub(dev, j) {
  if (!dev.acTrace) return currentAcContribution(dev);
  const n = dev.acTrace.length;
  const idx = Math.min(n - 1, Math.max(0, Math.round((j + 1) * n / SUBS) - 1));
  return dev.acTrace[idx];
}

// ---------------------------------------------------------------
// FIX (Controller ab 5.1.8): Simulationsschritt NICHT mehr an den
// Netz-Poll koppeln. 5.1.8 liest erst die Geraete, dann das Netz.
// Frueher lief der Zeitschritt im Grid-Handler -> Geraete-Ist war
// immer einen Schritt aelter als der Netzwert -> Schwingung.
// Jetzt: ein Schritt passiert, sobald ein Lese-Endpunkt im selben
// Schritt ZUM ZWEITEN MAL abgefragt wird (= neuer Reglerzyklus).
// Damit sehen Geraete-Report und Netzwert immer denselben Zustand,
// egal in welcher Reihenfolge der Controller liest (auch Sparmodus).
// ---------------------------------------------------------------
let servedThisStep = new Set();
let lastGrid = 0;        // echter Netzwert am Messzeitpunkt (Schrittende)
let lastGridMeas = 0;    // an den Controller gemeldeter Wert (mit Messrauschen)
let stepNo = 0;          // ganzzahliger Simulationsschritt (Basis fuer allen Zufall)

// Netzbilanz fuer eine gegebene Haushaltslast (Geraete-AC und PV-Ueberschuss
// sind innerhalb eines Schritts konstant, die Last kann sich aendern).
function gridBalance(load, acSum, surplus0, surplus1) {
  // PV-Ueberschuss wird vom Solarflow-Hybridwechselrichter AC-seitig
  // durchgereicht - aber NUR bis zur Hoehe des aktuellen Hausbedarfs
  // (Selbstverbrauch ist immer erlaubt, unabhaengig von gridReverse).
  // Ueberschuss DARUEBER HINAUS (echte Netzeinspeisung) wird nur
  // durchgereicht, wenn das jeweilige Geraet gridReverse=1 hat.
  const totalSurplus = surplus0 + surplus1;
  const remainingNeed = Math.max(load - acSum, 0);
  const selfConsumed = Math.min(totalSurplus, remainingNeed);
  const leftoverSurplus = totalSurplus - selfConsumed;

  let exportAllowed = 0, verworfen0 = 0, verworfen1 = 0;
  if (totalSurplus > 0 && leftoverSurplus > 0) {
    const share0 = surplus0 / totalSurplus;
    const share1 = surplus1 / totalSurplus;
    const leftover0 = leftoverSurplus * share0;
    const leftover1 = leftoverSurplus * share1;
    if (dev0.gridReverse === 1) exportAllowed += leftover0; else verworfen0 = leftover0;
    if (dev1.gridReverse === 1) exportAllowed += leftover1; else verworfen1 = leftover1;
  }
  const usableSurplus = selfConsumed + exportAllowed;
  return { grid: load - acSum - usableSurplus, verworfen0, verworfen1 };
}

function recompute(elapsed) {
  if (elapsed > 0) { simMinute += elapsed; stepNo++; }

  let surplus0 = 0, surplus1 = 0;
  if (elapsed > 0) {
    surplus0 = advanceDevice(dev0, elapsed);
    surplus1 = advanceDevice(dev1, elapsed);
  }
  const acSum = currentAcContribution(dev0) + currentAcContribution(dev1);

  // Last je Teilschritt. Ohne Rauschmodell: genau ein Wert wie bisher.
  let parts;
  let gridSum = 0, loadSum = 0, n = 0, bal = null;
  const delayed = DELAY_ON && elapsed > 0;
  if (!NOISE_ON) {
    const load = householdLoad(simMinute);
    parts = { total: load, basis: load, rausch: 0, kuehl: 0, events: 0, namen: [] };
    if (delayed && dev0.acTrace && dev1.acTrace) {
      // Mittelwert ueber den Verlauf (fuer grid_mittel_W), Messwert am Ende
      const m = Math.min(dev0.acTrace.length, dev1.acTrace.length);
      for (let i = 0; i < m; i++) {
        gridSum += gridBalance(load, dev0.acTrace[i] + dev1.acTrace[i], surplus0, surplus1).grid; n++;
      }
      loadSum = load * n;
    }
    bal = gridBalance(load, acSum, surplus0, surplus1);
    if (n === 0) { gridSum = bal.grid; loadSum = load; n = 1; }
  } else {
    const gFirst = elapsed > 0 ? (stepNo - 1) * SUBS + 1 : 0;
    const gLast = stepNo * SUBS;
    for (let g = gFirst; g <= gLast; g++) {
      parts = loadParts(g);
      const ac = delayed ? acAtSub(dev0, g - gFirst) + acAtSub(dev1, g - gFirst) : acSum;
      bal = gridBalance(parts.total, ac, surplus0, surplus1);
      gridSum += bal.grid; loadSum += parts.total; n++;
    }
  }

  // Messzeitpunkt = Schrittende (letzter Teilschritt), wie ein echter Zaehler
  dev0.lastPassThrough = Math.max(0, surplus0 - bal.verworfen0);
  dev1.lastPassThrough = Math.max(0, surplus1 - bal.verworfen1);
  lastGrid = bal.grid;
  lastGridMeas = NOISE_ON ? lastGrid + SCEN.messrauschenW * gaussN(NOISE_SEED, stepNo, "meter") : lastGrid;
  if (REPORT_AGE_S > 0) { recordHistory(dev0, delayed); recordHistory(dev1, delayed); }

  log.push({
    t: hhmm(simMinute), minute: Math.round(simMinute * 10000) / 10000,
    haushalt_W: Math.round(parts.total),
    grid_W: Math.round(lastGrid),
    soc_sf800: Math.round(dev0.soc), soc_sf2400: Math.round(dev1.soc),
    pv_sf800: Math.round(dev0.lastPv), pv_sf2400: Math.round(dev1.lastPv),
    ueberschuss_sf800: Math.round(surplus0), ueberschuss_sf2400: Math.round(surplus1),
    verworfen_sf800: Math.round(bal.verworfen0), verworfen_sf2400: Math.round(bal.verworfen1),
    bypass_sf800: Math.round(dev0.lastPassThrough), bypass_sf2400: Math.round(dev1.lastPassThrough),
    acMode_sf800: dev0.acMode, out_sf800: dev0.outputLimit, in_sf800: dev0.inputLimit,
    acMode_sf2400: dev1.acMode, out_sf2400: dev1.outputLimit, in_sf2400: dev1.inputLimit,
    socLimit_sf800: socLimitOf(dev0), socLimit_sf2400: socLimitOf(dev1),
    gridReverse_sf800: dev0.gridReverse, gridReverse_sf2400: dev1.gridReverse,
    // --- Zusatzspalten Rauschmodell (leer/0 ohne NOISE_SEED/SCENARIO) ---
    step: stepNo,
    seed: NOISE_ON ? NOISE_SEED : "",
    last_basis_W: Math.round(parts.basis),
    last_rauschen_W: Math.round(parts.rausch),
    last_kuehl_W: Math.round(parts.kuehl),
    last_events_W: Math.round(parts.events),
    event: parts.namen.join("+"),
    grid_meas_W: Math.round(lastGridMeas),
    grid_mittel_W: Math.round(gridSum / n),     // fuer Energie (Wh) je Schritt
    haushalt_mittel_W: Math.round(loadSum / n),
    ist_sf800: Math.round(dev0.lastAcPower),   // tatsaechliche AC-Leistung am Schrittende
    ist_sf2400: Math.round(dev1.lastAcPower),
    gemeldet_sf800: Math.round(reportedPower(dev0).ac),     // Ist-Leistung, wie gemeldet (bei REPORT_AGE_S aelter)
    gemeldet_sf2400: Math.round(reportedPower(dev1).ac),
  });
}

// Vor jedem Lese-Endpunkt aufrufen
function stepIfNewCycle(endpoint) {
  if (servedThisStep.has(endpoint)) {
    recompute(STEP_MIN);
    servedThisStep.clear();
  }
  servedThisStep.add(endpoint);
}

// Verlauf der tatsaechlichen AC-Leistung je Geraet (fuer REPORT_AGE_S).
// Zeitachse in Simulationssekunden; Schritt k endet bei k * STEP_SEC.
function recordHistory(dev, delayed) {
  if (!dev.hist) dev.hist = [];
  const pass = dev.lastPassThrough;
  if (delayed && dev.acTrace) {
    for (let i = 0; i < dev.acTrace.length; i++) {
      dev.hist.push({ t: dev.acTraceT0 + (i + 1) * dev.acTraceSeg, ac: dev.acTrace[i], pass: pass });
    }
  } else {
    dev.hist.push({ t: stepNo * STEP_SEC, ac: dev.lastAcPower, pass: pass });
  }
  const keepFrom = stepNo * STEP_SEC - REPORT_AGE_S - 2 * STEP_SEC;
  while (dev.hist.length > 1 && dev.hist[1].t < keepFrom) dev.hist.shift();
}
// Ist-Leistung, wie sie das Geraet meldet: Stand von vor REPORT_AGE_S Sekunden
function reportedPower(dev) {
  if (REPORT_AGE_S <= 0 || !dev.hist || !dev.hist.length) return { ac: dev.lastAcPower, pass: dev.lastPassThrough };
  const tq = stepNo * STEP_SEC - REPORT_AGE_S;
  let hit = null;
  for (const h of dev.hist) { if (h.t <= tq + 1e-9) hit = h; else break; }
  return hit ? { ac: hit.ac, pass: hit.pass } : { ac: dev.hist[0].ac, pass: dev.hist[0].pass };
}

function reportJson(dev) {
  const rp = reportedPower(dev);
  // Im Bypass (PV-Ueberschuss wird AC-seitig durchgereicht) steht der
  // Solarflow real im AC-Ausgangsmodus und meldet die gesamte
  // Ausgangsleistung in outputHomePower - unabhaengig vom geschriebenen acMode.
  const bypass = rp.pass > 0;
  // Meldung nach tatsaechlicher Flussrichtung (wichtig waehrend einer
  // verzoegerten Umstellung); ohne Leistungsfluss der geschriebene acMode
  const acMode = bypass ? 2 : (rp.ac > 0 ? 2 : rp.ac < 0 ? 1 : dev.acMode);
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
  // Messrauschen des Geraete-Reports (nur wenn Leistung fliesst; 0 bleibt 0)
  const devNoise = NOISE_ON ? SCEN.geraeteMessrauschenW * gaussN(NOISE_SEED, stepNo, "dev:" + dev.sn) : 0;
  if (acMode === 2) {
    const p = rp.ac + rp.pass;
    props.outputHomePower = p > 0 ? Math.max(0, Math.round(p + devNoise)) : 0;
    props.gridInputPower = 0;
  } else {
    const p = -rp.ac;
    props.outputHomePower = 0;
    props.gridInputPower = p > 0 ? Math.max(0, Math.round(p + devNoise)) : 0;
  }
  return JSON.stringify({ sn: dev.sn, properties: props });
}

// Tatsaechlich gelieferte AC-Leistung (nicht das Kommando): erreicht ein
// Geraet minSoc/maxSoc, sieht der Zaehler nur noch, was wirklich floss.
function currentAcContribution(dev) {
  return dev.lastAcPower;
}

// ---------------------------------------------------------------
// Log-Puffer (fuer die Auswertung nach dem Testlauf)
// ---------------------------------------------------------------
const log = [];
recompute(0); // Startzustand (wie frueher der erste Grid-Poll mit elapsed 0)

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
    stepIfNewCycle("grid");
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ total_power: Math.round(lastGridMeas) }));
    return;
  }

  // ---------------- Geraete lesen ----------------
  if ((path === "/dev0/properties/report" || path === "/dev1/properties/report") && req.method === "GET") {
    const dev = path === "/dev0/properties/report" ? dev0 : dev1;
    stepIfNewCycle(path);
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

      const powerWrite = p.acMode !== undefined || p.outputLimit !== undefined || p.inputLimit !== undefined;
      const tw = stepNo * STEP_SEC + WRITE_LAG_S;           // Simulationssekunde des Eintreffens
      const fromW = DELAY_ON && powerWrite ? cmdAt(dev, tw) : 0;
      if (p.acMode !== undefined) dev.acMode = p.acMode;
      if (p.outputLimit !== undefined) dev.outputLimit = p.outputLimit;
      if (p.inputLimit !== undefined) dev.inputLimit = p.inputLimit;
      if (DELAY_ON && powerWrite) {
        const toW = cmdPower(dev.acMode, dev.outputLimit, dev.inputLimit);
        let starting = START_DELAY_S > 0 && Math.abs(fromW) <= START_THRESH_W && toW > START_THRESH_W;
        let t0 = tw;
        if (starting && dev.trans && dev.trans.start) {
          if (tw < dev.trans.t0) t0 = dev.trans.t0;   // Anlauf laeuft noch: nicht verlaengern
          else starting = false;                      // Anlauf vorbei: Geraet ist wach
        } else if (starting) {
          t0 = tw + START_DELAY_S;
        }
        const rampS = DEV_RATE > 0 ? Math.abs(toW - fromW) / DEV_RATE : DEV_DELAY_S;
        dev.trans = { from: fromW, to: toW, t0: t0, t1: t0 + rampS, start: starting };
      }
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
  console.log("[mock] Geraeteverzoegerung: " + (DELAY_ON
    ? (DEV_RATE > 0 ? "Rampe " + DEV_RATE + " W/s" : DEV_DELAY_S + " s") + " (" + (DEV_RAMP === "step" ? "Totzeit" : "linear") + "), Schreib-Laufzeit " + WRITE_LAG_S + " s" +
      ", Anlauf aus Standby " + (START_DELAY_S > 0 ? "+" + START_DELAY_S + " s (bis " + START_THRESH_W + " W)" : "aus")
    : "aus (Vorgabe wirkt sofort)"));
  console.log("[mock] Geraete-Report: " + (REPORT_AGE_S > 0
    ? "Ist-Leistung " + REPORT_AGE_S + " s alt (Zaehler aktuell)"
    : "aktuell") + " (REPORT_AGE_S=" + REPORT_AGE_S + ")");
  if (!NOISE_ON) {
    console.log("[mock] Rauschmodell: aus (NOISE_SEED/SCENARIO nicht gesetzt)");
  } else {
    console.log("[mock] Rauschmodell: an | Szenario \"" + SCEN.name + "\" | Seed " + NOISE_SEED +
      " | Teilschritt " + SUB_SEC.toFixed(2) + " s (" + SUBS + " je Schritt)" +
      " | Grundrauschen " + SCEN.grundrauschenW + " W | Messrauschen " + SCEN.messrauschenW + " W" +
      " | Geraete-Messrauschen " + SCEN.geraeteMessrauschenW + " W");
    const intervalS = Number(process.env.INTERVAL_MS || 4000) / 1000;
    if (Math.abs(STEP_SEC - intervalS) > 0.01) {
      console.log("[mock] Hinweis: Simulationsschritt " + STEP_SEC.toFixed(2) +
        " s weicht vom Regelintervall " + intervalS + " s ab (STEP_MIN = Intervall in s / 60)");
    }
    const day = Math.floor(START_MIN / 1440);
    for (const it of eventsOfDay(day)) {
      console.log("[mock]   Ereignis Tag " + day + ": " + it.ev.typ + " " + hhmm(it.start) +
        "-" + hhmm(it.start + it.ev.dauer) + " (" + it.ev.dauer + " min)");
    }
  }
});

// Fuer den Runner: Log als JSON auf Signal ausgeben
process.on("SIGUSR2", () => {
  console.log("###LOG_START###");
  console.log(JSON.stringify(log));
  console.log("###LOG_END###");
});

module.exports = { server, log };
