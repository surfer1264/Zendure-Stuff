// =====================================================================
// zenDash-API + Watchdog (zendash_watch_src.js)
//
// Ein Script, zwei einzeln abschaltbare Module:
//   API      - JSON-Endpunkte fuers Dashboard (config_api / status_api /
//              kvs_set_api) und Auto-Stop beim manuellen Laden.
//              Schnittstelle unveraendert gegenueber zendash_api v2.7.
//   Watchdog - Meldungen bei vollem Akku, hoher Temperatur, Zell-
//              Unterspannung und nicht erreichbaren Hubs, dazu ein
//              Digest zu Sonnenauf- und -untergang.
//
// Beide Module teilen sich EINEN Poll je Hub, EINEN Ueberlappungsschutz
// und EINE Nachrichten-Warteschlange. Dadurch laufen Hub-Abfrage, KVS-
// Schreiben und Nachrichtenversand (HTTPS bei Signal/WhatsApp) nie
// gleichzeitig - genau diese Spitzen addierten sich, solange es zwei
// getrennte Scripte waren.
//
// WICHTIG: CONFIG.devices MUSS zur CONFIG des Regel-Scripts passen (gleiche
// IPs, gleiche Reihenfolge = gleicher Index i wie "zdmc_dev{i}_...").
// Jedes eingetragene Geraet ist fuer die API relevant; "watch" legt nur
// fest, ob der Watchdog es zusaetzlich ueberwacht.
//
// Endpunkte (nur bei api.enabled, alle mit CORS):
//   GET config_api  -> { version, setpoint, hysteresis, dischargeFixed,
//                        dischargeStartupPower, devices:[...] }
//   GET status_api  -> { grid:{power,online},
//                        hubs:[{id,soc,power,acMode,socLimit,
//                               gridReverse,pv,minVol,online}] }
//   GET kvs_set_api?data={"zdmc_...":wert} -> { success, written }
//
// AUTO-STOP MANUELLES LADEN: Laedt ein Geraet manuell (dischargeAllowed=0,
// reverse=0, inputLimit>0) und meldet der Hub socLimit=1, wird der manuelle
// Modus automatisch beendet. Laeuft auch ohne offenes Dashboard. Der
// Vorzustand (preManual) lebt nur im Speicher; nach einem Neustart
// Fallback dischargeAllowed=1/reverse=1.
// =====================================================================
let SCRIPT_TYPE = "zdmc-zendash-watch";
let VERSION = "3.1";
let CONFIG_SCHEMA = 1;
let CONFIG = {
  // ------------------------------------------------------------------
  // GERAETEBLOCK - wie im Regel-Script, gleiche Reihenfolge.
  // watch: true  = Watchdog ueberwacht dieses Geraet zusaetzlich
  //        false = nur API/Dashboard
  // ------------------------------------------------------------------
  devices: [
    {
      ip: "192.168.178.143",
      label: "SF2400",
      minSoc: 15,
      maxSoc: 100,
      dischargeAllowed: true,
      reverse: true,
      maxInputPower: 1000,
      maxOutput: 800,
      inputLimit: 0,
      watch: true
    },
    {
      ip: "192.168.178.150",
      label: "SF800",
      minSoc: 15,
      maxSoc: 100,
      dischargeAllowed: true,
      reverse: true,
      maxInputPower: 2000,
      maxOutput: 2000,
      inputLimit: 0,
      watch: true
    }
  ],

  // ------------------------------------------------------------------
  // MODUL API (Dashboard)
  // ------------------------------------------------------------------
  api: {
    enabled: true,

    // "local" = KVS auf DIESEM Geraet (Script laeuft neben dem Regler),
    // "<IP>"  = KVS auf dem Regler-Shelly, Zugriff per RPC ueber HTTP.
    // Voraussetzung: dort ist keine Authentifizierung aktiv.
    kvsHost: "192.168.178.117",

    // Reine Anzeige im Dashboard - 1:1 aus dem Regel-Script kopieren.
    hysteresis: 12,

    // Untere Grenze fuer zdmc_dischargeFixed (0 ausgenommen) - 1:1 aus
    // CONFIG.dischargeStartupPower im Regel-Script kopieren.
    dischargeStartupPower: 35,

    // Netzmessung - gleiche Struktur/Feldnamen wie im Regel-Script.
    gridSource: "remote",            // "local", "remote", "http_json"
    gridSourceIp: "192.168.178.117", // nur bei "remote"
    gridSourceEmId: 0,               // nur bei "remote"/"local"
    gridSourceUrl: "http://<IP-of-your-meter>/properties/report", // nur bei "http_json"
    gridSourceField: "total_power",  // auch Array fuer Pfade, z.B. ["StatusSNS","SML","Watt_Summe"]
    gridSourceInvert: false,

    // Takt bei offenem Dashboard bzw. manuellem Laden. Bewusst langsamer
    // als die Dashboard-Seite (4 s) - die Anzeige ist bis zu 8 s alt.
    pollIntervalSec: 8
  },

  // ------------------------------------------------------------------
  // MODUL WATCHDOG
  // ------------------------------------------------------------------
  watchdog: {
    enabled: true,

    // Abfrage-Intervall, wenn KEIN Dashboard offen ist. Bei offenem
    // Dashboard wertet der Watchdog die ohnehin geholten Daten aus.
    intervalSec: 120,

    vollSchwelle: 99,      // %
    entladeReset: 90,      // %
    minVoltWarn: 2.9,      // V
    minVoltReset: 3.1,     // V
    tempWarn: 45.0,        // °C
    tempReset: 30.0,       // °C

    // Meldung, wenn ein Hub so lange nicht erreichbar bzw. sein Report
    // nicht auswertbar ist (ersetzt errorThreshold - zaehlt Zeit statt
    // Fehlversuche und ist damit unabhaengig vom Poll-Takt).
    offlineAlarmMin: 10,

    sunriseOffset: 0,      // Min
    sunsetOffset: 0        // Min
  },

  // ------------------------------------------------------------------
  // NACHRICHTEN (von beiden Modulen genutzt)
  // ------------------------------------------------------------------
  notify: {
    enabled: false,
    typ: "WEBHOOK",        // "SIGNAL", "WHATSAPP" oder "WEBHOOK"
    phone: "PHONE-STRING",
    apiKey: "YOUR_API_KEY",
    webhookUrl: "http://<IP-ADRESSE>:8123/api/webhook/<id>",
    maxMessageLength: 900,
    // Meldungen aus dem API-Modul: Auto-Stop erfolgreich / fehlgeschlagen
    apiEvents: true
  },

  httpTimeout: 5,

  // false = nur wichtige Meldungen
  // true  = zusaetzlich API-Aufrufe mit Werten, KVS-Schreibvorgaenge,
  //         Moduswechsel, Nachrichtenversand, Watchdog-Ereignisse
  debug: false
};

// Schnittstellenstand fuer das Dashboard (config_api liefert ihn aus). Die
// Endpunkte sind unveraendert gegenueber zendash_api v2.7.
let API_VERSION = "2.7";

// =====================================================
// Plausibilitaets-Checks
// =====================================================

let API_ON = !!(CONFIG.api && CONFIG.api.enabled);
let WD_ON = !!(CONFIG.watchdog && CONFIG.watchdog.enabled);
let W = CONFIG.watchdog;

let DBG = !!CONFIG.debug;

// Nachrichten-Block. Fehlt "notify", aber ein alter Watchdog-Block
// "signal" ist vorhanden (aus myconfig_Watchdog.js uebernommen), wird der
// verwendet - sonst ginge die Einstellung stillschweigend verloren.
let N = CONFIG.notify;
if (!N && CONFIG.signal) {
  N = CONFIG.signal;
  print("HINWEIS: CONFIG.signal (altes Watchdog-Format) wird als CONFIG.notify verwendet.");
}
if (N && CONFIG.signal && N !== CONFIG.signal) {
  print("HINWEIS: CONFIG.signal (altes Watchdog-Format) wird ignoriert - es gilt CONFIG.notify (typ " + N.typ + ").");
}
if (!N) N = { enabled: false };
N.typ = String(N.typ || "").toUpperCase();
if (N.typ !== "SIGNAL" && N.typ !== "WHATSAPP" && N.typ !== "WEBHOOK") {
  print("WARNUNG: notify.typ '" + N.typ + "' unbekannt (SIGNAL, WHATSAPP, WEBHOOK) - Nachrichten abgeschaltet.");
  N.enabled = false;
}
if (!(N.maxMessageLength > 50)) N.maxMessageLength = 900;
if (N.apiEvents === undefined) N.apiEvents = true;

if (CONFIG.httpTimeout < 3) CONFIG.httpTimeout = 3;
if (!(CONFIG.api.pollIntervalSec >= 4)) CONFIG.api.pollIntervalSec = 8;

if (typeof CONFIG.api.dischargeStartupPower !== "number" || CONFIG.api.dischargeStartupPower < 1) {
  CONFIG.api.dischargeStartupPower = 35;
}

if (!(W.intervalSec >= 60)) W.intervalSec = 60;
if (!(W.offlineAlarmMin >= 1)) W.offlineAlarmMin = 1;
if (W.entladeReset >= W.vollSchwelle) W.entladeReset = W.vollSchwelle - 5;
if (W.minVoltReset <= W.minVoltWarn) W.minVoltReset = W.minVoltWarn + 0.1;
if (W.tempReset >= W.tempWarn) W.tempReset = W.tempWarn - 5;

let WATCH_COUNT = 0;
for (let i = 0; i < CONFIG.devices.length; i++) {
  let d = CONFIG.devices[i];
  d.watch = (d.watch !== false);
  if (d.watch) WATCH_COUNT++;
  // Grenzen wie im Regel-Script normalisieren, damit die Dashboard-Regler
  // dieselben Bereiche anbieten, die der Regler auch akzeptiert.
  d.minSoc = Math.max(10, Math.min(99, d.minSoc || 10));
  d.maxSoc = Math.max(d.minSoc + 1, Math.min(100, d.maxSoc || 100));
  if (typeof d.inputLimit !== "number") d.inputLimit = 0;
  d.inputLimit = Math.max(0, Math.min(d.maxInputPower || 0, d.inputLimit));
}

if (CONFIG.devices.length === 0) print("WARNUNG: CONFIG.devices ist leer!");
if (!API_ON && !WD_ON) print("WARNUNG: api und watchdog sind beide abgeschaltet - Script tut nichts.");

// =====================================================
// Allgemeine Helfer
// =====================================================

// Aufrufer pruefen DBG VOR dem Zusammenbau des Textes ("if (DBG) ..."),
// damit bei abgeschaltetem Debug keine Strings gebaut werden.
function logDebug(msg) {
  print("[DEBUG] " + msg);
}

function isNum(v) {
  return typeof v === "number" && !isNaN(v) && isFinite(v);
}

// ---------------------------------------------------------------------
// Werte aus JSON-Rohtext lesen, OHNE JSON.parse.
//
// Eine geparste /properties/report-Antwort (~1,2 kB, 60+ Felder) belegt
// mehrere hundert Variablen; aus dem Rohtext gelesen bleibt nur der String
// selbst im Speicher. Preis: Aendert Zendure Feldnamen oder Struktur, faellt
// das erst im Betrieb auf - deshalb liefern alle Helfer null statt zu raten.
//
// from/to begrenzen die Suche auf [from, to); to < 0 = bis Textende.
// Bewusst Offsets statt Teilstrings: s.slice() wuerde kopieren.
// ---------------------------------------------------------------------

function isWs(c) {
  return c === " " || c === "\n" || c === "\r" || c === "\t";
}

// Position direkt hinter "key": (Leerraum uebersprungen), sonst -1.
function jsonValuePos(s, key, from, to) {
  let tag = '"' + key + '"';
  let i = s.indexOf(tag, from || 0);
  if (i < 0 || (to >= 0 && i >= to)) return -1;
  i = s.indexOf(":", i + tag.length);
  if (i < 0 || (to >= 0 && i >= to)) return -1;
  let j = i + 1;
  while (j < s.length && isWs(s.charAt(j))) j++;
  return j;
}

// Zahl hinter "key": - auch als String ("12", z.B. aus der KVS) - oder null.
function jsonNum(s, key, from, to) {
  if (to === undefined) to = -1;
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

// String hinter "key": oder null (keine Escape-Behandlung, SNs sind ASCII).
function jsonStr(s, key, from, to) {
  let j = jsonValuePos(s, key, from, to);
  if (j < 0 || s.charAt(j) !== '"') return null;
  let e = s.indexOf('"', j + 1);
  if (e < 0 || (to >= 0 && e > to)) return null;
  return s.slice(j + 1, e);
}

// Billiger Vollstaendigkeits-Check: ein abgeschnittener Report endet nicht
// auf "}". Ohne ihn wuerden SoC/Temperatur vom Anfang noch gelesen, die
// Packs am Ende aber stillschweigend fehlen.
function endsWithBrace(s) {
  let e = s.length - 1;
  while (e >= 0 && isWs(s.charAt(e))) e--;
  return e >= 0 && s.charAt(e) === "}";
}

// =====================================================
// Ueberlappungsschutz - EINER fuer alles
//
// Gilt fuer: Poll (Netz + Hubs), config_api, kvs_set_api, Auto-Stop,
// Nachrichtenversand und die Startphase. Zaehler statt Flag, weil mehrere
// unabhaengige Nutzer ihn halten koennen.
// =====================================================

let busyCount = 0;
let busySince = 0;
let bgRunning = false;

// Laengster moeglicher Durchlauf: Netz + jeder Hub koennen in den Timeout
// laufen. Kleiner darf die Sicherung nicht sein, sonst greift sie mitten im
// Normalbetrieb und erlaubt genau die Ueberlappung, die sie verhindern soll.
let BUSY_TIMEOUT_MS = (CONFIG.devices.length + 1) * CONFIG.httpTimeout * 1000 + 5000;

function busyNow() {
  if (busyCount > 0 && (Date.now() - busySince) > BUSY_TIMEOUT_MS) {
    print("Ueberlappungsschutz haengt seit ueber " + (BUSY_TIMEOUT_MS / 1000) + " s - zurueckgesetzt");
    busyCount = 0;
    bgRunning = false;
    notifySending = false;
  }
  return busyCount > 0;
}

function busyEnter() {
  busyCount++;
  busySince = Date.now();
}

function busyLeave() {
  if (busyCount > 0) busyCount--;
}

// =====================================================
// Nachrichten - nie direkt senden, immer ueber die Warteschlange
//
// notify() legt nur ab. notifyPump() sendet genau EINE Nachricht, und nur
// wenn gerade nichts anderes laeuft (busyNow). Waehrend des Sendens ist der
// Schutz belegt - ein Poll wartet also, bis die Nachricht raus ist, und
// umgekehrt. Laeuft die Schlange ueber, faellt die aelteste Nachricht weg.
// =====================================================

let NOTIFY_MAX = 5;
let notifyQueue = [];
let notifySending = false;

let ENCODE_MAP = {
  " ": "%20", "ö": "oe", "ä": "ae", "ü": "ue", "ß": "ss",
  ":": "%3A", "(": "%28", ")": "%29", "\n": "%0A", "%": "%25",
  "°": "%C2%B0", "!": "%21", ",": "%2C", "&": "%26", "+": "%2B", "#": "%23"
};

function simpleEncode(str) {
  let out = "";
  for (let i = 0; i < str.length; i++) {
    let ch = str.charAt(i);
    out += (ENCODE_MAP[ch] || ch);
  }
  return out;
}

function notify(text) {
  print("[Meldung] " + text);
  if (!N.enabled) return;
  if (text.length > N.maxMessageLength) {
    text = text.substr(0, N.maxMessageLength - 15) + "\n...(gekuerzt)";
  }
  if (notifyQueue.length >= NOTIFY_MAX) {
    notifyQueue.splice(0, 1);
    print("Nachrichten-Warteschlange voll - aelteste Meldung verworfen.");
  }
  notifyQueue[notifyQueue.length] = text;
  if (DBG) logDebug("Nachricht eingereiht (" + N.typ + "), Warteschlange: " + notifyQueue.length);
}

function notifyPump() {
  if (notifySending || notifyQueue.length === 0) return;
  if (busyNow()) return;

  let text = notifyQueue[0];
  notifyQueue.splice(0, 1);
  if (DBG) logDebug("Sende Nachricht ueber " + N.typ + " (" + text.length + " Zeichen), danach noch " + notifyQueue.length + " in der Schlange");
  notifySending = true;
  busyEnter();

  let done = function (ok, info) {
    if (ok) { if (DBG) logDebug("Nachricht gesendet (" + N.typ + ", " + info + ")."); }
    else print("Fehler beim Senden der Nachricht: " + info);
    notifySending = false;
    busyLeave();
    // naechste Nachricht erst mit etwas Abstand, damit ein faelliger Poll
    // dazwischen kommen kann
    if (notifyQueue.length > 0) Timer.set(1000, false, notifyPump);
  };

  if (N.typ === "WEBHOOK") {
    Shelly.call("HTTP.Request", {
      method: "POST",
      url: N.webhookUrl,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
      timeout: CONFIG.httpTimeout
    }, function (res, err, msg) {
      if (err === 0) done(true, "HTTP " + (res ? res.code : "?"));
      else if (err === -104) done(true, "Timeout, vermutlich angekommen");
      else done(false, msg);
    });
    return;
  }

  let safeText = simpleEncode(text);
  let url;
  if (N.typ === "SIGNAL") {
    url = "https://api.callmebot.com/signal/send.php?phone=" + N.phone + "&apikey=" + N.apiKey + "&text=" + safeText;
  } else {
    url = "https://api.callmebot.com/whatsapp.php?phone=" + N.phone + "&text=" + safeText + "&apikey=" + N.apiKey;
  }
  safeText = null;

  Shelly.call("HTTP.GET", { url: url, timeout: CONFIG.httpTimeout }, function (res, err, msg) {
    res = null;
    if (err === 0) done(true, N.typ);
    else if (err === -104) done(true, "Timeout, vermutlich angekommen");
    else done(false, msg);
  });
}

// =====================================================
// KVS-Helfer (Modul API)
//
// lokal    - store ist ein fertiges Objekt {key: value, ...}
// entfernt - store ist der ROHE Antworttext; kvsValue() liest daraus
// Fehler   - store ist null; der Aufrufer nimmt die CONFIG-Vorgaben.
// =====================================================

let KVS_MATCH = "zdmc_*";

function kvsItemsToMap(rawItems) {
  let map = {};
  if (!rawItems) return map;
  if (Array.isArray(rawItems)) {
    for (let i = 0; i < rawItems.length; i++) {
      let entry = rawItems[i];
      if (entry && entry.key !== undefined) map[entry.key] = entry.value;
    }
  } else {
    for (let k in rawItems) {
      map[k] = rawItems[k].value !== undefined ? rawItems[k].value : rawItems[k];
    }
  }
  return map;
}

function kvsIsRemote() {
  return CONFIG.api.kvsHost !== "local" && CONFIG.api.kvsHost !== "";
}

function kvsGetAll(callback) {
  if (!kvsIsRemote()) {
    Shelly.call("KVS.GetMany", { match: KVS_MATCH }, function (result, error_code) {
      if (error_code !== 0 || !result || !result.items) { callback(null); return; }
      callback(kvsItemsToMap(result.items));
    });
    return;
  }
  Shelly.call("HTTP.GET", {
    url: "http://" + CONFIG.api.kvsHost + "/rpc/KVS.GetMany?match=" + KVS_MATCH,
    timeout: CONFIG.httpTimeout
  }, function (res, error_code) {
    if (error_code !== 0 || !res || res.code !== 200) { callback(null); return; }
    let body = res.body;
    res = null;
    callback(body);
  });
}

function kvsValue(store, key) {
  if (store === null || store === undefined) return undefined;
  if (typeof store === "string") {
    let i = store.indexOf('"' + key + '"');
    if (i < 0) return undefined;
    let v = jsonNum(store, "value", i);
    return (v === null) ? undefined : v;
  }
  return store[key];
}

// Nur Zahlen zulassen - schuetzt die URL beim entfernten Schreiben und haelt
// die KVS sauber (alle zdmc_-Werte sind numerisch).
function kvsSafeNumber(value) {
  let str = String(value);
  if (str.length === 0 || str.length > 12) return null;
  for (let i = 0; i < str.length; i++) {
    let c = str.charAt(i);
    if ((c < "0" || c > "9") && c !== "-" && c !== ".") return null;
  }
  return str;
}

function kvsSetOne(key, value, callback) {
  let str = kvsSafeNumber(value);
  if (str === null) {
    print("KVS: Wert fuer " + key + " abgelehnt (keine Zahl): " + value);
    callback(false);
    return;
  }
  if (DBG) {
    let cb0 = callback;
    callback = function (ok) {
      logDebug("KVS.Set " + key + "=" + str + (kvsIsRemote() ? " @" + CONFIG.api.kvsHost : " (lokal)") + " -> " + (ok ? "ok" : "FEHLER"));
      cb0(ok);
    };
  }
  if (!kvsIsRemote()) {
    Shelly.call("KVS.Set", { key: key, value: str }, function (result, error_code) {
      callback(error_code === 0);
    });
    return;
  }
  Shelly.call("HTTP.GET", {
    url: "http://" + CONFIG.api.kvsHost + "/rpc/KVS.Set?key=" + key + "&value=" + str,
    timeout: CONFIG.httpTimeout
  }, function (res, error_code) {
    callback(error_code === 0 && !!res && res.code === 200);
  });
}

// =====================================================
// Manueller Lademodus - Zustandsspiegel & Auto-Stop (Modul API)
//
// "Manuell aktiv" = dischargeAllowed=0, reverse=0, inputLimit>0.
// deviceState spiegelt den zuletzt bekannten Zustand, preManual den
// Zustand, zu dem beim Beenden zurueckgekehrt wird (nur im Speicher).
// =====================================================

let deviceState = [];
for (let dsi = 0; dsi < CONFIG.devices.length; dsi++) {
  let dsd = CONFIG.devices[dsi];
  deviceState[dsi] = {
    dischargeAllowed: dsd.dischargeAllowed !== false,
    reverse: !!dsd.reverse,
    inputLimit: dsd.inputLimit || 0
  };
}
let preManual = [];

// Pause zwischen einzelnen KVS-Schreibvorgaengen in einem Request - sonst
// treffen mehrere KVS.Set, der Poll UND die Reaktion des Regel-Scripts
// innerhalb weniger hundert Millisekunden zusammen.
let KVS_STEP_PAUSE_MS = 500;

function isManualActive(ds) {
  return !!ds && !ds.dischargeAllowed && !ds.reverse && Number(ds.inputLimit) > 0;
}

function anyManualActive() {
  for (let i = 0; i < deviceState.length; i++) {
    if (isManualActive(deviceState[i])) return true;
  }
  return false;
}

// Zerlegt "zdmc_devN_<feld>" in {index, field}; andere Keys -> null.
function parseDeviceKey(key) {
  if (key.indexOf("zdmc_dev") !== 0) return null;
  let rest = key.slice(8);
  let us = rest.indexOf("_");
  if (us < 0) return null;
  let idx = Number(rest.slice(0, us));
  if (idx !== idx) return null;
  let field = rest.slice(us + 1);
  if (field !== "dischargeAllowed" && field !== "reverse" && field !== "inputLimit") return null;
  return { index: idx, field: field };
}

// Vor dem Schreiben: preManual GENAU beim Uebergang in den manuellen Modus
// sichern bzw. beim Uebergang heraus loeschen - anhand des unveraenderten
// deviceState vor diesem Request (siehe Ausfuehrung in zendash_api v2.7).
function captureManualTransitions(data, keys) {
  let touched = [];
  for (let i = 0; i < keys.length; i++) {
    let pk = parseDeviceKey(keys[i]);
    if (!pk || !deviceState[pk.index]) continue;
    let idx = pk.index;
    if (!touched[idx]) {
      touched[idx] = {
        dischargeAllowed: deviceState[idx].dischargeAllowed,
        reverse: deviceState[idx].reverse,
        inputLimit: deviceState[idx].inputLimit
      };
    }
    let v = data[keys[i]];
    if (pk.field === "dischargeAllowed") touched[idx].dischargeAllowed = (Number(v) !== 0);
    else if (pk.field === "reverse") touched[idx].reverse = (Number(v) !== 0);
    else touched[idx].inputLimit = Number(v);
  }
  for (let idx = 0; idx < touched.length; idx++) {
    if (!touched[idx]) continue;
    let wasActive = isManualActive(deviceState[idx]);
    let willBeActive = isManualActive(touched[idx]);
    if (willBeActive && !wasActive) {
      preManual[idx] = {
        dischargeAllowed: deviceState[idx].dischargeAllowed,
        reverse: deviceState[idx].reverse
      };
      if (DBG) logDebug("Manuelles Laden START dev" + idx + " - Vorzustand gemerkt: dischargeAllowed=" +
        preManual[idx].dischargeAllowed + ", reverse=" + preManual[idx].reverse);
    }
    if (wasActive && !willBeActive) {
      preManual[idx] = null;
      if (DBG) logDebug("Manuelles Laden ENDE dev" + idx);
    }
  }
}

function applyDeviceKeysToState(data, keys) {
  for (let i = 0; i < keys.length; i++) {
    let pk = parseDeviceKey(keys[i]);
    if (!pk || !deviceState[pk.index]) continue;
    let v = Number(data[keys[i]]);
    if (pk.field === "dischargeAllowed") deviceState[pk.index].dischargeAllowed = (v !== 0);
    else if (pk.field === "reverse") deviceState[pk.index].reverse = (v !== 0);
    else deviceState[pk.index].inputLimit = v;
  }
}

// Nach jedem Poll: ist ein manuell ladendes Geraet laut Hub fertig
// (socLimit=1)? Nur wenn gerade nichts anderes schreibt; faellt es aus,
// greift der naechste Poll.
function checkAutoStop() {
  if (busyNow()) {
    if (DBG && anyManualActive()) logDebug("Auto-Stop-Pruefung verschoben (Slot belegt)");
    return;
  }
  for (let i = 0; i < HUBS.length; i++) {
    let hub = HUBS[i];
    if (!hub.online) continue;
    if (!isManualActive(deviceState[i])) continue;
    if (hub.socLimit !== 1) continue;
    autoStopDevice(i);
    return; // ein Geraet je Durchlauf
  }
}

function autoStopFailed(idx, step) {
  let lbl = CONFIG.devices[idx].label;
  print("Auto-Stop fuer " + lbl + " abgebrochen (" + step + "). Bitte Dashboard pruefen.");
  if (N.apiEvents) notify("⚠️ " + lbl + ": Auto-Stop fehlgeschlagen (" + step + ") - bitte Dashboard pruefen");
  busyLeave();
}

// Gleiche Reihenfolge und Pausen wie stopManual() im Dashboard: erst
// inputLimit=0, dann die beiden Schalter.
function autoStopDevice(idx) {
  let restore = preManual[idx] || { dischargeAllowed: true, reverse: true };
  let lbl = CONFIG.devices[idx].label;
  print("Auto-Stop: " + lbl + " meldet socLimit=1 - beende manuelles Laden.");

  busyEnter();
  kvsSetOne("zdmc_dev" + idx + "_inputLimit", 0, function (ok1) {
    if (!ok1) { autoStopFailed(idx, "inputLimit"); return; }
    deviceState[idx].inputLimit = 0;

    Timer.set(KVS_STEP_PAUSE_MS, false, function () {
      kvsSetOne("zdmc_dev" + idx + "_dischargeAllowed", restore.dischargeAllowed ? 1 : 0, function (ok2) {
        if (!ok2) { autoStopFailed(idx, "dischargeAllowed"); return; }
        deviceState[idx].dischargeAllowed = !!restore.dischargeAllowed;

        Timer.set(KVS_STEP_PAUSE_MS, false, function () {
          kvsSetOne("zdmc_dev" + idx + "_reverse", restore.reverse ? 1 : 0, function (ok3) {
            if (!ok3) { autoStopFailed(idx, "reverse"); return; }
            deviceState[idx].reverse = !!restore.reverse;
            preManual[idx] = null;
            print("Auto-Stop: " + lbl + " zurueck in der Regelung.");
            if (N.apiEvents) notify("✅ " + lbl + ": manuelles Laden beendet (voll), zurueck in der Regelung");
            busyLeave();
          });
        });
      });
    });
  });
}

// Beim Start den ECHTEN KVS-Zustand einlesen - wichtig, falls das Script
// waehrend eines laufenden manuellen Ladevorgangs neu startet.
function initDeviceState(done) {
  busyEnter();
  kvsGetAll(function (store) {
    for (let i = 0; i < CONFIG.devices.length; i++) {
      let d = CONFIG.devices[i];
      let da = kvsValue(store, "zdmc_dev" + i + "_dischargeAllowed");
      let rv = kvsValue(store, "zdmc_dev" + i + "_reverse");
      let il = kvsValue(store, "zdmc_dev" + i + "_inputLimit");
      deviceState[i] = {
        dischargeAllowed: (da !== undefined) ? (Number(da) !== 0) : (d.dischargeAllowed !== false),
        reverse: (rv !== undefined) ? (Number(rv) !== 0) : !!d.reverse,
        inputLimit: (il !== undefined) ? Number(il) : (d.inputLimit || 0)
      };
    }
    if (store === null) print("KVS beim Start nicht lesbar - Vorgaben aus CONFIG verwendet.");
    if (DBG) {
      for (let j = 0; j < deviceState.length; j++) {
        logDebug("Start dev" + j + ": dischargeAllowed=" + deviceState[j].dischargeAllowed + ", reverse=" +
          deviceState[j].reverse + ", inputLimit=" + deviceState[j].inputLimit + (isManualActive(deviceState[j]) ? " [MANUELL]" : ""));
      }
    }
    store = null;
    busyLeave();
    done();
  });
}

// =====================================================
// Query-String (Modul API)
// =====================================================

// mJS kennt kein decodeURIComponent() - einfache Prozent-Dekodierung.
function percentDecode(s) {
  let out = "";
  let i = 0;
  let n = s.length;
  while (i < n) {
    let c = s.charAt(i);
    if (c === "%" && i + 2 < n) {
      out += String.fromCharCode(parseInt(s.charAt(i + 1) + s.charAt(i + 2), 16));
      i += 3;
    } else if (c === "+") {
      out += " ";
      i += 1;
    } else {
      out += c;
      i += 1;
    }
  }
  return out;
}

// req.query ist auf Shelly ein ROHER Query-String.
function getQueryParam(query, name) {
  if (!query) return undefined;
  let pairs = query.split("&");
  for (let i = 0; i < pairs.length; i++) {
    let eq = pairs[i].indexOf("=");
    if (eq < 0) continue;
    if (percentDecode(pairs[i].slice(0, eq)) === name) return percentDecode(pairs[i].slice(eq + 1));
  }
  return undefined;
}

// =====================================================
// Netzmessung (Modul API)
// =====================================================

function readFieldPath(data, field) {
  if (typeof field === "string") return data[field];
  let current = data;
  for (let i = 0; i < field.length; i++) {
    if (current === undefined || current === null) return undefined;
    current = current[field[i]];
  }
  return current;
}

function updateGridPowerStatus(callback) {
  let A = CONFIG.api;

  if (A.gridSource === "local") {
    let em = Shelly.getComponentStatus("em:" + A.gridSourceEmId);
    if (!em) { callback(0, false); return; }
    let power = em.total_act_power;
    if (power === undefined) power = (em.a_act_power || 0) + (em.b_act_power || 0) + (em.c_act_power || 0);
    callback(Math.round(power), true);
    return;
  }

  if (A.gridSource === "remote") {
    Shelly.call("HTTP.GET", {
      url: "http://" + A.gridSourceIp + "/rpc/EM.GetStatus?id=" + A.gridSourceEmId,
      timeout: CONFIG.httpTimeout
    }, function (res, error_code) {
      if (error_code !== 0 || !res || res.code !== 200) { callback(0, false); return; }
      let power = jsonNum(res.body, "total_act_power");
      res = null;
      if (power === null) { callback(0, false); return; }
      callback(Math.round(power), true);
    });
    return;
  }

  if (A.gridSource === "http_json") {
    Shelly.call("HTTP.GET", { url: A.gridSourceUrl, timeout: CONFIG.httpTimeout }, function (res, error_code) {
      if (error_code !== 0 || !res || res.code !== 200) { callback(0, false); return; }
      let data;
      try { data = JSON.parse(res.body); } catch (e) { callback(0, false); return; }
      res = null;
      let value = readFieldPath(data, A.gridSourceField);
      data = null;
      if (value === undefined) { callback(0, false); return; }
      callback(Math.round(A.gridSourceInvert ? (value * -1) : value), true);
    });
    return;
  }

  callback(0, false);
}

// =====================================================
// Snapshot je Hub
//
// HUBS[i]  - genau die Felder, die status_api ausliefert (Dashboard-
//            Schnittstelle unveraendert). minVol als Rohwert (331 = 3,31 V).
// WSTATE[i]- Zusatzfelder und Merker des Watchdogs.
// Beide werden einmal angelegt und danach nur ueberschrieben - kein neues
// Objekt je Poll.
// =====================================================

let HUBS = [];
let WSTATE = [];
for (let hi = 0; hi < CONFIG.devices.length; hi++) {
  HUBS[hi] = {
    id: hi, soc: null, power: 0, acMode: null, socLimit: null,
    gridReverse: null, pv: null, minVol: null, online: false
  };
  WSTATE[hi] = {
    hyperTemp: null,
    minVolSn: null,
    minVolSoc: null,
    ts: 0,               // letzter erfolgreicher Poll
    failSince: 0,        // Beginn des aktuellen Ausfalls (0 = keiner)
    failReason: "",
    offlineMsgSent: false,
    akkuVollMsgSent: false,
    hyperTempMsgSent: false,
    lowVoltMsgSent: {}
  };
}

let LATEST_STATUS = {
  grid: { power: 0, online: false },
  hubs: HUBS
};
let STATUS_BODY = JSON.stringify(LATEST_STATUS);

function setHubOffline(index) {
  let h = HUBS[index];
  h.soc = null; h.power = 0; h.acMode = null; h.socLimit = null;
  h.gridReverse = null; h.pv = null; h.minVol = null; h.online = false;
}

// Laeuft ueber alle Packs in packData (Array aus FLACHEN Objekten), jede
// Suche auf das jeweilige Pack-Objekt begrenzt - Feldreihenfolge egal.
// Setzt minVol (kleinste Zellspannung > 0, schlafende Packs zaehlen nicht)
// und prueft - falls ueberwacht - die Unterspannung je Pack.
// logPacks: bei debug=true nur im Watchdog-Poll - liefert eine kompakte
// Zeile "sn:soc%/volt" je Pack zurueck, sonst "".
function scanPacks(index, body, checkVolt, logPacks) {
  let hub = HUBS[index];
  let ws = WSTATE[index];
  let lbl = CONFIG.devices[index].label;

  hub.minVol = null;
  ws.minVolSn = null;
  ws.minVolSoc = null;

  let p = jsonValuePos(body, "packData", 0, -1);
  if (p < 0 || body.charAt(p) !== "[") return logPacks ? "keine packData" : "";
  let arrEnd = body.indexOf("]", p);
  if (arrEnd < 0) return logPacks ? "packData unvollstaendig" : "";
  let packLog = "";

  let pos = p + 1;
  let count = 0;
  while (true) {
    let objStart = body.indexOf("{", pos);
    if (objStart < 0 || objStart > arrEnd) break;
    let objEnd = body.indexOf("}", objStart);
    if (objEnd < 0 || objEnd > arrEnd) break;
    count++;

    let raw = jsonNum(body, "minVol", objStart, objEnd);
    if (logPacks) {
      let lsn = jsonStr(body, "sn", objStart, objEnd);
      let lsoc = jsonNum(body, "socLevel", objStart, objEnd);
      packLog += (count > 1 ? ", " : "") + (lsn !== null ? lsn : "#" + count) + ":" +
        (lsoc !== null ? lsoc + "%" : "?%") + "/" +
        (raw === null ? "?V" : raw > 0 ? (raw / 100).toFixed(2) + "V" : "0V (schlaeft)");
    }
    if (raw !== null && raw > 0) {
      let sn = null;
      let packSoc = null;
      if (checkVolt || hub.minVol === null || raw < hub.minVol) {
        sn = jsonStr(body, "sn", objStart, objEnd);
        if (sn === null) sn = "#" + count;
        packSoc = jsonNum(body, "socLevel", objStart, objEnd);
      }

      if (checkVolt) {
        let volt = raw / 100;
        if (volt < W.minVoltWarn) {
          if (!ws.lowVoltMsgSent[sn]) {
            ws.lowVoltMsgSent[sn] = true;
            notify("⚠️ " + lbl + " Zelle " + sn + " nur " + volt + "V");
          }
        } else if (volt > W.minVoltReset) {
          ws.lowVoltMsgSent[sn] = false;
        }
      }

      if (hub.minVol === null || raw < hub.minVol) {
        hub.minVol = raw;
        ws.minVolSn = sn;
        ws.minVolSoc = packSoc;
      }
    }
    pos = objEnd + 1;
  }
  return packLog;
}

// Wertet einen Report aus. true = ok, false = nicht auswertbar.
function extractHub(index, body, watchNow, logPacks) {
  if (!endsWithBrace(body)) return false;
  let soc = jsonNum(body, "electricLevel");
  if (soc === null) return false;

  let hub = HUBS[index];
  let acMode = jsonNum(body, "acMode");
  let power = 0;
  if (acMode === 2) power = jsonNum(body, "outputHomePower") || 0;
  else if (acMode === 1) power = (jsonNum(body, "gridInputPower") || 0) * -1;

  hub.soc = soc;
  hub.power = Math.round(power);
  hub.acMode = acMode;
  hub.socLimit = jsonNum(body, "socLimit");
  hub.gridReverse = jsonNum(body, "gridReverse");
  hub.pv = jsonNum(body, "solarInputPower");
  hub.online = true;

  let ht = jsonNum(body, "hyperTmp");
  WSTATE[index].hyperTemp = (ht !== null) ? (ht - 2731) / 10 : null;

  let packLog = scanPacks(index, body, watchNow, logPacks);
  if (logPacks) {
    logDebug(CONFIG.devices[index].label + ": SoC " + soc + "%, " +
      (ht !== null ? ((ht - 2731) / 10).toFixed(1) + "C" : "?C") + " | Packs: " + (packLog || "keine"));
  }
  return true;
}

function pollHub(index, watchNow, logPacks, callback) {
  let cfg = CONFIG.devices[index];
  Shelly.call("HTTP.GET", {
    url: "http://" + cfg.ip + "/properties/report",
    timeout: CONFIG.httpTimeout
  }, function (res, error_code, error_msg) {
    if (error_code !== 0 || !res || res.code !== 200) {
      if (DBG) logDebug("HTTP-Fehler bei " + cfg.label + ": Code=" + error_code + " HTTP=" + (res ? res.code : "null") + " " + error_msg);
      res = null;
      setHubOffline(index);
      callback(index, "nicht erreichbar");
      return;
    }
    let body = res.body;
    res = null;
    let ok = false;
    try { ok = !!body && extractHub(index, body, watchNow, logPacks); } catch (e) { ok = false; }
    body = null;
    if (!ok) {
      setHubOffline(index);
      callback(index, "Report unlesbar");
      return;
    }
    WSTATE[index].ts = Date.now();
    callback(index, "");
  });
}

// =====================================================
// Watchdog-Auswertung
// =====================================================

function watchdogCheckHub(index, failReason) {
  let cfg = CONFIG.devices[index];
  let ws = WSTATE[index];
  let hub = HUBS[index];
  let now = Date.now();

  if (failReason !== "") {
    if (ws.failSince === 0) ws.failSince = now;
    ws.failReason = failReason;
    let mins = Math.floor((now - ws.failSince) / 60000);
    if (DBG) logDebug("Watchdog: " + cfg.label + " " + failReason + " seit " + mins + " min");
    if (!ws.offlineMsgSent && (now - ws.failSince) >= W.offlineAlarmMin * 60000) {
      ws.offlineMsgSent = true;
      notify("❌ " + cfg.label + ": " + failReason + " seit " + mins + " min");
    }
    return;
  }

  if (ws.failSince !== 0) {
    if (ws.offlineMsgSent) notify("✅ " + cfg.label + ": wieder erreichbar");
    ws.failSince = 0;
    ws.failReason = "";
    ws.offlineMsgSent = false;
  }

  if (hub.soc >= W.vollSchwelle && !ws.akkuVollMsgSent) {
    ws.akkuVollMsgSent = true;
    notify("🔋 " + cfg.label + " voll (" + hub.soc + "%)");
  } else if (hub.soc < W.entladeReset) {
    ws.akkuVollMsgSent = false;
  }

  if (isNum(ws.hyperTemp)) {
    if (ws.hyperTemp > W.tempWarn) {
      if (!ws.hyperTempMsgSent) {
        ws.hyperTempMsgSent = true;
        notify("🔥 " + cfg.label + " Temp hoch: " + ws.hyperTemp.toFixed(1) + "C");
      }
    } else if (ws.hyperTemp < W.tempReset) {
      ws.hyperTempMsgSent = false;
    }
  }
}

// Werte fuer Digest/Log. Aelter als zwei Watchdog-Intervalle = "n/a".
function deviceValues(index) {
  let hub = HUBS[index];
  let ws = WSTATE[index];
  let fresh = hub.online && ws.ts > 0 && (Date.now() - ws.ts) < 2 * W.intervalSec * 1000;
  if (!fresh) return "n/a";
  let tempStr = isNum(ws.hyperTemp) ? (ws.hyperTemp.toFixed(1) + "C") : "n/a";
  let volStr = (hub.minVol !== null) ? ((hub.minVol / 100).toFixed(2) + "V") : "n/a";
  return hub.soc + "%, " + tempStr + ", " + volStr;
}

function sendDigest(headerText) {
  let text = headerText;
  for (let i = 0; i < CONFIG.devices.length; i++) {
    let cfg = CONFIG.devices[i];
    if (!cfg.watch) continue;
    let lbl = cfg.label ? cfg.label.substr(0, 6) : "??????";
    text += "\n" + lbl + ": " + deviceValues(i);
  }
  notify(text);
}

// Wird per Schedule (Script.Eval) aufgerufen.
function sendAstroStatus(type) {
  if (DBG) logDebug("Astro-Event: " + type);
  sendDigest(type === "sunset" ? "🌇 Abend-Update:" : "🌅 Morgen-Update:");
  notifyPump();
}

// Nur die Schedules loeschen, die dieses Script selbst angelegt hat
// (Script.Eval mit der eigenen Script-ID) - fremde bleiben unberuehrt.
function isOwnSchedule(job, scriptId) {
  if (!job || !job.calls) return false;
  for (let k = 0; k < job.calls.length; k++) {
    let c = job.calls[k];
    if (c && c.method && c.method.toLowerCase() === "script.eval" &&
        c.params && c.params.id === scriptId) return true;
  }
  return false;
}

function setupAstroSchedules(done) {
  let scriptId = Shelly.getCurrentScriptId();
  let specs = [
    ["@sunrise" + (W.sunriseOffset >= 0 ? "+" : "") + W.sunriseOffset, "sunrise"],
    ["@sunset" + (W.sunsetOffset >= 0 ? "+" : "") + W.sunsetOffset, "sunset"]
  ];

  let createNext = function (n) {
    if (n >= specs.length) { done(); return; }
    let spec = specs[n][0];
    Shelly.call("Schedule.Create", {
      "enable": true,
      "timespec": spec,
      "calls": [{ "method": "Script.Eval", "params": { "id": scriptId, "code": "sendAstroStatus('" + specs[n][1] + "')" } }]
    }, function (res, err, msg) {
      if (err !== 0) print("Fehler Schedule (" + spec + "): " + msg);
      else if (DBG) logDebug("Schedule angelegt: " + spec);
      createNext(n + 1);
    });
  };

  let deleteNext = function (ids, n) {
    if (n >= ids.length) { createNext(0); return; }
    Shelly.call("Schedule.Delete", { id: ids[n] }, function (res, err, msg) {
      if (err !== 0) print("Fehler beim Loeschen von Schedule " + ids[n] + ": " + msg);
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

// =====================================================
// Scheduler - EIN Takt fuer beide Module
//
// fast: Dashboard offen oder manuelles Laden -> Netz + alle Hubs (8 s)
// due : Watchdog-Intervall abgelaufen      -> ueberwachte Hubs
// Keins von beiden: Leerlauf, keine Abfrage.
// =====================================================

let lastRequestAt = 0;
let IDLE_MS = 15000;
let lastWatchPoll = 0;
let lastFast = false;

function pollHubsSeq(index, fast, due, callback) {
  if (index >= CONFIG.devices.length) { callback(); return; }
  let watch = WD_ON && CONFIG.devices[index].watch;
  if (!fast && !(due && watch)) {
    pollHubsSeq(index + 1, fast, due, callback);
    return;
  }
  // Pack-Details nur im Watchdog-Poll ins Log - im 8-s-Takt waere das zu viel
  pollHub(index, watch, DBG && due && watch, function (idx, failReason) {
    if (watch) {
      try { watchdogCheckHub(idx, failReason); } catch (e) { print("Watchdog-Fehler bei " + CONFIG.devices[idx].label + ": " + e); }
    }
    pollHubsSeq(index + 1, fast, due, callback);
  });
}

function tick() {
  let now = Date.now();
  let fast = API_ON && ((now - lastRequestAt) <= IDLE_MS || anyManualActive());
  // 1 s Toleranz: der Takt trifft das Intervall sonst je nach Timer-Jitter
  // erst einen Tick spaeter.
  let due = WD_ON && WATCH_COUNT > 0 && (now - lastWatchPoll) >= W.intervalSec * 1000 - 1000;

  if (DBG && fast !== lastFast) {
    logDebug(fast ? ("Schneller Takt AN (" + (anyManualActive() ? "manuelles Laden" : "Dashboard aktiv") + ")") : "Schneller Takt AUS - Leerlauf");
  }
  lastFast = fast;

  if (!fast && !due) { notifyPump(); return; }
  if (bgRunning || busyNow()) return;

  bgRunning = true;
  busyEnter();
  // Beginn statt Ende des Durchlaufs merken - sonst wandert das Intervall
  // um die Dauer jedes Polls nach hinten.
  if (due) lastWatchPoll = now;

  let afterHubs = function () {
    if (fast) {
      try { STATUS_BODY = JSON.stringify(LATEST_STATUS); } catch (e) { print("status_api: " + e); }
    }
    bgRunning = false;
    busyLeave();
    // Erst NACH busyLeave(): busyNow() soll hier echte fremde
    // Nebenlaeufigkeit zeigen, nicht den eigenen, gerade beendeten Poll.
    if (fast) {
      try { checkAutoStop(); } catch (e) { print("Auto-Stop-Fehler: " + e); }
    }
    notifyPump();
  };

  if (fast) {
    updateGridPowerStatus(function (power, online) {
      LATEST_STATUS.grid.power = power;
      LATEST_STATUS.grid.online = online;
      pollHubsSeq(0, fast, due, afterHubs);
    });
  } else {
    pollHubsSeq(0, fast, due, afterHubs);
  }
}

// =====================================================
// Endpunkte (Modul API)
// =====================================================

function buildDeviceDefaults() {
  let arr = [];
  for (let i = 0; i < CONFIG.devices.length; i++) {
    let d = CONFIG.devices[i];
    arr[i] = {
      id: i, ip: d.ip, label: d.label,
      minSoc: d.minSoc, maxSoc: d.maxSoc,
      maxOutput: d.maxOutput, maxInputPower: d.maxInputPower,
      inputLimit: d.inputLimit,
      dischargeAllowed: d.dischargeAllowed !== false,
      reverse: !!d.reverse
    };
  }
  return arr;
}

// Private-Network-Access-Preflight von Chrome & Co. beantworten.
function handlePreflight(req, res) {
  if (req.method !== "OPTIONS") return false;
  res.code = 200;
  res.headers = [
    ["Access-Control-Allow-Origin", "*"],
    ["Access-Control-Allow-Private-Network", "true"],
    ["Access-Control-Allow-Methods", "GET, OPTIONS"],
    ["Access-Control-Allow-Headers", "*"]
  ];
  res.body = "";
  res.send();
  return true;
}

function sendJson(res, code, body) {
  res.code = code;
  res.headers = [["Content-Type", "application/json"], ["Access-Control-Allow-Origin", "*"]];
  res.body = body;
  res.send();
}

// Sammelabfrage: mehrere offene Dashboards erzeugen genau ein KVS.GetMany.
let CONFIG_WAIT_MS = 200;
let CONFIG_WAIT_MAX = 10;
let configPending = false;
let configWaiters = [];

function answerConfigWaiters(body) {
  for (let i = 0; i < configWaiters.length; i++) sendJson(configWaiters[i], 200, body);
  configWaiters = [];
}

function serveConfig(res, attempt) {
  if (attempt === 0) {
    if (configPending) { configWaiters[configWaiters.length] = res; return; }
    configPending = true;
  }
  if (busyNow() && attempt < CONFIG_WAIT_MAX) {
    Timer.set(CONFIG_WAIT_MS, false, function () { serveConfig(res, attempt + 1); });
    return;
  }
  if (DBG) logDebug("config_api: lese KVS" + (attempt > 0 ? " (nach " + (attempt * CONFIG_WAIT_MS) + " ms Wartezeit" +
    (busyNow() ? ", Slot weiter belegt - trotzdem" : "") + ")" : ""));

  busyEnter();
  let devices = buildDeviceDefaults();
  let setpoint = 0;
  let dischargeFixed = 0;

  kvsGetAll(function (store) {
    let v = kvsValue(store, "zdmc_setpoint");
    if (v !== undefined) setpoint = Number(v);
    let df = kvsValue(store, "zdmc_dischargeFixed");
    if (df !== undefined) dischargeFixed = Number(df);

    for (let i = 0; i < devices.length; i++) {
      let d = kvsValue(store, "zdmc_dev" + i + "_dischargeAllowed");
      let r = kvsValue(store, "zdmc_dev" + i + "_reverse");
      let m = kvsValue(store, "zdmc_dev" + i + "_minSoc");
      let l = kvsValue(store, "zdmc_dev" + i + "_inputLimit");
      if (d !== undefined) devices[i].dischargeAllowed = (Number(d) !== 0);
      if (r !== undefined) devices[i].reverse = (Number(r) !== 0);
      if (m !== undefined) devices[i].minSoc = Number(m);
      if (l !== undefined) devices[i].inputLimit = Number(l);
    }
    let kvsOk = (store !== null);
    store = null;

    let body = JSON.stringify({
      version: API_VERSION,
      setpoint: setpoint,
      hysteresis: CONFIG.api.hysteresis,
      dischargeFixed: dischargeFixed,
      dischargeStartupPower: CONFIG.api.dischargeStartupPower,
      devices: devices
    });

    busyLeave();
    configPending = false;
    if (DBG) {
      let line = "config_api: Antwort" + (!kvsOk ? " (KVS NICHT lesbar - CONFIG-Vorgaben)" : "") +
        " setpoint=" + setpoint + " dischargeFixed=" + dischargeFixed;
      for (let j = 0; j < devices.length; j++) {
        line += " | dev" + j + " da=" + (devices[j].dischargeAllowed ? 1 : 0) + " rv=" + (devices[j].reverse ? 1 : 0) +
          " minSoc=" + devices[j].minSoc + " il=" + devices[j].inputLimit;
      }
      logDebug(line + (configWaiters.length ? " (+" + configWaiters.length + " wartende Anfragen)" : ""));
    }
    sendJson(res, 200, body);
    answerConfigWaiters(body);
  });
}

function keysHasField(keys, key) {
  for (let i = 0; i < keys.length; i++) {
    if (keys[i] === key) return true;
  }
  return false;
}

// Beim Beenden des manuellen Ladens nur mit inputLimit=0: Schalter aus
// preManual ergaenzen (explizit mitgeschickte Werte bleiben unangetastet).
function fillManualStopDefaults(data, keys) {
  let originalLen = keys.length;
  for (let i = 0; i < originalLen; i++) {
    let pk = parseDeviceKey(keys[i]);
    if (!pk || pk.field !== "inputLimit") continue;
    if (Number(data[keys[i]]) !== 0) continue;
    let idx = pk.index;
    if (!deviceState[idx] || !isManualActive(deviceState[idx])) continue;

    let daKey = "zdmc_dev" + idx + "_dischargeAllowed";
    let rvKey = "zdmc_dev" + idx + "_reverse";
    let restore = preManual[idx] || { dischargeAllowed: true, reverse: true };
    if (!keysHasField(keys, daKey)) { data[daKey] = restore.dischargeAllowed ? 1 : 0; keys[keys.length] = daKey; }
    if (!keysHasField(keys, rvKey)) { data[rvKey] = restore.reverse ? 1 : 0; keys[keys.length] = rvKey; }
    if (DBG) logDebug("kvs_set_api: Stopp dev" + idx + " ergaenzt um " + daKey + "=" + data[daKey] + ", " + rvKey + "=" + data[rvKey] +
      (preManual[idx] ? " (aus Vorzustand)" : " (Fallback 1/1)"));
  }
}

// Nacheinander schreiben, mit Pause zwischen den Schritten.
function writeKeys(res, data, keys, index, allOk) {
  if (index >= keys.length) {
    if (allOk) applyDeviceKeysToState(data, keys);
    busyLeave();
    if (DBG) logDebug("kvs_set_api: " + (allOk ? "OK" : "FEHLER") + ", " + keys.length + " Key(s) geschrieben" +
      (anyManualActive() ? " - manuelles Laden aktiv" : ""));
    sendJson(res, allOk ? 200 : 500, JSON.stringify({ success: allOk, written: keys.length }));
    return;
  }
  let k = keys[index];
  kvsSetOne(k, data[k], function (ok) {
    let nextOk = allOk && ok;
    let nextIndex = index + 1;
    if (nextIndex >= keys.length) { writeKeys(res, data, keys, nextIndex, nextOk); return; }
    Timer.set(KVS_STEP_PAUSE_MS, false, function () { writeKeys(res, data, keys, nextIndex, nextOk); });
  });
}

function handleKvsSet(req, res) {
  let dataParam = getQueryParam(req.query, "data");
  if (DBG) logDebug("kvs_set_api: Aufruf data=" + dataParam);
  if (dataParam === undefined) {
    sendJson(res, 400, JSON.stringify({ success: false, error: "missing data param" }));
    return;
  }
  let data = null;
  try { data = JSON.parse(dataParam); } catch (e) { data = null; }
  dataParam = null;
  if (!data || typeof data !== "object") {
    sendJson(res, 400, JSON.stringify({ success: false, error: "invalid json" }));
    return;
  }

  let keys = Object.keys(data);
  let allowedKeys = [];
  for (let i = 0; i < keys.length; i++) {
    if (keys[i].indexOf("zdmc_") !== 0) continue;
    // Der Regler akzeptiert 0 ODER >= dischargeStartupPower und verwirft
    // alles dazwischen kommentarlos - hier vorab ablehnen.
    if (keys[i] === "zdmc_dischargeFixed") {
      let dv = Number(data[keys[i]]);
      if (dv !== 0 && !(dv >= CONFIG.api.dischargeStartupPower)) {
        if (DBG) logDebug("kvs_set_api: abgelehnt - zdmc_dischargeFixed=" + dv + " (erlaubt 0 oder >= " + CONFIG.api.dischargeStartupPower + ")");
        sendJson(res, 400, JSON.stringify({
          success: false,
          error: "dischargeFixed muss 0 oder >= " + CONFIG.api.dischargeStartupPower + " sein"
        }));
        return;
      }
    }
    allowedKeys[allowedKeys.length] = keys[i];
  }
  if (DBG && allowedKeys.length < keys.length) logDebug("kvs_set_api: " + (keys.length - allowedKeys.length) + " Key(s) ohne Praefix zdmc_ ignoriert");

  if (allowedKeys.length === 0) {
    sendJson(res, 200, JSON.stringify({ success: true, written: 0 }));
    return;
  }

  writeWhenFree(res, data, allowedKeys, 0);
}

// Wie config_api: kurz auf einen freien Slot warten (hoechstens
// CONFIG_WAIT_MAX * CONFIG_WAIT_MS), dann auf jeden Fall schreiben - ein
// Dashboard-Klick darf nicht verloren gehen. Der Zustandsvergleich
// (fill/capture) laeuft erst jetzt, damit er einen eventuell in der
// Wartezeit gelaufenen Auto-Stop schon sieht.
function writeWhenFree(res, data, keys, attempt) {
  if (busyNow() && attempt < CONFIG_WAIT_MAX) {
    Timer.set(CONFIG_WAIT_MS, false, function () { writeWhenFree(res, data, keys, attempt + 1); });
    return;
  }
  if (DBG && attempt > 0) logDebug("kvs_set_api: schreibe nach " + (attempt * CONFIG_WAIT_MS) + " ms Wartezeit" + (busyNow() ? " (Slot weiter belegt - trotzdem)" : ""));
  fillManualStopDefaults(data, keys);
  captureManualTransitions(data, keys);
  // Schreibvorgang belegt den Schutz: kein Poll und kein Nachrichtenversand
  // parallel, und checkAutoStop() kollidiert nicht mit einem Dashboard-Klick.
  busyEnter();
  writeKeys(res, data, keys, 0, true);
}

function registerEndpoints() {
  HTTPServer.registerEndpoint("config_api", function (req, res) {
    if (handlePreflight(req, res)) return;
    lastRequestAt = Date.now();
    try { serveConfig(res, 0); } catch (e) {
      print("config_api: " + e);
      configPending = false;
      sendJson(res, 500, JSON.stringify({ success: false, error: "internal" }));
    }
  });

  HTTPServer.registerEndpoint("status_api", function (req, res) {
    if (handlePreflight(req, res)) return;
    lastRequestAt = Date.now();
    sendJson(res, 200, STATUS_BODY);
  });

  HTTPServer.registerEndpoint("kvs_set_api", function (req, res) {
    if (handlePreflight(req, res)) return;
    lastRequestAt = Date.now();
    try { handleKvsSet(req, res); } catch (e) {
      print("kvs_set_api: " + e);
      sendJson(res, 500, JSON.stringify({ success: false, error: "internal" }));
    }
  });
}

// =====================================================
// Start - nacheinander, damit die Startphase keine Spitze erzeugt:
// KVS-Zustand lesen -> Schedules -> Takt starten.
// =====================================================

function printBanner() {
  print("--------------------------------");
  print("zenDash-API + Watchdog v" + VERSION + " (API-Schnittstelle " + API_VERSION + ")");
  print("Module     : API " + (API_ON ? "AN" : "AUS") + " | Watchdog " + (WD_ON ? "AN" : "AUS"));
  let line = "Geraete    :";
  for (let i = 0; i < CONFIG.devices.length; i++) {
    line += " " + CONFIG.devices[i].label + (CONFIG.devices[i].watch && WD_ON ? "[W]" : "");
  }
  print(line);
  if (WD_ON) print("Watchdog   : alle " + W.intervalSec + " s, Offline-Alarm nach " + W.offlineAlarmMin + " min");
  let ziel = "";
  if (N.enabled) ziel = (N.typ === "WEBHOOK") ? (" -> " + String(N.webhookUrl).split("/")[2]) : " -> callmebot";
  print("Nachrichten: " + (N.enabled ? N.typ + ziel : "aus") + " | Debug: " + (DBG ? "AN" : "AUS"));
  print("--------------------------------");
}

function startTicking() {
  Timer.set(CONFIG.api.pollIntervalSec * 1000, true, tick);
  Timer.set(1000, false, tick);
  if (API_ON) print("Endpunkte: config_api / status_api / kvs_set_api auf DIESEM Geraet");
}

function startWatchdogPart() {
  if (!WD_ON) { startTicking(); return; }
  notify("✅ zenDash/Watchdog v" + VERSION + " gestartet (" + WATCH_COUNT + "/" + CONFIG.devices.length + " ueberwacht)");
  setupAstroSchedules(startTicking);
}

printBanner();
if (API_ON) {
  registerEndpoints();
  initDeviceState(startWatchdogPart);
} else if (WD_ON) {
  startWatchdogPart();
}