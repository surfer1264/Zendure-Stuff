// =====================================================================
// Zendure Dashboard API (zendure_dashboard_api.js)
//
// Schlankes Backend-Script fuer den Shelly: liefert NUR noch JSON-Daten
// ueber HTTP - keine HTML-Auslieferung mehr (das lag zu nah an der
// Speichergrenze des Scripts, siehe unten). Die eigentliche Dashboard-
// Seite ist jetzt eine eigenstaendige HTML-Datei (zendure-dashboard.html),
// die diese Endpunkte per fetch() aufruft (dank Access-Control-Allow-Origin
// funktioniert das auch von einer lokalen Datei / anderem Host aus).
//
// Laeuft als EIGENES Script neben zerooutput_multi_kvs.js auf demselben
// Geraet (oder auf dem Geraet mit der lokalen EM-Messung, falls
// gridSource "local" genutzt wird).
//
// WICHTIG: CONFIG.devices und CONFIG.gridSource* MUESSEN zu CONFIG in
// zerooutput_multi_kvs.js passen (gleiche IPs, gleiche Reihenfolge der
// Geraete = gleicher Index i wie "zdmc_dev{i}_..."). Aenderst du dort die
// Geraeteliste, hier nachziehen.
//
// Endpunkte (alle mit CORS, koennen von jeder Seite/jedem Host aus
// aufgerufen werden):
//   GET config_api    -> { setpoint, hysteresis, devices:[...] }
//                        devices enthaelt die aktuellen KVS-Werte fuer
//                        dischargeAllowed / reverse / minSoc / inputLimit.
//                        hysteresis ist reine ANZEIGE (siehe CONFIG unten).
//   GET status_api    -> { grid:{power,online},
//                          hubs:[{id,soc,power,acMode,socLimit,gridReverse,online}] }
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
      dryRun: false
    },
    {
      ip: "192.168.178.150",
      label: "SF800",
      minSoc: 15,
      maxSoc: 100,
      dischargeAllowed: true,
      reverse: true,
      maxInputPower: 1000,
      maxOutput: 800,
      dryRun: false
    }
  ],

  // Hysterese ist im Regel-Script NICHT ueber die KVS veraenderbar. Der Wert
  // wird hier nur gespiegelt, damit das Dashboard ihn anzeigen kann (gleicher
  // Wert wie CONFIG.hysteresis im Regel-Script eintragen).
  hysteresis: 12,

  // ------------------------------------------------------------------
  // SMARTMETER SECTION - 1:1 Struktur/Feldnamen wie in zerooutput_multi_kvs.js
  // Where to read the household grid power from, there are three options
  gridSource: "local", // "local", "remote", "http_json"
  // ------------------------------------------------------------------
  // ONLY required/used when gridSource = "remote".
  // IP address of the Shelly Pro 3EM providing the grid measurement.
  gridSourceIp: "<IP_OF_YOUR_3EM_PRO_SHELLY>",
  // EM channel id to read (usually 0). Only used when gridSource = "remote".
  gridSourceEmId: 0,
  // ------------------------------------------------------------------
  // ONLY requested when gridSource = "http_json". Example is made for the Zendure Smart Meter 3CT, read the DOC for other devices.
  // Full URL of a generic JSON grid meter. Only used when gridSource = "http_json".
  gridSourceUrl: "http://<IP-of-your-meter>/properties/report",
  // Name of the JSON field in that response which holds the total grid power in watts.
  // Kann auch ein Array sein fuer verschachtelte Pfade, z.B. ["StatusSNS","SML","Watt_Summe"].
  gridSourceField: "total_power",
  // Set to true if the sign of gridSourceField is inverted compared to what
  // this script expects (positive = importing from grid).
  gridSourceInvert: false,

  httpTimeout: 5,
  pollIntervalSec: 5,

  // Ringpuffer fuer den Dashboard-Chart: so viele Messpunkte werden im
  // Script vorgehalten. Zeitfenster = historySize * pollIntervalSec.
  // 30 * 5 s = 150 s. Groesser = laengeres Fenster, aber mehr Heap.
  historySize: 30
};

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

// Zeitpunkt der letzten Anfrage von der Dashboard-Seite (irgendein
// Endpunkt). Solange laenger nichts reinkam, pausiert backgroundPoll die
// eigentlichen HTTP-Abfragen an Netzzaehler/Hubs (kein Dashboard offen =
// keine Anfragen noetig).
let lastRequestAt = 0;
let IDLE_MS = 15000;


// =====================================================
// Ueberlappungsschutz
//
// Die beiden speicherhungrigen Vorgaenge sind das Parsen der Hub-Antwort
// (/properties/report, mehrere kB Rohtext + Objektbaum) und das KVS.GetMany
// in config_api. Liefen sie gleichzeitig, addierten sich ihre Spitzen - genau
// das treibt memPeak hoch. Das Flag laesst immer nur einen von beiden laufen.
//
// Zusaetzlich schuetzt es davor, dass sich der Hintergrund-Timer selbst
// ueberholt, wenn ein Hub laenger braucht als pollIntervalSec.
// =====================================================

let busy = false;
let busySince = 0;

// Sicherung: bleibt ein Callback aus (z.B. abgewiesener Shelly.call), haengt
// das Flag sonst dauerhaft und die Abfragen stehen still.
let BUSY_TIMEOUT_MS = 15000;

// Wie lange config_api hoechstens auf einen freien Slot wartet, bevor es
// trotzdem loslegt: CONFIG_WAIT_MAX * CONFIG_WAIT_MS.
let CONFIG_WAIT_MS = 200;
let CONFIG_WAIT_MAX = 10;

function busyNow() {
  if (busy && (Date.now() - busySince) > BUSY_TIMEOUT_MS) {
    print("busy-Flag haengt seit ueber " + (BUSY_TIMEOUT_MS / 1000) + " s - zurueckgesetzt");
    busy = false;
  }
  return busy;
}

function busyLock() {
  busy = true;
  busySince = Date.now();
}

function busyRelease() {
  busy = false;
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
        let data;
        try { data = JSON.parse(res.body); } catch (e) { callback({ power: 0, online: false }); return; }
        res = null;
        if (data.total_act_power === undefined) {
          callback({ power: 0, online: false });
          return;
        }
        callback({ power: Math.round(data.total_act_power), online: true });
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
      let data;
      try { data = JSON.parse(res.body); } catch (e) { callback(offlineHub(index)); return; }

      // Roh-Antwort sofort freigeben: /properties/report ist mehrere kB gross
      // und muss nicht parallel zum geparsten Objekt im Heap liegen.
      res = null;

      if (!data.properties) {
        callback(offlineHub(index));
        return;
      }

      let p = data.properties;
      data = null;

      let power = 0;
      if (p.acMode === 2) {
        power = p.outputHomePower || 0;
      } else if (p.acMode === 1) {
        power = (p.gridInputPower || 0) * -1;
      }

      callback({
        id: index,
        soc: p.electricLevel,
        power: Math.round(power),
        // Zusatzstatus fuer die Anzeige im Dashboard:
        //   acMode     0/undef = Standby, 1 = Laden (AC-Eingang), 2 = Entladen
        //   socLimit   0 = frei, 1 = Laden gesperrt (voll), 2 = Entladen gesperrt
        //   gridReverse 1 = Netzladen freigegeben, 2 = gesperrt (Flotte voll)
        acMode: (p.acMode !== undefined) ? p.acMode : null,
        socLimit: (p.socLimit !== undefined) ? p.socLimit : null,
        gridReverse: (p.gridReverse !== undefined) ? p.gridReverse : null,
        online: true
      });
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

  // Belegt: entweder laeuft der vorige Durchlauf noch, oder config_api
  // arbeitet gerade. Diesen Takt auslassen, beim naechsten neu versuchen.
  if (busyNow()) return;

  busyLock();
  updateGridPowerStatus(function (grid) {
    LATEST_STATUS.grid = grid;
    updateAllHubsStatus(0, [], function (hubs) {
      LATEST_STATUS.hubs = hubs;
      busyRelease();
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

// Wartet auf einen freien Slot, bevor das KVS.GetMany losgeschickt wird.
// Nach CONFIG_WAIT_MAX vergeblichen Anlaeufen wird trotzdem geantwortet -
// lieber eine ueberlappende Spitze als eine haengende Dashboard-Abfrage.
function serveConfig(res, attempt) {
  if (busyNow() && attempt < CONFIG_WAIT_MAX) {
    Timer.set(CONFIG_WAIT_MS, false, function () {
      serveConfig(res, attempt + 1);
    });
    return;
  }

  busyLock();
  let devices = buildDeviceDefaults();
  let setpoint = 0;

  Shelly.call("KVS.GetMany", { match: KVS_MATCH }, function (result, error_code) {
    if (error_code === 0 && result && result.items) {
      let items = kvsItemsToMap(result.items);
      if (items["zdmc_setpoint"] !== undefined) setpoint = Number(items["zdmc_setpoint"]);

      for (let i = 0; i < devices.length; i++) {
        let dKey = "zdmc_dev" + i + "_dischargeAllowed";
        let rKey = "zdmc_dev" + i + "_reverse";
        let mKey = "zdmc_dev" + i + "_minSoc";
        let lKey = "zdmc_dev" + i + "_inputLimit";
        if (items[dKey] !== undefined) devices[i].dischargeAllowed = (Number(items[dKey]) !== 0);
        if (items[rKey] !== undefined) devices[i].reverse = (Number(items[rKey]) !== 0);
        if (items[mKey] !== undefined) devices[i].minSoc = Number(items[mKey]);
        if (items[lKey] !== undefined) devices[i].inputLimit = Number(items[lKey]);
      }
    }

    res.code = 200;
    res.headers = [
      ["Content-Type", "application/json"],
      ["Access-Control-Allow-Origin", "*"]
    ];
    res.body = JSON.stringify({
      setpoint: setpoint,
      // Nur zur Anzeige - das Regel-Script liest keinen KVS-Wert dafuer.
      hysteresis: CONFIG.hysteresis,
      devices: devices
    });
    busyRelease();
    res.send();
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
  res.body = JSON.stringify(LATEST_STATUS);
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

  let remaining = allowedKeys.length;
  let allOk = true;

  for (let i = 0; i < allowedKeys.length; i++) {
    let k = allowedKeys[i];
    Shelly.call("KVS.Set", { key: k, value: String(data[k]) }, function (result, error_code) {
      if (error_code !== 0) allOk = false;
      remaining--;
      if (remaining === 0) {
        res.code = allOk ? 200 : 500;
        res.headers = [["Content-Type", "application/json"], ["Access-Control-Allow-Origin", "*"]];
        res.body = JSON.stringify({ success: allOk, written: allowedKeys.length });
        res.send();
      }
    });
  }
});

print("Zendure Dashboard API gestartet (nur JSON-Endpunkte, kein HTML).");
print("config_api / status_api / kvs_set_api unter http://<shelly-ip>/script/<id>/<name>");