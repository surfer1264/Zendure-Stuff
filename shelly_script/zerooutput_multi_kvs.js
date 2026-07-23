// Zendure Dynamic Output Controller - Multi-Device Version
// Shelly Gen2/3/4 Script (mJS) fuer das Balancing mehrerer Zendure-Geraete gegen einen Pro 3EM oder generischen JSON-Zaehler
// Alle HTTP-Requests je Geraet sequenziell (kein paralleler Zugriff auf den Shelly)
// Konfiguration erfolgt ausschliesslich im CONFIG-Block unten
// Siehe Projekt-Dokumentation fuer Einrichtung und Hintergrund

let CONFIG = {
  version: "1.2.0 KVS",
  
  devices: [
     {
      ip: "192.168.178.143",   // Zendure IP address
      label: "SF2400",          // short name, used in logs/messages

      minSoc: 18,               // no discharge below this SOC (%)
      maxOutput: 2400,           // max discharge/export power (W)
      minOutput: 35,            // don't bother writing values below this (W)

      reverse: false,            // may this device charge from the grid?
      maxSoc: 100,               // no charging from grid at/above this SOC (%)
      maxInputPower: 2400,       // max charge power from grid (W)

      dryRun: false  
    },
    {
      ip: "192.168.178.143",   // Zendure IP address
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

  // SMARTMETER SECTION
  // Where to read the household grid power from, there are three options 
  gridSource: "local", // "local", "remote", "http_json"
  // ------------------------------------------------------------------
  // ONLY required/used when gridSource = "remote".
  // IP address of the Shelly Pro 3EM providing the grid measurement.
  gridSourceIp: "<IP address of the Shelly Pro 3EM here>",
  // EM channel id to read (usually 0). Only used when gridSource = "remote".
  gridSourceEmId: 0,
  // ------------------------------------------------------------------
  // ONLY requested when gridSource = "http_json". Example is made for the Zendure Smart Meter 3CT, read the DOC for other devices.
  // Full URL of a generic JSON grid meter. Only used when
  gridSourceUrl: "http://<IP-of-your-meter>/properties/report",
  // Name of the JSON field in that response which holds the total grid power in watts
  gridSourceField: "total_power",
  // Set to true if the sign of gridSourceField is inverted compared to what
  // this script expects (positive = importing from grid).
  gridSourceInvert: false,
  
  // ------------------------------------------------------------------
  // RULES ENGINE CORE PARAMETERS
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
  // THRESHOLD SECTION
  // Concentration mode: run only ONE device at low load instead of splitting a small amount across all of them. 
  // Uses hysteresis (two separate thresholds) so the number of active devices doesn't flap
  discharge: {
    concentrateBelow: 600,   // W - below this combined target, use ONE device
    spreadAbove: 800         // W - above this, split across all devices
  },

  charge: {
    concentrateBelow: 600,
    spreadAbove: 800
  },
  // Time-coupled hysteresis for the (only) spread -> single transition.
  concentrateHoldMinutes: 3,


  // ------------------------------------------------------------------
  // SOC BALANCING SECTION
  // Which device is "the one" in concentration mode is sticky (does not
  // re-evaluate every cycle) to avoid rapid switching. It only changes
  // if another device's advantage reaches socMargin percentage points 
  // (immediate switch as well - no hold time).
  rebalance: {
    socMargin: 10        // percentage points of advantage required to switch
  },

  // ------------------------------------------------------------------
  // REVERSE MODE SECTION (charging from the grid) - global hysteresis
  // Minimum charging power in watts required to START charging from the grid. 
  reverseStartupPower: 30,
  // Charging power in watts below which charging from the grid is STOPPED again (must be <= reverseStartupPower).
  reverseStopPower: 10,

  // ------------------------------------------------------------------
  // INTERNAL SECTION BE CAREFUL
  // Update interval (milliseconds)
  interval: 4000,
  // Watchdog timeout in milliseconds (covers the whole cycle: grid read + all device reads + distribution + all device writes)
  watchdog: 10000,
  // Keeping this comfortably shorter than the watchdog (second)   
  httpTimeout: 5,
  // Number of consecutive failures of the same type (per device, or globally for the grid meter / watchdog) before a Signal notification
  errorThreshold: 5,
  // operation to keep the console output clean.
  debug: false,

  // ------------------------------------------------------------------
  // MESSAGE SECTION  via CallMeBot (https://www.callmebot.com/blog/free-api-signal-send-messages/)
  signal: {

    enabled: false,          // set to true to activate Signal notifications
	typ: "SIGNAL",			 // Signal oor WHATSAPP
    phone: "PHONE-STRING",   // e.g. +4917XXXXXXXX
    apiKey: "YOUR_API_KEY"   // your CallMeBot API key

  }
};



if (CONFIG.reverseStopPower > CONFIG.reverseStartupPower) {
  print(
    "reverseStopPower groesser als reverseStartupPower - " +
    "setze beide auf: " + CONFIG.reverseStartupPower
  );

  CONFIG.reverseStopPower = CONFIG.reverseStartupPower;
}

if (CONFIG.discharge.concentrateBelow > CONFIG.discharge.spreadAbove) {
  print("CONFIG.discharge: concentrateBelow > spreadAbove - setze spreadAbove = concentrateBelow");
  CONFIG.discharge.spreadAbove = CONFIG.discharge.concentrateBelow;
}

if (CONFIG.charge.concentrateBelow > CONFIG.charge.spreadAbove) {
  print("CONFIG.charge: concentrateBelow > spreadAbove - setze spreadAbove = concentrateBelow");
  CONFIG.charge.spreadAbove = CONFIG.charge.concentrateBelow;
}

// Hold time (spread -> single) in cycles, derived once from
// concentrateHoldMinutes 
let CONCENTRATE_HOLD_CYCLES = Math.max(
  1,
  Math.round((CONFIG.concentrateHoldMinutes * 60000) / CONFIG.interval)
);

// ------------------------------------------------------------------
// Live parameter overrides via the Shelly's own built-in Key-Value-Store

// Set a value externally via the Shelly's own local RPC, e.g.:
//   POST http://<shelly-ip>/rpc/KVS.Set  {"key":"zdmc_setpoint","value":50}
//
// ------------------------------------------------------------------
let KVS_MATCH = "zdmc_*";

let state = {
  gridPower: 0,
  smoothedOutput: null,
  busy: false,
  watchdogTimer: null,

  cycleId: 0,
  cycleStartedAt: 0,

  errors: { em: 0, watchdog: 0, kvs: 0 },
  notified: { em: false, watchdog: false, kvs: false },

  discharge: { mode: "spread", active: null, holdCycles: 0 },
  charge: { mode: "spread", active: null, holdCycles: 0 },

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
	atMaxSoc: false,

    errors: { connect: 0, json: 0, serial: 0, write: 0 },
    notified: { connect: false, json: false, serial: false, write: false }
  };
}

// ------------------------------------------------------------------
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

// ------------------------------------------------------------------
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

// ------------------------------------------------------------------
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

// ------------------------------------------------------------------
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

// ------------------------------------------------------------------
function debugStale(where, myCycle) {
  if (CONFIG.debug) {
    print("DEBUG " + where + " -> verworfen (Zyklus " + myCycle +
      " veraltet, aktuell ist " + state.cycleId + ")");
  }
}

// ------------------------------------------------------------------
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

// ------------------------------------------------------------------
function unlock(myCycle) {
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

// ------------------------------------------------------------------
// Apply a single KVS override: parses raw into a number, runs it
// through validate(), and only calls apply() if both checks pass.
// Silently keeps the previous CONFIG value on any invalid input.
function applyKvsValue(key, raw, validate, apply) {
  let n = Number(raw);

  if (isNaN(n) || !isFinite(n)) {
    print("KVS " + key + ": ungueltiger Wert '" + raw + "' - ignoriert");
    return;
  }

  if (!validate(n)) {
    print("KVS " + key + ": Wert " + n + " ausserhalb des erlaubten Bereichs - ignoriert");
    return;
  }

  apply(n);
}

// ------------------------------------------------------------------
function readKvsOverrides(myCycle, callback) {
  Shelly.call("KVS.GetMany", { match: KVS_MATCH }, function (res, err_code, err_msg) {
    if (myCycle !== state.cycleId) {
      debugStale("readKvsOverrides", myCycle);
      return;
    }

    if (err_code !== 0 || !res || !res.items) {
      reportError(state.errors, state.notified, "kvs", "KVS",
        "GetMany fehlgeschlagen (" + err_msg + ") - CONFIG unveraendert");

      callback();
      return;
    }

    reportSuccess(state.errors, state.notified, "kvs", "KVS");

    let items = res.items;
    let always = function () { return true; };

    if (items["zdmc_setpoint"]) {
      applyKvsValue("zdmc_setpoint", items["zdmc_setpoint"].value, always,
        function (v) { CONFIG.setpoint = v; });
    }

    if (items["zdmc_hysteresis"]) {
      applyKvsValue("zdmc_hysteresis", items["zdmc_hysteresis"].value,
        function (v) { return v >= 0; },
        function (v) { CONFIG.hysteresis = v; });
    }

    if (items["zdmc_dampingFactor"]) {
      applyKvsValue("zdmc_dampingFactor", items["zdmc_dampingFactor"].value,
        function (v) { return v > 0; },
        function (v) { CONFIG.dampingFactor = v > 1 ? 1 : v; });
    }

    if (items["zdmc_discharge_concentrateBelow"]) {
      applyKvsValue("zdmc_discharge_concentrateBelow", items["zdmc_discharge_concentrateBelow"].value,
        function (v) { return v >= 0; },
        function (v) { CONFIG.discharge.concentrateBelow = v; });
    }

    if (items["zdmc_discharge_spreadAbove"]) {
      applyKvsValue("zdmc_discharge_spreadAbove", items["zdmc_discharge_spreadAbove"].value,
        function (v) { return v >= 0; },
        function (v) { CONFIG.discharge.spreadAbove = v; });
    }

    if (items["zdmc_charge_concentrateBelow"]) {
      applyKvsValue("zdmc_charge_concentrateBelow", items["zdmc_charge_concentrateBelow"].value,
        function (v) { return v >= 0; },
        function (v) { CONFIG.charge.concentrateBelow = v; });
    }

    if (items["zdmc_charge_spreadAbove"]) {
      applyKvsValue("zdmc_charge_spreadAbove", items["zdmc_charge_spreadAbove"].value,
        function (v) { return v >= 0; },
        function (v) { CONFIG.charge.spreadAbove = v; });
    }

    // Re-validate ordering after applying overrides - mirrors the
    // startup checks, in case only one side of a pair got overridden.
    if (CONFIG.discharge.concentrateBelow > CONFIG.discharge.spreadAbove) {
      CONFIG.discharge.spreadAbove = CONFIG.discharge.concentrateBelow;
    }

    if (CONFIG.charge.concentrateBelow > CONFIG.charge.spreadAbove) {
      CONFIG.charge.spreadAbove = CONFIG.charge.concentrateBelow;
    }

    callback();
  });
}

// ------------------------------------------------------------------
// Writes ONE missing default into KVS, then moves to the next pair.
// Sequential on purpose (same pattern as writeAllDevices/syncSocLimitsAll)
// rather than firing all KVS.Set calls at once.
function seedKvsDefaultsStep(pairs, index, callback) {
  if (index >= pairs.length) {
    callback();
    return;
  }

  let pair = pairs[index];

  Shelly.call("KVS.Set", { key: pair.key, value: pair.value }, function (res, err_code, err_msg) {
    if (err_code !== 0) {
      print("KVS-Seed: " + pair.key + " konnte nicht geschrieben werden (" + err_msg + ")");
    } else {
      print("KVS-Seed: " + pair.key + " = " + pair.value + " initial gesetzt");
    }

    seedKvsDefaultsStep(pairs, index + 1, callback);
  });
}

// ------------------------------------------------------------------
// Runs ONCE at startup (not per cycle - KVS is flash-backed, and this
// avoids wearing it out). Reads what's already in KVS and writes the
// current CONFIG default ONLY for keys that don't exist yet - so a
// fresh install ends up with sensible starting values that Home
// Assistant (or curl) can read immediately, while any value a user
// already set externally is never touched/overwritten.
function seedKvsDefaults(callback) {
  Shelly.call("KVS.GetMany", { match: KVS_MATCH }, function (res, err_code, err_msg) {
    if (err_code !== 0 || !res || !res.items) {
      print("KVS-Seed uebersprungen - KVS.GetMany nicht verfuegbar");
      callback();
      return;
    }

    let items = res.items;
    let missing = [];

    if (!items["zdmc_setpoint"])
      missing.push({ key: "zdmc_setpoint", value: CONFIG.setpoint });

    if (!items["zdmc_hysteresis"])
      missing.push({ key: "zdmc_hysteresis", value: CONFIG.hysteresis });

    if (!items["zdmc_dampingFactor"])
      missing.push({ key: "zdmc_dampingFactor", value: CONFIG.dampingFactor });

    if (!items["zdmc_discharge_concentrateBelow"])
      missing.push({ key: "zdmc_discharge_concentrateBelow", value: CONFIG.discharge.concentrateBelow });

    if (!items["zdmc_discharge_spreadAbove"])
      missing.push({ key: "zdmc_discharge_spreadAbove", value: CONFIG.discharge.spreadAbove });

    if (!items["zdmc_charge_concentrateBelow"])
      missing.push({ key: "zdmc_charge_concentrateBelow", value: CONFIG.charge.concentrateBelow });

    if (!items["zdmc_charge_spreadAbove"])
      missing.push({ key: "zdmc_charge_spreadAbove", value: CONFIG.charge.spreadAbove });

    if (missing.length === 0) {
      print("KVS-Seed: alle Keys bereits vorhanden, nichts zu tun");
      callback();
      return;
    }

    print("KVS-Seed: schreibe " + missing.length + " fehlende(n) Default-Wert(e)...");
    seedKvsDefaultsStep(missing, 0, callback);
  });
}

// ------------------------------------------------------------------
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

// ------------------------------------------------------------------
function httpPost(url, body, callback) {
  let bodyStr = JSON.stringify(body);

  if (CONFIG.debug) {
    print("DEBUG httpPost -> url: " + url + " | body: " + bodyStr);
  }

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

// ------------------------------------------------------------------
function handleGenericGridResponse(myCycle, res, meterLabel, field, invert, callback) {
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

  let value;
  let fieldLabel;

  if (typeof field === "string") {

    // Bisheriges Verhalten: flacher Top-Level-Zugriff
    value = data[field];
    fieldLabel = field;

  } else {

    // field ist ein Array aus Schluesseln - verschachtelten Pfad Ebene
    // fuer Ebene ablaufen, z. B. ["StatusSNS", "SML", "Watt_Summe"]
    let current = data;
    fieldLabel = "";

    for (let i = 0; i < field.length; i++) {

      if (i > 0) fieldLabel += ".";
      fieldLabel += field[i];

      if (current === undefined || current === null) {
        current = undefined;
        break;
      }

      current = current[field[i]];

    }

    value = current;

  }

  if (value === undefined) {
    reportError(state.errors, state.notified, "em", meterLabel,
      "Antwort enthaelt kein Feld '" + fieldLabel + "'");

    unlock(myCycle);
    callback(false);
    return;
  }

  reportSuccess(state.errors, state.notified, "em", meterLabel);
  state.gridPower = invert ? (value * -1) : value;

  callback(true);
}

// ------------------------------------------------------------------
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

// ------------------------------------------------------------------
function readDevice(index, myCycle, callback) {
  let cfg = CONFIG.devices[index];
  let ds = state.devices[index];

  httpGet(

    "http://" + cfg.ip + "/properties/report",

    function (res) {
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

      ds.soc = data.properties.electricLevel;
	  ds.atMaxSoc = (ds.soc >= cfg.maxSoc);

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

// ------------------------------------------------------------------
function readAllDevices(index, myCycle, callback) {
  if (index >= CONFIG.devices.length) {
    callback();
    return;
  }

  readDevice(index, myCycle, function () {
    readAllDevices(index + 1, myCycle, callback);
  });
}

// ------------------------------------------------------------------
function zeroOutputs() {
  let out = [];

  for (let i = 0; i < CONFIG.devices.length; i++) {
    out[i] = 0;
  }

  return out;
}

// ------------------------------------------------------------------
function calculate(myCycle) {
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

// ------------------------------------------------------------------
function updateMode(directionState, targetMagnitude, cfg) {
  let currentMode = directionState.mode;

  if (currentMode === "single") {
    if (targetMagnitude > cfg.spreadAbove) {
      directionState.holdCycles = 0; // fresh start for the next spread->single evaluation
      return "spread";
    }

    return "single";
  }

  // currentMode === "spread"

  if (targetMagnitude > cfg.spreadAbove) {
    directionState.holdCycles = 0; // genuine spike back up - reset the hold counter
    return "spread";
  }

  if (targetMagnitude < cfg.concentrateBelow) {
    directionState.holdCycles = directionState.holdCycles + 1;

    if (directionState.holdCycles >= CONCENTRATE_HOLD_CYCLES) {
      directionState.holdCycles = 0;
      return "single";
    }

    return "spread";
  }

  // Dead zone between concentrateBelow and spreadAbove: freeze the
  // counter (neither progress nor reset) and stay in spread mode.
  return "spread";
}

// ------------------------------------------------------------------
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

// ------------------------------------------------------------------
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

// ------------------------------------------------------------------
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

// ------------------------------------------------------------------
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

// ------------------------------------------------------------------
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

// ------------------------------------------------------------------
function distributeDischarge(target) {
  let weights = computeDischargeWeights();
  let weight = weights.weight;
  let active = weights.active;

  state.discharge.mode = updateMode(state.discharge, target, CONFIG.discharge);

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

    print("Ziel uebersteigt maxOutput von " + CONFIG.devices[idx].label +
      " - wechsle sofort in den Mehrere-Geraete-Modus");
    state.discharge.mode = "spread";
    state.discharge.holdCycles = 0;
  }

  return waterFillDischarge(target, weight, active);
}

// ------------------------------------------------------------------
function distributeCharge(target) {
  let weights = computeChargeWeights();
  let weight = weights.weight;
  let active = weights.active;
  let magnitude = -target;

  state.charge.mode = updateMode(state.charge, magnitude, CONFIG.charge);

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
    state.charge.holdCycles = 0;
  }

  return waterFillCharge(target, weight, active);
}

// ------------------------------------------------------------------
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
      ds.outputLimit = output[i];
      print("  " + cfg.label + ": [DRYRUN] wuerde schreiben: " + output[i] +
        " W " + (output[i] >= 0 ? "(Export)" : "(Laden vom Netz)"));
      continue;
    }

    toWrite[toWrite.length] = i;
  }

  if (toWrite.length === 0) {
    unlock(myCycle);
    return;
  }

  Timer.set(0, false, function () {
    if (myCycle !== state.cycleId) {
      debugStale("applyOutputs (nach Timer.set(0))", myCycle);
      return;
    }

    writeAllDevices(toWrite, output, myCycle, 0, function () {
      unlock(myCycle);
    });
  });
}

// ------------------------------------------------------------------
function writeDevice(index, output, myCycle, callback) {
  if (myCycle !== state.cycleId) {
    debugStale("writeDevice(" + CONFIG.devices[index].label + ") vor dem Schreiben", myCycle);
    return;
  }

  let cfg = CONFIG.devices[index];
  let ds = state.devices[index];
  let target = output[index];

  let acMode, outputLimit, inputLimit;

  if (target === 0 && cfg.reverse && ds.atMaxSoc) {
    // Geraet ist untaetig, WEIL es voll ist (SOC >= maxSoc) - bleibt
    // logisch im Eingang/Lade-Modus bei 0 W statt in den Ausgang-Modus
    // zu wechseln (leistungsmaessig identisch, 0 W ist 0 W).
    acMode = 1;
    outputLimit = 0;
    inputLimit = 0;
  } else if (target >= 0) {
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

    function (res, error_code, error_message) {
      if (myCycle !== state.cycleId) {
        debugStale("writeDevice(" + cfg.label + ") Antwort", myCycle);
        return;
      }

      if (res && res.code === 200) {
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

// ------------------------------------------------------------------
function writeAllDevices(indices, output, myCycle, pos, callback) {
  if (pos >= indices.length) {
    callback();
    return;
  }

  writeDevice(indices[pos], output, myCycle, function () {
    writeAllDevices(indices, output, myCycle, pos + 1, callback);
  });
}

// ------------------------------------------------------------------
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

  readKvsOverrides(myCycle, function () {
    readGridPower(myCycle, function (ok) {
      if (!ok) return; // unlock() already called inside readGridPower on failure

      readAllDevices(0, myCycle, function () {
        Timer.set(0, false, function () {
          calculate(myCycle);
        });
      });
    });
  });
}

// ------------------------------------------------------------------
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

// ------------------------------------------------------------------
function syncSocLimitsAll(index, callback) {
  if (index >= CONFIG.devices.length) {
    callback();
    return;
  }

  syncSocLimitsDevice(index, function () {
    syncSocLimitsAll(index + 1, callback);
  });
}

let bannerLines = [];

bannerLines[bannerLines.length] = "--------------------------------";
bannerLines[bannerLines.length] = "Verion " + CONFIG.version;
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
bannerLines[bannerLines.length] = "Konzentrieren-Haltezeit: " +
  CONFIG.concentrateHoldMinutes + " min (" + CONCENTRATE_HOLD_CYCLES +
  " Zyklen) - gilt fuer spread->single, discharge+charge";
bannerLines[bannerLines.length] = "Ausgleich  : ab " + CONFIG.rebalance.socMargin +
  " Prozentpunkten Vorsprung, sofort";
bannerLines[bannerLines.length] = "Reverse Start/Stop: " +
  CONFIG.reverseStartupPower + " W / " + CONFIG.reverseStopPower + " W";
bannerLines[bannerLines.length] = "Err.Thresh : " + CONFIG.errorThreshold;
bannerLines[bannerLines.length] = "Debug      : " + (CONFIG.debug ? "aktiviert" : "deaktiviert");
bannerLines[bannerLines.length] = "Signal     : " + (CONFIG.signal.enabled ? "aktiviert" : "deaktiviert");
bannerLines[bannerLines.length] = "KVS-Live-Override: setpoint/hysteresis/dampingFactor/" +
  "discharge+charge concentrateBelow+spreadAbove (Keys: " + KVS_MATCH + ")";
bannerLines[bannerLines.length] = "--------------------------------";

let bannerIndex = 0;

// ------------------------------------------------------------------
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
    print("SoC-Sync abgeschlossen.");
    print("Pruefe KVS auf fehlende Default-Werte (einmalig)...");

    seedKvsDefaults(function () {
      print("KVS-Seed abgeschlossen - starte Regelbetrieb.");
      print("--------------------------------");

      Timer.set(
        CONFIG.interval,
        true,
        update
      );
    });
  });
});