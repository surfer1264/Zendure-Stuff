// Test-Skript fuer die Modus-/Sticky-Logik aus zerooutput_multi.js
// (Konzentration bei Niedriglast, Hysterese, Sticky-Geraeteauswahl,
// langsamer Ausgleich, Sicherheits-Cutoffs, Kapazitaets-Override)
//
// Laeuft mit reinem Node.js, KEINE Hardware noetig:
//   node test_multi_device.js
//
// Die Kernfunktionen (updateMode, pickStickyDevice, computeDischargeWeights,
// computeChargeWeights, waterFillDischarge, waterFillCharge,
// distributeDischarge, distributeCharge, zeroOutputs) sind 1:1 aus dem
// Shelly-Script kopiert - keine Neuimplementierung, damit der Test wirklich
// den ausgelieferten Code prueft und nicht nur eine Nachbildung davon.
//
// Jede Fallgruppe simuliert eine Folge von Zyklen (wie das Script sie alle
// paar Sekunden durchlaeuft) und protokolliert Modus, aktives Geraet,
// Ausgleichs-Zaehler und die berechneten Watt-Werte pro Zyklus.

function print() {
  console.log.apply(console, arguments);
}

let CONFIG = null;
let state = null;
let REBALANCE_HOLD_CYCLES = 1;

// ============================================================
// Auto-extrahierte Kernfunktionen aus zerooutput_multi.js
// (identischer Code wie im Shelly-Script - keine Neuimplementierung)
// ============================================================
function zeroOutputs() {

  let out = [];

  for (let i = 0; i < CONFIG.devices.length; i++) {
    out[i] = 0;
  }

  return out;
}

function updateMode(currentMode, targetMagnitude, cfg) {

  if (currentMode === "single") {

    if (targetMagnitude > cfg.spreadAbove) {
      return "spread";
    }

    return "single";

  }

  if (targetMagnitude < cfg.concentrateBelow) {
    return "single";
  }

  return "spread";

}

function pickStickyDevice(weight, active, selector) {

  let n = weight.length;

  if (selector.active !== null &&
      (!active[selector.active] || weight[selector.active] <= 0)) {
    selector.active = null;
    selector.rebalanceCounter = 0;
  }

  let bestIdx = -1;
  let bestWeight = -1;

  for (let i = 0; i < n; i++) {
    if (active[i] && weight[i] > bestWeight) {
      bestWeight = weight[i];
      bestIdx = i;
    }
  }

  if (selector.active === null) {
    selector.active = bestIdx; // stays -1 if nobody is usable at all
    selector.rebalanceCounter = 0;
    return selector.active;
  }

  if (bestIdx === -1 || bestIdx === selector.active) {
    selector.rebalanceCounter = 0;
    return selector.active;
  }

  let advantage = weight[bestIdx] - weight[selector.active];

  if (advantage >= CONFIG.rebalance.socMargin) {

    selector.rebalanceCounter = selector.rebalanceCounter + 1;

    if (selector.rebalanceCounter >= REBALANCE_HOLD_CYCLES) {

      print("Sanfter Ausgleich: bevorzugtes Geraet wechselt zu " +
        CONFIG.devices[bestIdx].label + " (Vorsprung " +
        Math.round(advantage) + " Prozentpunkte, anhaltend)");

      selector.active = bestIdx;
      selector.rebalanceCounter = 0;

    }

  } else {

    selector.rebalanceCounter = 0;

  }

  return selector.active;

}

function computeDischargeWeights() {

  let n = CONFIG.devices.length;
  let weight = [];
  let active = [];

  for (let i = 0; i < n; i++) {

    if (!state.devices[i].available) {
      weight[i] = 0;
      active[i] = false;
      continue;
    }

    let w = state.devices[i].soc - CONFIG.devices[i].minSoc;
    if (w < 0) w = 0;

    weight[i] = w;
    active[i] = (w > 0);

  }

  return { weight: weight, active: active };

}

function computeChargeWeights() {

  let n = CONFIG.devices.length;
  let weight = [];
  let active = [];

  for (let i = 0; i < n; i++) {

    if (!state.devices[i].available || !CONFIG.devices[i].reverse) {
      weight[i] = 0;
      active[i] = false;
      continue;
    }

    let ds = state.devices[i];
    let cfg = CONFIG.devices[i];

    let w = cfg.maxSoc - ds.soc;
    if (w < 0) w = 0;

    weight[i] = w;
    active[i] = (w > 0);

    if (w === 0) {

      if (!ds.maxSocLogged) {
        print(cfg.label + ": SOC-Obergrenze erreicht (" + ds.soc +
          "% >= " + cfg.maxSoc + "%) - Laden vom Netz gesperrt");
        ds.maxSocLogged = true;
      }

    } else if (ds.maxSocLogged) {

      print(cfg.label + ": SOC wieder unter Obergrenze (" + ds.soc +
        "% < " + cfg.maxSoc + "%) - Laden bei Bedarf wieder moeglich");
      ds.maxSocLogged = false;

    }

  }

  return { weight: weight, active: active };

}

function waterFillDischarge(target, weight, active) {

  let n = weight.length;
  let output = [];

  for (let i = 0; i < n; i++) {
    output[i] = 0;
  }

  let remaining = target;
  let guard = 0;

  while (remaining > 0 && guard <= n) {

    guard++;

    let sumW = 0;
    for (let i = 0; i < n; i++) {
      if (active[i]) sumW += weight[i];
    }

    if (sumW <= 0) break;

    let cappedSomething = false;

    for (let i = 0; i < n; i++) {

      if (!active[i]) continue;

      let share = remaining * weight[i] / sumW;
      let cap = CONFIG.devices[i].maxOutput;

      if (share >= cap) {

        output[i] = cap;
        remaining -= cap;
        active[i] = false;
        cappedSomething = true;

      }

    }

    if (!cappedSomething) {

      for (let i = 0; i < n; i++) {
        if (active[i]) {
          output[i] = remaining * weight[i] / sumW;
        }
      }

      remaining = 0;

    }

  }

  // Defensive floor safety-net: even in spread mode, if the water-filled
  // shares end up smaller than minOutput (e.g. thresholds misconfigured),
  // don't overshoot by flooring every device independently - concentrate
  // on the single best one instead.
  let activeCount = 0;
  let sumMinOutput = 0;
  let bestIdx = -1;
  let bestWeight = -1;

  for (let i = 0; i < n; i++) {
    if (weight[i] > 0) {
      activeCount++;
      sumMinOutput += CONFIG.devices[i].minOutput;
      if (weight[i] > bestWeight) {
        bestWeight = weight[i];
        bestIdx = i;
      }
    }
  }

  if (activeCount > 1 && target < sumMinOutput && bestIdx >= 0) {

    for (let i = 0; i < n; i++) {
      output[i] = 0;
    }

    let o = Math.round(target);

    if (o > 0 && o < CONFIG.devices[bestIdx].minOutput) {
      o = CONFIG.devices[bestIdx].minOutput;
    }

    if (o > CONFIG.devices[bestIdx].maxOutput) {
      o = CONFIG.devices[bestIdx].maxOutput;
    }

    output[bestIdx] = o;

  } else {

    for (let i = 0; i < n; i++) {

      let o = Math.round(output[i]);

      if (o > 0 && o < CONFIG.devices[i].minOutput) {
        o = CONFIG.devices[i].minOutput;
      }

      output[i] = o;

    }

  }

  return output;

}

function waterFillCharge(target, weight, active) {

  let n = weight.length;
  let magnitude = -target;
  let output = [];

  for (let i = 0; i < n; i++) {
    output[i] = 0;
  }

  let remaining = magnitude;
  let guard = 0;

  while (remaining > 0 && guard <= n) {

    guard++;

    let sumW = 0;
    for (let i = 0; i < n; i++) {
      if (active[i]) sumW += weight[i];
    }

    if (sumW <= 0) break;

    let cappedSomething = false;

    for (let i = 0; i < n; i++) {

      if (!active[i]) continue;

      let share = remaining * weight[i] / sumW;
      let cap = CONFIG.devices[i].maxInputPower;

      if (share >= cap) {

        output[i] = cap;
        remaining -= cap;
        active[i] = false;
        cappedSomething = true;

      }

    }

    if (!cappedSomething) {

      for (let i = 0; i < n; i++) {
        if (active[i]) {
          output[i] = remaining * weight[i] / sumW;
        }
      }

      remaining = 0;

    }

  }

  for (let i = 0; i < n; i++) {

    let o = Math.round(output[i]);

    if (o < CONFIG.reverseStopPower) {
      o = 0;
    }

    output[i] = o > 0 ? (o * -1) : 0;

  }

  return output;

}

function distributeDischarge(target) {

  let weights = computeDischargeWeights();
  let weight = weights.weight;
  let active = weights.active;

  state.discharge.mode = updateMode(state.discharge.mode, target, CONFIG.discharge);

  if (state.discharge.mode === "single") {

    let idx = pickStickyDevice(weight, active, state.discharge);

    if (idx === -1) {
      return zeroOutputs(); // nobody has any headroom at all
    }

    if (target <= CONFIG.devices[idx].maxOutput) {

      let output = zeroOutputs();
      let o = Math.round(target);

      if (o > 0 && o < CONFIG.devices[idx].minOutput) {
        o = CONFIG.devices[idx].minOutput;
      }

      output[idx] = o;
      return output;

    }

    // The preferred single device can't cover the target on its own -
    // real necessity overrides the hysteresis, switch to spread NOW.
    print("Ziel uebersteigt maxOutput von " + CONFIG.devices[idx].label +
      " - wechsle sofort in den Mehrere-Geraete-Modus");
    state.discharge.mode = "spread";

  }

  return waterFillDischarge(target, weight, active);

}

function distributeCharge(target) {

  let weights = computeChargeWeights();
  let weight = weights.weight;
  let active = weights.active;
  let magnitude = -target;

  state.charge.mode = updateMode(state.charge.mode, magnitude, CONFIG.charge);

  if (state.charge.mode === "single") {

    let idx = pickStickyDevice(weight, active, state.charge);

    if (idx === -1) {
      return zeroOutputs();
    }

    if (magnitude <= CONFIG.devices[idx].maxInputPower) {

      let output = zeroOutputs();
      let o = Math.round(magnitude);

      if (o < CONFIG.reverseStopPower) {
        o = 0;
      }

      output[idx] = o > 0 ? (o * -1) : 0;
      return output;

    }

    print("Ladebedarf uebersteigt maxInputPower von " + CONFIG.devices[idx].label +
      " - wechsle sofort in den Mehrere-Geraete-Modus");
    state.charge.mode = "spread";

  }

  return waterFillCharge(target, weight, active);

}

// ============================================================
// Test-Infrastruktur
// ============================================================
//
// WICHTIG: Diese Konfigurationen sind vom echten Script (CONFIG in
// zerooutput_multi.js) UNABHAENGIG - sie dienen dazu, gezielt bestimmte
// Faelle zu zeigen (z. B. ein kuenstlich kleines maxInputPower fuer den
// Kapazitaets-Override-Test). Aenderst du Werte im echten Script, merkt
// dieses Testskript nichts davon automatisch.
//
// Willst du DEINE echten Werte pruefen: einfach den Inhalt von
// CONFIG.devices / CONFIG.discharge / CONFIG.charge / CONFIG.rebalance
// aus zerooutput_multi.js hier unten einfuegen (Feldnamen sind absichtlich
// identisch - reines Copy&Paste, keine Anpassung noetig) und Szenarien
// nach Bedarf mit deinen eigenen SOC-Werten/Zielen ergaenzen.
//
// Aenderst du dagegen die LOGIK selbst (updateMode, pickStickyDevice,
// waterFillDischarge/Charge, distributeDischarge/Charge) im echten
// Script, muessen diese Funktionen hier oben neu extrahiert werden -
// sonst testet dieses Skript veralteten Code.

const DEVICES_PROD = [
  { label: "SF800", minSoc: 15, maxOutput: 800, minOutput: 35,
    reverse: true, maxSoc: 100, maxInputPower: 1200 },
  { label: "SF2400Pro", minSoc: 10, maxOutput: 2400, minOutput: 50,
    reverse: false, maxSoc: 100, maxInputPower: 0 }
];

// Testkonfiguration: fuer die Lade-Szenarien duerfen hier AUSNAHMSWEISE
// beide Geraete laden, damit die Sticky-Auswahl auf der Lade-Seite
// ueberhaupt zwischen zwei Kandidaten waehlen kann (in der echten
// Produktivkonfiguration darf nur SF800 laden).
const DEVICES_BOTH_REVERSE = [
  { label: "SF800", minSoc: 15, maxOutput: 800, minOutput: 35,
    reverse: true, maxSoc: 100, maxInputPower: 1200 },
  { label: "SF2400Pro", minSoc: 10, maxOutput: 2400, minOutput: 50,
    reverse: true, maxSoc: 100, maxInputPower: 1500 }
];

// Testkonfiguration mit kuenstlich kleiner Ladeleistung, um den
// Kapazitaets-Override auf der Lade-Seite sauber zu zeigen.
const DEVICES_SMALL_CHARGE = [
  { label: "SF800", minSoc: 15, maxOutput: 800, minOutput: 35,
    reverse: true, maxSoc: 100, maxInputPower: 300 },
  { label: "SF2400Pro", minSoc: 10, maxOutput: 2400, minOutput: 50,
    reverse: false, maxSoc: 100, maxInputPower: 0 }
];

const DISCHARGE_CFG = { concentrateBelow: 800, spreadAbove: 1200 };
const CHARGE_CFG = { concentrateBelow: 400, spreadAbove: 800 };
// holdMinutes klein gehalten, damit sich die Zyklenzahl im Test noch gut
// lesen laesst (bei CONFIG.interval=3000ms -> 20 Zyklen Wartezeit)
const REBALANCE_CFG = { socMargin: 20, holdMinutes: 1 };

function setup(devices, dischargeCfg, chargeCfg) {
  CONFIG = {
    devices: devices,
    discharge: dischargeCfg || DISCHARGE_CFG,
    charge: chargeCfg || CHARGE_CFG,
    rebalance: REBALANCE_CFG,
    interval: 3000,
    reverseStopPower: 10
  };
  REBALANCE_HOLD_CYCLES = Math.max(1,
    Math.round((CONFIG.rebalance.holdMinutes * 60000) / CONFIG.interval));

  state = {
    discharge: { mode: "spread", active: null, rebalanceCounter: 0 },
    charge: { mode: "spread", active: null, rebalanceCounter: 0 },
    devices: []
  };

  for (let i = 0; i < devices.length; i++) {
    state.devices[i] = { soc: 50, available: true, maxSocLogged: false };
  }
}

function activeLabel(selector) {
  return selector.active === null ? "-" : CONFIG.devices[selector.active].label;
}

function fmtOutputs(output) {
  let parts = [];
  for (let i = 0; i < output.length; i++) {
    parts.push(CONFIG.devices[i].label + "=" + output[i] + "W");
  }
  return parts.join(", ");
}

function logDischarge(cycle, target, output) {
  console.log(
    String(cycle).padStart(3) + " | Ziel " + String(target).padStart(5) +
    "W | Modus " + state.discharge.mode.padEnd(6) +
    " | Aktiv " + activeLabel(state.discharge).padEnd(10) +
    " | Zaehler " + String(state.discharge.rebalanceCounter).padStart(2) +
    "/" + REBALANCE_HOLD_CYCLES +
    " | " + fmtOutputs(output)
  );
}

function logCharge(cycle, target, output) {
  console.log(
    String(cycle).padStart(3) + " | Ziel " + String(target).padStart(5) +
    "W | Modus " + state.charge.mode.padEnd(6) +
    " | Aktiv " + activeLabel(state.charge).padEnd(10) +
    " | Zaehler " + String(state.charge.rebalanceCounter).padStart(2) +
    "/" + REBALANCE_HOLD_CYCLES +
    " | " + fmtOutputs(output)
  );
}

// ============================================================
// A) Entladen: Hysterese des Moduswechsels
//    Erwartung: sinkt sofort in "single" (kein Warten fuers Verkleinern),
//    bleibt "single" bis ueber spreadAbove, bleibt dann "spread" bis
//    wieder unter concentrateBelow.
// ============================================================
function scenarioA() {
  console.log("\n=== A) Entladen: Hysterese des Moduswechsels ===");
  setup(DEVICES_PROD);
  state.devices[0].soc = 60;
  state.devices[1].soc = 60;

  let targets = [200, 600, 900, 1000, 1300, 1000, 700, 500, 200];
  for (let c = 0; c < targets.length; c++) {
    let out = distributeDischarge(targets[c]);
    logDischarge(c + 1, targets[c], out);
  }
}

// ============================================================
// B) Entladen: kleiner/schwankender Vorsprung (< socMargin) fuehrt
//    NIE zum Wechsel, egal wie lange er anhaelt.
// ============================================================
function scenarioB() {
  console.log("\n=== B) Entladen: Sticky-Auswahl bleibt stabil bei kleinem Vorsprung (<socMargin) ===");
  setup(DEVICES_PROD);

  for (let c = 0; c < 15; c++) {
    state.devices[0].soc = 50 + (c % 2);       // leichtes Rauschen
    state.devices[1].soc = 58 - (c % 2);       // dauerhaft ca. 8-13 Punkte vorn, aber < socMargin(20)
    let out = distributeDischarge(300);        // bleibt im Single-Bereich
    logDischarge(c + 1, 300, out);
  }
}

// ============================================================
// C) Entladen: grosser, ANHALTENDER Vorsprung fuehrt nach genau
//    REBALANCE_HOLD_CYCLES Zyklen zum Wechsel - nicht frueher.
// ============================================================
function scenarioC() {
  console.log("\n=== C) Entladen: sanfter Ausgleich nach anhaltendem, grossem Vorsprung ===");
  setup(DEVICES_PROD);
  state.devices[0].soc = 80; // SF800 zuerst gewaehlt (hoeheres Gewicht)
  state.devices[1].soc = 50;

  for (let c = 0; c < 5; c++) {
    let out = distributeDischarge(300);
    logDischarge(c + 1, 300, out);
  }

  console.log("  -- SF2400Pro laedt jetzt stark auf, Vorsprung wird gross und bleibt bestehen --");
  state.devices[1].soc = 99; // Gewicht 89 vs. 65 -> Vorsprung 24 >= socMargin(20)

  for (let c = 5; c < 5 + REBALANCE_HOLD_CYCLES + 3; c++) {
    let out = distributeDischarge(300);
    logDischarge(c + 1, 300, out);
  }
}

// ============================================================
// C2) Entladen: Vorsprung flackert um die Marge -> Zaehler resettet
//     sich staendig, es kommt NIE zum Wechsel (kein Punkte-Sammeln).
// ============================================================
function scenarioC2() {
  console.log("\n=== C2) Entladen: flackernder Vorsprung um die Marge -> kein Wechsel (kein Punkte-Sammeln) ===");
  setup(DEVICES_PROD);
  state.devices[0].soc = 80;
  state.devices[1].soc = 50;

  for (let c = 0; c < 30; c++) {
    // Vorsprung pendelt knapp um die Marge (24 / 16 im Wechsel)
    state.devices[1].soc = (c % 2 === 0) ? 99 : 91;
    let out = distributeDischarge(300);
    logDischarge(c + 1, 300, out);
  }
}

// ============================================================
// D) Entladen: aktives Geraet faellt unter minSoc -> SOFORTIGER
//    Wechsel, unabhaengig vom Ausgleichs-Zaehler.
// ============================================================
function scenarioD() {
  console.log("\n=== D) Entladen: aktives Geraet faellt unter minSoc -> sofortiger Wechsel ===");
  setup(DEVICES_PROD);
  state.devices[0].soc = 50; // zuerst gewaehlt (Gewicht 35 vs. 30)
  state.devices[1].soc = 40;

  for (let c = 0; c < 3; c++) {
    let out = distributeDischarge(300);
    logDischarge(c + 1, 300, out);
  }

  console.log("  -- SF800 faellt unter minSoc (15%) --");
  state.devices[0].soc = 12;

  for (let c = 3; c < 6; c++) {
    let out = distributeDischarge(300);
    logDischarge(c + 1, 300, out);
  }
}

// ============================================================
// E) Entladen: gewaehltes Geraet reicht trotz "single"-Modus nicht
//    aus -> sofortiger Wechsel in den Mehrere-Geraete-Modus, auch
//    wenn das Ziel eigentlich noch unter spreadAbove liegt.
// ============================================================
function scenarioE() {
  console.log("\n=== E) Entladen: Kapazitaets-Override (Ziel < spreadAbove, aber > maxOutput des Geraets) ===");
  setup(DEVICES_PROD);
  state.devices[0].soc = 90; // SF800 gewaehlt, maxOutput nur 800W
  state.devices[1].soc = 50;

  for (let c = 0; c < 2; c++) {
    let out = distributeDischarge(300);
    logDischarge(c + 1, 300, out);
  }

  console.log("  -- Bedarf steigt auf 1000W (< spreadAbove 1200W, aber > SF800 maxOutput 800W) --");
  for (let c = 2; c < 4; c++) {
    let out = distributeDischarge(1000);
    logDischarge(c + 1, 1000, out);
  }
}

// ============================================================
// F) Laden: Hysterese + Sticky-Auswahl mit zwei ladefaehigen Geraeten
// ============================================================
function scenarioF() {
  console.log("\n=== F) Laden: Hysterese + Sticky-Auswahl (Testkonfig: beide Geraete duerfen laden) ===");
  setup(DEVICES_BOTH_REVERSE);
  state.devices[0].soc = 50;
  state.devices[1].soc = 30; // mehr Platz nach oben -> zuerst gewaehlt

  let targets = [-100, -300, -500, -600, -900, -600, -300, -100];
  for (let c = 0; c < targets.length; c++) {
    let out = distributeCharge(targets[c]);
    logCharge(c + 1, targets[c], out);
  }
}

// ============================================================
// G) Laden: aktives Geraet erreicht maxSoc -> sofortiger Wechsel
// ============================================================
function scenarioG() {
  console.log("\n=== G) Laden: aktives Geraet erreicht maxSoc -> sofortiger Wechsel ===");
  setup(DEVICES_BOTH_REVERSE);
  state.devices[0].soc = 60;
  state.devices[1].soc = 40; // mehr Platz -> zuerst gewaehlt

  for (let c = 0; c < 3; c++) {
    let out = distributeCharge(-200);
    logCharge(c + 1, -200, out);
  }

  console.log("  -- Geraet 2 (aktiv) erreicht 100% SOC --");
  state.devices[1].soc = 100;

  for (let c = 3; c < 6; c++) {
    let out = distributeCharge(-200);
    logCharge(c + 1, -200, out);
  }
}

// ============================================================
// H) Laden: Kapazitaets-Override (Ladebedarf > maxInputPower des
//    gewaehlten Geraets, obwohl Ziel < spreadAbove ist)
// ============================================================
function scenarioH() {
  console.log("\n=== H) Laden: Kapazitaets-Override (nur SF800 darf laden, kuenstlich kleines maxInputPower) ===");
  setup(DEVICES_SMALL_CHARGE);
  state.devices[0].soc = 50;
  state.devices[1].soc = 50;

  for (let c = 0; c < 2; c++) {
    let out = distributeCharge(-200);
    logCharge(c + 1, -200, out);
  }

  console.log("  -- Ladebedarf 500W (< spreadAbove 800W, aber > SF800 maxInputPower 300W) --");
  for (let c = 2; c < 4; c++) {
    let out = distributeCharge(-500);
    logCharge(c + 1, -500, out);
  }
}

// ============================================================
// I) Realer Aufbau: SF2400 (echtes Geraet) + FATAMORGANA (Dry-Run-
//    Testprofil, gleiche IP wie SF2400) mit den tatsaechlich in
//    multi.js verwendeten Werten (minSoc 15/50, maxOutput 800/1200,
//    Entladen/Laden-Schwellen 60/100 W). Deckt Konzentrationsmodus bei
//    niedrigem Ziel, Wechsel in Wasserfuellung samt minOutput-Floor bei
//    sehr ungleichen Gewichten (44 vs. 9), Sticky-Verhalten beim
//    Zurueckwechseln, sowie auf der Lade-Seite den Ausschluss von
//    SF2400 (reverse:false) und FATAMORGANAs maxSoc-Deckel ab - alles
//    Faelle, die so oder so aehnlich auf der echten Hardware
//    durchgespielt wurden.
// ============================================================
const DEVICES_ACTUAL = [
  { label: "SF2400", minSoc: 15, maxOutput: 800, minOutput: 35,
    reverse: false, maxSoc: 100, maxInputPower: 1200 },
  { label: "FATAMORGANA", minSoc: 50, maxOutput: 1200, minOutput: 35,
    reverse: true, maxSoc: 100, maxInputPower: 1200 }
];

const DISCHARGE_CFG_ACTUAL = { concentrateBelow: 60, spreadAbove: 100 };
const CHARGE_CFG_ACTUAL = { concentrateBelow: 60, spreadAbove: 100 };

function scenarioI_discharge() {
  console.log("\n=== I) Realer Aufbau - Entladen (SOC 59% beide, Schwellen 60/100W) ===");
  setup(DEVICES_ACTUAL, DISCHARGE_CFG_ACTUAL, CHARGE_CFG_ACTUAL);
  state.devices[0].soc = 59; // Gewicht 44 (59-15)
  state.devices[1].soc = 59; // Gewicht  9 (59-50)

  let targets = [40, 150, 90, 50];
  for (let c = 0; c < targets.length; c++) {
    let out = distributeDischarge(targets[c]);
    logDischarge(c + 1, targets[c], out);
  }
  console.log("  (bei 150W: FATAMORGANAs rechnerischer Anteil ~25W liegt unter");
  console.log("   minOutput 35W und wird einzeln hochgerundet - dieselbe Floor-");
  console.log("   Logik, die im Live-Test SF2400=62W/FATAMORGANA=35W bei Ziel 75W ergab)");
}

function scenarioI_charge() {
  console.log("\n=== I) Realer Aufbau - Laden (SOC 61% beide, Schwellen 60/100W) ===");
  setup(DEVICES_ACTUAL, DISCHARGE_CFG_ACTUAL, CHARGE_CFG_ACTUAL);
  state.devices[0].soc = 61;
  state.devices[1].soc = 61; // Gewicht 39 (100-61), einziges reverse:true Geraet

  let targets = [-50, -150];
  for (let c = 0; c < targets.length; c++) {
    let out = distributeCharge(targets[c]);
    logCharge(c + 1, targets[c], out);
  }
  console.log("  (SF2400 bleibt in JEDEM Zyklus bei 0W - reverse:false schliesst");
  console.log("   es in computeChargeWeights() komplett von der Ladeverteilung aus)");

  console.log("  -- FATAMORGANA erreicht maxSoc (100%) --");
  state.devices[1].soc = 100;
  let out = distributeCharge(-100);
  logCharge(targets.length + 1, -100, out);
}

// ============================================================
// Alle Szenarien ausfuehren
// ============================================================

scenarioA();
scenarioB();
scenarioC();
scenarioC2();
scenarioD();
scenarioE();
scenarioF();
scenarioG();
scenarioH();
scenarioI_discharge();
scenarioI_charge();