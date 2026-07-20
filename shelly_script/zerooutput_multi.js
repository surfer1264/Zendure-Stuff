// Zendure Dynamic Output Controller - MULTI-DEVICE Version
// Runs on any Shelly Gen2/3 device with scripting support.
//
// Balances the household grid power to (roughly) zero using TWO OR MORE
// Zendure devices at once. All devices are treated as one combined
// "virtual battery": the script reads the grid power once, adds up what
// all Zendure devices are currently doing, and calculates ONE combined
// target power - exactly like the single-device version. That combined
// target is then SPLIT across the configured devices every cycle:
//
//   - Discharge (export towards household): each device's share is
//     weighted by how far its SOC is above its own configured minSoc.
//     A fuller battery therefore contributes more. A device at or below
//     its minSoc gets a weight of 0 and is left alone (safety cutoff -
//     this falls out of the weighting automatically, no special case
//     needed).
//   - Charge (import from grid, only for devices with reverse=true):
//     mirrored - weighted by how much room is left below maxSoc.
//   - Each device's share is capped at its own maxOutput / maxInputPower.
//     Whatever a capped device can't take is redistributed across the
//     remaining (uncapped) devices in the same cycle ("water filling"),
//     so a small device and a big device can be mixed and the big one
//     will pick up the slack.
//   - If the combined capacity of all available devices isn't enough to
//     reach the target, the script simply delivers as much as it can -
//     no error, it just under-delivers for that cycle.
//
// Structurally this supports any number of devices (CONFIG.devices is a
// plain array) - tested/designed for 2, but adding a third device is just
// adding another entry to the array.
//
// Requests to each device (report + write) are sent SEQUENTIALLY, never
// in parallel, to avoid overloading the Shelly's limited HTTP/memory
// resources.
//
// Setup:
// 1. Remove ALL Zendure devices from HEMS in the app.
// 2. Copy the whole content and paste it into your Shelly Script UI.
// 3. Set CONFIG.gridSource ("local" = script runs ON the Pro 3EM itself,
//    "remote" = script runs on any other Shelly and reads a Pro 3EM
//    over the network via RPC, "http_json" = reads grid power from any
//    other JSON-over-HTTP meter, e.g. the Zendure Smart Meter 3CT).
// 4. Fill in CONFIG.devices with one entry per Zendure device (IP,
//    label, minSoc/maxSoc, maxOutput, minOutput, reverse, maxInputPower).
// 5. Set gridSourceIp / gridSourceUrl depending on the chosen gridSource.
// 6. Press start (and set it to start on boot time of the Shelly).
//
// This is based on the single-device Zendure Dynamic Output Controller
// and might be working on similar setups.
//
// Signal notifications via CallMeBot, adapted from
// https://github.com/surfer1264/Zendure-Stuff (zenSDKWatchDog)
//
// ... And ofc. a lot of AI coding aid was involved ;-)
//
// ======================================================

let CONFIG = {

  // One entry per Zendure device. Add/remove entries to change the
  // number of devices - the rest of the script adapts automatically.
  // dryRun (per device, default false): if true, the device is still
  // polled normally and takes part in the distribution weighting exactly
  // like a real participant, but it is NEVER actually written to - the
  // script only logs what it WOULD have sent. Handy for testing the
  // multi-device split with a second, fictional device profile while you
  // only own one real Zendure: point a second entry at the SAME ip as
  // your real device with dryRun:true and different minSoc/maxOutput, and
  // watch the console to see how the split would behave with real, live
  // SOC/power data - without ever risking a conflicting write to your
  // actual hardware. Note: if two entries share the same ip, that
  // device's power is only counted ONCE towards the combined grid-balance
  // target (calculate() dedupes by ip) - otherwise the same physical
  // device's output would be summed twice, inflating the target and
  // causing a runaway feedback loop.
  devices: [
    {
      ip: "192.168.178.xxx",   // Zendure IP address
      label: "SF2400",          // short name, used in logs/messages

      minSoc: 15,               // no discharge below this SOC (%)
      maxOutput: 2400,           // max discharge/export power (W)
      minOutput: 35,            // don't bother writing values below this (W)

      reverse: true,            // may this device charge from the grid?
      maxSoc: 100,               // no charging from grid at/above this SOC (%)
      maxInputPower: 2400,       // max charge power from grid (W)

      dryRun: false             // true = read + calculate only, never write
    },
    {
      ip: "192.168.178.yyy",   // Zendure IP address
      label: "SF800",          // short name, used in logs/messages

      minSoc: 15,               // no discharge below this SOC (%)
      maxOutput: 800,           // max discharge/export power (W)
      minOutput: 35,            // don't bother writing values below this (W)

      reverse: true,            // may this device charge from the grid?
      maxSoc: 100,               // no charging from grid at/above this SOC (%)
      maxInputPower: 1200,       // max charge power from grid (W)

      dryRun: false             // true = read + calculate only, never write
    },
  ],

  // Where to read the household grid power from:
  // "local"     -> script runs directly on the Shelly Pro 3EM and reads
  //                Shelly.getComponentStatus("em:<gridSourceEmId>") locally
  // "remote"    -> script runs on ANY other Shelly device and reads the
  //                grid power from a Shelly Pro 3EM elsewhere in the
  //                network via its HTTP RPC API (EM.GetStatus)
  // "http_json" -> generic: reads the grid power from ANY device that
  //                exposes a flat JSON object via plain HTTP GET, e.g. the
  //                Zendure Smart Meter 3CT (http://<IP>/properties/report)
  //                or similar third-party meters. Configure gridSourceUrl /
  //                gridSourceField / gridSourceInvert below.
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
  // this script expects (positive = importing from grid). Test by
  // switching on a big consumer at home and checking whether the printed
  // "Grid:" value in the console goes positive - if it goes negative
  // instead, set this to true.
  gridSourceInvert: false,

  // Update interval in milliseconds
  interval: 4000,

  // Watchdog timeout in milliseconds (covers the whole cycle: grid read +
  // all device reads + distribution + all device writes)
  watchdog: 8000,

  // Per-request timeout in SECONDS for every individual HTTP call to a
  // device (GET and POST). Deliberately kept well under CONFIG.watchdog
  // (in milliseconds): if a single call is allowed to run longer than our
  // own watchdog, the watchdog can give up on the cycle (Timer.clear()
  // only cancels OUR timer, it can't pull back an HTTP request already
  // handed to the firmware) while that request is still genuinely
  // pending in the background. Repeated slow/unresponsive cycles can
  // then accumulate orphaned in-flight calls until the firmware's own
  // hard limit on concurrent calls is hit ("Uncaught Error: Too many
  // calls in progress"). Keeping this comfortably shorter than the
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
  // Concentration mode: run only ONE device at low load instead of
  // splitting a small amount across all of them. Uses hysteresis (two
  // separate thresholds) so the number of active devices doesn't flap
  // back and forth around a single value. Between the two thresholds,
  // whichever mode is currently active stays active.
  // ------------------------------------------------------------------
  discharge: {
    concentrateBelow: 400,   // W - below this combined target, use ONE device
    spreadAbove: 600        // W - above this, split across all devices
  },

  charge: {
    concentrateBelow: 400,
    spreadAbove: 800
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
  // Whether an individual device is ALLOWED to charge from the grid at
  // all is configured per device (CONFIG.devices[i].reverse). These two
  // values control the system-wide start/stop hysteresis for entering or
  // leaving "charging mode" as a whole (mirrors the single-device script;
  // kept global here since starting/stopping should be a single system
  // decision, not something each device decides independently).

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

  // Signal notifications via CallMeBot (https://www.callmebot.com/blog/free-api-signal-send-messages/)
  signal: {

    enabled: false,          // set to true to activate Signal notifications
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

  // Global error types: "em" (grid meter), "watchdog" (stuck cycle)
  errors: { em: 0, watchdog: 0 },
  notified: { em: false, watchdog: false },

  // Concentration-mode state, tracked separately for discharge and charge
  // since the system could in principle resume either with its own
  // previously-preferred device. "spread" is the safe/neutral starting
  // mode - the very first cycle(s) always used it before this feature
  // existed, so starting there preserves prior behaviour until the mode
  // logic has had a chance to evaluate the first real target.
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

  let url =
    "https://api.callmebot.com/signal/send.php?phone=" +
    CONFIG.signal.phone +
    "&apikey=" +
    CONFIG.signal.apiKey +
    "&text=" +
    safeText;

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

function lock() {

  state.busy = true;

  if (state.watchdogTimer !== null)
    Timer.clear(state.watchdogTimer);

  state.watchdogTimer = Timer.set(
    CONFIG.watchdog,
    false,
    function () {

      reportError(state.errors, state.notified, "watchdog", "System",
        "Zyklus haengengeblieben (Watchdog-Timeout)");

      state.busy = false;
      state.watchdogTimer = null;

    }
  );
}

function unlock() {

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

function handleGenericGridResponse(res, meterLabel, field, invert, callback) {

  if (!res || res.code !== 200) {

    reportError(state.errors, state.notified, "em", meterLabel, "nicht erreichbar");
    unlock();
    callback(false);
    return;

  }

  let data;

  try {

    data = JSON.parse(res.body);

  }

  catch (e) {

    reportError(state.errors, state.notified, "em", meterLabel, "Fehler beim Parsen der Antwort");
    unlock();
    callback(false);
    return;

  }

  let value = data[field];

  if (value === undefined) {

    reportError(state.errors, state.notified, "em", meterLabel,
      "Antwort enthaelt kein Feld '" + field + "'");

    unlock();
    callback(false);
    return;

  }

  reportSuccess(state.errors, state.notified, "em", meterLabel);
  state.gridPower = invert ? (value * -1) : value;

  callback(true);

}

function readGridPower(callback) {

  if (CONFIG.gridSource === "local") {

    let em = Shelly.getComponentStatus("em:" + CONFIG.gridSourceEmId);

    if (!em) {

      reportError(state.errors, state.notified, "em", "Lokaler EM",
        "Kein Messwert verfuegbar (em:" + CONFIG.gridSourceEmId + " nicht gefunden)");

      unlock();
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

  unlock();
  callback(false);

}

// ======================================================
// Read Zendure devices (sequentially, one after another)
// ======================================================

function readDevice(index, callback) {

  let cfg = CONFIG.devices[index];
  let ds = state.devices[index];

  httpGet(

    "http://" + cfg.ip + "/properties/report",

    function (res) {

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

function readAllDevices(index, callback) {

  if (index >= CONFIG.devices.length) {
    callback();
    return;
  }

  readDevice(index, function () {
    readAllDevices(index + 1, callback);
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

function calculate() {

  let n = CONFIG.devices.length;
  let sumZen = 0;
  let availableCount = 0;

  // Dedupe by IP: two CONFIG entries pointing at the same physical device
  // (e.g. a real entry plus a dryRun testing entry on the same IP - see
  // the dryRun comment above CONFIG.devices) are the SAME battery. Only
  // count that device's power once, otherwise it gets summed twice into
  // sumZen, which inflates the calculated target, which makes the script
  // write an even higher value to the real device, which reads even
  // higher next cycle - a runaway feedback loop. The split/weighting
  // logic below is unaffected and still runs per entry, so this only
  // fixes the combined target, not the split preview.
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
    unlock();
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

    // System-wide startup deadband: only begin charging if the deficit is
    // big enough. If the system is ALREADY charging (sumZen < 0), it may
    // continue down to the smaller reverseStopPower threshold instead -
    // this mirrors the single-device hysteresis behaviour.
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

  applyOutputs(output);

}

// ======================================================
// Concentration mode: decide whether ONE device or ALL devices should
// be active this cycle, and (if one) WHICH device - with hysteresis on
// both decisions so neither flaps.
// ======================================================

// Hysteresis on "how many devices should be active". Between the two
// configured thresholds, whatever mode is already active stays active -
// this is the same two-threshold pattern used for the SOC/temperature
// alarms elsewhere in this project, just applied to device count.
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

function applyOutputs(output) {

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
    unlock();
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

    writeAllDevices(toWrite, output, 0, function () {
      unlock();
    });

  });


}

// ======================================================
// Write output limit to a Zendure device (sequentially across devices)
// ======================================================

function writeDevice(index, output, callback) {

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

function writeAllDevices(indices, output, pos, callback) {

  if (pos >= indices.length) {
    callback();
    return;
  }

  writeDevice(indices[pos], output, function () {
    writeAllDevices(indices, output, pos + 1, callback);
  });

}

// ======================================================
// Main control loop
// ======================================================

function update() {

  if (state.busy) {

    print("Vorheriger Zyklus laeuft noch");
    return;

  }

  lock();

  for (let i = 0; i < CONFIG.devices.length; i++) {
    state.devices[i].available = false;
  }

  readGridPower(function (ok) {

    if (!ok) return; // unlock() already called inside readGridPower on failure

    readAllDevices(0, function () {

      // Deferred via Timer.set(0, ...): calculate() (and everything it
      // calls - distributeDischarge/distributeCharge/waterFillDischarge/
      // waterFillCharge) needs a fair amount of local variables and
      // nested loops, and running it directly inside the last device's
      // GET-response callback was enough to exceed mJS's stack budget on
      // this device (seen as "Too much recursion" the first time the
      // charge/water-fill branch actually ran). Breaking out into a fresh
      // event loop tick here gives it a shallow stack to start from -
      // same fix pattern as the write-path deferral in applyOutputs().
      Timer.set(0, false, calculate);

    });

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

function printBannerLine() {

  if (bannerIndex >= bannerLines.length) {
    // Startup banner fully printed - release it. Without this, the whole
    // array of (fairly long, per-device) strings stays referenced by the
    // top-level `bannerLines` variable for the entire remaining runtime of
    // the script, permanently occupying memory it will never need again.
    bannerLines = null;
    return;
  }

  print(bannerLines[bannerIndex]);
  bannerIndex = bannerIndex + 1;

  Timer.set(150, false, printBannerLine);

}

printBannerLine();

if (CONFIG.signal.enabled) {
  sendSignalMessage("Zendure Multi-Device-Controller gestartet (" +
    CONFIG.devices.length + " Geraete).");
}

Timer.set(
  CONFIG.interval,
  true,
  update
);
