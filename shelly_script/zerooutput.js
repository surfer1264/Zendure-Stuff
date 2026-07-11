// Zendure Dynamic Output Controller
// Runs on a Shelly Pro 3PM
//
// It tries to output power into the household according to current load
// The aim is to output as little power as possible to the public net and
// use the most inside the household and batteries.
// Everything locally without any cloud involved.
//
// 1. Remove the Zendure from HEMS in the app
// 2. Copy the whole content and paste it into your Shell 3PM Script UI
// 3. Set the Zendure-IP
// 4. Press start (and set it to start on boot time of the Shelly)
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
//
// ... And ofc. a lot of AI coding aid was involved ;-)
//
// ======================================================

let CONFIG = {

  // Zendure IP address
  zendure: "IP-ADRESSE",

  // Update interval in milliseconds
  interval: 3000,

  // Watchdog timeout in milliseconds
  watchdog: 5000,

  // Minimum battery state of charge required for output
  minSoc: 20,

  // Minimum allowed output power for start
  minOutput: 50,

  // Maximum allowed output power, Limit
  maxOutput: 800,

  // Target grid power in watts (e.g. 0 = balance to zero,
  // negative = slight export, positive = slight import)
  setpoint: 0,

  // Hysteresis in watts - minimum change required before a new
  // output value is written to the Zendure (reduces write frequency)
  hysteresis: 10,

  // Number of consecutive failures of the same type before a
  // Signal notification is sent (avoids alarm spam on single glitches)
  errorThreshold: 3,

  // Signal notifications via CallMeBot (https://www.callmebot.com/blog/free-api-signal-send-messages/)
  signal: {

    enabled: false,          // set to true to activate Signal notifications
    phone: "PHONE-STRING",   // e.g. +4917XXXXXXXX
    apiKey: "YOUR_API_KEY"   // your CallMeBot API key

  }

};

let state = {

  gridPower: 0,
  zenOutput: 0,
  soc: 0,
  serial: null,
  outputLimit: -1,
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
// Read local Shelly power measurement
// ======================================================

function readGridPower() {

  let em = Shelly.getComponentStatus("em:0");

  if (!em) {

    reportError("em", "Kein EM-Messwert verfuegbar (em:0 nicht gefunden)");
    unlock();
    return false;

  }

  reportSuccess("em");
  state.gridPower = em.total_act_power;

  return true;

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

      state.zenOutput =
        data.properties.outputHomePower;

      calculate();

    }
  );
}

// ======================================================
// Calculate required output power
// ======================================================

function calculate() {

  let output = 0;

  // Only provide output above minimum SOC

  if (state.soc > CONFIG.minSoc) {

    // Regulate grid power towards the configured setpoint
    output = Math.round(
      (state.gridPower - CONFIG.setpoint) + state.zenOutput
    );

    // Limit lower boundary

    if (output < 0)
      output = 0;

    // Limit maximum output

    if (output > CONFIG.maxOutput)
      output = CONFIG.maxOutput;

    // Apply minimum output only when output is active

    if (output > 0 &&
        output < CONFIG.minOutput)

      output = CONFIG.minOutput;

  }

  // Skip update if change is within the hysteresis band

  if (state.outputLimit >= 0 &&
      Math.abs(output - state.outputLimit) < CONFIG.hysteresis) {

    unlock();
    return;

  }

  state.outputLimit = output;

  print(
    "Grid:",
    state.gridPower,
    "W | Zendure:",
    state.zenOutput,
    "W | SOC:",
    state.soc,
    "% | Setpoint:",
    CONFIG.setpoint,
    "W | SN:",
    state.serial,
    "| Output:",
    output,
    "W"
  );

  writeZendure(output);

}

// ======================================================
// Write output limit to Zendure
// ======================================================

function writeZendure(output) {

  httpPost(

    "http://" + CONFIG.zendure + "/properties/write",

    {

      sn: state.serial,

      properties: {

        outputLimit: output

      }
    },

    function(res) {

      if (res && res.code === 200) {

        print("Zendure output set:", output, "W");
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

  // Read power directly from local Shelly meter
  if (!readGridPower())
    return;

  // Read Zendure data and calculate output
  readZendure();

}

// ======================================================
// Startup
// ======================================================

print("--------------------------------");
print("Zendure Controller started");
print("Interval   :", CONFIG.interval, "ms");
print("Watchdog   :", CONFIG.watchdog, "ms");
print("Min SOC    :", CONFIG.minSoc, "%");
print("Min Out    :", CONFIG.minOutput, "W");
print("Max Out    :", CONFIG.maxOutput, "W");
print("Setpoint   :", CONFIG.setpoint, "W");
print("Hysteresis :", CONFIG.hysteresis, "W");
print("Err.Thresh :", CONFIG.errorThreshold);
print("Signal     :", CONFIG.signal.enabled ? "aktiviert" : "deaktiviert");
print("--------------------------------");

if (CONFIG.signal.enabled) {
  sendSignalMessage("Zendure-Controller gestartet.");
}

Timer.set(
  CONFIG.interval,
  true,
  update
);
