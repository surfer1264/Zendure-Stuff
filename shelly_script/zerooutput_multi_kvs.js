// Zendure Dynamic Output Controller - Multi-Device Version
// Shelly Gen2/3/4 Script (mJS) fuer das Balancing mehrerer Zendure-Geraete gegen einen Pro 3EM oder generischen JSON-Zaehler
// Alle HTTP-Requests je Geraet sequenziell (kein paralleler Zugriff auf den Shelly)
// Konfiguration erfolgt ausschliesslich im CONFIG-Block unten
// Siehe Projekt-Dokumentation fuer Einrichtung und Hintergrund

let CONFIG = {
  version: "2.0.1 KVS (direction change cooldown)",
  
  devices: [
     {
      ip: "192.168.178.143",    // Zendure IP address
      label: "SF2400",          // short name, used in logs/messages

      minSoc: 18,               // no discharge below this SOC (%)
      maxSoc: 100,               // no charging from grid at/above this SOC (%)
      dischargeAllowed: true,   // may this device discharge/export at all? (KVS-live-overridable)
      reverse: true,            // may this device charge from the grid? (KVS-live-overridable)
      maxInputPower: 2400,       // max charge power from grid (W)
      maxOutput: 800,          // max discharge/export power (W)
      
      dryRun: false              // only simulation; true = read + calculate only, never write
    },
    {
      ip: "192.168.178.143",    // Zendure IP address
      label: "Fatamorgana",     // short name, used in logs/messages

      minSoc: 15,               // no discharge below this SOC (%)
      maxSoc: 100,              // no charging from grid at/above this SOC (%)
      dischargeAllowed: false,   // may this device discharge/export at all? (KVS-live-overridable)
      reverse: true,            // may this device charge from the grid? (KVS-live-overridable)
      maxInputPower: 1200,      // max charge power from grid (W)
      maxOutput: 800,           // max discharge/export power (W)

      dryRun: true              // only simulation; true = read + calculate only, never write
    },
  ],
// ------------------------------------------------------------------
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
  setpoint: 0, // (KVS-live-overridable)
  // Hysteresis in watts, PER DEVICE - minimum change required before a new
  // output value is written to that device (reduces write frequency)
  hysteresis: 10, // (KVS-live-overridable)
  // Damping / gain factor for the COMBINED control signal (0 < factor <= 1),
  dampingFactor: 0.6, // (KVS-live-overridable)

  // ------------------------------------------------------------------
  // THRESHOLD SECTION ONLY RELEVANT FOR MULTI DEVICES (more than one Solarflow)
  // Concentration mode: run only ONE device at low load instead of splitting a small amount across all of them. 
  // Uses hysteresis (two separate thresholds) so the number of active devices doesn't flap
  discharge: {
    concentrateBelow: 600,  // W - below this combined target, use ONE device
    spreadAbove: 800        // W - above this, split across all devices
  },

  charge: {
    concentrateBelow: 600,
    spreadAbove: 800
  },
  // Time-coupled hysteresis for the (only) spread -> single transition.
  concentrateHoldMinutes: 3,

  // ------------------------------------------------------------------
  // SOC BALANCING SECTION ONLY RELEVANT FOR MULTI DEVICES (more than one Solarflow)
  // Define the maximum allowed SOC difference between devices in percent points. 
  rebalance: {
    socMargin: 10        // percentage points of advantage required to switch
  },

  // ------------------------------------------------------------------
  // REVERSE MODE SECTION (charging from the grid) - global hysteresis - ONLY relevant for reverse: true (see CONFIG device)
  // Minimum charging power in watts required to START charging from the grid. 
  reverseStartupPower: 30,
  // Charging power in watts below which charging from the grid is STOPPED again (must be <= reverseStartupPower).
  reverseStopPower: 10,

  // ------------------------------------------------------------------
  // DISCHARGE MODE SECTION - globale Start/Stop-Hysterese, spiegelbildlich
  // Minimum discharge/export power in watts required to START discharging.
  dischargeStartupPower: 35,
  // Discharge power in watts below which discharging is STOPPED again (must be <= dischargeStartupPower).
  dischargeStopPower: 15,

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
  // AC-RICHTUNGSWECHSEL SECTION - schuetzt reine AC-ladefaehige Solarflows ohne eigene smarte Umschaltrampe vor zu haeufigem Hin-und-Her
  directionChangeCooldown: 8000,
  // Master switch: KVS-Live-Override an/aus (false = kein KVS.GetMany pro Zyklus/Seeding, Werte fix auf CONFIG)
  kvsEnabled: false,
  // true = JEDER Start ueberschreibt KVS-Werte mit CONFIG (verliert Live-Overrides!) - danach zurueck auf false
  kvsForceReseed: false,
  // operation to keep the console output clean.
  debug: false,

  // ------------------------------------------------------------------
  // MESSAGE SECTION  via CallMeBot (https://www.callmebot.com/blog/free-api-signal-send-messages/)
  signal: {

    enabled: false,          // set to true to activate Signal notifications
	  typ: "SIGNAL",			     // Signal oor WHATSAPP
    phone: "PHONE-STRING",   // e.g. +4917XXXXXXXX
    apiKey: "YOUR_API_KEY"   // your CallMeBot API key

  }
};

// Plausibilitaets-Checks fuer CONFIG (einmalig beim Start) - Endwerte
// werden im Banner ausgegeben, daher hier keine eigenen Printouts.
function checkBand(band) {
  if (band.concentrateBelow < 35) band.concentrateBelow = 35;
  if (band.spreadAbove < 50) band.spreadAbove = 50;
  if (band.concentrateBelow >= band.spreadAbove) band.spreadAbove = band.concentrateBelow +15 ;
}

if (CONFIG.interval < 2500) CONFIG.interval = 2500;
if (CONFIG.watchdog < CONFIG.interval * 2.5) CONFIG.watchdog = CONFIG.interval * 2.5;
if (CONFIG.dampingFactor < 0.1) CONFIG.dampingFactor = 0.1;
if (CONFIG.dampingFactor > 1) CONFIG.dampingFactor = 1;
if (CONFIG.setpoint < -50) CONFIG.setpoint = -50;
if (CONFIG.setpoint > 50) CONFIG.setpoint = 50;
if (CONFIG.hysteresis >50) CONFIG.hysteresis = 50;
if (CONFIG.hysteresis < 5) CONFIG.hysteresis = 5;
if (CONFIG.rebalance.socMargin < 3) CONFIG.rebalance.socMargin = 3;
if (CONFIG.rebalance.socMargin > 25) CONFIG.rebalance.socMargin = 25;

checkBand(CONFIG.discharge);
checkBand(CONFIG.charge);

if (CONFIG.reverseStopPower >= CONFIG.reverseStartupPower) {  CONFIG.reverseStartupPower = CONFIG.reverseStopPower + 10; }

if (CONFIG.dischargeStopPower < 0) CONFIG.dischargeStopPower = 0;
if (CONFIG.dischargeStopPower >= CONFIG.dischargeStartupPower) { CONFIG.dischargeStartupPower = CONFIG.dischargeStopPower + 10; }

if (CONFIG.directionChangeCooldown < 0) CONFIG.directionChangeCooldown = 0;
if (CONFIG.directionChangeCooldown > 0 && CONFIG.directionChangeCooldown < CONFIG.interval * 1.5) {CONFIG.directionChangeCooldown = CONFIG.interval * 1.5;}

// Hold time (spread -> single) in cycles, derived once from
// concentrateHoldMinutes 
let CONCENTRATE_HOLD_CYCLES = Math.max(
  1,
  Math.round((CONFIG.concentrateHoldMinutes * 60000) / CONFIG.interval)
);

// Live parameter overrides via the Shelly's own built-in Key-Value-Store
// POST http://<shelly-ip>/rpc/KVS.Set  {"key":"zdmc_setpoint","value":50}
// Per-device keys use the device's array index (see banner "[devN]"), e.g.:
// POST .../rpc/KVS.Set  {"key":"zdmc_dev0_dischargeAllowed","value":0}  // 1 = erlaubt, 0 = gesperrt
// POST .../rpc/KVS.Set  {"key":"zdmc_dev0_reverse","value":1}          // 1 = erlaubt, 0 = gesperrt
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

  discharge: { mode: "single", active: null, holdCycles: 0 },
  charge: { mode: "single", active: null, holdCycles: 0 },

  devices: []
};

for (let i = 0; i < CONFIG.devices.length; i++) {
  state.devices[i] = {
    soc: 0,
    serial: null,
    zenPower: 0,        // current signed power flow, from the device's own report
    available: false,   // was this device read successfully THIS cycle?
    outputLimit: null,  // last EFFEKTIV geschriebene signierte Leistung (nach Cooldown, falls aktiv)
    maxSocLogged: false,
	atMaxSoc: false,

    acMode: null,          // zuletzt tatsaechlich geschriebener/simulierter acMode (1=Laden/Idle, 2=Entladen)
    acModeChangedAt: 0,    // Zeitpunkt (Date.now()) des letzten ECHTEN Richtungswechsels

    errors: { connect: 0, json: 0, serial: 0, write: 0 },
    notified: { connect: false, json: false, serial: false, write: false }
  };
}

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

// Normalizes the "items" field returned by KVS.GetMany into a plain {key: {value, etag}} lookup map. 
function kvsItemsToMap(rawItems) {
  let map = {};

  if (!rawItems) return map;

  if (Array.isArray(rawItems)) {
    for (let idx = 0; idx < rawItems.length; idx++) {
      let entry = rawItems[idx];
      if (entry && entry.key !== undefined) {
        map[entry.key] = entry;
      }
    }
  } else {
    // already an object keyed by KVS key name
    map = rawItems;
  }

  return map;
}

// Apply a single KVS override: parses raw into a number, runs it
// through validate(), and only calls apply() if both checks pass.
function applyKvsValue(key, raw, currentValue, validate, apply) {
  let n = Number(raw);

  if (isNaN(n) || !isFinite(n)) {
    if (CONFIG.debug) print("KVS " + key + ": ungueltiger Wert '" + raw + "' - ignoriert");
    return;
  }

  if (!validate(n)) {
    if (CONFIG.debug) print("KVS " + key + ": Wert " + n + " ausserhalb des erlaubten Bereichs - ignoriert");
    return;
  }

  if (CONFIG.debug && n !== currentValue) {
    print("KVS " + key + ": Wert uebernommen (" + currentValue + " -> " + n + ")");
  }

  apply(n);
}

function readKvsOverrides(myCycle, callback) {
  if (!CONFIG.kvsEnabled) {
    callback();
    return;
  }

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

    if (CONFIG.debug && res.total !== undefined &&
        Array.isArray(res.items) && res.total > res.items.length) {
      print("DEBUG KVS.GetMany: nur " + res.items.length + " von " +
        res.total + " passenden Eintraegen erhalten (Pagination?) - " +
        "ggf. Offset-Handling ergaenzen");
    }

    let items = kvsItemsToMap(res.items);
    let always = function () { return true; };

    if (items["zdmc_setpoint"]) {
      applyKvsValue("zdmc_setpoint", items["zdmc_setpoint"].value, CONFIG.setpoint,
      function (v) { return v >= -50 && v <= 50; },
      function (v) { CONFIG.setpoint = v; });
    }

    if (items["zdmc_hysteresis"]) {
      applyKvsValue("zdmc_hysteresis", items["zdmc_hysteresis"].value, CONFIG.hysteresis,
      function (v) { return v >= 5 && v <= 50; },
      function (v) { CONFIG.hysteresis = v; });
    }

    if (items["zdmc_dampingFactor"]) {
      applyKvsValue("zdmc_dampingFactor", items["zdmc_dampingFactor"].value, CONFIG.dampingFactor,
        function (v) { return v >= 0.1 && v <= 1; },
        function (v) { CONFIG.dampingFactor = v; });
    }

    for (let i = 0; i < CONFIG.devices.length; i++) {
      let dev = CONFIG.devices[i];

      let dischargeKey = "zdmc_dev" + i + "_dischargeAllowed";
      if (items[dischargeKey]) {
        applyKvsValue(dischargeKey, items[dischargeKey].value,
          (dev.dischargeAllowed === false ? 0 : 1),
          function (v) { return v === 0 || v === 1; },
          function (v) { dev.dischargeAllowed = (v !== 0); });
      }

      let reverseKey = "zdmc_dev" + i + "_reverse";
      if (items[reverseKey]) {
        applyKvsValue(reverseKey, items[reverseKey].value,
          (dev.reverse ? 1 : 0),
          function (v) { return v === 0 || v === 1; },
          function (v) { dev.reverse = (v !== 0); });
      }
    }

    callback();
  });
}

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
    } else if (CONFIG.debug) {
      print("KVS-Seed: " + pair.key + " = " + pair.value + " initial gesetzt");
    }

    seedKvsDefaultsStep(pairs, index + 1, callback);
  });
}

// Runs ONCE at startup (not per cycle - KVS is flash-backed, and this
// avoids wearing it out). By default (CONFIG.kvsForceReseed === false)
function seedKvsDefaults(callback) {
  if (!CONFIG.kvsEnabled) {
    print("KVS-Seed uebersprungen - kvsEnabled: false");
    callback();
    return;
  }

  Shelly.call("KVS.GetMany", { match: KVS_MATCH }, function (res, err_code, err_msg) {
    if (err_code !== 0 || !res || !res.items) {
      print("KVS-Seed uebersprungen - KVS.GetMany nicht verfuegbar");
      callback();
      return;
    }

    let items = kvsItemsToMap(res.items);
    let pairs = [];

    function addPair(key, value) {
      if (CONFIG.kvsForceReseed || !items[key]) {
        pairs.push({ key: key, value: value });
      }
    }

    addPair("zdmc_setpoint", CONFIG.setpoint);
    addPair("zdmc_hysteresis", CONFIG.hysteresis);
    addPair("zdmc_dampingFactor", CONFIG.dampingFactor);

    for (let i = 0; i < CONFIG.devices.length; i++) {
      addPair("zdmc_dev" + i + "_dischargeAllowed",
        CONFIG.devices[i].dischargeAllowed === false ? 0 : 1);
      addPair("zdmc_dev" + i + "_reverse",
        CONFIG.devices[i].reverse ? 1 : 0);
    }

    if (pairs.length === 0) {
      if (CONFIG.debug) print("KVS-Seed: alle Keys bereits vorhanden, nichts zu tun");
      callback();
      return;
    }

    if (CONFIG.kvsForceReseed) {
      print("KVS-Seed: kvsForceReseed aktiv - schreibe " + pairs.length +
        " Wert(e) aus CONFIG (bestehende Live-Overrides werden ueberschrieben!)");
    } else {
      print("KVS-Seed: schreibe " + pairs.length + " fehlende(n) Default-Wert(e)...");
    }

    seedKvsDefaultsStep(pairs, 0, callback);
  });
}

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

function readAllDevices(index, myCycle, callback) {
  if (index >= CONFIG.devices.length) {
    callback();
    return;
  }

  readDevice(index, myCycle, function () {
    readAllDevices(index + 1, myCycle, callback);
  });
}

function zeroOutputs() {
  let out = [];

  for (let i = 0; i < CONFIG.devices.length; i++) {
    out[i] = 0;
  }

  return out;
}

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
    let alreadyDischarging = sumZen > 0;

    if (!alreadyDischarging && target < CONFIG.dischargeStartupPower) {
      output = zeroOutputs();
    } else {
      output = distributeDischarge(target);
    }
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

function computeDischargeWeights() {
  let n = CONFIG.devices.length;
  let weight = [];
  let active = [];

  for (let i = 0; i < n; i++) {
    if (!state.devices[i].available || CONFIG.devices[i].dischargeAllowed === false) {
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

  // Analog zu waterFillCharge: pro Geraet einfach auf 0 setzen, wenn der
  // zugewiesene Anteil unter der globalen Stop-Schwelle liegt - Ein Geraet laeuft
  // entweder mit sinnvoller Leistung oder gar nicht.
  for (let i = 0; i < n; i++) {
    let o = Math.round(output[i]);

    if (o < CONFIG.dischargeStopPower) {
      o = 0;
    }

    output[i] = o;
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

  state.discharge.mode = updateMode(state.discharge, target, CONFIG.discharge);

  if (state.discharge.mode === "single") {
    let idx = pickStickyDevice(weight, active, state.discharge);

    if (idx === -1) {
      return zeroOutputs(); // nobody has any headroom at all
    }

    if (target <= CONFIG.devices[idx].maxOutput) {
      let output = zeroOutputs();
      let o = Math.round(target);

      if (o < CONFIG.dischargeStopPower) {
        o = 0;
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

// Ermittelt acMode/outputLimit/inputLimit aus dem Zielwert - zentrale
// Stelle, damit Print (Vorschau in applyOutputs) und tatsaechlicher
// Write (writeDevice) garantiert dieselbe Logik verwenden.
function planWrite(target, cfg, ds) {
  if (target === 0 && cfg.reverse && ds.atMaxSoc) {
    // Geraet ist untaetig, WEIL es voll ist (SOC >= maxSoc) - bleibt
    // logisch im Eingang/Lade-Modus bei 0 W statt in den Ausgang-Modus
    // zu wechseln (leistungsmaessig identisch, 0 W ist 0 W).
    return { acMode: 1, outputLimit: 0, inputLimit: 0 };
  }

  if (target >= 0) {
    return { acMode: 2, outputLimit: target, inputLimit: 0 }; // discharge / export
  }

  return { acMode: 1, outputLimit: 0, inputLimit: Math.abs(target) }; // charge / import from grid
}

function acModeLabel(acMode) {
  return acMode === 2 ? "Export" : "Import/Idle";
}

// Signierte Leistung, die ein plan-Objekt tatsaechlich am Geraet bewirkt -
// Gegenstueck zu planWrite(): bei acMode 2 ist das +outputLimit (Export),
// bei acMode 1 ist es -inputLimit (Import) bzw. 0 (Idle/voll). Wird als
// "letzter effektiv geschriebener Wert" in ds.outputLimit gespeichert,
// damit die Hysteresis-Pruefung in applyOutputs() immer gegen das vergleicht,
// was WIRKLICH zuletzt geschrieben wurde - nicht gegen den rohen,
// moeglicherweise vom Cooldown ueberschriebenen Zielwert.
function planSignedPower(plan) {
  return plan.acMode === 2 ? plan.outputLimit : (plan.inputLimit * -1);
}

// Verhindert zu haeufige acMode-Wechsel (Laden<->Entladen) an EINEM Geraet.
// Greift nur, wenn plan.acMode vom zuletzt geschriebenen/simulierten
// ds.acMode abweicht UND CONFIG.directionChangeCooldown seit dem letzten
// echten Wechsel noch nicht abgelaufen ist. In diesem Fall wird die ALTE
// Richtung mit 0 W gehalten (kein Umschalten, aber auch kein Leistungsfluss
// in die neue Richtung), bis die Sperrzeit abgelaufen ist.
function enforceDirectionCooldown(plan, ds, now) {
  if (CONFIG.directionChangeCooldown <= 0) return plan;
  if (ds.acMode === null) return plan;              // noch nie geschrieben - nichts zu vergleichen
  if (plan.acMode === ds.acMode) return plan;        // keine Richtungsaenderung angefordert

  let elapsed = now - ds.acModeChangedAt;
  if (elapsed >= CONFIG.directionChangeCooldown) return plan; // Sperrzeit abgelaufen, Wechsel erlaubt

  if (CONFIG.debug) {
    print("Cooldown aktiv (" + Math.round((CONFIG.directionChangeCooldown - elapsed) / 1000) +
      "s verbleibend) - Richtungswechsel blockiert, halte " + acModeLabel(ds.acMode));
  }

  return { acMode: ds.acMode, outputLimit: 0, inputLimit: 0 };
}

function applyOutputs(output, myCycle) {
  let n = CONFIG.devices.length;
  let toWrite = [];
  let now = Date.now(); // einheitlicher Zeitpunkt fuer die Cooldown-Vorschau dieses Zyklus

  for (let i = 0; i < n; i++) {
    let ds = state.devices[i];
    let cfg = CONFIG.devices[i];

    let rawPlan = planWrite(output[i], cfg, ds);
    let plan = enforceDirectionCooldown(rawPlan, ds, now);
    let signedPower = planSignedPower(plan);

    print(
      "  " + cfg.label + ": SOC " + (ds.available ? ds.soc + "%" : "n/a") +
      " | Ist " + ds.zenPower + " W | Soll " + output[i] + " W" +
      " | acMode " + plan.acMode + " (" + acModeLabel(plan.acMode) + ")" +
      (plan.acMode !== rawPlan.acMode ? " [Cooldown haelt Richtung]" : "") +
      (cfg.dryRun ? " [DRYRUN - wird nicht geschrieben]" : "")
    );

    if (!ds.available) continue;

    if (ds.outputLimit !== null &&
        Math.abs(signedPower - ds.outputLimit) < CONFIG.hysteresis) {
      continue; // effektiv geschriebener Wert wuerde sich kaum aendern - Schreibvorgang ueberspringen
    }

    if (cfg.dryRun) {
      if (ds.acMode === null || ds.acMode !== plan.acMode) {
        ds.acModeChangedAt = now;
      }
      ds.acMode = plan.acMode;
      ds.outputLimit = signedPower;

      print("  " + cfg.label + ": [DRYRUN] wuerde schreiben: " + signedPower +
        " W " + (signedPower >= 0 ? "(Export)" : "(Laden vom Netz)"));
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

function writeDevice(index, output, myCycle, callback) {
  if (myCycle !== state.cycleId) {
    debugStale("writeDevice(" + CONFIG.devices[index].label + ") vor dem Schreiben", myCycle);
    return;
  }

  let cfg = CONFIG.devices[index];
  let ds = state.devices[index];
  let target = output[index];

  let plan = planWrite(target, cfg, ds);
  plan = enforceDirectionCooldown(plan, ds, Date.now()); // frischer Zeitpunkt, moeglichst nah am echten Schreibvorgang

  let acMode = plan.acMode;
  let outputLimit = plan.outputLimit;
  let inputLimit = plan.inputLimit;
  let signedPower = planSignedPower(plan);

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
        if (ds.acMode === null || ds.acMode !== acMode) {
          ds.acModeChangedAt = Date.now();
        }
        ds.acMode = acMode;
        ds.outputLimit = signedPower;

        print(cfg.label + ": Leistung gesetzt: " + signedPower + " W " +
          (signedPower >= 0 ? "(Export)" : "(Laden vom Netz)"));
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

function syncSocLimitsDevice(index, callback) {
  let cfg = CONFIG.devices[index];
  let ds = state.devices[index];

  if (cfg.dryRun) {
    print("  " + cfg.label + ": [DRYRUN] SoC-Grenzwerte werden nicht geschrieben");

    // WICHTIG: callback() NICHT synchron aufrufen - bei mehreren
    // aufeinanderfolgenden dryRun-Geraeten wuerde sich syncSocLimitsAll()
    // sonst rein synchron immer tiefer verschachteln (kein echter HTTP-Call,
    // der den Stack zwischendurch ueber den Event-Loop abbaut) und den
    // flachen nativen mJS-Stack zum Ueberlaufen bringen ("Too much
    // recursion"). Timer.set(0, ...) erzwingt denselben Event-Loop-Sprung,
    // den ein echtes Geraet automatisch durch seinen HTTP-Callback bekommt.
    Timer.set(0, false, callback);
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
    "  - [dev" + i + "] " + cfg.label + " (" + cfg.ip + "): Entladen " +
    (cfg.dischargeAllowed === false ? "nein" : "ja") +
    ", minSoc " + cfg.minSoc +
    "%, maxOutput " + cfg.maxOutput + " W, Laden vom Netz " +
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
bannerLines[bannerLines.length] = "Discharge Start/Stop: " +
  CONFIG.dischargeStartupPower + " W / " + CONFIG.dischargeStopPower + " W";
bannerLines[bannerLines.length] = "Richtungswechsel-Cooldown: " +
  (CONFIG.directionChangeCooldown > 0 ?
    (CONFIG.directionChangeCooldown / 1000) + " s (pro Geraet)" : "deaktiviert");
bannerLines[bannerLines.length] = "Err.Thresh : " + CONFIG.errorThreshold;
bannerLines[bannerLines.length] = "Debug      : " + (CONFIG.debug ? "aktiviert" : "deaktiviert");
bannerLines[bannerLines.length] = "Signal     : " + (CONFIG.signal.enabled ? "aktiviert" : "deaktiviert");
bannerLines[bannerLines.length] = "KVS-Feature: " + (CONFIG.kvsEnabled ? "aktiviert" : "DEAKTIVIERT (kein Live-Override, kein Seeding)");

if (CONFIG.kvsEnabled) {
  bannerLines[bannerLines.length] = "KVS-Live-Override: setpoint/hysteresis/dampingFactor/" +
    "dev{n}_dischargeAllowed/dev{n}_reverse (Keys: " + KVS_MATCH + ")";
  bannerLines[bannerLines.length] = "KVS-Force-Reseed  : " + (CONFIG.kvsForceReseed ?
    "AKTIV - ueberschreibt bei JEDEM Start alle Live-Overrides mit CONFIG!" :
    "aus (Standard, empfohlen)");
}

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