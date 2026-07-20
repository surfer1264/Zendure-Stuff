// Zendure Dynamic Output Controller - MULTI-DEVICE Version
// Runs on any Shelly Gen2/3 device with scripting support.
// ... And ofc. a lot of AI coding aid was involved ;-)
// ======================================================

let CONFIG = {
  devices: [
     {
      ip: "192.168.178.143",   // Zendure IP address
      label: "SF2400",          // short name, used in logs/messages

      minSoc: 15,               // no discharge below this SOC (%)
      maxOutput: 1200,           // max discharge/export power (W)
      minOutput: 35,            // don't bother writing values below this (W)

      reverse: false,            // may this device charge from the grid?
      maxSoc: 100,               // no charging from grid at/above this SOC (%)
      maxInputPower: 2400,       // max charge power from grid (W)

      dryRun: false  
    },
    {
      ip: "192.168.178.144",   // Zendure IP address
      label: "SF800",          // short name, used in logs/messages

      minSoc: 15,               // no discharge below this SOC (%)
      maxOutput: 800,           // max discharge/export power (W)
      minOutput: 35,            // don't bother writing values below this (W)

      reverse: true,            // may this device charge from the grid?
      maxSoc: 100,               // no charging from grid at/above this SOC (%)
      maxInputPower: 1200,       // max charge power from grid (W)

      dryRun: false              // true = read + calculate only, never write
    },
  ],

  // Where to read the household grid power from:
  // "local"     -> script runs directly on the Shelly Pro 3EM and reads
  // "remote"    -> script runs on ANY other Shelly device
  // "http_json" -> generic: reads the grid power from ANY device that
  gridSource: "local",

  // IP address of the Shelly Pro 3EM providing the grid measurement.
  // Only required/used when gridSource = "remote".
  gridSourceIp: "<IP address of the Shelly Pro 3EM here>",

  // EM channel id to read (usually 0). Only used when gridSource = "remote".
  gridSourceEmId: 0,

  // Full URL of a generic JSON grid meter. Only used when
  // gridSource = "http_json". Example for the Zendure Smart Meter 3CT:
  // "http://192.168.178.150/properties/report"
  gridSourceUrl: "http://<IP-of-your-meter>/properties/report",

  // Name of the JSON field in that response which holds the total grid
  // power in watts. For the Zendure Smart Meter 3CT this is "total_power".
  gridSourceField: "total_power",

  // Set to true if the sign of gridSourceField is inverted compared to what
  // this script expects (positive = importing from grid).
  gridSourceInvert: false,

  // Update interval in milliseconds
  interval: 4000,

  // Watchdog timeout in milliseconds (covers the whole cycle: grid read +
  // all device reads + distribution + all device writes)
  watchdog: 10000,

  // Keeping this comfortably shorter than the
  // watchdog ensures every call is actually resolved (success or
  // failure) well before that can happen.
  httpTimeout: 5,

  // Target grid power in watts (e.g. 0 = balance to zero,
  // negative = slight export, positive = slight import)
  setpoint: 0,

  // Hysteresis in watts, PER DEVICE - minimum change required before a new
  // output value is written to that device (reduces write frequency)
  hysteresis: 10,

  // Damping / gain factor for the COMBINED control signal (0 < factor <= 1),
  // applied before the target is split across devices. See original
  // single-device script for details. 1.0 = no damping, 0.6 = default.
  dampingFactor: 0.6,

  // ------------------------------------------------------------------
  // Uses hysteresis (two separate thresholds) so the number of active devices doesn't flap
  // back and forth around a single value. Between the two thresholds,
  // whichever mode is currently active stays active.
  // ------------------------------------------------------------------
  discharge: {
    concentrateBelow: 2000,   // W - below this combined target, use ONE device
    spreadAbove: 2400        // W - above this, split across all devices
  },

  charge: {
    concentrateBelow: 2000,
    spreadAbove: 2400
  },

  // Which device is "the one" in concentration mode is sticky (does not
  // re-evaluate every cycle) to avoid rapid switching. It only changes
  // if the active device fails, hits its own safety limit (minSoc/maxSoc -
  // immediate switch, no delay), or if another device's advantage reaches
  // socMargin percentage points (immediate switch as well - no hold time).
  rebalance: {
    socMargin: 10        // percentage points of advantage required to switch
  },

  // ------------------------------------------------------------------
  // Reverse mode (charging from the grid) - global hysteresis
  // ------------------------------------------------------------------
  // Minimum charging power in watts required to START charging from
  // the grid. Acts as a deadband so the system doesn't switch into
  // charge mode for a negligible power deficit.
  reverseStartupPower: 30,

  // Charging power in watts below which charging from the grid is
  // STOPPED again (must be <= reverseStartupPower).
  reverseStopPower: 10,

  // Number of consecutive failures of the same type (per device, or
  // globally for the grid meter / watchdog) before a Signal notification
  // is sent (avoids alarm spam on single glitches)
  errorThreshold: 5,

  // Verbose write-request logging (exact outgoing httpPost URL/body, and
  // full res/error_code/error_message on a failed write). Set to true
  // temporarily when diagnosing write problems; leave false for normal
  // operation to keep the console output clean.
  debug: false,

  // Message notifications via CallMeBot (https://www.callmebot.com/blog/free-api-signal-send-messages/)
  signal: {

    enabled: false,          // set to true to activate Signal notifications
	typ: "SIGNAL",			     // Signal oor WHATSAPP
    phone: "PHONE-STRING",   // e.g. +4917XXXXXXXX
    apiKey: "YOUR_API_KEY"   // your CallMeBot API key

  }

};

// Sanity check: the stop threshold must never be larger than the startup
// threshold, otherwise charging would never be able to switch off again.
if (CONFIG.reverseStopPower > CONFIG.reverseStartupPower) {

  print(
    "reverseStopPower groesser als reverseStartupPower - " +
    "setze beide auf: " + CONFIG.reverseStartupPower
  );

  CONFIG.reverseStopPower = CONFIG.reverseStartupPower;

}

// Sanity check: concentrateBelow must not exceed spreadAbove, otherwise the
// hysteresis band is inverted and the mode would flap every cycle.
if (CONFIG.discharge.concentrateBelow > CONFIG.discharge.spreadAbove) {
  print("CONFIG.discharge: concentrateBelow > spreadAbove - setze spreadAbove = concentrateBelow");
  CONFIG.discharge.spreadAbove = CONFIG.discharge.concentrateBelow;
}

if (CONFIG.charge.concentrateBelow > CONFIG.charge.spreadAbove) {
  print("CONFIG.charge: concentrateBelow > spreadAbove - setze spreadAbove = concentrateBelow");
  CONFIG.charge.spreadAbove = CONFIG.charge.concentrateBelow;
}

// ======================================================
// State
// ======================================================

let state = {

  gridPower: 0,
  smoothedOutput: null,
  busy: false,
  watchdogTimer: null,


  cycleId: 0,
  cycleStartedAt: 0,

  // Global error types: "em" (grid meter), "watchdog" (stuck cycle)
  errors: { em: 0, watchdog: 0 },
  notified: { em: false, watchdog: false },

  discharge: { mode: "spread", active: null },
  charge: { mode: "spread", active: null },

  devices: []

};

for (let i = 0; i < CONFIG.devices.length; i++) {

  state.devices[i] = {

    soc: 0,
    serial: null,
    zenPower: 0,        // current signed power flow, from the device's own report
    available: false,   // was this device read successfully THIS cycle?
    outputLimit: null,  // last value written to this device
    maxSocLogged: false,

    // Per-device error types: "connect", "json", "serial", "write"
    errors: { connect: 0, json: 0, serial: 0, write: 0 },
    notified: { connect: false, json: false, serial: false, write: false }

  };

}

// ======================================================
// Signal notifications (CallMeBot)
// ======================================================

function simpleEncode(str) {

  let out = "";

  let map = {
    " ": "%20", "ö": "oe", "ä": "ae", "ü": "ue", "ß": "ss",
    ":": "%3A", "(": "%28", ")": "%29", "\n": "%0A", "%": "%25",
    "°": "%C2%B0", "!": "%21"
  };

  for (let i = 0; i < str.length; i++) {

    let ch = str.charAt(i);
    out += (map[ch] || ch);

  }

  return out;
}

function sendSignalMessage(text) {

  if (!CONFIG.signal.enabled)
    return;

  let safeText = simpleEncode(text);
  let url = "url";

  if (CONFIG.signal.typ == "SIGNAL")
    url = "https://api.callmebot.com/signal/send.php?phone=" + CONFIG.signal.phone + "&apikey=" + CONFIG.signal.apiKey +  "&text=" + safeText;
  else
	url = "https://api.callmebot.com/whatsapp.php?phone=" + CONFIG.signal.phone + "&text=" + safeText + "&apikey=" + CONFIG.signal.apiKey;
		

  print("Sende Signal-Nachricht...");

  Shelly.call(
    "HTTP.GET",
    { url: url, timeout: 15 },
    function (result, error_code, error_msg) {

      if (error_code === 0)
        print("Signal-Nachricht erfolgreich gesendet.");
      else if (error_code === -104)
        print("Signal-Timeout (-104), Nachricht kam vermutlich trotzdem an.");
      else
        print("Fehler beim Senden der Signal-Nachricht: " + error_msg);

    }
  );
}


// ======================================================
// Error / recovery bookkeeping (generic - used both globally and
// per device, by passing the matching errors/notified objects)
// ======================================================

function reportError(errors, notified, type, label, message) {

  errors[type] = errors[type] + 1;

  print(
    "FEHLER (" + label + "/" + type + "): " + message +
    " - aufeinanderfolgende Fehler: " + errors[type]
  );

  if (errors[type] >= CONFIG.errorThreshold && !notified[type]) {

    notified[type] = true;

    sendSignalMessage(
      label + " Fehler (" + type + "): " + message + "\n" +
      errors[type] + " Versuche in Folge fehlgeschlagen."
    );

  }
}

function reportSuccess(errors, notified, type, label) {

  if (errors[type] > 0 || notified[type]) {

    if (notified[type]) {

      sendSignalMessage(
        label + ": Fehler (" + type + ") behoben, laeuft wieder normal."
      );

    }

    errors[type] = 0;
    notified[type] = false;

  }
}

// ======================================================
// Lock handling and watchdog (covers the whole cycle: grid read,
// all device reads, distribution, all device writes)
// ======================================================

// DEBUG-only helper: log that an async response/continuation was
// recognized as belonging to a stale (already-abandoned) cycle and was
// discarded before touching any shared state. Kept as a single helper
// so every guard point logs in the same format.
function debugStale(where, myCycle) {
  if (CONFIG.debug) {
    print("DEBUG " + where + " -> verworfen (Zyklus " + myCycle +
      " veraltet, aktuell ist " + state.cycleId + ")");
  }
}

function lock() {

  state.busy = true;
  state.cycleId = state.cycleId + 1;
  state.cycleStartedAt = Date.now();

  if (CONFIG.debug) {
    print("DEBUG Zyklus " + state.cycleId + " gestartet");
  }

  if (state.watchdogTimer !== null)
    Timer.clear(state.watchdogTimer);

  state.watchdogTimer = Timer.set(
    CONFIG.watchdog,
    false,
    function () {

      reportError(state.errors, state.notified, "watchdog", "System",
        "Zyklus haengengeblieben (Watchdog-Timeout, " +
        (Date.now() - state.cycleStartedAt) + " ms)");

      state.busy = false;
      state.watchdogTimer = null;

    }
  );

  return state.cycleId;

}

function unlock(myCycle) {

  // A stale cycle (one the watchdog already gave up on, whose async
  // chain only completes later) must never touch busy/watchdogTimer -
  // that state belongs to whichever cycle is current NOW, and clearing
  // it out from under a still-running newer cycle would disable its
  // watchdog protection without it actually being done.
  if (myCycle !== state.cycleId) {
    debugStale("unlock", myCycle);
    return;
  }

  if (CONFIG.debug) {
    print("DEBUG Zyklus " + myCycle + " abgeschlossen nach " +
      (Date.now() - state.cycleStartedAt) + " ms");
  }

  reportSuccess(state.errors, state.notified, "watchdog", "System");

  state.busy = false;

  if (state.watchdogTimer !== null) {

    Timer.clear(state.watchdogTimer);
    state.watchdogTimer = null;

  }
}

// ======================================================
// HTTP helper functions
// ======================================================

function httpGet(url, callback) {

  Shelly.call(
    "HTTP.GET",
    {
      url: url,
      timeout: CONFIG.httpTimeout
    },
    callback
  );
}

function httpPost(url, body, callback) {

  let bodyStr = JSON.stringify(body);

  if (CONFIG.debug) {
    print("DEBUG httpPost -> url: " + url + " | body: " + bodyStr);
  }

  // Back to the plain HTTP.Request form (headers + JSON string body) -
  // confirmed correct by an isolated standalone test with the exact same
  // payload. The earlier -103 "Malformed JSON request" errors were never
  // about the request format; they trace to something in multi.js's own
  // execution context (memory pressure, most likely - see the trimmed
  // bannerLines below), not to how the write request is built.
  Shelly.call(
    "HTTP.Request",
    {
      method: "POST",
      url: url,

      headers: {
        "Content-Type": "application/json"
      },

      body: bodyStr,

      timeout: CONFIG.httpTimeout

    },
    callback
  );
}

// ======================================================
// Read grid power - locally (script runs on the Pro 3EM itself),
// remotely from a Shelly Pro 3EM via RPC, or generically from any
// other device (e.g. Zendure Smart Meter 3CT) that returns a flat
// JSON object with a total-power field over plain HTTP GET.
// ======================================================

function handleGenericGridResponse(myCycle, res, meterLabel, field, invert, callback) {

  // Stale cycle (a newer one has already started since this request was
  // sent) - do nothing at all, not even call the callback further.
  if (myCycle !== state.cycleId) {
    debugStale("readGridPower", myCycle);
    return;
  }

  if (!res || res.code !== 200) {

    reportError(state.errors, state.notified, "em", meterLabel, "nicht erreichbar");
    unlock(myCycle);
    callback(false);
    return;

  }

  let data;

  try {

    data = JSON.parse(res.body);

  }

  catch (e) {

    reportError(state.errors, state.notified, "em", meterLabel, "Fehler beim Parsen der Antwort");
    unlock(myCycle);
    callback(false);
    return;

  }

  let value = data[field];

  if (value === undefined) {

    reportError(state.errors, state.notified, "em", meterLabel,
      "Antwort enthaelt kein Feld '" + field + "'");

    unlock(myCycle);
    callback(false);
    return;

  }

  reportSuccess(state.errors, state.notified, "em", meterLabel);
  state.gridPower = invert ? (value * -1) : value;

  callback(true);

}

function readGridPower(myCycle, callback) {

  if (CONFIG.gridSource === "local") {

    let em = Shelly.getComponentStatus("em:" + CONFIG.gridSourceEmId);

    if (!em) {

      reportError(state.errors, state.notified, "em", "Lokaler EM",
        "Kein Messwert verfuegbar (em:" + CONFIG.gridSourceEmId + " nicht gefunden)");

      unlock(myCycle);
      callback(false);
      return;

    }

    reportSuccess(state.errors, state.notified, "em", "Lokaler EM");
    state.gridPower = em.total_act_power;

    callback(true);
    return;

  }

  if (CONFIG.gridSource === "remote") {

    httpGet(

      "http://" + CONFIG.gridSourceIp +
      "/rpc/EM.GetStatus?id=" + CONFIG.gridSourceEmId,

      function (res) {

        handleGenericGridResponse(
          myCycle,
          res,
          "Remote-EM (" + CONFIG.gridSourceIp + ")",
          "total_act_power",
          false,
          callback
        );

      }
    );

    return;

  }

  if (CONFIG.gridSource === "http_json") {

    httpGet(

      CONFIG.gridSourceUrl,

      function (res) {

        handleGenericGridResponse(
          myCycle,
          res,
          "Grid-Meter (" + CONFIG.gridSourceUrl + ")",
          CONFIG.gridSourceField,
          CONFIG.gridSourceInvert,
          callback
        );

      }
    );

    return;

  }

  reportError(state.errors, state.notified, "em", "Konfiguration",
    "Unbekannter CONFIG.gridSource: " + CONFIG.gridSource);

  unlock(myCycle);
  callback(false);

}

// ======================================================
// Read Zendure devices (sequentially, one after another)
// ======================================================

function readDevice(index, myCycle, callback) {

  let cfg = CONFIG.devices[index];
  let ds = state.devices[index];

  httpGet(

    "http://" + cfg.ip + "/properties/report",

    function (res) {

      // Stale cycle - a newer one has already started since this GET was
      // sent. Do not touch ds.* with what could be outdated data, and
      // don't continue the (equally stale) readAllDevices chain either.
      if (myCycle !== state.cycleId) {
        debugStale("readDevice(" + cfg.label + ")", myCycle);
        return;
      }

      if (!res || res.code !== 200) {

        reportError(ds.errors, ds.notified, "connect", cfg.label, "Geraet nicht erreichbar");
        callback();
        return;

      }

      reportSuccess(ds.errors, ds.notified, "connect", cfg.label);

      let data;

      try {

        data = JSON.parse(res.body);

      }

      catch (e) {

        reportError(ds.errors, ds.notified, "json", cfg.label, "Fehler beim Parsen der Antwort");
        callback();
        return;

      }

      reportSuccess(ds.errors, ds.notified, "json", cfg.label);

      if (data.sn) {
        ds.serial = data.sn;
      }

      if (!ds.serial) {

        reportError(ds.errors, ds.notified, "serial", cfg.label, "Keine Seriennummer gefunden");
        callback();
        return;

      }

      reportSuccess(ds.errors, ds.notified, "serial", cfg.label);

      ds.soc = data.packData[0].socLevel;

      // Determine the device's current actual power flow, signed:
      // positive = currently discharging/exporting (acMode 2)
      // negative = currently charging from the grid (acMode 1)
      let acMode = data.properties.acMode;

      if (acMode === 2) {

        ds.zenPower = data.properties.outputHomePower;

      } else if (acMode === 1) {

        ds.zenPower = (data.properties.gridInputPower || 0) * -1;

      } else {

        ds.zenPower = 0;

      }

      ds.available = true;
      callback();

    }
  );
}

function readAllDevices(index, myCycle, callback) {

  if (index >= CONFIG.devices.length) {
    callback();
    return;
  }

  readDevice(index, myCycle, function () {
    readAllDevices(index + 1, myCycle, callback);
  });

}

// ======================================================
// Calculate the combined target and split it across devices
// ======================================================

function zeroOutputs() {

  let out = [];

  for (let i = 0; i < CONFIG.devices.length; i++) {
    out[i] = 0;
  }

  return out;
}

function calculate(myCycle) {

  // Stale cycle (deferred here via Timer.set(0,...) from update() - a
  // newer cycle may have already started in the meantime) - skip
  // entirely rather than recomputing damping/mode/sticky-device off
  // data that a fresher cycle may have already superseded.
  if (myCycle !== state.cycleId) {
    debugStale("calculate", myCycle);
    return;
  }

  let n = CONFIG.devices.length;
  let sumZen = 0;
  let availableCount = 0;

  let countedIps = {};

  for (let i = 0; i < n; i++) {

    if (state.devices[i].available) {

      let ip = CONFIG.devices[i].ip;

      if (!countedIps[ip]) {
        sumZen += state.devices[i].zenPower;
        countedIps[ip] = true;
      }

      availableCount++;
    }

  }

  if (availableCount === 0) {

    print("Kein Geraet erreichbar - Zyklus uebersprungen");
    unlock(myCycle);
    return;

  }

  // Combined (undamped) target power, exactly like the single-device
  // script, just with the SUM of all devices' current power flow.
  let raw = Math.round((state.gridPower - CONFIG.setpoint) + sumZen);

  if (state.smoothedOutput === null) {

    state.smoothedOutput = raw;

  } else {

    state.smoothedOutput =
      state.smoothedOutput + CONFIG.dampingFactor * (raw - state.smoothedOutput);

  }

  let target = Math.round(state.smoothedOutput);

  let anyReverseCapable = false;

  for (let i = 0; i < n; i++) {
    if (CONFIG.devices[i].reverse) {
      anyReverseCapable = true;
    }
  }

  let output;

  if (target >= 0) {

    output = distributeDischarge(target);

  } else if (!anyReverseCapable) {

    // Charging desired but no device allows it -> nothing to do
    output = zeroOutputs();

  } else {

    let alreadyCharging = sumZen < 0;

    if (!alreadyCharging && target > (CONFIG.reverseStartupPower * -1)) {

      output = zeroOutputs();

    } else {

      output = distributeCharge(target);

    }

  }

  print(
    "Grid: " + state.gridPower + " W | Summe Geraete: " + sumZen +
    " W | Kombiniertes Ziel (gedaempft): " + target + " W"
  );

  applyOutputs(output, myCycle);

}

// ======================================================
// Concentration mode: decide whether ONE device or ALL devices should
// be active this cycle, and (if one) WHICH device - with hysteresis on
// both decisions so neither flaps.
// ======================================================

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

// Sticky device selection for concentration mode. `selector` is a small
// persistent object ({ active }), one for discharge and one for charge,
// that survives across cycles. The currently active device keeps being
// used unless it becomes unavailable, hits its own safety limit, or
// another device's advantage reaches socMargin percentage points -
// all three cases switch immediately, no hold/wait time.
function pickStickyDevice(weight, active, selector) {

  let n = weight.length;

  if (selector.active !== null &&
      (!active[selector.active] || weight[selector.active] <= 0)) {
    selector.active = null;
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
    return selector.active;
  }

  if (bestIdx === -1 || bestIdx === selector.active) {
    return selector.active;
  }

  let advantage = weight[bestIdx] - weight[selector.active];

  if (advantage >= CONFIG.rebalance.socMargin) {

    print("Ausgleich: bevorzugtes Geraet wechselt zu " +
      CONFIG.devices[bestIdx].label + " (Vorsprung " +
      Math.round(advantage) + " Prozentpunkte)");

    selector.active = bestIdx;

  }

  return selector.active;

}

// ======================================================
// Weight calculation - identical safety-cutoff semantics as before
// (weight 0 = excluded), factored out so both the mode/sticky decision
// and the water-filling function share exactly the same numbers.
// ======================================================

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

// ======================================================
// Water-filling core (used in "spread" mode, and as the automatic
// fallback when concentration mode's single device can't cover the
// target on its own). Same logic as before, factored to take
// pre-computed weight/active arrays.
// ======================================================

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

// ======================================================
// Top-level distribution entry points, called from calculate(). Decide
// the mode (single/spread) with hysteresis, then either concentrate on
// one sticky device or fall back to full water-filling.
// ======================================================

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

// ======================================================
// Apply the calculated outputs: log, apply per-device hysteresis,
// and write only the devices that actually changed enough.
// ======================================================

function applyOutputs(output, myCycle) {

  let n = CONFIG.devices.length;
  let toWrite = [];

  for (let i = 0; i < n; i++) {

    let ds = state.devices[i];
    let cfg = CONFIG.devices[i];

    print(
      "  " + cfg.label + ": SOC " + (ds.available ? ds.soc + "%" : "n/a") +
      " | Ist " + ds.zenPower + " W | Soll " + output[i] + " W" +
      (cfg.dryRun ? " [DRYRUN - wird nicht geschrieben]" : "")
    );

    if (!ds.available) continue;

    if (ds.outputLimit !== null &&
        Math.abs(output[i] - ds.outputLimit) < CONFIG.hysteresis) {
      continue; // change too small for this device, skip write
    }

    if (cfg.dryRun) {
      // dryRun devices are never actually written, so there's no "confirmed
      // success" to wait for - track the value right here so this line only
      // repeats once it changes enough (same behaviour as before).
      ds.outputLimit = output[i];
      print("  " + cfg.label + ": [DRYRUN] wuerde schreiben: " + output[i] +
        " W " + (output[i] >= 0 ? "(Export)" : "(Laden vom Netz)"));
      continue;
    }

    // NOTE: ds.outputLimit is intentionally NOT set here for real devices
    // anymore. It's only updated in writeDevice() once the write is
    // actually confirmed successful (res.code === 200). This way a failed
    // write gets retried on every following cycle where the target still
    // differs by more than the hysteresis from the value that was truly
    // last applied on the device - instead of being silently skipped
    // because the script wrongly believed the device was already there.
    toWrite[toWrite.length] = i;

  }

  if (toWrite.length === 0) {
    unlock(myCycle);
    return;
  }

  // Deferred via Timer.set(0, ...) instead of calling writeAllDevices()
  // directly: by this point the call stack is already several levels deep
  // (GET-response callback -> readAllDevices -> calculate -> applyOutputs),
  // all still synchronous. Timer.set(0, ...) breaks out into a fresh event
  // loop tick, so the write RPC call fires from a much shallower stack -
  // testing whether stack depth (as opposed to heap, which measured
  // plenty free) is behind the -103 errors.
  Timer.set(0, false, function () {

    // Re-check after the deferral: a newer cycle could have started in
    // this gap too.
    if (myCycle !== state.cycleId) {
      debugStale("applyOutputs (nach Timer.set(0))", myCycle);
      return;
    }

    writeAllDevices(toWrite, output, myCycle, 0, function () {
      unlock(myCycle);
    });

  });


}

// ======================================================
// Write output limit to a Zendure device (sequentially across devices)
// ======================================================

function writeDevice(index, output, myCycle, callback) {

  // Stale cycle - stop the whole writeAllDevices chain right here rather
  // than firing (more) writes derived from outdated calculations. Any
  // write already in flight from before this cycle went stale can't be
  // recalled, but its response will also be caught by the guard below.
  if (myCycle !== state.cycleId) {
    debugStale("writeDevice(" + CONFIG.devices[index].label + ") vor dem Schreiben", myCycle);
    return;
  }

  let cfg = CONFIG.devices[index];
  let ds = state.devices[index];
  let target = output[index];

  let acMode, outputLimit, inputLimit;

  if (target >= 0) {

    acMode = 2;          // discharge / export
    outputLimit = target;
    inputLimit = 0;

  } else {

    acMode = 1;           // charge / import from grid
    outputLimit = 0;
    inputLimit = Math.abs(target);

  }

  httpPost(

    "http://" + cfg.ip + "/properties/write",

    {

      sn: ds.serial,

      properties: {

        acMode: acMode,
        outputLimit: outputLimit,
        inputLimit: inputLimit,
        smartMode: 1

      }
    },

    // Shelly.call() invokes this with (result, error_code, error_message) -
    // capture all three so a failure can actually be diagnosed instead of
    // just being logged as "fehlgeschlagen" with no further detail.
    function (res, error_code, error_message) {

      // Stale by the time the response arrives (a newer cycle started
      // while this write was still in flight) - don't commit outputLimit
      // or continue the chain with data a fresher cycle has superseded.
      if (myCycle !== state.cycleId) {
        debugStale("writeDevice(" + cfg.label + ") Antwort", myCycle);
        return;
      }

      if (res && res.code === 200) {

        // Only NOW - after a confirmed successful write - remember the
        // value as actually applied. This is what makes the per-device
        // hysteresis check in applyOutputs() trustworthy: a failed write
        // will make ds.outputLimit stay at its old value, so the next
        // cycle's differing target will exceed the hysteresis band again
        // and trigger a fresh retry, instead of being silently skipped.
        ds.outputLimit = target;

        print(cfg.label + ": Leistung gesetzt: " + target + " W " +
          (target >= 0 ? "(Export)" : "(Laden vom Netz)"));
        reportSuccess(ds.errors, ds.notified, "write", cfg.label);

      } else {

        if (CONFIG.debug) {
          print(
            "DEBUG " + cfg.label + "/write - res: " + JSON.stringify(res) +
            " | error_code: " + error_code +
            " | error_message: " + error_message
          );
        }

        reportError(ds.errors, ds.notified, "write", cfg.label,
          "Schreibvorgang fehlgeschlagen");

      }

      callback();

    }
  );
}

function writeAllDevices(indices, output, myCycle, pos, callback) {

  if (pos >= indices.length) {
    callback();
    return;
  }

  writeDevice(indices[pos], output, myCycle, function () {
    writeAllDevices(indices, output, myCycle, pos + 1, callback);
  });

}

// ======================================================
// Main control loop
// ======================================================

function update() {

  if (state.busy) {

    print("Vorheriger Zyklus laeuft noch");

    if (CONFIG.debug) {
      print("DEBUG Tick uebersprungen - Zyklus " + state.cycleId +
        " laeuft seit " + (Date.now() - state.cycleStartedAt) + " ms");
    }

    return;

  }

  let myCycle = lock();

  for (let i = 0; i < CONFIG.devices.length; i++) {
    state.devices[i].available = false;
  }

  readGridPower(myCycle, function (ok) {

    if (!ok) return; // unlock() already called inside readGridPower on failure

    readAllDevices(0, myCycle, function () {

      // Deferred via Timer.set(0, ...): calculate() (and everything it
      // calls - distributeDischarge/distributeCharge/waterFillDischarge/
      // waterFillCharge) needs a fair amount of local variables and
      // nested loops, and running it directly inside the last device's
      // GET-response callback was enough to exceed mJS's stack budget on
      // this device (seen as "Too much recursion" the first time the
      // charge/water-fill branch actually ran). Breaking out into a fresh
      // event loop tick here gives it a shallow stack to start from -
      // same fix pattern as the write-path deferral in applyOutputs().
      Timer.set(0, false, function () {
        calculate(myCycle);
      });

    });

  });

}

// ======================================================
// One-time SoC-limit sync (minSoc / socSet) at startup
// ======================================================

function syncSocLimitsDevice(index, callback) {

  let cfg = CONFIG.devices[index];
  let ds = state.devices[index];

  if (cfg.dryRun) {
    print("  " + cfg.label + ": [DRYRUN] SoC-Grenzwerte werden nicht geschrieben");
    callback();
    return;
  }

  httpGet(

    "http://" + cfg.ip + "/properties/report",

    function (res) {

      if (!res || res.code !== 200) {
        print("  " + cfg.label + ": SoC-Sync uebersprungen - Geraet nicht erreichbar");
        callback();
        return;
      }

      let data;

      try {
        data = JSON.parse(res.body);
      } catch (e) {
        print("  " + cfg.label + ": SoC-Sync uebersprungen - Fehler beim Parsen der Antwort");
        callback();
        return;
      }

      if (!data.sn) {
        print("  " + cfg.label + ": SoC-Sync uebersprungen - keine Seriennummer gefunden");
        callback();
        return;
      }

      ds.serial = data.sn;

      // Config values are whole percent, device properties are in
      // per-mille (tenths of a percent) - e.g. 15 % -> 150, 100 % -> 1000.
      let minSocRaw = Math.round(cfg.minSoc * 10);
      let maxSocRaw = Math.round(cfg.maxSoc * 10);

      httpPost(

        "http://" + cfg.ip + "/properties/write",

        {
          sn: ds.serial,
          properties: {
            minSoc: minSocRaw,
            socSet: maxSocRaw
          }
        },

        function (res2, error_code, error_message) {

          if (res2 && res2.code === 200) {

            print("  " + cfg.label + ": SoC-Grenzwerte synchronisiert (minSoc " +
              cfg.minSoc + "%, maxSoc " + cfg.maxSoc + "%)");

          } else {

            if (CONFIG.debug) {
              print(
                "DEBUG " + cfg.label + "/socSync - res: " + JSON.stringify(res2) +
                " | error_code: " + error_code +
                " | error_message: " + error_message
              );
            }

            print("  " + cfg.label + ": SoC-Sync fehlgeschlagen beim Schreiben");

          }

          callback();

        }
      );

    }
  );

}

function syncSocLimitsAll(index, callback) {

  if (index >= CONFIG.devices.length) {
    callback();
    return;
  }

  syncSocLimitsDevice(index, function () {
    syncSocLimitsAll(index + 1, callback);
  });

}

// ======================================================
// Startup
// ======================================================

let bannerLines = [];

bannerLines[bannerLines.length] = "--------------------------------";
bannerLines[bannerLines.length] = "Zendure Multi-Device Controller gestartet";
bannerLines[bannerLines.length] = "Geraete    : " + CONFIG.devices.length;

for (let i = 0; i < CONFIG.devices.length; i++) {

  let cfg = CONFIG.devices[i];

  bannerLines[bannerLines.length] =
    "  - " + cfg.label + " (" + cfg.ip + "): minSoc " + cfg.minSoc +
    "%, maxOutput " + cfg.maxOutput + " W, minOutput " + cfg.minOutput +
    " W, Laden vom Netz " +
    (cfg.reverse
      ? ("ja (maxInput " + cfg.maxInputPower + " W, maxSoc " + cfg.maxSoc + "%)")
      : "nein") +
    (cfg.dryRun ? "  [DRYRUN]" : "");

}

bannerLines[bannerLines.length] = "Grid source: " + CONFIG.gridSource +
  (CONFIG.gridSource === "remote" ? " (" + CONFIG.gridSourceIp + ")" : "") +
  (CONFIG.gridSource === "http_json" ?
    " (" + CONFIG.gridSourceUrl + ", Feld: " + CONFIG.gridSourceField +
    (CONFIG.gridSourceInvert ? ", invertiert" : "") + ")" : "");
bannerLines[bannerLines.length] = "Interval   : " + CONFIG.interval + " ms";
bannerLines[bannerLines.length] = "Watchdog   : " + CONFIG.watchdog + " ms";
bannerLines[bannerLines.length] = "HTTP-Timeout: " + CONFIG.httpTimeout + " s (pro Anfrage)";
bannerLines[bannerLines.length] = "Setpoint   : " + CONFIG.setpoint + " W";
bannerLines[bannerLines.length] = "Hysteresis : " + CONFIG.hysteresis + " W (pro Geraet)";
bannerLines[bannerLines.length] = "Damping    : " + CONFIG.dampingFactor;
bannerLines[bannerLines.length] = "Entladen   : ein Geraet unter " +
  CONFIG.discharge.concentrateBelow + " W, verteilen ueber " +
  CONFIG.discharge.spreadAbove + " W";
bannerLines[bannerLines.length] = "Laden      : ein Geraet unter " +
  CONFIG.charge.concentrateBelow + " W, verteilen ueber " +
  CONFIG.charge.spreadAbove + " W";
bannerLines[bannerLines.length] = "Ausgleich  : ab " + CONFIG.rebalance.socMargin +
  " Prozentpunkten Vorsprung, sofort";
bannerLines[bannerLines.length] = "Reverse Start/Stop: " +
  CONFIG.reverseStartupPower + " W / " + CONFIG.reverseStopPower + " W";
bannerLines[bannerLines.length] = "Err.Thresh : " + CONFIG.errorThreshold;
bannerLines[bannerLines.length] = "Debug      : " + (CONFIG.debug ? "aktiviert" : "deaktiviert");
bannerLines[bannerLines.length] = "Signal     : " + (CONFIG.signal.enabled ? "aktiviert" : "deaktiviert");
bannerLines[bannerLines.length] = "--------------------------------";

let bannerIndex = 0;

function printBannerLine(onDone) {

  if (bannerIndex >= bannerLines.length) {
    bannerLines = null;
    if (onDone) onDone();
    return;
  }

  print(bannerLines[bannerIndex]);
  bannerIndex = bannerIndex + 1;

  Timer.set(150, false, function () {
    printBannerLine(onDone);
  });

}

printBannerLine(function () {

  if (CONFIG.signal.enabled) {
    sendSignalMessage("Zendure Multi-Device-Controller gestartet (" +
      CONFIG.devices.length + " Geraete).");
  }

  print("--------------------------------");
  print("Synchronisiere SoC-Grenzwerte (minSoc/maxSoc) einmalig mit allen Geraeten...");

  syncSocLimitsAll(0, function () {

    print("SoC-Sync abgeschlossen - starte Regelbetrieb.");
    print("--------------------------------");

    Timer.set(
      CONFIG.interval,
      true,
      update
    );

  });

});
