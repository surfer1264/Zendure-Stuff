// =====================================================================
// Zendure Dashboard API (zendure_dashboard_api.js)
//
// WICHTIG: CONFIG.devices und CONFIG.gridSource* MUESSEN zu der CONFIG in
// RegelController-Script passen (gleiche IPs, gleiche Reihenfolge der
// Geraete = gleicher Index i wie "zdmc_dev{i}_..."). 
//
// Endpunkte (alle mit CORS, koennen von jeder Seite/jedem Host aus
// aufgerufen werden):
//   GET config_api    -> { version, setpoint, hysteresis, devices:[...] }
//                        devices enthaelt die aktuellen KVS-Werte fuer
//                        dischargeAllowed / reverse / minSoc / inputLimit.
//                        hysteresis ist reine ANZEIGE (siehe CONFIG unten).
//   GET status_api    -> { grid:{power,online},
//                          hubs:[{id,soc,power,acMode,socLimit,
//                                 gridReverse,pv,minVol,online}] }
//                        Kein Verlauf - den fuehrt die Dashboard-Seite selbst.
//   GET kvs_set_api?data={"zdmc_...":wert}  -> { success, written }
//                        schreibt jeden Key mit Praefix zdmc_ ungeprueft.
// =====================================================================

let CONFIG = {
  // ------------------------------------------------------------------
  // GERAETEBLOCK - 1:1 aus zerooutput_multi_kvs.js kopieren, gleiche
  // Reihenfolge (Index i == zdmc_dev{i}_... in der KVS). Alle Felder des
  // Regel-Scripts duerfen stehen bleiben; dieses Script nutzt sie zum Teil
  // nur als Grenzwerte fuer die Dashboard-Regler.
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
      dryRun: false
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
      dryRun: false
    }
  ],

  // ------------------------------------------------------------------
  // WO LIEGT DIE KVS?
  //   "local"  - dieses Script laeuft auf demselben Geraet wie das
  //              Regel-Script und greift direkt zu (Shelly.call).
  //   "<IP>"   - dieses Script laeuft auf einem EIGENEN Shelly; die KVS
  //              wird per nativer RPC ueber HTTP gelesen und geschrieben:
  //              http://<IP>/rpc/KVS.GetMany bzw. /rpc/KVS.Set
  //
  // Bei getrenntem Betrieb ausserdem gridSource auf "remote" stellen und
  // gridSourceIp auf den Shelly mit der EM-Messung zeigen lassen.
  // Voraussetzung: auf dem KVS-Geraet ist keine Authentifizierung aktiv.
  // ------------------------------------------------------------------
  kvsHost: "192.168.178.117",

  hysteresis: 12,

  // ------------------------------------------------------------------
  // SMARTMETER SECTION - 1:1 Struktur/Feldnamen wie in zerooutput_multi_kvs.js
  gridSource: "remote", // "local", "remote", "http_json"
  // ------------------------------------------------------------------
  // ONLY required/used when gridSource = "remote".
  // IP address of the Shelly Pro 3EM providing the grid measurement.
  gridSourceIp: "192.168.178.117",
  // EM channel id to read (usually 0). Only used when gridSource = "remote".
  gridSourceEmId: 0,
  // ------------------------------------------------------------------
  // ONLY requested when gridSource = "http_json". Example is made for the Zendure Smart Meter 3CT, read the DOC for other devices.
  gridSourceUrl: "http://<IP-of-your-meter>/properties/report",
  // Name of the JSON field in that response which holds the total grid power in watts.
  // Kann auch ein Array sein fuer verschachtelte Pfade, z.B. ["StatusSNS","SML","Watt_Summe"].
  gridSourceField: "total_power",
  // Set to true if the sign of gridSourceField is inverted 
  gridSourceInvert: false,

  httpTimeout: 5,

  // Bewusst langsamer als die Dashboard-Seite (4 s). 
  // Die Anzeige wird dadurch bis zu 8 s alt
  pollIntervalSec: 8
};

// Versionsstand dieses Scripts. Wird von config_api mitgeliefert, damit das
let VERSION = "2.1";

// Grenzen wie im Regel-Script normalisieren, damit die Dashboard-Regler
// dieselben Bereiche anbieten, die readKvsOverrides() dort auch akzeptiert.
for (let i = 0; i < CONFIG.devices.length; i++) {
  let d = CONFIG.devices[i];
  d.minSoc = Math.max(10, Math.min(99, d.minSoc));
  d.maxSoc = Math.max(d.minSoc + 1, Math.min(100, d.maxSoc));
  if (typeof d.inputLimit !== "number") d.inputLimit = 0;
  d.inputLimit = Math.max(0, Math.min(d.maxInputPower, d.inputLimit));
}

let KVS_MATCH = "zdmc_*";

// Zwischenspeicher fuer Hintergrund-Polling
let LATEST_STATUS = {
  grid: { power: 0, online: false },
  hubs: []
};

// Fertige JSON-Antwort fuer status_api. Wird einmal je Hintergrund-Durchlauf
// gebaut statt bei jeder Anfrage: bei mehreren offenen Dashboards sparte das
// sonst mehrfach dieselbe Serialisierung derselben Daten.
let STATUS_BODY = JSON.stringify(LATEST_STATUS);

// Zeitpunkt der letzten Anfrage von der Dashboard-Seite (irgendein
// Endpunkt). Solange laenger nichts reinkam, pausiert backgroundPoll die
// eigentlichen HTTP-Abfragen an Netzzaehler/Hubs (kein Dashboard offen =
// keine Anfragen noetig).
let lastRequestAt = 0;
let IDLE_MS = 15000;


// =====================================================
// Ueberlappungsschutz
//
// Die beiden speicherhungrigen Vorgaenge sind das Parsen der Hub-Antworten
// (/properties/report, mehrere kB Rohtext + Objektbaum) und das KVS.GetMany
// in config_api. Laufen sie gleichzeitig, addieren sich ihre Spitzen.
//
// WICHTIG: Das war frueher EIN Boolean fuer ZWEI unabhaengige Nutzer - wer
// zuerst freigab, gab auch fuer den anderen frei. Gab config_api nach seiner
// Wartezeit auf und legte danach das Flag um, startete der naechste Timer-Takt
// einen zweiten Hintergrund-Durchlauf, obwohl der erste noch lief. Bei
// langsamen oder nicht erreichbaren Hubs stapelten sich so mehrere Durchlaeufe
// mit je einem geparsten Report im Heap. Deshalb jetzt ein Zaehler statt eines
// Flags, plus ein eigener Riegel fuer den Hintergrund-Durchlauf.
// =====================================================

let busyCount = 0;
let busySince = 0;

// Eigener Schutz des Hintergrund-Durchlaufs gegen sich selbst - unabhaengig
// davon, was die Endpunkte mit dem Zaehler machen.
let bgRunning = false;

// Sicherung gegen ein haengendes Callback. Muss groesser sein als der
// laengstmoegliche Durchlauf, sonst greift sie mitten im Normalbetrieb und
// erlaubt genau die Ueberlappung, die sie verhindern soll:
// jede Abfrage (Netzzaehler + jeder Hub) kann in den Timeout laufen.
let BUSY_TIMEOUT_MS = (CONFIG.devices.length + 1) * CONFIG.httpTimeout * 1000 + 5000;

// Wie lange config_api hoechstens auf einen freien Slot wartet, bevor es
// trotzdem loslegt: CONFIG_WAIT_MAX * CONFIG_WAIT_MS.
let CONFIG_WAIT_MS = 200;
let CONFIG_WAIT_MAX = 10;

function busyNow() {
  if (busyCount > 0 && (Date.now() - busySince) > BUSY_TIMEOUT_MS) {
    print("Ueberlappungsschutz haengt seit ueber " + (BUSY_TIMEOUT_MS / 1000) + " s - zurueckgesetzt");
    busyCount = 0;
    bgRunning = false;
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
// KVS-Helfer
// =====================================================

function kvsItemsToMap(rawItems) {
  let map = {};
  if (!rawItems) return map;

  if (Array.isArray(rawItems)) {
    for (let i = 0; i < rawItems.length; i++) {
      let entry = rawItems[i];
      if (entry && entry.key !== undefined) {
        map[entry.key] = entry.value;
      }
    }
  } else {
    for (let k in rawItems) {
      map[k] = rawItems[k].value !== undefined ? rawItems[k].value : rawItems[k];
    }
  }
  return map;
}

// ---------------------------------------------------------------------
// KVS-Zugriff: lokal per Shelly.call, entfernt per nativer RPC ueber HTTP.
//
// Beide Wege liefern denselben "store" an den Aufrufer:
//   lokal    - ein fertiges Objekt {key: value, ...}
//   entfernt - der ROHE Antworttext; einzelne Werte holt kvsValue() daraus,
//              ohne JSON.parse (siehe Begruendung bei jsonNum unten)
// Bei einem Fehler ist store null; der Aufrufer arbeitet dann mit den
// Vorgabewerten aus CONFIG weiter, statt die Anfrage haengen zu lassen.
// ---------------------------------------------------------------------

function kvsIsRemote() {
  return CONFIG.kvsHost !== "local" && CONFIG.kvsHost !== "";
}

function kvsGetAll(callback) {
  if (!kvsIsRemote()) {
    Shelly.call("KVS.GetMany", { match: KVS_MATCH }, function (result, error_code) {
      if (error_code !== 0 || !result || !result.items) { callback(null); return; }
      callback(kvsItemsToMap(result.items));
    });
    return;
  }

  Shelly.call(
    "HTTP.GET",
    {
      url: "http://" + CONFIG.kvsHost + "/rpc/KVS.GetMany?match=" + KVS_MATCH,
      timeout: CONFIG.httpTimeout
    },
    function (res, error_code) {
      if (error_code !== 0 || !res || res.code !== 200) { callback(null); return; }
      let body = res.body;
      res = null;
      callback(body);
    }
  );
}

// Holt einen einzelnen Wert aus dem store - egal welcher Form.
function kvsValue(store, key) {
  if (store === null || store === undefined) return undefined;

  if (typeof store === "string") {
    let i = store.indexOf('"' + key + '"');
    if (i < 0) return undefined;
    // Nach dem Schluessel folgt das Wertobjekt; dessen "value" lesen.
    let v = jsonNum(store, "value", i);
    return (v === null) ? undefined : v;
  }

  return store[key];
}

// Nur Zahlen zulassen. Schuetzt beim entfernten Schreiben davor, dass ein
// Wert aus dem Query-String die URL zerlegt, und haelt die KVS sauber -
// alle zdmc_-Werte sind numerisch.
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
  if (str === null) { callback(false); return; }

  if (!kvsIsRemote()) {
    Shelly.call("KVS.Set", { key: key, value: str }, function (result, error_code) {
      callback(error_code === 0);
    });
    return;
  }

  Shelly.call(
    "HTTP.GET",
    {
      url: "http://" + CONFIG.kvsHost + "/rpc/KVS.Set?key=" + key + "&value=" + str,
      timeout: CONFIG.httpTimeout
    },
    function (res, error_code) {
      callback(error_code === 0 && !!res && res.code === 200);
    }
  );
}

// mJS kennt kein globales decodeURIComponent() - eigene, einfache
// Prozent-Dekodierung (reicht fuer unsere ASCII-JSON-Payloads).
function percentDecode(s) {
  let out = "";
  let i = 0;
  let n = s.length;
  while (i < n) {
    let c = s.charAt(i);
    if (c === "%" && i + 2 < n) {
      let hex = s.charAt(i + 1) + s.charAt(i + 2);
      out += String.fromCharCode(parseInt(hex, 16));
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

// req.query ist auf Shelly ein ROHER Query-String, kein fertiges Objekt -
// muss manuell geparst werden (siehe Shelly HTTPServer-Doku-Beispiele).
function getQueryParam(query, name) {
  if (!query) return undefined;
  let pairs = query.split("&");
  for (let i = 0; i < pairs.length; i++) {
    let eq = pairs[i].indexOf("=");
    if (eq < 0) continue;
    let k = percentDecode(pairs[i].slice(0, eq));
    if (k === name) {
      return percentDecode(pairs[i].slice(eq + 1));
    }
  }
  return undefined;
}


// =====================================================
// Hintergrund-Polling (Netz + Hubs entkoppelt abfragen)
// =====================================================

// Liest ein Feld aus einem JSON-Objekt - field kann ein einfacher
// String-Key ODER ein Array verschachtelter Keys sein (z.B. fuer
// gridSourceField: ["StatusSNS","SML","Watt_Summe"]). Spiegelbildlich zu
// handleGenericGridResponse() in zerooutput_multi_kvs.js.
// ---------------------------------------------------------------------
// Werte aus der Hub-Antwort OHNE JSON.parse ziehen.
//
// Grund steht im Geraete-Log: Espruino teilt sich einen Variablenpool von
// rund 1600 Eintraegen fuer ALLE Scripte zusammen. Eine geparste
// /properties/report-Antwort (~1,3 kB, 60+ Felder) belegt davon mehrere
// hundert. Laufen Regel-Script und dieses Script gleichzeitig durch ihren
// Parse, reisst der Pool - und es stirbt, wer als naechstes anfordert.
// Aus dem Rohtext gelesen bleibt nur der String selbst im Speicher.
//
// Preis dafuer: Aendert Zendure die Feldnamen, faellt das erst im Betrieb
// auf. Deshalb liefert jede Funktion null statt zu raten, und ein fehlendes
// electricLevel gilt als "Hub nicht auswertbar".
// ---------------------------------------------------------------------

// Liest die Zahl hinter "key": aus dem Rohtext. null, wenn nicht vorhanden.
// "from" ist der Startoffset - bewusst ein Offset und kein Teilstring, denn
// s.slice() wuerde bei jedem Aufruf den kompletten Rest kopieren.
function jsonNum(s, key, from) {
  let tag = '"' + key + '"';
  let i = s.indexOf(tag, from || 0);
  if (i < 0) return null;
  i = s.indexOf(":", i + tag.length);
  if (i < 0) return null;

  let j = i + 1;
  while (j < s.length && s.charAt(j) === " ") j++;
  // KVS liefert Werte teils als String ("value":"12") - Anfuehrungszeichen
  // ueberspringen, damit dieselbe Funktion beide Formen liest.
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

// Kleinster Wert ueber ALLE Vorkommen eines Keys - fuer minVol, das je Pack
// einmal auftaucht. Werte <= 0 (schlafender Pack) zaehlen nicht mit.
function jsonMin(s, key) {
  let tag = '"' + key + '"';
  let best = null;
  let from = 0;
  while (true) {
    let i = s.indexOf(tag, from);
    if (i < 0) break;
    from = i + tag.length;
    let v = jsonNum(s, key, i);
    if (v !== null && v > 0 && (best === null || v < best)) best = v;
  }
  return best;
}

function readFieldPath(data, field) {
  if (typeof field === "string") {
    return data[field];
  }
  let current = data;
  for (let i = 0; i < field.length; i++) {
    if (current === undefined || current === null) return undefined;
    current = current[field[i]];
  }
  return current;
}

function updateGridPowerStatus(callback) {
  if (CONFIG.gridSource === "local") {
    let em = Shelly.getComponentStatus("em:" + CONFIG.gridSourceEmId);
    if (!em) {
      callback({ power: 0, online: false });
      return;
    }
    let power = em.total_act_power;
    if (power === undefined) {
      power = (em.a_act_power || 0) + (em.b_act_power || 0) + (em.c_act_power || 0);
    }
    callback({ power: Math.round(power), online: true });
    return;
  }

  if (CONFIG.gridSource === "remote") {
    Shelly.call(
      "HTTP.GET",
      {
        url: "http://" + CONFIG.gridSourceIp + "/rpc/EM.GetStatus?id=" + CONFIG.gridSourceEmId,
        timeout: CONFIG.httpTimeout
      },
      function (res, error_code) {
        if (error_code !== 0 || !res || res.code !== 200) {
          callback({ power: 0, online: false });
          return;
        }
        // Wie bei den Hubs ohne JSON.parse - spart Variablen im gemeinsamen Pool.
        let power = jsonNum(res.body, "total_act_power");
        res = null;
        if (power === null) {
          callback({ power: 0, online: false });
          return;
        }
        callback({ power: Math.round(power), online: true });
      }
    );
    return;
  }

  if (CONFIG.gridSource === "http_json") {
    Shelly.call(
      "HTTP.GET",
      {
        url: CONFIG.gridSourceUrl,
        timeout: CONFIG.httpTimeout
      },
      function (res, error_code) {
        if (error_code !== 0 || !res || res.code !== 200) {
          callback({ power: 0, online: false });
          return;
        }
        let data;
        try { data = JSON.parse(res.body); } catch (e) { callback({ power: 0, online: false }); return; }
        res = null;
        let value = readFieldPath(data, CONFIG.gridSourceField);
        if (value === undefined) {
          callback({ power: 0, online: false });
          return;
        }
        let power = CONFIG.gridSourceInvert ? (value * -1) : value;
        callback({ power: Math.round(power), online: true });
      }
    );
    return;
  }

  callback({ power: 0, online: false });
}

function offlineHub(index) {
  return {
    id: index, soc: null, power: 0,
    acMode: null, socLimit: null, gridReverse: null,
    pv: null, minVol: null,
    online: false
  };
}

function updateHubStatus(index, callback) {
  let cfg = CONFIG.devices[index];

  Shelly.call(
    "HTTP.GET",
    {
      url: "http://" + cfg.ip + "/properties/report",
      timeout: CONFIG.httpTimeout
    },
    function (res, error_code) {
      if (error_code !== 0 || !res || res.code !== 200) {
        callback(offlineHub(index));
        return;
      }

      let body = res.body;
      res = null;

      let soc = jsonNum(body, "electricLevel");
      if (soc === null) {
        callback(offlineHub(index));
        return;
      }

      let acMode = jsonNum(body, "acMode");
      let power = 0;
      if (acMode === 2) power = jsonNum(body, "outputHomePower") || 0;
      else if (acMode === 1) power = (jsonNum(body, "gridInputPower") || 0) * -1;

      let hub = {
        id: index,
        soc: soc,
        power: Math.round(power),
        acMode: acMode,
        socLimit: jsonNum(body, "socLimit"),
        gridReverse: jsonNum(body, "gridReverse"),
        pv: jsonNum(body, "solarInputPower"),
        minVol: jsonMin(body, "minVol"),
        online: true
      };
      body = null;

      callback(hub);
    }
  );
}

function updateAllHubsStatus(index, results, callback) {
  if (index >= CONFIG.devices.length) {
    callback(results);
    return;
  }
  updateHubStatus(index, function (r) {
    results[results.length] = r;
    updateAllHubsStatus(index + 1, results, callback);
  });
}

// Hauptfunktion fuer das periodische Hintergrund-Update
function backgroundPoll() {
  if (Date.now() - lastRequestAt > IDLE_MS) {
    // kein Dashboard aktiv - Netzzaehler/Hubs nicht unnoetig abfragen
    return;
  }

  // Laeuft der vorige Durchlauf noch, oder arbeitet gerade ein Endpunkt?
  // Dann diesen Takt auslassen und beim naechsten neu versuchen.
  if (bgRunning) return;
  if (busyNow()) return;

  bgRunning = true;
  busyEnter();
  updateGridPowerStatus(function (grid) {
    LATEST_STATUS.grid = grid;
    updateAllHubsStatus(0, [], function (hubs) {
      LATEST_STATUS.hubs = hubs;
      STATUS_BODY = JSON.stringify(LATEST_STATUS);
      bgRunning = false;
      busyLeave();
    });
  });
}

Timer.set(CONFIG.pollIntervalSec * 1000, true, backgroundPoll);
backgroundPoll(); // erster sofortiger Aufruf


// =====================================================
// API: Endpunkte
// =====================================================

function buildDeviceDefaults() {
  let arr = [];
  for (let i = 0; i < CONFIG.devices.length; i++) {
    let d = CONFIG.devices[i];
    arr[i] = {
      id: i,
      ip: d.ip,
      label: d.label,
      minSoc: d.minSoc,
      maxSoc: d.maxSoc,
      maxOutput: d.maxOutput,
      maxInputPower: d.maxInputPower,
      inputLimit: d.inputLimit,
      dischargeAllowed: d.dischargeAllowed !== false,
      reverse: !!d.reverse
    };
  }
  return arr;
}

// Chrome & Co. schicken vor dem eigentlichen fetch() an eine private
// IP-Adresse (z.B. 192.168.x.x) aus einem "unsicheren" Kontext (u.a.
// file://-Seiten) zuerst einen OPTIONS-Preflight mit der Frage, ob
// Private Network Access erlaubt ist. Ohne passende Antwort blockiert
// der Browser die eigentliche Anfrage mit "Failed to fetch".
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

// Sammelabfrage fuer config_api: mehrere gleichzeitige Anfragen teilen sich
// EIN KVS.GetMany. Bewusst ohne Ergebnis-Cache - ein dauerhaft gehaltener
// Antwort-String kostet im knappen Variablenpool mehr, als er einspart.
// Kurzzeit-Cache fuer config_api. Mehrere offene Dashboards (oder Tabs)
// fragen sonst unabhaengig voneinander dieselben KVS-Werte ab, jedes mit einem
// eigenen KVS.GetMany. Die Zeitspanne ist bewusst kurz und liegt unter der
// Nachlaufzeit, die die Dashboard-Seite nach einer Schreibkette einhaelt -
// eine gerade gesetzte Aenderung wird also nie aus dem Cache beantwortet.
// Laeuft bereits eine Abfrage (inklusive Wartezeit auf einen freien Slot),
// stellen sich weitere Anfragen hier an, statt ein eigenes KVS.GetMany
// loszuschicken. Mehrere offene Dashboards erzeugen dadurch genau eine
// Abfrage, nicht eine pro Seite.
let configPending = false;
let configWaiters = [];

function sendConfigBody(res, body) {
  res.code = 200;
  res.headers = [
    ["Content-Type", "application/json"],
    ["Access-Control-Allow-Origin", "*"]
  ];
  res.body = body;
  res.send();
}

function answerConfigWaiters(body) {
  for (let i = 0; i < configWaiters.length; i++) {
    sendConfigBody(configWaiters[i], body);
  }
  configWaiters = [];
}

function serveConfig(res, attempt) {
  if (attempt === 0) {
    if (configPending) {
      configWaiters[configWaiters.length] = res;
      return;
    }
    configPending = true;
  }

  if (busyNow() && attempt < CONFIG_WAIT_MAX) {
    Timer.set(CONFIG_WAIT_MS, false, function () {
      serveConfig(res, attempt + 1);
    });
    return;
  }

  busyEnter();
  let devices = buildDeviceDefaults();
  let setpoint = 0;

  kvsGetAll(function (store) {
    // store === null: KVS nicht lesbar. Dann bleiben die Vorgabewerte aus
    // CONFIG stehen, damit das Dashboard trotzdem eine Antwort bekommt.
    let v = kvsValue(store, "zdmc_setpoint");
    if (v !== undefined) setpoint = Number(v);

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

    let body = JSON.stringify({
      version: VERSION,
      setpoint: setpoint,
      hysteresis: CONFIG.hysteresis,
      devices: devices
    });

    busyLeave();
    configPending = false;

    sendConfigBody(res, body);
    answerConfigWaiters(body);
  });
}

HTTPServer.registerEndpoint("config_api", function (req, res) {
  if (handlePreflight(req, res)) return;
  lastRequestAt = Date.now();
  serveConfig(res, 0);
});

HTTPServer.registerEndpoint("status_api", function (req, res) {
  if (handlePreflight(req, res)) return;
  lastRequestAt = Date.now();
  res.code = 200;
  res.headers = [
    ["Content-Type", "application/json"],
    ["Access-Control-Allow-Origin", "*"]
  ];
  res.body = STATUS_BODY;
  res.send();
});

HTTPServer.registerEndpoint("kvs_set_api", function (req, res) {
  if (handlePreflight(req, res)) return;
  lastRequestAt = Date.now();

  let dataParam = getQueryParam(req.query, "data");
  if (dataParam === undefined) {
    res.code = 400;
    res.headers = [["Content-Type", "application/json"], ["Access-Control-Allow-Origin", "*"]];
    res.body = JSON.stringify({ success: false, error: "missing data param" });
    res.send();
    return;
  }

  let data = null;
  try { data = JSON.parse(dataParam); } catch (e) { data = null; }

  if (!data || typeof data !== "object") {
    res.code = 400;
    res.headers = [["Content-Type", "application/json"], ["Access-Control-Allow-Origin", "*"]];
    res.body = JSON.stringify({ success: false, error: "invalid json" });
    res.send();
    return;
  }

  let keys = Object.keys(data);
  let allowedKeys = [];
  for (let i = 0; i < keys.length; i++) {
    if (keys[i].indexOf("zdmc_") === 0) allowedKeys[allowedKeys.length] = keys[i];
  }

  if (allowedKeys.length === 0) {
    res.code = 200;
    res.headers = [["Content-Type", "application/json"], ["Access-Control-Allow-Origin", "*"]];
    res.body = JSON.stringify({ success: true, written: 0 });
    res.send();
    return;
  }

  writeKeys(res, data, allowedKeys, 0, true);
});

// Nacheinander schreiben, nicht parallel: bei entfernter KVS ist jeder
// Schreibvorgang eine eigene HTTP-Anfrage, und mehrere gleichzeitig offene
// Anfragen sind genau die Spitze, die wir vermeiden wollen.
function writeKeys(res, data, keys, index, allOk) {
  if (index >= keys.length) {
    res.code = allOk ? 200 : 500;
    res.headers = [["Content-Type", "application/json"], ["Access-Control-Allow-Origin", "*"]];
    res.body = JSON.stringify({ success: allOk, written: keys.length });
    res.send();
    return;
  }

  let k = keys[index];
  kvsSetOne(k, data[k], function (ok) {
    writeKeys(res, data, keys, index + 1, allOk && ok);
  });
}

print("Zendure Dashboard API v" + VERSION + " gestartet (nur JSON-Endpunkte, kein HTML).");
print("config_api / status_api / kvs_set_api unter " + CONFIG.kvsHost);