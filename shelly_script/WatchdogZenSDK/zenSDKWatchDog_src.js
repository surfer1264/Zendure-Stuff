// ========== AkkuVolt Watchdog - Multi-Device (Hub2/SF2400Pro u.a.) via REST ==========
// Speicherschonende Version v1.4.0 (Report ohne JSON.parse, eigene Schedules statt DeleteAll)

print("Starte AkkuVolt-Watchdog Multi-Device");

// ==================== KONFIGURATION ====================

let CONFIG = {
  version: "1.4.0",

  devices: [
    { ip: "192.168.178.143", label: "SF2400", enabled: true },
    { ip: "192.168.178.150", label: "SF800", enabled: true }
  ],

  // Warnschwellen (global)
  vollSchwelle: 99,        // %
  entladeReset: 90,        // %
  minVoltWarn: 2.9,        // V
  minVoltReset: 3.1,       // V
  tempWarn: 45.0,          // °C
  tempReset: 30.0,         // °C

  // Astro-Offset
  sunriseOffset: 0,        // Min
  sunsetOffset: 0,

  maxMessageLength: 900,   // Zeichen vor Trim

  // Nachrichtenversand
  signal: {
    enabled: false,
    typ: "SIGNAL",         // "SIGNAL", "WHATSAPP" oder "WEBHOOK"
    phone: "PHONE-STRING",
    apiKey: "YOUR_API_KEY",
    webhookUrl: "http://<IP-ADRESSE>:8123/api/webhook/<id>"
  },

  // Polling & Timer
  pollIntervalMs: 120000,
  httpTimeout: 5,
  watchdog: 15000,
  errorThreshold: 5,

  // Extended Logging
  debug: false,             // true = ausfuehrliche Logging-Ausgaben / false = nur wichtige Logs
  // Banner-Darstellung
  bannerVerbose: false      // true = schrittweises Banner / false = 1 Zeile
};

// ==================== PLAUSIBILITAETS-CHECKS ====================

if (CONFIG.pollIntervalMs < 60000) CONFIG.pollIntervalMs = 60000;
if (CONFIG.httpTimeout < 3) CONFIG.httpTimeout = 3;
if (CONFIG.errorThreshold < 1) CONFIG.errorThreshold = 1;

if (CONFIG.entladeReset >= CONFIG.vollSchwelle) CONFIG.entladeReset = CONFIG.vollSchwelle - 5;
if (CONFIG.minVoltReset <= CONFIG.minVoltWarn) CONFIG.minVoltReset = CONFIG.minVoltWarn + 0.1;
if (CONFIG.tempReset >= CONFIG.tempWarn) CONFIG.tempReset = CONFIG.tempWarn - 5;

let minWatchdog = CONFIG.devices.length * (CONFIG.httpTimeout * 1000 + 1000) + 5000;
if (CONFIG.watchdog < minWatchdog) CONFIG.watchdog = minWatchdog;

if (CONFIG.devices.length === 0) {
  print("WARNUNG: CONFIG.devices ist leer!");
}

// Globales Map-Objekt um Allokation bei jedem Aufruf zu verhindern
let ENCODE_MAP = {
  " ": "%20", "ö": "oe", "ä": "ae", "ü": "ue", "ß": "ss",
  ":": "%3A", "(": "%28", ")": "%29", "\n": "%0A", "%": "%25",
  "°": "%C2%B0", "!": "%21", ",": "%2C"
};

// ==================== STATUS / STATE ====================

let state = {
  busy: false,
  watchdogTimer: null,
  cycleId: 0,
  cycleStartedAt: 0,

  errors: { watchdog: 0 },
  notified: { watchdog: false },

  devices: []
};

// Nur aktive Geräte im State vorhalten
for (let i = 0; i < CONFIG.devices.length; i++) {
  if (CONFIG.devices[i].enabled) {
    state.devices[i] = {
      soc: null,
      hyperTemp: null,

      minVol: null,
      minVolSoc: null,
      minVolSn: null,

      available: false,

      akkuVollMsgSent: false,
      hyperTempMsgSent: false,
      lowVoltMsgSent: {},

      errors: { connect: 0, json: 0 },
      notified: { connect: false, json: false }
    };
  }
}

// ==================== HILFSFUNKTIONEN & BENACHRICHTIGUNG ====================

function logDebug(msg) {
  if (CONFIG.debug) {
    print("[DEBUG] " + msg);
  }
}

function simpleEncode(str) {
  let out = "";
  for (let i = 0; i < str.length; i++) {
    let ch = str.charAt(i);
    out += (ENCODE_MAP[ch] || ch);
  }
  return out;
}

function sendWebhookMessage(text) {
  print("Sende Webhook-Benachrichtigung...");

  Shelly.call(
    "HTTP.Request",
    {
      method: "POST",
      url: CONFIG.signal.webhookUrl,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
      timeout: CONFIG.httpTimeout
    },
    function (res, err, msg) {
      if (err === 0) {
        if (res && res.code >= 200 && res.code < 300) {
          print("Webhook-Benachrichtigung erfolgreich gesendet (HTTP " + res.code + ").");
        } else {
          print("Webhook empfangen, aber HTTP Code: " + (res ? res.code : "?"));
        }
      } else if (err === -104) {
        print("Webhook-Timeout (-104), Nachricht vermutlich trotzdem angekommen.");
      } else {
        print("Fehler beim Senden der Webhook-Benachrichtigung: " + msg);
      }
    }
  );
}

function sendSignalMessage(text) {
  if (!CONFIG.signal.enabled) return;

  if (CONFIG.signal.typ == "WEBHOOK") {
    sendWebhookMessage(text);
    return;
  }

  let url;
  let safeText = simpleEncode(text);

  if (CONFIG.signal.typ == "SIGNAL")
    url = "https://api.callmebot.com/signal/send.php?phone=" + CONFIG.signal.phone + "&apikey=" + CONFIG.signal.apiKey + "&text=" + safeText;
  else
    url = "https://api.callmebot.com/whatsapp.php?phone=" + CONFIG.signal.phone + "&text=" + safeText + "&apikey=" + CONFIG.signal.apiKey;

  print("Sende Nachricht (" + CONFIG.signal.typ + ")...");

  Shelly.call(
    "HTTP.GET",
    { url: url, timeout: CONFIG.httpTimeout },
    function (result, error_code, error_msg) {
      if (error_code === 0)
        print("Nachricht erfolgreich gesendet.");
      else if (error_code === -104)
        print("Timeout (-104), Nachricht kam vermutlich trotzdem an.");
      else
        print("Fehler beim Senden der Nachricht: " + error_msg);
    }
  );
}

function reportError(errors, notified, type, label, message) {
  errors[type] = errors[type] + 1;
  print("Err (" + label + "/" + type + "): " + message + " (Count: " + errors[type] + ")");

  if (errors[type] >= CONFIG.errorThreshold && !notified[type]) {
    notified[type] = true;
    sendSignalMessage(label + " Err (" + type + "): " + message);
  }
}

function reportSuccess(errors, notified, type, label) {
  if (errors[type] > 0 || notified[type]) {
    logDebug("Fehler behoben: " + label + " (" + type + ")");
    if (notified[type]) {
      sendSignalMessage(label + ": Fehler " + type + " behoben.");
    }
    errors[type] = 0;
    notified[type] = false;
  }
}

function isNum(v) {
  return typeof v === "number" && !isNaN(v) && isFinite(v);
}

// ==================== WATCHDOG & LOCK ====================

function onWatchdogTimeout() {
  reportError(state.errors, state.notified, "watchdog", "System", "Timeout");
  state.busy = false;
  state.watchdogTimer = null;
}

function lock() {
  state.busy = true;
  state.cycleId++;
  state.cycleStartedAt = Date.now();

  logDebug("Start Zyklus #" + state.cycleId);

  if (state.watchdogTimer !== null) Timer.clear(state.watchdogTimer);
  state.watchdogTimer = Timer.set(CONFIG.watchdog, false, onWatchdogTimeout);

  return state.cycleId;
}

function unlock(myCycle) {
  if (myCycle !== state.cycleId) return;

  logDebug("Zyklus #" + myCycle + " beendet in " + (Date.now() - state.cycleStartedAt) + " ms");

  reportSuccess(state.errors, state.notified, "watchdog", "System");
  state.busy = false;

  if (state.watchdogTimer !== null) {
    Timer.clear(state.watchdogTimer);
    state.watchdogTimer = null;
  }
}

// ==================== LOGIK & VERARBEITUNG ====================

function checkSocFull(index) {
  let ds = state.devices[index];
  let cfg = CONFIG.devices[index];
  if (ds.soc === null) return;

  if (ds.soc >= CONFIG.vollSchwelle && !ds.akkuVollMsgSent) {
    ds.akkuVollMsgSent = true;
    sendSignalMessage("🔋 " + cfg.label + " voll (" + ds.soc + "%)");
  } else if (ds.soc < CONFIG.entladeReset) {
    ds.akkuVollMsgSent = false;
  }
}

function checkHyperTemp(index) {
  let ds = state.devices[index];
  let cfg = CONFIG.devices[index];
  if (!isNum(ds.hyperTemp)) return;

  if (ds.hyperTemp > CONFIG.tempWarn) {
    if (!ds.hyperTempMsgSent) {
      ds.hyperTempMsgSent = true;
      sendSignalMessage("🔥 " + cfg.label + " Temp hoch: " + ds.hyperTemp.toFixed(1) + "C");
    }
  } else if (ds.hyperTemp < CONFIG.tempReset) {
    ds.hyperTempMsgSent = false;
  }
}

// ---------------------------------------------------------------------
// Werte aus der Hub-Antwort OHNE JSON.parse ziehen (seit v1.4.0).
//
// Grund: Eine geparste /properties/report-Antwort (~1,3 kB, 60+ Felder)
// belegt mehrere hundert Variablen. Laeuft zeitgleich die zenDash-API auf
// demselben Shelly durch ihren Poll, addieren sich die Spitzen. Aus dem
// Rohtext gelesen bleibt nur der String selbst im Speicher - gleiche
// Technik wie in zendash_api (jsonNum/jsonMin).
//
// Preis: Aendert Zendure Feldnamen oder Struktur, faellt das erst im
// Betrieb auf. Deshalb liefern alle Helfer null statt zu raten, und ein
// fehlendes electricLevel gilt als "Report nicht auswertbar" (Fehlertyp json).
//
// Annahme fuer packData: ein Array aus FLACHEN Objekten (keine
// verschachtelten {} oder [] innerhalb eines Packs). Jede Suche wird auf
// das jeweilige Pack-Objekt begrenzt, damit kein Wert aus dem naechsten
// Pack oder von ausserhalb gelesen wird - die Feldreihenfolge ist egal.
// ---------------------------------------------------------------------

// Position direkt hinter "key": (Leerzeichen uebersprungen), sonst -1.
// Wird nur im Bereich [from, to) gesucht; to < 0 = bis Textende.
function jsonValuePos(s, key, from, to) {
  let tag = '"' + key + '"';
  let i = s.indexOf(tag, from || 0);
  if (i < 0 || (to >= 0 && i >= to)) return -1;
  i = s.indexOf(":", i + tag.length);
  if (i < 0 || (to >= 0 && i >= to)) return -1;
  let j = i + 1;
  while (j < s.length) {
    let c = s.charAt(j);
    if (c !== " " && c !== "\n" && c !== "\r" && c !== "\t") break;
    j++;
  }
  return j;
}

// Zahl hinter "key": - auch als String ("12") - oder null.
function jsonNumIn(s, key, from, to) {
  let j = jsonValuePos(s, key, from, to);
  if (j < 0) return null;
  if (s.charAt(j) === '"') j++;
  let start = j;
  while (j < s.length) {
    let c = s.charAt(j);
    if ((c >= "0" && c <= "9") || c === "-" || c === "+" || c === "." || c === "e" || c === "E") j++;
    else break;
  }
  if (j === start) return null;
  let v = Number(s.slice(start, j));
  return (v !== v) ? null : v;
}

// String hinter "key": oder null (keine Escape-Behandlung noetig, SNs sind ASCII).
function jsonStrIn(s, key, from, to) {
  let j = jsonValuePos(s, key, from, to);
  if (j < 0 || s.charAt(j) !== '"') return null;
  let e = s.indexOf('"', j + 1);
  if (e < 0 || (to >= 0 && e > to)) return null;
  return s.slice(j + 1, e);
}

// Laeuft ueber alle Packs in packData, meldet Unterspannung je Pack und
// merkt sich den Pack mit der niedrigsten Zellspannung.
function scanPacks(index, body) {
  let ds = state.devices[index];
  let cfg = CONFIG.devices[index];

  ds.minVol = null;
  ds.minVolSoc = null;
  ds.minVolSn = null;

  let p = jsonValuePos(body, "packData", 0, -1);
  if (p < 0 || body.charAt(p) !== "[") {
    logDebug(cfg.label + ": Keine packData im Report gefunden.");
    return;
  }
  let arrEnd = body.indexOf("]", p);
  if (arrEnd < 0) {
    logDebug(cfg.label + ": packData unvollstaendig.");
    return;
  }

  let pos = p + 1;
  let count = 0;
  while (true) {
    let objStart = body.indexOf("{", pos);
    if (objStart < 0 || objStart > arrEnd) break;
    let objEnd = body.indexOf("}", objStart);
    if (objEnd < 0 || objEnd > arrEnd) break;
    count++;

    let sn = jsonStrIn(body, "sn", objStart, objEnd);
    if (sn === null) sn = "#" + count;
    let rawMin = jsonNumIn(body, "minVol", objStart, objEnd);
    let packSoc = jsonNumIn(body, "socLevel", objStart, objEnd);
    let pMinV = (rawMin !== null) ? rawMin / 100 : null;

    logDebug("  Pack [" + sn + "]: SoC=" + packSoc + "%, MinVol=" + (pMinV !== null ? pMinV + "V" : "n/a"));

    if (pMinV !== null) {
      if (pMinV > 0 && pMinV < CONFIG.minVoltWarn) {
        if (!ds.lowVoltMsgSent[sn]) {
          ds.lowVoltMsgSent[sn] = true;
          sendSignalMessage("⚠️ " + cfg.label + " Zelle " + sn + " nur " + pMinV + "V");
        }
      } else if (pMinV > CONFIG.minVoltReset) {
        ds.lowVoltMsgSent[sn] = false;
      }

      // 0 V = schlafender Pack, zaehlt nicht als Minimum (wie zendash_api)
      if (pMinV > 0 && (ds.minVol === null || pMinV < ds.minVol)) {
        ds.minVol = pMinV;
        ds.minVolSoc = packSoc;
        ds.minVolSn = sn;
      }
    }

    pos = objEnd + 1;
  }

  logDebug(cfg.label + ": " + count + " Akkupack(s) gefunden.");
}

// true = Report ausgewertet, false = nicht auswertbar
function processDeviceBody(index, body) {
  let ds = state.devices[index];

  // Billiger Vollstaendigkeits-Check: ein abgeschnittener Report endet nicht
  // auf "}". Ohne diesen Check wuerden SoC/Temperatur aus dem Anfang noch
  // gelesen, die Packs am Ende aber stillschweigend fehlen.
  let e = body.length - 1;
  while (e >= 0 && (body.charAt(e) === " " || body.charAt(e) === "\n" || body.charAt(e) === "\r" || body.charAt(e) === "\t")) e--;
  if (e < 0 || body.charAt(e) !== "}") return false;

  let soc = jsonNumIn(body, "electricLevel", 0, -1);
  if (soc === null) return false;
  ds.soc = soc;

  let ht = jsonNumIn(body, "hyperTmp", 0, -1);
  if (ht !== null) ds.hyperTemp = (ht - 2731) / 10;

  scanPacks(index, body);
  ds.available = true;

  checkSocFull(index);
  checkHyperTemp(index);
  return true;
}

function onDeviceHttpResult(index, myCycle, res, err_code, err_msg, callback) {
  let cfg = CONFIG.devices[index];
  let ds = state.devices[index];

  if (err_code !== 0 || !res || res.code !== 200) {
    ds.available = false;
    logDebug("HTTP-Fehler bei " + cfg.label + " (" + cfg.ip + "): Code=" + err_code + " HTTP=" + (res ? res.code : "null") + " Msg=" + err_msg);
    reportError(ds.errors, ds.notified, "connect", cfg.label, "Unerreichbar");
    callback();
    return;
  }

  let body = res.body;
  res = null;

  logDebug("HTTP OK von " + cfg.label + " (" + cfg.ip + "), Laenge=" + (body ? body.length : 0) + " Bytes");
  reportSuccess(ds.errors, ds.notified, "connect", cfg.label);

  if (!body || !processDeviceBody(index, body)) {
    ds.available = false;
    logDebug("Report nicht auswertbar bei " + cfg.label + ". Data: " + (body ? body.substr(0, 50) + "..." : "empty"));
    body = null;
    reportError(ds.errors, ds.notified, "json", cfg.label, "Report unlesbar");
    callback();
    return;
  }
  body = null;

  reportSuccess(ds.errors, ds.notified, "json", cfg.label);
  callback();
}

function pollDevice(index, myCycle, callback) {
  let cfg = CONFIG.devices[index];
  logDebug("Abfrage gestartet: " + cfg.label + " (" + cfg.ip + ")");

  Shelly.call("HTTP.GET", { url: "http://" + cfg.ip + "/properties/report", timeout: CONFIG.httpTimeout }, function (res, err_code, err_msg) {
    if (myCycle !== state.cycleId) {
      logDebug("Zyklus veraltet für " + cfg.label + " (aktuell: " + state.cycleId + ", callback: " + myCycle + ")");
      return;
    }
    onDeviceHttpResult(index, myCycle, res, err_code, err_msg, callback);
  });
}

function readAllDevices(index, myCycle, callback) {
  if (index >= CONFIG.devices.length) {
    Timer.set(0, false, function () {
      if (myCycle === state.cycleId) callback();
    });
    return;
  }

  let cfg = CONFIG.devices[index];
  if (!cfg.enabled) {
    logDebug("Geraet übersprungen (deaktiviert): " + cfg.label);
    Timer.set(0, false, function () {
      if (myCycle === state.cycleId) readAllDevices(index + 1, myCycle, callback);
    });
    return;
  }

  pollDevice(index, myCycle, function () {
    readAllDevices(index + 1, myCycle, callback);
  });
}

// ==================== DIGEST & ASTRO ====================

function deviceValues(index) {
  let ds = state.devices[index];
  let socStr = (ds && ds.available && ds.soc !== null) ? (ds.soc + "%") : "n/a";
  let tempStr = (ds && ds.available && isNum(ds.hyperTemp)) ? (ds.hyperTemp.toFixed(1) + "C") : "n/a";
  let volStr = (ds && ds.available && isNum(ds.minVol)) ? (ds.minVol.toFixed(2) + "V") : "n/a";
  return socStr + ", " + tempStr + ", " + volStr;
}

function printDeviceSummary() {
  print("Geraete-Status:");
  for (let i = 0; i < CONFIG.devices.length; i++) {
    let cfg = CONFIG.devices[i];
    if (cfg.enabled) {
      print("  " + cfg.label + ": " + deviceValues(i));
    }
  }
}

function sendDigest(headerText) {
  let text = headerText;
  for (let i = 0; i < CONFIG.devices.length; i++) {
    let cfg = CONFIG.devices[i];
    if (!cfg.enabled) continue;
    let lbl = cfg.label ? cfg.label.substr(0, 6) : "??????"; // inline first6()
    text += "\n" + lbl + ": " + deviceValues(i);
  }

  if (text.length > CONFIG.maxMessageLength) {
    text = text.substr(0, CONFIG.maxMessageLength - 15) + "\n...(gekuerzt)";
  }

  sendSignalMessage(text);
}

function sendAstroStatus(type) {
  logDebug("Astro-Event ausgelöst: " + type);
  sendDigest(type === "sunset" ? "🌇 Abend-Update:" : "🌅 Morgen-Update:");
}

// Legt die beiden Astro-Schedules an. Seit v1.4.0 werden vorher NUR die
// Schedules geloescht, die dieses Script selbst angelegt hat (erkennbar an
// einem Script.Eval-Aufruf mit der eigenen Script-ID) - frueher loeschte
// Schedule.DeleteAll ALLE Schedules des Geraets, auch fremde.
function isOwnSchedule(job, scriptId) {
  if (!job || !job.calls) return false;
  for (let k = 0; k < job.calls.length; k++) {
    let c = job.calls[k];
    if (c && c.method && c.method.toLowerCase() === "script.eval" &&
        c.params && c.params.id === scriptId) return true;
  }
  return false;
}

function setupAstroSchedules() {
  let scriptId = Shelly.getCurrentScriptId();

  let specs = [
    ["@sunrise" + (CONFIG.sunriseOffset >= 0 ? "+" : "") + CONFIG.sunriseOffset, "sunrise"],
    ["@sunset" + (CONFIG.sunsetOffset >= 0 ? "+" : "") + CONFIG.sunsetOffset, "sunset"]
  ];

  // Nacheinander anlegen statt parallel - spart gleichzeitig offene RPCs.
  let createNext = function (n) {
    if (n >= specs.length) return;
    let spec = specs[n][0];
    Shelly.call("Schedule.Create", {
      "enable": true,
      "timespec": spec,
      "calls": [{ "method": "Script.Eval", "params": { "id": scriptId, "code": "sendAstroStatus('" + specs[n][1] + "')" } }]
    }, function (res, err, msg) {
      if (err !== 0) print("Fehler Schedule (" + spec + "): " + msg);
      else logDebug("Schedule erfolgreich angelegt: " + spec);
      createNext(n + 1);
    });
  };

  let deleteNext = function (ids, n) {
    if (n >= ids.length) { createNext(0); return; }
    Shelly.call("Schedule.Delete", { id: ids[n] }, function (res, err, msg) {
      if (err !== 0) print("Fehler beim Loeschen von Schedule " + ids[n] + ": " + msg);
      else logDebug("Alter eigener Schedule " + ids[n] + " geloescht.");
      deleteNext(ids, n + 1);
    });
  };

  Shelly.call("Schedule.List", null, function (res, err, msg) {
    if (err !== 0 || !res || !res.jobs) {
      // Lieber doppelte Schedules riskieren als fremde loeschen.
      print("Schedule.List fehlgeschlagen (" + msg + ") - lege Schedules ohne Aufraeumen an.");
      createNext(0);
      return;
    }
    let ids = [];
    for (let i = 0; i < res.jobs.length; i++) {
      if (isOwnSchedule(res.jobs[i], scriptId)) ids[ids.length] = res.jobs[i].id;
    }
    res = null;
    deleteNext(ids, 0);
  });
}

function onCycleComplete(myCycle) {
  if (myCycle !== state.cycleId) return;

  let anyAvailable = false;
  for (let i = 0; i < CONFIG.devices.length; i++) {
    if (state.devices[i] && state.devices[i].available) anyAvailable = true;
  }

  if (!anyAvailable) {
    print("Kein Geraet erreichbar in diesem Zyklus");
  } else {
    printDeviceSummary();
  }

  unlock(myCycle);
}

function update() {
  if (state.busy) {
    print("Vorheriger Zyklus laeuft noch - überspringe Update");
    return;
  }

  let myCycle = lock();

  for (let i = 0; i < CONFIG.devices.length; i++) {
    if (state.devices[i]) state.devices[i].available = false;
  }

  readAllDevices(0, myCycle, function () {
    onCycleComplete(myCycle);
  });
}

// ==================== START ====================

let enabledCount = 0;
for (let i = 0; i < CONFIG.devices.length; i++) {
  if (CONFIG.devices[i].enabled) enabledCount++;
}

function startApp() {
  sendSignalMessage("✅ AkkuVolt Watchdog gestartet (" + enabledCount + "/" + CONFIG.devices.length + " aktiv)");
  setupAstroSchedules();

  print("Ueberwachung aktiv. Intervall: " + (CONFIG.pollIntervalMs / 1000) + "s");
  print("--------------------------------");

  Timer.set(2000, false, update);
  Timer.set(CONFIG.pollIntervalMs, true, update);
}

// Haupt-Einstiegspunkt
if (CONFIG.bannerVerbose) {
  // Banner nur deklarieren wenn explizit aktiviert
  let printBannerStep = function(step, onDone) {
    let TOTAL_STEPS = 10 + CONFIG.devices.length;

    if (step === 0) print("--------------------------------");
    else if (step === 1) print("AkkuVolt Watchdog " + CONFIG.version);
    else if (step === 2) print("Geraete    : " + CONFIG.devices.length + " (aktiv: " + enabledCount + ")");
    else if (step >= 3 && step < 3 + CONFIG.devices.length) {
      let dev = CONFIG.devices[step - 3];
      print("  - " + dev.label + " (" + dev.ip + ")" + (dev.enabled ? "" : " [OFF]"));
    } else {
      let f = step - (3 + CONFIG.devices.length);
      if (f === 0) print("Intervall  : " + CONFIG.pollIntervalMs + " ms");
      if (f === 1) print("ErrThresh  : " + CONFIG.errorThreshold);
      if (f === 2) print("Voll ab    : " + CONFIG.vollSchwelle + "% (Reset: " + CONFIG.entladeReset + "%)");
      if (f === 3) print("MinVolt    : " + CONFIG.minVoltWarn + "V (Reset: " + CONFIG.minVoltReset + "V)");
      if (f === 4) print("Temp-Warn  : " + CONFIG.tempWarn + "C (Reset: " + CONFIG.tempReset + "C)");
      if (f === 5) print("Nachrichten: " + (CONFIG.signal.enabled ? CONFIG.signal.typ : "aus"));
      if (f === 6) print("Debug      : " + (CONFIG.debug ? "AN" : "AUS"));
      if (f === 7) print("--------------------------------");
    }

    if (step + 1 < TOTAL_STEPS) {
      Timer.set(100, false, function () { printBannerStep(step + 1, onDone); });
    } else if (onDone) {
      onDone();
    }
  };
  printBannerStep(0, startApp);
} else {
  print("AkkuVolt Watchdog " + CONFIG.version + " gestartet (" + enabledCount + "/" + CONFIG.devices.length + " aktiv)");
  startApp();
}