// Zendure Dynamic Output Controller
// Runs on any Shelly Gen2/3 device with scripting support.
//
// It tries to output power into the household according to current load
// The aim is to output as little power as possible to the public net and
// use the most inside the household and batteries.
// Everything locally without any cloud involved.
//
// 1. Remove the Zendure from HEMS in the app
// 2. Copy the whole content and paste it into your Shelly Script UI
// 3. Set CONFIG.gridSource ("local" = script runs ON the Pro 3EM itself,
//    "remote" = script runs on any other Shelly and reads a Pro 3EM
//    over the network via RPC, "http_json" = reads grid power from any
//    other JSON-over-HTTP meter, e.g. the Zendure Smart Meter 3CT)
// 4. Set the Zendure-IP (and gridSourceIp / gridSourceUrl depending on
//    the chosen gridSource)
// 5. Press start (and set it to start on boot time of the Shelly)
// Optional: change parameters in CONFIG to your liking
//
// This is working on a SolarFlow 800 with 2 battery packs
// and might be working on similar setups.
// On Jul. 09th 2026 there was a major outage of the Zendure cloud
// which inspired that script to be more independend from the outside.
// It should even work if the internet connection is down.
//
// Signal notifications via CallMeBot, adapted from
// https://github.com/surfer1264/Zendure-Stuff (zenSDKWatchDog)
// - **Reverse-Lademodus (Laden vom Netz mit Start-/Stop-Schwelle):**
//  Das Konzept (Start-/Stop-Deadband für das Laden vom Netz) orientiert sich
//  am `REVERSE`-Feature aus tost11s Projekt
//  https://github.com/tost11/zendure-shelly-tools/tree/main
////
// ... And ofc. a lot of AI coding aid was involved ;-)
//
// ======================================================

let CONFIG = {

  // Zendure IP address
  zendure: "IP-Adresse",
  // zendure: "192.168.178.143",

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
  // this script expects (positive = importing from grid / more household
  // load than covered, negative = exporting into the grid). Test by
  // switching on a big consumer at home and checking whether the printed
  // "Grid:" value in the console goes positive - if it goes negative
  // instead, set this to true.
  gridSourceInvert: false,

  // Update interval in milliseconds
  interval: 3000,

  // Watchdog timeout in milliseconds
  watchdog: 5000,

  // Minimum battery state of charge required for output
  minSoc: 15,

  // Minimum allowed output power
  minOutput: 35,

  // Maximum allowed output power
  maxOutput: 800,

  // Target grid power in watts (e.g. 0 = balance to zero,
  // negative = slight export, positive = slight import)
  setpoint: 0,

  // Hysteresis in watts - minimum change required before a new
  // output value is written to the Zendure (reduces write frequency)
  hysteresis: 10,

  // Damping / gain factor for the control signal (0 < factor <= 1).
  // The output does NOT jump directly to the freshly calculated target
  // value each cycle. Instead it moves only a fraction of the way there:
  //   smoothedOutput = smoothedOutput + dampingFactor * (target - smoothedOutput)
  // 1.0   = no damping, output follows the target immediately (old behavior)
  // 0.6   = output moves 30% of the remaining distance per cycle (default,
  //         smooths out sudden load spikes/dips over a few cycles)
  // 0.05  = very sluggish, strongly smoothed reaction
  // Note: the SOC safety cutoff (minSoc) always reacts immediately and
  // bypasses damping, so the battery is never held back from stopping.
  dampingFactor: 0.6,

  // ------------------------------------------------------------------
  // Reverse mode: allows charging the Zendure FROM the grid, in
  // addition to the normal discharge/export into the household.
  // Mirrors the "REVERSE" feature of the original Shelly-tos-Controller.
  // https://github.com/tost11/zendure-shelly-tools/tree/main
  // (see zendure_power_control/control_zendure_power_ip.js)
  // ------------------------------------------------------------------

  // Enables loading (charging) the battery from the grid whenever the
  // combined target power becomes negative (i.e. more household load
  // than the battery alone would need to cover, so it's worth pulling
  // extra energy from the grid to charge). Only makes sense if you have
  // another inverter/source feeding your home network already.
  // false = charging from the grid is disabled entirely (default,
  //         matches the original single-direction behavior)
  reverse: false,

  // Maximum power in watts to draw FROM the grid while charging.
  // Only relevant when reverse = true.
  maxInputPower: 1200,

  // Minimum charging power in watts required to START charging from
  // the grid. Acts as a deadband so the battery doesn't switch into
  // charge mode for a negligible power deficit. Only relevant when
  // reverse = true.
  reverseStartupPower: 30,

  // Charging power in watts below which charging from the grid is
  // STOPPED again (must be <= reverseStartupPower). Only relevant
  // when reverse = true.
  reverseStopPower: 10,

  // Upper SOC limit in percent. At or above this value, charging from
  // the grid is blocked entirely (mirrors minSoc, just for the charge
  // side instead of the discharge side). Reacts immediately, bypasses
  // damping. This is an independent, script-side safeguard - it does
  // NOT rely on the Zendure firmware's own overcharge protection
  // (socSet/socLimit), which the script has no visibility into.
  // Only relevant when reverse = true.
  maxSoc: 100,

  // Number of consecutive failures of the same type before a
  // Signal notification is sent (avoids alarm spam on single glitches)
  errorThreshold: 5,

  // Signal notifications via CallMeBot (https://www.callmebot.com/blog/free-api-signal-send-messages/)
  signal: {

    enabled: false,          // set to true to activate Signal notifications
    phone: "PHONE-STRING",   // e.g. +4917XXXXXXXX
    apiKey: "YOUR_API_KEY"   // your CallMeBot API key

  }

};

// Sanity check, analogous to the original Shelly-tos-Controller:
// the stop threshold must never be larger than the startup threshold,
// otherwise charging would never be able to switch off again.
if (CONFIG.reverseStopPower > CONFIG.reverseStartupPower) {

  print(
    "reverseStopPower groesser als reverseStartupPower - " +
    "setze beide auf: " + CONFIG.reverseStartupPower
  );

  CONFIG.reverseStopPower = CONFIG.reverseStartupPower;

}

let state = {

  gridPower: 0,
  zenPower: 0,
  soc: 0,
  serial: null,
  outputLimit: null,
  smoothedOutput: null,
  maxSocLogged: false,
  busy: false,
  watchdogTimer: null,

  // Consecutive error counters, one per failure type
  errors: {
    em: 0,
    connect: 0,
    json: 0,
    serial: 0,
    write: 0,
    watchdog: 0
  },

  // Tracks whether a notification was already sent for the
  // currently ongoing error streak (avoids repeated spamming)
  notified: {
    em: false,
    connect: false,
    json: false,
    serial: false,
    write: false,
    watchdog: false
  }

};

// ======================================================
// Signal notifications (CallMeBot) - adapted from zenSDKWatchDog
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
// Error / recovery bookkeeping
// ======================================================

// Call on every failure of a given type. Increments the counter,
// prints the error, and sends a Signal notification once the
// configured threshold is reached (only once per streak).
function reportError(type, message) {

  state.errors[type] = state.errors[type] + 1;

  print(
    "FEHLER (" + type + "):",
    message,
    "- aufeinanderfolgende Fehler:",
    state.errors[type]
  );

  if (state.errors[type] >= CONFIG.errorThreshold &&
      !state.notified[type]) {

    state.notified[type] = true;

    sendSignalMessage(
      "Zendure-Controller Fehler (" + type + "): " +
      message + "\n" +
      state.errors[type] + " Versuche in Folge fehlgeschlagen."
    );

  }
}

// Call on successful recovery of a given type. Resets the
// counter and allows future notifications for that type again.
function reportSuccess(type) {

  if (state.errors[type] > 0 || state.notified[type]) {

    if (state.notified[type]) {

      sendSignalMessage(
        "Zendure-Controller: Fehler (" + type + ") behoben, laeuft wieder normal."
      );

    }

    state.errors[type] = 0;
    state.notified[type] = false;

  }
}

// ======================================================
// Lock handling and watchdog
// ======================================================

function lock() {

  state.busy = true;

  if (state.watchdogTimer !== null)
    Timer.clear(state.watchdogTimer);

  state.watchdogTimer = Timer.set(
    CONFIG.watchdog,
    false,
    function () {

      reportError("watchdog", "Zyklus haengengeblieben (Watchdog-Timeout)");

      state.busy = false;
      state.watchdogTimer = null;

    }
  );
}

function unlock() {

  // A normal (non-watchdog) completion means the cycle did not
  // hang - count this as recovery for the watchdog error type.
  reportSuccess("watchdog");

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
      url: url
    },
    callback
  );
}

function httpPost(url, body, callback) {

  Shelly.call(
    "HTTP.Request",
    {
      method: "POST",
      url: url,

      headers: {
        "Content-Type": "application/json"
      },

      body: JSON.stringify(body)

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

// Shared handler for any HTTP+JSON based grid meter (used by both
// "remote" and "http_json"). `field` is the JSON property to read,
// `invert` optionally flips its sign to match this script's
// convention (positive = importing from grid).
function handleGenericGridResponse(res, meterLabel, field, invert, callback) {

  if (!res || res.code !== 200) {

    reportError("em", meterLabel + " nicht erreichbar");
    unlock();
    callback(false);
    return;

  }

  let data;

  try {

    data = JSON.parse(res.body);

  }

  catch(e) {

    reportError("em", "Fehler beim Parsen der Antwort von " + meterLabel);
    unlock();
    callback(false);
    return;

  }

  let value = data[field];

  if (value === undefined) {

    reportError(
      "em",
      meterLabel + "-Antwort enthaelt kein Feld '" + field + "'"
    );

    unlock();
    callback(false);
    return;

  }

  reportSuccess("em");
  state.gridPower = invert ? (value * -1) : value;

  callback(true);

}

function readGridPower(callback) {

  if (CONFIG.gridSource === "local") {

    let em = Shelly.getComponentStatus("em:" + CONFIG.gridSourceEmId);

    if (!em) {

      reportError(
        "em",
        "Kein lokaler EM-Messwert verfuegbar (em:" +
        CONFIG.gridSourceEmId + " nicht gefunden)"
      );

      unlock();
      callback(false);
      return;

    }

    reportSuccess("em");
    state.gridPower = em.total_act_power;

    callback(true);
    return;

  }

  if (CONFIG.gridSource === "remote") {

    // Fetch the value from a Shelly Pro 3EM elsewhere in the network
    // via its standard RPC API.
    httpGet(

      "http://" + CONFIG.gridSourceIp +
      "/rpc/EM.GetStatus?id=" + CONFIG.gridSourceEmId,

      function(res) {

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

    // Generic JSON meter, e.g. Zendure Smart Meter 3CT
    // (http://<IP>/properties/report -> field "total_power").
    httpGet(

      CONFIG.gridSourceUrl,

      function(res) {

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

  reportError("em", "Unbekannter CONFIG.gridSource: " + CONFIG.gridSource);
  unlock();
  callback(false);

}

// ======================================================
// Read Zendure status
// ======================================================

function readZendure() {

  httpGet(

    "http://" + CONFIG.zendure + "/properties/report",

    function(res) {

      if (!res || res.code !== 200) {

        reportError("connect", "Zendure nicht erreichbar");
        unlock();
        return;

      }

      reportSuccess("connect");

      let data;

      try {

        data = JSON.parse(res.body);

      }

      catch(e) {

        reportError("json", "Fehler beim Parsen der Zendure-Antwort");
        unlock();
        return;

      }

      reportSuccess("json");

      // Get serial number from Zendure response
      if (data.sn) {

        state.serial = data.sn;

      }

      if (!state.serial) {

        reportError("serial", "Keine Zendure-Seriennummer gefunden");
        unlock();
        return;

      }

      reportSuccess("serial");

      state.soc =
        data.packData[0].socLevel;

      // Determine the Zendure's current actual power flow, signed:
      // positive = currently discharging/exporting (acMode 2)
      // negative = currently charging from the grid (acMode 1)
      let acMode = data.properties.acMode;

      if (acMode === 2) {

        state.zenPower = data.properties.outputHomePower;

      } else if (acMode === 1) {

        state.zenPower = (data.properties.gridInputPower || 0) * -1;

      } else {

        state.zenPower = 0;

      }

      calculate();

    }
  );
}

// ======================================================
// Calculate required output power
// ======================================================

function calculate() {

  // Raw (undamped) combined target power:
  // positive = discharge/export towards household+grid
  // negative = charge/import from the grid (only usable if CONFIG.reverse)
  let raw = Math.round(
    (state.gridPower - CONFIG.setpoint) + state.zenPower
  );

  let target = 0;
  let immediate = false; // true = bypass damping (safety cutoff)

  if (raw >= 0) {

    // ---------------- Export / discharge side ----------------

    if (state.soc <= CONFIG.minSoc) {

      // Safety cutoff: no discharge below minimum SOC.
      // Reacts immediately, bypasses damping.
      target = 0;
      immediate = true;

    } else {

      target = raw;

      if (target > CONFIG.maxOutput)
        target = CONFIG.maxOutput;

    }

  } else {

    // ---------------- Charge / import side ----------------

    if (!CONFIG.reverse) {

      // Charging from the grid not enabled -> nothing to do
      target = 0;

    } else if (state.soc >= CONFIG.maxSoc) {

      // Safety cutoff: battery already at/above the configured max SOC.
      // Reacts immediately, bypasses damping - mirrors the minSoc
      // cutoff on the discharge side. This is informational only (not
      // an error), so just a console print - no Signal notification.
      target = 0;
      immediate = true;

      if (!state.maxSocLogged) {

        print(
          "SOC-Obergrenze erreicht (" + state.soc + "% >= " +
          CONFIG.maxSoc + "%) - Laden vom Netz gesperrt"
        );

        state.maxSocLogged = true;

      }

    } else {

      if (state.maxSocLogged) {

        print(
          "SOC wieder unter Obergrenze (" + state.soc + "% < " +
          CONFIG.maxSoc + "%) - Laden vom Netz bei Bedarf wieder moeglich"
        );

        state.maxSocLogged = false;

      }

      target = raw;

      if (state.zenPower >= 0 &&
          target < 0 &&
          target >= (CONFIG.reverseStartupPower * -1)) {

        // Not enough deficit yet to be worth starting to charge
        target = 0;

      } else if (target < (CONFIG.maxInputPower * -1)) {

        target = CONFIG.maxInputPower * -1;

      }

    }

  }

  // Apply damping/gain: instead of jumping straight to the new
  // target, move only a fraction (dampingFactor) of the remaining
  // distance per cycle. This smooths out sudden load spikes/dips.
  // The safety cutoff above always bypasses this and applies instantly.

  if (immediate || state.smoothedOutput === null) {

    state.smoothedOutput = target;

  } else {

    state.smoothedOutput =
      state.smoothedOutput +
      CONFIG.dampingFactor * (target - state.smoothedOutput);

  }

  let output = Math.round(state.smoothedOutput);

  // Post-damping deadbands / floors

  if (output >= 0) {

    // Apply minimum output only when discharge is active
    // if (output > 0 && output < CONFIG.minOutput)
    if (output > 0 && output < CONFIG.minOutput && target > 0)
      output = CONFIG.minOutput;

  } else {

    if (!CONFIG.reverse) {

      // Should not happen (target was already forced to 0 above),
      // but guard against residual damping drift just in case.
      output = 0;

    } else if (Math.abs(output) < CONFIG.reverseStopPower) {

      output = 0;

    }

  }

  // Skip update if change is within the hysteresis band

  if (state.outputLimit !== null &&
      Math.abs(output - state.outputLimit) < CONFIG.hysteresis) {

    unlock();
    return;

  }

  state.outputLimit = output;

  print(
    "Grid:",
    state.gridPower,
    "W | Zendure:",
    state.zenPower,
    "W | SOC:",
    state.soc,
    "% | Setpoint:",
    CONFIG.setpoint,
    "W | SN:",
    state.serial,
    "| Combined:",
    output,
    "W",
    output >= 0 ? "(Export)" : "(Laden vom Netz)"
  );

  writeZendure(output);

}

// ======================================================
// Write output limit to Zendure
// ======================================================

function writeZendure(output) {

  let acMode, outputLimit, inputLimit;

  if (output >= 0) {

    acMode = 2;          // discharge / export
    outputLimit = output;
    inputLimit = 0;

  } else {

    acMode = 1;           // charge / import from grid
    outputLimit = 0;
    inputLimit = Math.abs(output);

  }

  httpPost(

    "http://" + CONFIG.zendure + "/properties/write",

    {

      sn: state.serial,

      properties: {

        acMode: acMode,
        outputLimit: outputLimit,
        inputLimit: inputLimit,
        smartMode: 1

      }
    },

    function(res) {

      if (res && res.code === 200) {

        print("Zendure Leistung gesetzt:", output, "W");
        reportSuccess("write");

      }

      else {

        reportError("write", "Zendure-Schreibvorgang fehlgeschlagen");

      }

      unlock();

    }
  );
}

// ======================================================
// Main control loop
// ======================================================

function update() {

  if (state.busy) {

    print("Previous cycle still running");
    return;

  }

  lock();

  // Read grid power (local or remote, depending on CONFIG.gridSource)
  readGridPower(function(ok) {

    if (!ok)
      return;

    // Read Zendure data and calculate output
    readZendure();

  });

}

// ======================================================
// Startup
// ======================================================

let bannerLines = [
  "--------------------------------",
  "Zendure Controller started",
  "Grid source: " + CONFIG.gridSource +
    (CONFIG.gridSource === "remote" ? " (" + CONFIG.gridSourceIp + ")" : "") +
    (CONFIG.gridSource === "http_json" ?
      " (" + CONFIG.gridSourceUrl + ", Feld: " + CONFIG.gridSourceField +
      (CONFIG.gridSourceInvert ? ", invertiert" : "") + ")" : ""),
  "Interval   : " + CONFIG.interval + " ms",
  "Watchdog   : " + CONFIG.watchdog + " ms",
  "Min SOC    : " + CONFIG.minSoc + " %",
  "Min Out    : " + CONFIG.minOutput + " W",
  "Max Out    : " + CONFIG.maxOutput + " W",
  "Setpoint   : " + CONFIG.setpoint + " W",
  "Hysteresis : " + CONFIG.hysteresis + " W",
  "Damping    : " + CONFIG.dampingFactor,
  "Reverse    : " + (CONFIG.reverse ? "aktiviert" : "deaktiviert") +
    (CONFIG.reverse ?
      " (max " + CONFIG.maxInputPower + " W, Start " +
      CONFIG.reverseStartupPower + " W, Stop " +
      CONFIG.reverseStopPower + " W, maxSOC " +
      CONFIG.maxSoc + " %)" : ""),
  "Err.Thresh : " + CONFIG.errorThreshold,
  "Signal     : " + (CONFIG.signal.enabled ? "aktiviert" : "deaktiviert"),
  "--------------------------------"
];
 
let bannerIndex = 0;
 
function printBannerLine() {
 
  if (bannerIndex >= bannerLines.length)
    return;
 
  print(bannerLines[bannerIndex]);
  bannerIndex = bannerIndex + 1;
 
  Timer.set(150, false, printBannerLine);
 
}
 
printBannerLine();

if (CONFIG.signal.enabled) {
  sendSignalMessage("Zendure-Controller gestartet.");
}

Timer.set(
  CONFIG.interval,
  true,
  update
);
