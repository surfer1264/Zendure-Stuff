// Zendure Dynamic Output Controller - Multi-Device Version
// Shelly mJS: Balancing mehrerer Zendure-Geraete gegen Pro 3EM/JSON-Zaehler
// Konfiguration erfolgt ausschliesslich im CONFIG-Block unten
let SCRIPT_TYPE = "zdmc-controller";
let VERSION = "5.3.5";
let CONFIG_SCHEMA = 1;
let CONFIG = {
  devices: [
     {
      ip: "192.168.178.143",    // Zendure IP address
      label: "SF2400",          // short name, used in logs/messages
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
      label: "Fatamorgana",
      minSoc: 15,
      maxSoc: 100,
      dischargeAllowed: true,
      reverse: true,
      maxInputPower: 2000,
      maxOutput: 2000,
      dryRun: false
    },
  ],
  // ------------------------------------------------------------------
  // SMARTMETER SECTION
  gridSource: "local", // "local", "remote", "http_json"
  // ------------------------------------------------------------------
  // ONLY required/used when gridSource = "remote".
  gridSourceIp: "<IP address Shelly Pro 3EM>",
  gridSourceEmId: 0,
  // ------------------------------------------------------------------
  // only gridSource=http_json; z.B. Zendure 3CT
  gridSourceUrl: "http://<IP-of-your-meter>/properties/report",
  gridSourceField: "total_power",
  gridSourceInvert: false,

  // ------------------------------------------------------------------
  // RULES ENGINE CORE PARAMETERS
  setpoint: 0, // (KVS-live-overridable)
  // Hysteresis in watts, PER DEVICE
  hysteresis: 12,
  // Damping / gain factor for the COMBINED control signal (0.4 <= factor <= 0.8),
  dampingFactor: 0.65,
  // OPTIONAL: Faktor der schnellen Flanke bei Spruengen in Richtung
  // "weniger Export" (0.4 <= factor <= 0.9). Fehlt der Eintrag, gilt 0.9.
  // jumpFactor: 0.9,

  // ------------------------------------------------------------------
  // THRESHOLD SECTION ONLY RELEVANT FOR MULTI DEVICES
  discharge: {
    concentrateBelow: 600,  // W - below this combined target, use ONE device
    spreadAbove: 800        // W - above this, split across all devices
  },

  charge: {
    concentrateBelow: 600,
    spreadAbove: 800
  },
  // Time-coupled hysteresis for  (only) spread -> single
  concentrateHoldMinutes: 3,

  // ------------------------------------------------------------------
  // SOC-BALANCING Max. SOC-Differenz zwischen Geraeten (%)
  rebalance: {
    socMargin: 5        // percentage points of advantage required to switch
  },

  // ------------------------------------------------------------------
  // REVERSE-Hysterese, nur bei reverse:true relevant
  reverseStartupPower: 35,
  // Ladeleistung, unter der gestoppt wird
  reverseStopPower: 15,
  // gridReverse-Modus: dynamic / always1 / always2
  gridReverseMode: "dynamic",
  chargeResetMargin: 10, // nur relevant bei gridReverseMode: "dynamic"

  // ------------------------------------------------------------------
  // DISCHARGE MODE SECTION
  dischargeStartupPower: 35,
  // Entladeleistung, unter der gestoppt wird
  dischargeStopPower: 15,

  // ------------------------------------------------------------------
  // INTERNAL SECTION BE CAREFUL
  // Update interval (milliseconds)
  interval: 4000,
  // Dont Change It
  // Anzahl Fehler bis Benachrichtigung
  errorThreshold: 6,
  // Cooldown-Takte Laden/Entladen-Wechsel
  directionChangeHoldCycles: 4,
  // true->smartMode 0, false->1
  standbySmartModeZero: false,
  // KVS-Live-Override an/aus (false = CONFIG fix, kein KVS-Zugriff)
  // ------------------------------------------------------------------
  kvsEnabled: false,
  // true = Start ueberschreibt KVS mit CONFIG, danach false
  kvsForceReseed: false,
  // operation to keep the console output clean.
  // ------------------------------------------------------------------
  debug: false,
  // ------------------------------------------------------------------
  // ADAPTIVE POLLING - reduziert HTTP-Last auf die Zendure-Geraete,
  idleSkip: {
    enabled: true,       // false = Funktion komplett aus, Verhalten wie vorher
    cyclesUnchanged: 4,  // so viele Zyklen in Folge innerhalb der Hysterese, bevor ausgesetzt wird
    maxSkipSeconds: 44   // max. Alter der Geraete-Daten (SOC/socLimit) waehrend des Aussetzens
  },

  // ------------------------------------------------------------------
  // MESSAGE SECTION
  signal: {
    enabled: false,          // set to true to activate notifications
	typ: "WEBHOOK",			 // "SIGNAL", "WHATSAPP" oder "WEBHOOK"
    phone: "PHONE-STRING",   // e.g. +4917XXXXXXXX (nur SIGNAL/WHATSAPP)
    apiKey: "YOUR_API_KEY",  // CallMeBot API key
    webhookUrl: "http://<IP-ADRESSE>:8123/api/webhook/<deine-webhook-id>" // only webhook
  }
};
if (CONFIG.interval < 3000) CONFIG.interval = 3000;
CONFIG.watchdog = CONFIG.interval * 2.5;

function checkBand(band) {
  if (band.concentrateBelow < 35) band.concentrateBelow = 35;
  if (band.spreadAbove < 50) band.spreadAbove = 50;
  if (band.concentrateBelow >= band.spreadAbove) band.spreadAbove = band.concentrateBelow +15 ;
}
checkBand(CONFIG.discharge);
checkBand(CONFIG.charge);

// Mindestabstand zwischen minSoc und maxSoc in Prozentpunkten. Gilt beim
// Start und beim Live-Override von zdmc_devN_minSoc ueber die KVS.
let SOC_GAP = 5;

for (let i = 0; i < CONFIG.devices.length; i++) {
  if (typeof CONFIG.devices[i].minSoc !== "number") CONFIG.devices[i].minSoc = 10;
  if (typeof CONFIG.devices[i].maxSoc !== "number") CONFIG.devices[i].maxSoc = 100;
  CONFIG.devices[i].minSoc = Math.max(10, Math.min(100 - SOC_GAP, CONFIG.devices[i].minSoc));
  CONFIG.devices[i].maxSoc = Math.max(CONFIG.devices[i].minSoc + SOC_GAP, Math.min(100, CONFIG.devices[i].maxSoc));
  if (typeof CONFIG.devices[i].inputLimit !== "number") CONFIG.devices[i].inputLimit = 0;
  CONFIG.devices[i].inputLimit = Math.max(0,
    Math.min(CONFIG.devices[i].maxInputPower, CONFIG.devices[i].inputLimit));
}

CONFIG.dampingFactor       = Math.max(0.4, Math.min(0.8, CONFIG.dampingFactor));
CONFIG.setpoint            = Math.max(-40, Math.min(40, CONFIG.setpoint));
CONFIG.hysteresis          = Math.max(5, Math.min(40, CONFIG.hysteresis));
CONFIG.rebalance.socMargin = Math.max(5, Math.min(25, CONFIG.rebalance.socMargin));
CONFIG.chargeResetMargin   = Math.max(10, Math.min(25, CONFIG.chargeResetMargin));
// v5.2.0: Sprungschwelle fuer die asymmetrische Daempfung (siehe calculate()).
// 3x Hysterese, max. 50 W. hysteresis ist nicht KVS-aenderbar -> einmalig.
let JUMP_THRESHOLD = Math.min(3 * CONFIG.hysteresis, 50);
// Faktor der schnellen Flanke (1 = ungedaempft). 0.9 statt 1: bei ~3 s
// Reaktionszeit der Geraete schiesst ein voller Sprung sonst leicht ueber
// und wird im Folgetakt zurueckgenommen (Hin und Her).
// v5.2.3: optional per CONFIG.jumpFactor setzbar. Fehlt der Eintrag (oder ist
// er keine gueltige Zahl), gilt der Standard 0.9. Ein gesetzter Wert wird auf
// 0.4 ... 0.9 begrenzt - nie ueber 0.9.
let JUMP_FACTOR = 0.9;
if (typeof CONFIG.jumpFactor === "number" && isFinite(CONFIG.jumpFactor)) {
  JUMP_FACTOR = Math.max(0.4, Math.min(0.9, CONFIG.jumpFactor));
}
if (CONFIG.reverseStopPower >= CONFIG.reverseStartupPower) {  CONFIG.reverseStartupPower = CONFIG.reverseStopPower + 15; }
if (CONFIG.dischargeStopPower < 0) CONFIG.dischargeStopPower = 15;
if (CONFIG.dischargeStopPower >= CONFIG.dischargeStartupPower) { CONFIG.dischargeStartupPower = CONFIG.dischargeStopPower + 15; }

// Globaler Fix-Sollwert fuer Entladung in Watt (KVS-live-overridable).
// 0 = aus (normale Netzsaldo-Regelung). Gueltige Werte: 0 ODER >= dischargeStartupPower.
// Ersetzt bei aktivem Wert die Netzsaldo-basierte Berechnung im Entladepfad komplett -
// Ladepfad (chargeTarget) bleibt unberuehrt.
CONFIG.dischargeFixed=0;

// Entlade-Hysterese (Prozentpunkte ueber minSoc). Ein Geraet, das bis minSoc
// entladen hat, darf erst ab minSoc + dischargeResetMargin wieder entladen -
// unabhaengig davon, dass die Firmware socLimit=2 bereits bei minSoc+1 aufhebt.
// Verhindert Flattern an der minSoc-Grenze (PV laedt nach -> sofort wieder
// Entladen -> minSoc -> Standby ...). Bereich 3..79 (KVS-live-overridable).
// Wirksam ist je Geraet hoechstens maxSoc - minSoc - 11, siehe
// dischargeResetMarginFor().
CONFIG.dischargeResetMargin = Math.max(3, Math.min(79, CONFIG.dischargeResetMargin || 3));

// Mindestanzahl aufeinanderfolgender Standby-Zyklen (acMode 1, output=0,
// input=0 - egal ob natuerlich in der Totzone oder durch
// directionChangeHoldCycles erzwungen), bevor smartMode wirklich auf 0
// geschrieben wird. Nur relevant bei standbySmartModeZero:true. Verhindert
// Flash-Writes bei kurzen Nulldurchgaengen/Pendelbewegungen um den
// Netto-Nullpunkt (z.B. schwankender PV-Ertrag nahe 0 W).
CONFIG.standbyHoldCycles = 15;

CONFIG.directionChangeHoldCycles = Math.max(4, Math.min(20, CONFIG.directionChangeHoldCycles));

// Hold time (spread -> single) in cycles
let CONCENTRATE_HOLD_CYCLES = Math.max(5, Math.round((CONFIG.concentrateHoldMinutes * 60000) / CONFIG.interval));

// Entprellung single -> spread: so viele Zyklen wird eine Ueberschreitung von
let SPREAD_TRIGGER_CYCLES = 1;
SPREAD_TRIGGER_CYCLES = Math.max(1, SPREAD_TRIGGER_CYCLES);

// idleSkip: Sekunden -> Zyklen, unabhaengig vom gewaehlten CONFIG.interval
CONFIG.idleSkip.cyclesUnchanged = Math.max(3, Math.min(50, CONFIG.idleSkip.cyclesUnchanged));
CONFIG.idleSkip.maxSkipSeconds  = Math.max(CONFIG.interval / 1000, CONFIG.idleSkip.maxSkipSeconds);
let IDLE_SKIP_CYCLES = Math.max(3, Math.round((CONFIG.idleSkip.maxSkipSeconds * 1000) / CONFIG.interval));

// Live parameter overrides (Key-Value-Store)
let KVS_MATCH = "zdmc_*";

let state = {
  gridPower: 0,
  smoothedOutput: null,
  smoothedCharge: null,
  busy: false,
  watchdogTimer: null,

  // v5.3.4: KVS-Uebernahme nach kvs_rev (kvsTrigger). pending = Aenderung
  // gemeldet, noch nicht gelesen; kvsBusy = Lesen/Geraete-Sync laeuft.
  kvsPending: false,
  kvsBusy: false,
  kvsBusySince: 0,

  cycleId: 0,
  cycleStartedAt: 0,

  // Zyklusdauer, stuendlich ins Log (cycleStatsLog). Nur Summen, kein Puffer.
  cyFrom: Date.now(),
  cyN: 0,
  cySum: 0,
  cyMax: 0,
  cySkip: 0,

  errors: { em: 0, watchdog: 0, kvs: 0 },
  notified: { em: false, watchdog: false, kvs: false },

  discharge: { mode: "single", active: null, holdCycles: 0, triggerCycles: 0 },
  charge: { mode: "single", active: null, holdCycles: 0, triggerCycles: 0 },
  allMaxedLogged: false,

  idleUnchangedCount: 0,
  idleSkipRemaining: 0,
  idleSkipActiveThisCycle: false,

  devices: []
};

for (let i = 0; i < CONFIG.devices.length; i++) {
  state.devices[i] = {
    soc: 0,
    socLimit: null,
    socStatus: null,
    serial: null,
    zenPower: 0,
    available: false,
    outputLimit: null,
    maxSocLogged: false,
    gridReverse: null,
    acMode: null,
    smartMode: null,

    realDirection: null, reversalHoldCount: 0, standbyHoldCount: 0,
    dischargeLocked: false, // Entlade-Hysterese, siehe CONFIG.dischargeResetMargin

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

// ------------------------------------------------------------------
// v4.5.1: Zentraler Wrapper um Shelly.call().
//
// Der Call-Pool des Shelly ist begrenzt. Ist er voll, wird der Aufruf
// NICHT angenommen: Shelly.call wirft dann sofort ("Too many calls in
// progress") und der Callback laeuft nie.
// Hier wird der Wurf abgefangen und in den normalen Fehlerpfad umgeleitet:
// der Callback wird mit res=null nachgezogen. Alle Aufrufer pruefen bereits
// auf "res && res.code === 200" bzw. "err_code !== 0" und landen damit in
// ihrer bestehenden Fehlerbehandlung. Ebenso wichtig: der Callback laeuft
// UEBERHAUPT - in fast allen Ketten ist er es, der den Zyklus weiterschiebt
// und unlock() ausloest. Ohne ihn haengt der Zyklus bis zum Watchdog.
//
// ACHTUNG: Das ist Schadensbegrenzung, keine Vermeidung. Der abgewiesene
// Call geht verloren und wird nicht wiederholt.
// ------------------------------------------------------------------
function safeCall(method, params, callback) {
  try {
    Shelly.call(method, params, callback);
  } catch (e) {
    print("Shelly.call abgewiesen (" + method + "): " + e);

    // NICHT synchron zurueckrufen - sonst laeuft der Callback noch im
    // Frame des Aufrufers und rekursive Ketten bauen Stack auf.
    try {
      Timer.set(0, false, function () {
        callback(null, -1, "call rejected");
      });
    } catch (e2) {
      // Auch der Timer-Pool ist erschoepft. Dann lieber synchron
      // zurueckrufen als das Skript sterben zu lassen.
      try {
        callback(null, -1, "call rejected");
      } catch (e3) {
        print("CB-Fehler: " + e3);
      }
    }
  }
}

// v5.1.7: gemeinsamer Ergebnis-Callback fuer Webhook/Signal/WhatsApp (nur print)
function msgResult(tag) {
  return function (result, error_code, error_msg) {
    if (error_code === 0) print(tag + " gesendet");
    else if (error_code === -104) print(tag + " Timeout (-104), evtl. zugestellt");
    else print(tag + " Fehler: " + error_msg);
  };
}

// Einfacher Webhook-Versand: fester JSON-Body {"message": "..."}
function sendWebhookMessage(text) {

  safeCall(
    "HTTP.Request",
    {
      method: "POST",
      url: CONFIG.signal.webhookUrl,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
      timeout: 8
    },
    msgResult(CONFIG.signal.typ)
  );
}

function sendSignalMessage(text) {
  if (!CONFIG.signal.enabled)
    return;

  if (CONFIG.signal.typ == "WEBHOOK") {
    sendWebhookMessage(text);
    return;
  }

  let safeText = simpleEncode(text);
  let url = "url";

  if (CONFIG.signal.typ == "SIGNAL")
    url = "https://api.callmebot.com/signal/send.php?phone=" + CONFIG.signal.phone + "&apikey=" + CONFIG.signal.apiKey +  "&text=" + safeText;
  else
	url = "https://api.callmebot.com/whatsapp.php?phone=" + CONFIG.signal.phone + "&text=" + safeText + "&apikey=" + CONFIG.signal.apiKey;

  safeCall(
    "HTTP.GET",
    { url: url, timeout: 8 },
    msgResult(CONFIG.signal.typ)
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
      "❌ " + label + " Fehler (" + type + "): " + message + "\n" +
      errors[type] + " Versuche in Folge fehlgeschlagen."
    );
  }
}

function reportSuccess(errors, notified, type, label) {
  if (errors[type] > 0 || notified[type]) {
    if (notified[type]) {
      sendSignalMessage(
        "✅ " + label + ": Fehler (" + type + ") behoben, laeuft wieder normal."
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

// Nur im Debug-Modus aufgerufen: Heap-Stand des Skripts ausgeben
function memLog(tag) {
  let s = Shelly.getComponentStatus("script:" + Script.id);
  if (s) print("DEBUG MEM " + tag + ": used " + s.mem_used + " peak " + s.mem_peak + " free " + s.mem_free);
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
        Math.round(Date.now() - state.cycleStartedAt) + " ms)");

      state.busy = false;
      state.watchdogTimer = null;
      if (state.kvsPending) Timer.set(0, false, kvsTrigger);
    }
  );

  return state.cycleId;
}

// Schreibt die Zyklus-Statistik der letzten Stunde und beginnt ein neues Fenster.
// avg/max nur aus Zyklen mit Geraeteabfrage (Sparmodus-Zyklen sind kuerzer).
function cycleStatsLog(now) {
  print("Zyklen 1h: n " + state.cyN +
    " | avg " + (state.cyN > 0 ? Math.round(state.cySum / state.cyN) : 0) + " ms" +
    " | max " + Math.round(state.cyMax) + " ms" +
    " | uebersprungen " + state.cySkip +
    " | interval " + CONFIG.interval + " ms");

  state.cyFrom = now;
  state.cyN = 0;
  state.cySum = 0;
  state.cyMax = 0;
  state.cySkip = 0;
}

function unlock(myCycle) {
  if (myCycle !== state.cycleId) {
    debugStale("unlock", myCycle);
    return;
  }

  let now = Date.now();
  let d = now - state.cycleStartedAt;

  if (!state.idleSkipActiveThisCycle) {
    state.cyN = state.cyN + 1;
    state.cySum = state.cySum + d;
    if (d > state.cyMax) state.cyMax = d;
  }

  // Uhr zurueckgesprungen (z.B. Zeitsync nach Start): Fenster neu beginnen
  if (now < state.cyFrom) state.cyFrom = now;
  if (now - state.cyFrom >= 3600000) cycleStatsLog(now);

  if (CONFIG.debug) {
    print("DEBUG Zyklus " + myCycle + " abgeschlossen nach " + Math.round(d) + " ms");
    memLog("Zyklusende");
  }

  reportSuccess(state.errors, state.notified, "watchdog", "System");

  state.busy = false;

  if (state.watchdogTimer !== null) {
    Timer.clear(state.watchdogTimer);
    state.watchdogTimer = null;
  }

  if (state.kvsPending) Timer.set(0, false, kvsTrigger);
}

// v5.3.4: KVS-Aenderungen nur ZWISCHEN zwei Regelzyklen uebernehmen und nie
// mehrere Durchlaeufe gleichzeitig. Vorher startete jedes kvs_rev-Ereignis
// sofort einen eigenen Lesedurchlauf - beim manuellen Laden (3 Keys kurz
// nacheinander) liefen drei davon parallel zum Zyklus, dazu der Geraete-Write
// (peak bis 21126). Jetzt: Ereignis merkt nur vor; gelesen wird, wenn kein
// Zyklus laeuft (sonst ab unlock()). Waehrenddessen setzt update() aus.
// Kommt waehrend des Lesens eine weitere Aenderung, folgt genau ein
// weiterer Durchlauf.
function kvsTrigger() {
  if (!state.kvsPending || state.kvsBusy || state.busy) return;

  state.kvsPending = false;
  state.kvsBusy = true;
  state.kvsBusySince = Date.now();

  readKvsOverrides(function () {
    state.kvsBusy = false;
    print("KVS-Overrides aktualisiert.");
    if (state.kvsPending) Timer.set(0, false, kvsTrigger);
  });
}

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

  // Uebernommene Aenderungen immer loggen, damit sichtbar ist, welcher Key
  // den Override ausgeloest hat (ungueltige Werte weiterhin nur mit debug).
  if (n !== currentValue) {
    print("KVS " + key + ": Wert uebernommen (" + currentValue + " -> " + n + ")");
  }

  apply(n);
}

// v5.3.2: Jeder Key wird einzeln per KVS.Get gelesen statt alle auf einmal
// per KVS.GetMany. GetMany legt alle Keys samt etag gleichzeitig in den Heap
// (~2,3 kB) - das war die hoechste Speicherspitze beim Start. Beim Start
// (seed) wird ein fehlender Key (-105 "not found") direkt mit dem CONFIG-Wert
// angelegt; der eigene Seed-Durchlauf mit zweitem GetMany entfaellt.
// Kein cycleId-Stale-Check (v5.1.6): KVS-Werte gelten zyklusunabhaengig.
function readKvsOverrides(callback, seed) {
  if (!CONFIG.kvsEnabled) {
    callback();
    return;
  }

  // v5.3.5: Nach einer Aenderung von aussen EIN KVS.GetMany statt 11
  // Einzelabfragen. Seit 5.3.4 laeuft das nur zwischen zwei Zyklen - dann
  // liegt kein Report im Speicher und die GetMany-Antwort (~2,3 kB) bleibt
  // unter der Zyklus-Spitze. 11 RPCs dagegen bremsten den Shelly genau dann,
  // wenn das Dashboard schreibt (KVS.Set des Watch-Scripts lief in Timeouts).
  // Beim Start (seed) bleibt es bei Einzelabfragen: Grundstand dort hoeher.
  if (!seed) {
    kvsReadAll(callback);
    return;
  }

  if (seed && CONFIG.kvsForceReseed) {
    print("KVS-Seed: kvsForceReseed aktiv - schreibe alle Werte aus CONFIG " +
      "(bestehende Live-Overrides werden ueberschrieben!)");
  }

  kvsStep(0, seed, [], 0, callback);
}

// Alle Keys mit einem KVS.GetMany lesen und uebernehmen (nie schreiben).
function kvsReadAll(callback) {
  safeCall("KVS.GetMany", { match: KVS_MATCH }, function (res, err_code, err_msg) {
    let todo = [];

    if (err_code !== 0 || !res || !res.items) {
      reportError(state.errors, state.notified, "kvs", "KVS",
        "GetMany fehlgeschlagen (" + err_msg + ") - CONFIG unveraendert");
    } else {
      reportSuccess(state.errors, state.notified, "kvs", "KVS");
      if (CONFIG.debug) memLog("KVS GetMany");

      let items = res.items;
      let arr = Array.isArray(items);

      for (let n = 0; kvsKey(n) !== null; n++) {
        let key = kvsKey(n);
        let raw;

        if (arr) {
          for (let j = 0; j < items.length; j++) {
            if (items[j] && items[j].key === key) { raw = items[j].value; break; }
          }
        } else if (items[key]) {
          // aeltere Firmware: Objekt {key: {value, etag}}
          raw = items[key].value;
        }

        if (raw === undefined) continue;

        let f = kvsField(n);
        applyKvsValue(key, raw, f.c, f.ok, f.set);
        if (f.s !== undefined && kvsField(n).c !== f.c) todo.push(f.s);
      }
      items = null;
    }

    res = null;
    // Geraete-Syncs erst nach diesem Callback - die Firmware haelt die
    // GetMany-Antwort bis dahin fest.
    Timer.set(0, false, function () {
      runKvsSyncs(todo, 0, callback);
    });
  });
}

// Name von Key n: 0-2 global, danach je Geraet 4 Keys. null = kein Key mehr.
function kvsKey(n) {
  if (n < 3) return ["zdmc_setpoint", "zdmc_dischargeResetMargin", "zdmc_dischargeFixed"][n];
  n = n - 3;
  let i = (n - n % 4) / 4;
  if (i >= CONFIG.devices.length) return null;
  return "zdmc_dev" + i + "_" + ["dischargeAllowed", "reverse", "minSoc", "inputLimit"][n % 4];
}

// Zu Key n: aktueller Wert (c), Pruefung (ok), Uebernahme (set) und ggf. der
// Geraete-Sync fuer runKvsSyncs (s: gerade = minSoc, ungerade = inputLimit).
function kvsField(n) {
  if (n === 0) return { c: CONFIG.setpoint,
    ok: function (v) { return v >= -40 && v <= 40; },
    set: function (v) { CONFIG.setpoint = v; } };
  if (n === 1) return { c: CONFIG.dischargeResetMargin,
    ok: function (v) { return v >= 3 && v <= 79 && Math.round(v) === v; },
    set: function (v) { CONFIG.dischargeResetMargin = v; } };
  if (n === 2) return { c: CONFIG.dischargeFixed,
    ok: function (v) { return v === 0 || v >= CONFIG.dischargeStartupPower; },
    set: function (v) { CONFIG.dischargeFixed = v; } };

  n = n - 3;
  let i = (n - n % 4) / 4;
  let f = n % 4;
  let dev = CONFIG.devices[i];
  let bin = function (v) { return v === 0 || v === 1; };

  if (f === 0) return { c: (dev.dischargeAllowed === false ? 0 : 1), ok: bin,
    set: function (v) { dev.dischargeAllowed = (v !== 0); } };
  if (f === 1) return { c: (dev.reverse ? 1 : 0), ok: bin,
    set: function (v) { dev.reverse = (v !== 0); } };
  if (f === 2) return { c: dev.minSoc, s: i * 2,
    ok: function (v) { return v >= 10 && v <= dev.maxSoc - SOC_GAP; },
    set: function (v) { dev.minSoc = v; } };
  return { c: dev.inputLimit, s: i * 2 + 1,
    ok: function (v) { return v >= 0 && v <= dev.maxInputPower; },
    set: function (v) { dev.inputLimit = v; } };
}

// Liest Key n, uebernimmt ihn bzw. legt ihn an (seed), dann Key n + 1.
// Nicht lesbare Keys (ausser "fehlt") werden gezaehlt und am Ende gemeldet.
function kvsStep(n, seed, todo, fails, callback) {
  let key = kvsKey(n);

  if (key === null) {
    if (fails > 0) {
      reportError(state.errors, state.notified, "kvs", "KVS",
        fails + " Key(s) nicht lesbar - CONFIG dafuer unveraendert");
    } else {
      reportSuccess(state.errors, state.notified, "kvs", "KVS");
    }
    if (CONFIG.debug) memLog("KVS gelesen");
    runKvsSyncs(todo, 0, callback);
    return;
  }

  safeCall("KVS.Get", { key: key }, function (res, err_code, err_msg) {
    let f = kvsField(n);
    let write = false;

    if (err_code === 0 && res) {
      if (seed && CONFIG.kvsForceReseed) {
        write = true;
      } else {
        applyKvsValue(key, res.value, f.c, f.ok, f.set);
        if (f.s !== undefined && kvsField(n).c !== f.c) todo.push(f.s);
      }
    } else if (err_code === -105) {
      write = seed;
    } else {
      fails = fails + 1;
      if (CONFIG.debug) print("DEBUG KVS.Get " + key + " fehlgeschlagen (" + err_msg + ")");
    }

    res = null;
    let next = function () {
      kvsStep(n + 1, seed, todo, fails, callback);
    };

    if (!write) {
      next();
      return;
    }

    safeCall("KVS.Set", { key: key, value: f.c }, function (r, e, m) {
      if (e !== 0) print("KVS-Seed: " + key + " konnte nicht geschrieben werden (" + m + ")");
      else print("KVS-Seed: " + key + " = " + f.c + " gesetzt");
      next();
    });
  });
}

// Fuehrt die Geraete-Syncs nach dem KVS-Lesen nacheinander aus (v5.3.1).
function runKvsSyncs(todo, k, callback) {
  if (k >= todo.length) {
    callback();
    return;
  }

  let n = todo[k];
  let idx = (n - n % 2) / 2;
  let next = function () {
    if (CONFIG.debug) memLog("nach KVS-Sync " + CONFIG.devices[idx].label);
    runKvsSyncs(todo, k + 1, callback);
  };

  if (n % 2) syncInputLimitDevice(idx, next);
  else syncMinSocDevice(idx, next);
}

// v5.3.0: Wert hinter "k": aus dem JSON-Rohtext lesen, OHNE JSON.parse (spart
// ~2,4 kB Heap je Report). Suche in [a, b), b < 0 = bis Textende. Zahl oder
// null; mit q String oder null. Zendure liefert kompaktes JSON ("k":Wert) -
// aendert sich das Format, gibt es null statt eines geratenen Werts.
function jv(s, k, a, b, q) {
  let i = s.indexOf('"' + k + '":', a);
  if (i < 0 || (b >= 0 && i >= b)) return null;
  i = i + k.length + 3;
  if (q) {
    let e = s.indexOf('"', i + 1);
    return (s.charAt(i) === '"' && e > 0) ? s.slice(i + 1, e) : null;
  }
  let j = i;
  while (j < s.length && "0123456789-+.eE".indexOf(s.charAt(j)) >= 0) j++;
  let v = Number(s.slice(i, j));
  return (j === i || v !== v) ? null : v;
}

// Beginn von "properties", -1 = Report unbrauchbar (leer oder abgeschnitten).
// Die Seriennummer steht davor; die Werte zwischen "properties" und
// "packData" (dort stehen sn, heatState usw. je Akkupack noch einmal).
function propsPos(r) {
  return (r && r.lastIndexOf("}") >= r.length - 3) ? r.indexOf('"properties"') : -1;
}

function httpGet(url, callback) {
  safeCall(
    "HTTP.GET",
    {
      url: url,
      timeout: 4
    },
    callback
  );
}

function httpPost(url, body, callback) {
  let bodyStr = JSON.stringify(body);

  if (CONFIG.debug) {
    print("DEBUG httpPost -> url: " + url + " | body: " + bodyStr);
  }

  safeCall(
    "HTTP.Request",
    {
      method: "POST",
      url: url,
      headers: {
        "Content-Type": "application/json"
      },

      body: bodyStr,
      timeout: 4
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

  // Roh-Antwort sofort freigeben (siehe readDevice)
  res = null;

  let value;
  let fieldLabel;

  if (typeof field === "string") {

    // Bisheriges Verhalten: flacher Top-Level-Zugriff
    value = data[field];
    fieldLabel = field;

  } else {

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

      if (CONFIG.debug) {
        print("DEBUG " + cfg.label + ": report " + res.body.length + " Bytes");
        memLog("vor parse " + cfg.label);
      }

      // v5.3.0: Werte direkt aus dem Rohtext lesen (kein JSON.parse)
      let body = res.body;
      res = null;
      let a = propsPos(body);
      let b = a > 0 ? body.indexOf('"packData"', a) : -1;
      let soc = a > 0 ? jv(body, "electricLevel", a, b) : null;

      if (soc === null) {
        body = null;
        reportError(ds.errors, ds.notified, "json", cfg.label, "Fehler beim Parsen der Antwort");
        callback();
        return;
      }

      reportSuccess(ds.errors, ds.notified, "json", cfg.label);

      let sn = jv(body, "sn", 0, a, 1);
      if (sn) {
        ds.serial = sn;
      }

      if (!ds.serial) {
        body = null;
        reportError(ds.errors, ds.notified, "serial", cfg.label, "Keine Seriennummer gefunden");
        callback();
        return;
      }

      reportSuccess(ds.errors, ds.notified, "serial", cfg.label);

      ds.soc = soc;

      let newSocLimit = jv(body, "socLimit", a, b);
      if (ds.socLimit !== null && newSocLimit !== ds.socLimit) {
        print(cfg.label + ": socLimit " + ds.socLimit + "->" + newSocLimit +
          (newSocLimit === 1 ? " (Ladesperre)" : newSocLimit === 2 ? " (Entladesperre)" : " (normal)"));
      }
      ds.socLimit = newSocLimit;

      let newSocStatus = jv(body, "socStatus", a, b);
      if (ds.socStatus !== null && newSocStatus !== ds.socStatus) {
        print(cfg.label + ": socStatus " + newSocStatus +
          (newSocStatus === 1 ? " (Kalibrierung, aus Verteilung)" : " (Kalibrierung beendet)"));
      }
      ds.socStatus = newSocStatus;

      ds.gridReverse = jv(body, "gridReverse", a, b);

      // v5.1.9: Offgrid-Leistung nur mit debug fuer die Logzeile merken -
      // ohne debug kein zusaetzliches Feld im Geraetezustand. Geraete ohne
      // Offgrid-Ausgang liefern kein gridOffPower (null -> nicht geloggt).
      if (CONFIG.debug) ds.offGrid = jv(body, "gridOffPower", a, b);

      let acMode = jv(body, "acMode", a, b);
      ds.zenPower = acMode === 2 ? (jv(body, "outputHomePower", a, b) || 0) :
        acMode === 1 ? -(jv(body, "gridInputPower", a, b) || 0) : 0;

      body = null; // Rohtext freigeben, BEVOR callback() synchron das naechste Geraet anstoesst
      if (CONFIG.debug) memLog("nach parse " + cfg.label);
      ds.available = true;
      callback();
    }
  );
}

// v5.2.3: Abfrage-Reihenfolge pro Zyklus. Zuerst Geraete, die gerade NICHT
// regeln, danach die regelnden (zuletzt geschriebenes Soll != 0 oder
// gemeldetes Ist != 0) - jeweils in CONFIG-Reihenfolge. Direkt danach liest
// update() den Zaehler. So liegt das Ist des regelnden Geraets zeitlich
// unmittelbar vor dem Netzwert und raw = Netz + Ist passt zusammen, auch wenn
// jede HTTP-Abfrage ~1 s dauert. Regeln alle Geraete, entspricht die
// Reihenfolge der bisherigen (CONFIG-Reihenfolge).
function buildPollOrder() {
  let idle = [];
  let active = [];

  for (let i = 0; i < CONFIG.devices.length; i++) {
    let ds = state.devices[i];
    let isActive = (ds.outputLimit !== null && ds.outputLimit !== 0) ||
      ds.zenPower !== 0;

    if (isActive) active.push(i);
    else idle.push(i);
  }

  for (let k = 0; k < active.length; k++) {
    idle.push(active[k]);
  }

  return idle;
}

function readAllDevices(order, pos, myCycle, callback) {
  if (pos >= order.length) {
    callback();
    return;
  }

  readDevice(order[pos], myCycle, function () {
    readAllDevices(order, pos + 1, myCycle, callback);
  });
}

function zeroOutputs() {
  let out = [];

  for (let i = 0; i < CONFIG.devices.length; i++) {
    out[i] = 0;
  }

  return out;
}

// Prueft, ob der neu berechnete Output pro Geraet innerhalb der bestehenden
// Schreib-Hysterese um den zuletzt tatsaechlich geschriebenen Wert (ds.outputLimit)
// liegt UND die Richtung (Export/Idle-Import) gleich bliebe. Anker ist bewusst
// ds.outputLimit (aendert sich nur bei echtem Schreibvorgang) statt des Werts aus
// dem Vorzyklus - sonst koennte der Wert langsam ueber viele kleine Schritte aus
// dem Band "wegdriften", ohne dass es je erkannt wuerde.
function isOutputWithinHysteresis(output) {
  for (let i = 0; i < output.length; i++) {
    let ds = state.devices[i];

    if (!ds.available) continue;

    if (ds.outputLimit === null || ds.acMode === null) {
      return false; // noch nie geschrieben - kein Anker vorhanden
    }

    let targetAcMode = output[i] > 0 ? 2 : 1; // gleiche Zuordnung wie planWrite()

    if (targetAcMode !== ds.acMode) {
      return false; // Richtungswechsel zaehlt immer als Aenderung
    }

    if (Math.abs(output[i] - ds.outputLimit) >= CONFIG.hysteresis) {
      return false;
    }
  }

  return true;
}

function calculate(myCycle) {
  if (myCycle !== state.cycleId) {
    debugStale("calculate", myCycle);
    return;
  }

  if (CONFIG.debug) memLog("nach Netz");

  let n = CONFIG.devices.length;
  let sumZen = 0;
  let sumZenReverse = 0;
  let availableCount = 0;
  // v5.2.2: entlaedt gerade (Ist) ein Geraet, das NICHT in der Ladesperre
  // steht? socLimit=1-Geraete (PV-Bypass bei vollem Akku) zaehlen bewusst
  // nicht - deren Einspeisung soll weiterhin von einem anderen Geraet
  // geladen werden duerfen.
  let anyDischarging = false;

  let countedIps = {};

  for (let i = 0; i < n; i++) {
    if (state.devices[i].available) {
      let ip = CONFIG.devices[i].ip;

      if (!countedIps[ip]) {
        sumZen += state.devices[i].zenPower;

        if (CONFIG.devices[i].reverse && state.devices[i].socLimit !== 1) {
          sumZenReverse += state.devices[i].zenPower;
        }

        if (state.devices[i].socLimit !== 1 &&
            state.devices[i].zenPower > CONFIG.dischargeStopPower) {
          anyDischarging = true;
        }

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

  updateGridReverseLock();

  // v5.1.8: Asymmetrische Daempfung - in Richtung "weniger Export" schnell
  // (Faktor JUMP_FACTOR), in Gegenrichtung wie bisher mit dampingFactor.
  // Entladen: sinkt der Bedarf (Last aus), wird schnell zurueckgenommen.
  // Laden:    steigt der Ueberschuss (Wolke weg), wird schnell mehr geladen.
  // Die Gegenrichtung (mehr Entladen / weniger Laden) bleibt gedaempft -
  // dort entsteht kurz Netzbezug statt Export.
  // v5.2.0: schnelle Flanke (JUMP_FACTOR) erst ab einem Sprung > JUMP_THRESHOLD. Kleinere
  // Abweichungen (Messrauschen) werden wieder symmetrisch gedaempft - sonst
  // gehen Rausch-Ausreisser nach unten voll durch, nach oben nur gedaempft
  // (Zittern, mehr Schreibvorgaenge, leichter Bias Richtung Netzbezug).
  let raw = Math.round((state.gridPower - CONFIG.setpoint) + sumZen);

  if (state.smoothedOutput === null) {
    state.smoothedOutput = raw;
  } else {
    let aD = (raw < state.smoothedOutput - JUMP_THRESHOLD) ? JUMP_FACTOR : CONFIG.dampingFactor;
    state.smoothedOutput = state.smoothedOutput + aD * (raw - state.smoothedOutput);
  }

  // v5.2.2: Entlade-Signal nicht unter 0 W fallen lassen. dischargeTarget
  // wird nur bei >= 0 verwendet - ein negativer Wert hatte keine Funktion,
  // musste nach einer kurzen Exportspitze aber gedaempft wieder hochlaufen
  // (mehrere Zyklen Netzbezug, bevor das Entladen wieder startete).
  if (state.smoothedOutput < 0) state.smoothedOutput = 0;

  let dischargeTarget = Math.round(state.smoothedOutput);
  let dischargeFixedActive = CONFIG.dischargeFixed > 0;

  if (dischargeFixedActive) {
    dischargeTarget = CONFIG.dischargeFixed;
  }

  let rawCharge = Math.round((state.gridPower - CONFIG.setpoint) + sumZenReverse);

  if (state.smoothedCharge === null) {
    state.smoothedCharge = rawCharge;
  } else {
    let aC = (rawCharge < state.smoothedCharge - JUMP_THRESHOLD) ? JUMP_FACTOR : CONFIG.dampingFactor;
    state.smoothedCharge = state.smoothedCharge + aC * (rawCharge - state.smoothedCharge);
  }

  let chargeTarget = Math.round(state.smoothedCharge);

  let anyReverseCapable = false;

  for (let i = 0; i < n; i++) {
    if (CONFIG.devices[i].reverse) {
      anyReverseCapable = true;
    }
  }

  let chargeOutput = zeroOutputs();
  let chargeExclude = {};

  if (anyReverseCapable) {
    let alreadyChargingRev = sumZenReverse < 0;

    // v5.2.2: Laden nur NEU starten, wenn kein Geraet mehr real entlaedt.
    // Ein Export-Ausschlag waehrend des Entladens (Last kurz aus) wird so
    // zuerst nur durch Zuruecknehmen der Entladung beantwortet. Liegt im
    // Folgezyklus (Ist = 0 W) weiterhin Export an, startet das Laden dann
    // regulaer. Laufendes Laden (alreadyChargingRev) bleibt unberuehrt.
    // Bei aktivem dischargeFixed gilt die Sperre nicht: die feste Entladung
    // ist gewollt, PV-Ueberschuss soll weiter von einem anderen Geraet
    // geladen werden duerfen (Verhalten wie 5.2.1).
    if (chargeTarget < 0 &&
        (alreadyChargingRev ||
         ((!anyDischarging || dischargeFixedActive) &&
          chargeTarget <= (CONFIG.reverseStartupPower * -1)))) {
      chargeOutput = distributeCharge(chargeTarget);

      for (let i = 0; i < n; i++) {
        if (chargeOutput[i] !== 0) chargeExclude[i] = true;
      }
    }
  }

  let dischargeOutput;
  let alreadyDischarging = sumZen > 0;

  if (dischargeTarget >= 0 &&
      (alreadyDischarging || dischargeTarget >= CONFIG.dischargeStartupPower)) {
    dischargeOutput = distributeDischarge(dischargeTarget, chargeExclude);
  } else {
    dischargeOutput = zeroOutputs();
  }

  // v4.2.2: Bypass-Korrektur. socLimit=1-Geraete (Akku voll, "Laden vom Netz
  // gesperrt") bekommen in computeDischargeWeights() weiterhin ganz normal
  // einen Soll-Anteil zugeteilt (bewusst KEIN Ausschluss - sonst Deadlock,
  // das Geraet wuerde nie wieder einen Soll bekommen und socLimit nie mehr
  // verlassen). Liefert ein solches Geraet real (Ist) mehr, als ihm zugeteilt
  // wurde (Bypass-Ueberschuss), wird dieser Mehrbetrag JEDEN Zyklus frisch
  // aus aktuellem Ist/Soll ermittelt und von den uebrigen, nicht gesperrten
  // Geraeten abgezogen. Unterlieferung (Geraet faehrt Akku gerade hoch) wird
  // bewusst NICHT korrigiert - das gleicht der bestehende Regelkreis ueber
  // den naechsten Zyklus (Netzsaldo -> dischargeTarget) von selbst aus.
  dischargeOutput = applyBypassExcessCorrection(dischargeOutput);

  let output = [];
  for (let i = 0; i < n; i++) {
    output[i] = chargeOutput[i] !== 0 ? chargeOutput[i] : dischargeOutput[i];
  }

  let ladeKorrektur = chargeTarget - dischargeTarget;

  print(
    "Netzsaldo: " + Math.round(state.gridPower) + " W | Ist-Summe: " + sumZen +
    " W | Regelsignal: " + dischargeTarget +
    (dischargeFixedActive ? " W [FIX]" : " W") +
    " | Ladekorrektur: " + ladeKorrektur + " W"
  );

  if (CONFIG.idleSkip.enabled) {
    let withinBand = isOutputWithinHysteresis(output);

    if (state.idleSkipActiveThisCycle) {
      // Dieser Zyklus lief OHNE frischen Geraete-Poll (SOC/socLimit ggf. veraltet).
      // Nur Fruehabbruch pruefen - ein NEUER Sparmodus-Zeitraum darf hier
      // nicht gestartet werden, sonst reiht sich der Skip mit veralteten Daten
      // nahtlos aneinander und maxSkipSeconds waere wirkungslos.
      if (!withinBand) {
        print("Sparmodus aus (Hysterese/Richtung)");
        state.idleSkipRemaining = 0;
        state.idleUnchangedCount = 0;
      }
    } else {
      // Voller Poll-Zyklus mit frischen Geraetedaten - nur hier darf ein
      // neuer Sparmodus-Zeitraum beginnen.
      if (withinBand) {
        state.idleUnchangedCount = state.idleUnchangedCount + 1;

        if (state.idleUnchangedCount >= CONFIG.idleSkip.cyclesUnchanged) {
          state.idleSkipRemaining = IDLE_SKIP_CYCLES;
          state.idleUnchangedCount = 0;

          print("Sparmodus an: " + IDLE_SKIP_CYCLES + " Zyklen ohne Geraete-Poll");
        }
      } else {
        state.idleUnchangedCount = 0;
      }
    }
  }

  applyOutputs(output, myCycle);
}

function updateMode(directionState, targetMagnitude, cfg, capExceeded) {
  let currentMode = directionState.mode;

  if (currentMode === "single") {
    if (targetMagnitude > cfg.spreadAbove || capExceeded) {
      directionState.triggerCycles = directionState.triggerCycles + 1;

      if (directionState.triggerCycles > SPREAD_TRIGGER_CYCLES) {
        directionState.triggerCycles = 0;
        directionState.holdCycles = 0; // fresh start for the next spread->single evaluation
        return "spread";
      }

      return "single"; // Zyklus wird ausgesetzt - noch nicht bestaetigt
    }

    directionState.triggerCycles = 0;
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

  // Dead zone between concentrateBelow and spreadAbove:
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
    print("Ausgleich -> " + CONFIG.devices[bestIdx].label + " (+" + Math.round(advantage) + "%)");

    selector.active = bestIdx;
  }

  return selector.active;
}

// Wirksame Entlade-Hysterese eines Geraets: hoechstens maxSoc - minSoc - 11
// (Margin < maxSoc - minSoc - 10). Ist das Fenster dafuer zu klein, gilt 3.
function dischargeResetMarginFor(cfg) {
  return Math.max(3, Math.min(CONFIG.dischargeResetMargin, cfg.maxSoc - cfg.minSoc - 11));
}

function computeDischargeWeights(exclude) {
  let n = CONFIG.devices.length;
  let weight = [];
  let active = [];

  for (let i = 0; i < n; i++) {
    let ds = state.devices[i];
    let cfg = CONFIG.devices[i];

    // Entlade-Hysterese pflegen: Sperre ab minSoc, Freigabe erst ab minSoc + Margin
    if (ds.available) {
      if (ds.socLimit === 2 || ds.soc <= cfg.minSoc) ds.dischargeLocked = true;
      else if (ds.soc >= cfg.minSoc + dischargeResetMarginFor(cfg)) ds.dischargeLocked = false;
    }

    if (!ds.available || cfg.dischargeAllowed === false || ds.socLimit === 2 ||
        ds.dischargeLocked || ds.socStatus === 1 || (exclude && exclude[i])) {
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

// gridReverse-Sperrbedingung: fleet-weit, UNABHAENGIG von cfg.reverse.
function allDevicesAtChargeLimit() {
  let anyAvailable = false;
  for (let i = 0; i < CONFIG.devices.length; i++) {
    let ds = state.devices[i];
    if (!ds.available) return false;
    anyAvailable = true;
    if (ds.socLimit !== 1) return false;
  }
  return anyAvailable;
}

// gridReverse-Freigabebedingung: fleet-weit, UNABHAENGIG von cfg.reverse.
function anyDeviceClearlyBelowMax() {
  for (let i = 0; i < CONFIG.devices.length; i++) {
    let ds = state.devices[i];
    let cfg = CONFIG.devices[i];
    if (ds.available && ds.soc < cfg.maxSoc - CONFIG.chargeResetMargin) return true;
  }
  return false;
}

function evaluateChargeCapacity() {
  let n = CONFIG.devices.length;
  let weight = [];
  let active = [];

  for (let i = 0; i < n; i++) {
    let ds = state.devices[i];
    let cfg = CONFIG.devices[i];

    if (ds.socLimit === 1 || ds.socStatus === 1) {
      weight[i] = 0;
      active[i] = false;
      continue;
    }

    if (!ds.available || !cfg.reverse) {
      weight[i] = 0;
      active[i] = false;
      continue;
    }

    let w = cfg.maxSoc - ds.soc;
    if (w < 0) w = 0;

    weight[i] = w;
    active[i] = (w > 0);

    if (w === 0) {
      if (!ds.maxSocLogged) {
        print(cfg.label + ": maxSoc erreicht (" + ds.soc + "/" + cfg.maxSoc + "%)");
        ds.maxSocLogged = true;
      }
    } else if (ds.maxSocLogged) {
      print(cfg.label + ": unter maxSoc (" + ds.soc + "/" + cfg.maxSoc + "%)");
      ds.maxSocLogged = false;
    }
  }

  return { weight: weight, active: active };
}

function computeChargeWeights() {
  let result = evaluateChargeCapacity();
  return { weight: result.weight, active: result.active };
}

// Zentrale, pro Zyklus EINMAL laufende gridReverse-Fleet-Steuerung.
function updateGridReverseLock() {
  if (CONFIG.gridReverseMode !== "dynamic") return;

  if (!state.allMaxedLogged) {
    if (allDevicesAtChargeLimit()) {
      state.allMaxedLogged = true;
      setGridReverseAll(0, 2, function () {});
    }
  } else {
    if (anyDeviceClearlyBelowMax()) {
      state.allMaxedLogged = false;
      setGridReverseAll(0, 1, function () {});
    }
  }
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

  // Analog zu waterFillCharge: pro Geraet einfach auf 0 setzen, wenn der unter globalen Stop-Schwelle liegt
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

function distributeDischarge(target, exclude) {
  let weights = computeDischargeWeights(exclude);
  let weight = weights.weight;
  let active = weights.active;

  // Kapazitaet des AKTUELL aktiven Geraets (Stand letzter Zyklus) pruefen -
  // das ist die Grundlage fuer den Debounce, NICHT ein sofortiger Bypass.
  let stickyIdx = state.discharge.active;
  let capExceeded = (stickyIdx !== null && stickyIdx !== -1 &&
    CONFIG.devices[stickyIdx] && target > CONFIG.devices[stickyIdx].maxOutput);

  state.discharge.mode = updateMode(state.discharge, target, CONFIG.discharge, capExceeded);

  if (state.discharge.mode === "single") {
    let idx = pickStickyDevice(weight, active, state.discharge);

    if (idx === -1) {
      return zeroOutputs(); // nobody has any headroom at all
    }

    let cfg = CONFIG.devices[idx];
    let output = zeroOutputs();
    let o = Math.round(target);

    if (o > cfg.maxOutput) {
      if (CONFIG.debug) {
        print("DEBUG " + cfg.label + ": Ziel " + o +
          " W ueber maxOutput - waehrend Entprellung am Deckel (" +
          cfg.maxOutput + " W) gehalten");
      }
      o = cfg.maxOutput;
    }

    if (o < CONFIG.dischargeStopPower) {
      o = 0;
    }

    output[idx] = o;
    return output;
  }

  return waterFillDischarge(target, weight, active);
}

function distributeCharge(target) {
  let weights = computeChargeWeights();
  let weight = weights.weight;
  let active = weights.active;
  let magnitude = -target;

  let stickyIdx = state.charge.active;
  let capExceeded = (stickyIdx !== null && stickyIdx !== -1 &&
    CONFIG.devices[stickyIdx] && magnitude > CONFIG.devices[stickyIdx].maxInputPower);

  state.charge.mode = updateMode(state.charge, magnitude, CONFIG.charge, capExceeded);

  if (state.charge.mode === "single") {
    let idx = pickStickyDevice(weight, active, state.charge);

    if (idx === -1) {
      return zeroOutputs();
    }

    let cfg = CONFIG.devices[idx];
    let output = zeroOutputs();
    let o = Math.round(magnitude);

    if (o > cfg.maxInputPower) {
      if (CONFIG.debug) {
        print("DEBUG " + cfg.label + ": Ladebedarf " + o +
          " W ueber maxInputPower - waehrend Entprellung am Deckel (" +
          cfg.maxInputPower + " W) gehalten");
      }
      o = cfg.maxInputPower;
    }

    if (o < CONFIG.reverseStopPower) {
      o = 0;
    }

    output[idx] = o > 0 ? (o * -1) : 0;
    return output;
  }

  return waterFillCharge(target, weight, active);
}

// v4.2.2: Ermittelt pro Zyklus frisch, ob socLimit=1-Geraete (Bypass) mehr
// liefern als ihnen zugeteilt wurde, und legt den Ueberschuss auf die
// uebrigen, nicht gesperrten Geraete um. Kein Zustand, kein Timer - reine
// Funktion der aktuellen Ist-/Soll-Werte dieses einen Zyklus.
// v5.1.2: Ergebnis wird nie negativ (Untergrenze 0 bzw. dischargeStopPower).
// Frueher konnte ein negativer Anteil als Ladebefehl wirken - auch bei
// reverse:false und vorbei an allen Laderegeln. Ein Restueberschuss fuehrt
// jetzt zu Export und wird im Folgezyklus vom regulaeren Ladepfad
// uebernommen (rawCharge negativ, da sumZenReverse socLimit=1 ausschliesst).
function applyBypassExcessCorrection(dischargeOutput) {
  let n = CONFIG.devices.length;
  let excess = 0;

  for (let i = 0; i < n; i++) {
    let ds = state.devices[i];
    if (ds.available && ds.socLimit === 1) {
      let e = ds.zenPower - dischargeOutput[i];
      if (e > 0) excess += e; // nur Ueberlieferung zaehlt, Untershoot bewusst ignoriert
    }
  }

  if (excess <= 0) return dischargeOutput;

  let corrected = dischargeOutput.slice();
  let poolTotal = 0;

  for (let i = 0; i < n; i++) {
    let ds = state.devices[i];
    if (ds.available && ds.socLimit !== 1 && corrected[i] > 0) {
      poolTotal += corrected[i];
    }
  }

  if (poolTotal <= 0) {
    // Niemand entlaedt gerade aktiv - hier kann die Korrektur nicht greifen.
    // Wird ueber den normalen Regelkreis (Netzsaldo -> chargeTarget) im
    // naechsten Zyklus abgefangen, da sumZenReverse socLimit=1 bereits
    // ausschliesst.
    return dischargeOutput;
  }

  for (let i = 0; i < n; i++) {
    let ds = state.devices[i];
    if (!ds.available || ds.socLimit === 1 || corrected[i] <= 0) continue;

    let share = corrected[i] / poolTotal;
    let cut = Math.round(excess * share);
    corrected[i] -= cut;
    // Nie negativ: Restueberschuss uebernimmt im Folgezyklus der Ladepfad
    // (reverse, maxSoc, maxInputPower, Start/Stop-Schwellen gelten dort)
    if (corrected[i] < CONFIG.dischargeStopPower) corrected[i] = 0;
  }

  print("Bypass-Korrektur: " + excess + " W umverteilt");

  return corrected;
}

// acMode/outputLimit/inputLimit aus dem Zielwert
function planWrite(target, cfg, ds) {
  if (target === 0) {
    // Standby (auch Volltank): immer acMode 1.
    // smartMode wird NICHT hier entschieden - das macht einheitlich
    // resolveStandbySmartMode(), auch fuer den per Cooldown erzwungenen Fall.
    return { acMode: 1, outputLimit: 0, inputLimit: 0, smartMode: 1 };
  }

  if (target > 0) {
    return { acMode: 2, outputLimit: target, inputLimit: 0, smartMode: 1 }; // export
  }

  return { acMode: 1, outputLimit: 0, inputLimit: Math.abs(target), smartMode: 1 }; // laden
}

function acModeLabel(acMode) {
  return acMode === 2 ? "Export" : "Import/Idle";
}

// signierte Leistung aus dem plan-Objekt
function planSignedPower(plan) {
  return plan.acMode === 2 ? plan.outputLimit : (plan.inputLimit * -1);
}

function enforceDirectionCooldown(plan, ds) {
  if (CONFIG.directionChangeHoldCycles <= 0) return plan;

  if (plan.outputLimit === 0 && plan.inputLimit === 0) {
    ds.reversalHoldCount = 0;
    return plan;
  }

  if (ds.realDirection === null || ds.realDirection === plan.acMode) {
    ds.reversalHoldCount = 0;
    return plan;
  }

  ds.reversalHoldCount = ds.reversalHoldCount + 1;

  if (ds.reversalHoldCount > CONFIG.directionChangeHoldCycles) return plan;

  if (CONFIG.debug) {
    print("Richtungswechsel blockiert (" + ds.reversalHoldCount + "/" +
      CONFIG.directionChangeHoldCycles + "), halte Standby");
  }

  return { acMode: 1, outputLimit: 0, inputLimit: 0, smartMode: 1 };
  // smartMode final: siehe resolveStandbySmartMode()
}

// Gibt smartMode:0 erst frei, wenn das Geraet eine Mindestanzahl Zyklen
// ununterbrochen im Standby war (acMode 1, outputLimit=0, inputLimit=0) -
// unabhaengig davon, ob planWrite() das natuerlich lieferte oder
// enforceDirectionCooldown() einen Richtungswechsel blockiert hat.
// Jeder Nicht-Standby-Zyklus resettet den Zaehler sofort. Nur bei
// standbySmartModeZero:true relevant - sonst reiner Passthrough.
function resolveStandbySmartMode(plan, ds) {
  let isStandby = (plan.outputLimit === 0 && plan.inputLimit === 0);

  if (!isStandby || !CONFIG.standbySmartModeZero) {
    ds.standbyHoldCount = 0;
    return plan;
  }

  ds.standbyHoldCount = ds.standbyHoldCount + 1;

  if (ds.standbyHoldCount >= CONFIG.standbyHoldCycles) {
    if (CONFIG.debug && ds.standbyHoldCount === CONFIG.standbyHoldCycles) {
      print("smartMode 0 freigegeben nach " + ds.standbyHoldCount + " Standby-Zyklen");
    }
    plan.smartMode = 0;
  }

  return plan;
}

function updateRealDirection(ds, acMode, outputLimit, inputLimit) {
  if (outputLimit === 0 && inputLimit === 0) return;
  ds.realDirection = acMode;
}

function applyOutputs(output, myCycle) {
  let n = CONFIG.devices.length;
  let toWrite = [];
  let plans = [];

  for (let i = 0; i < n; i++) {
    let ds = state.devices[i];
    let cfg = CONFIG.devices[i];

    // v5.0.3: Geraet steht im manuellen AC-Laden (Dashboard-Knopf) - beide
    // Schalter aus UND ein Ladelimit gesetzt. Die Verteilrechnung schliesst
    // solche Geraete zwar schon ueber Gewicht=0 aus, berechnet aber trotzdem
    // ein Soll von 0 W und wuerde es bei naechster Gelegenheit auch schreiben
    // (sobald der Cache vom Ziel abweicht) - das hat bisher das manuelle
    // Laden nach wenigen Sekunden wieder auf Standby zurueckgesetzt. Deshalb
    // hier komplett aussteigen: kein Plan, kein Schreiben, Geraet bleibt
    // unberuehrt, bis der Nutzer "Manuelles Laden beenden" klickt (dann
    // wird inputLimit wieder 0 und dieser Zweig greift nicht mehr).
    if (cfg.dischargeAllowed === false && cfg.reverse === false && cfg.inputLimit > 0) {
      print(
        "  " + cfg.label + ": manuelles Laden aktiv (" + cfg.inputLimit +
        " W) - Regelung fuer dieses Geraet pausiert"
      );
      continue;
    }

    let rawPlan = planWrite(output[i], cfg, ds);
    let plan = enforceDirectionCooldown(rawPlan, ds);
    plan = resolveStandbySmartMode(plan, ds);
    let signedPower = planSignedPower(plan);
    plans[i] = plan;

    print(
      "  " + cfg.label + ": SOC " + (ds.available ? ds.soc + "%" : "n/a") +
      " | socL " + ds.socLimit +
      " | gridR " + (ds.gridReverse === null ? "n/a" : ds.gridReverse) +
      " | Ist " + ds.zenPower + " W | Soll " + output[i] + " W" +
      (CONFIG.debug && typeof ds.offGrid === "number" ? " | offGP " + ds.offGrid + " W" : "") +
      " | acMode " + plan.acMode + " (" + acModeLabel(plan.acMode) + ")" +
      (plan !== rawPlan ? " [Cooldown haelt Standby]" : "") +
      (cfg.dryRun ? " [DRYRUN - wird nicht geschrieben]" : "")
    );

    if (!ds.available) continue;

    if (ds.outputLimit !== null &&
        Math.abs(signedPower - ds.outputLimit) < CONFIG.hysteresis &&
        ds.acMode === plan.acMode &&
        ds.smartMode === plan.smartMode) {
      continue; // Wert/acMode/smartMode unveraendert
    }

    if (cfg.dryRun) {
      updateRealDirection(ds, plan.acMode, plan.outputLimit, plan.inputLimit);
      ds.acMode = plan.acMode;
      ds.outputLimit = signedPower;
      ds.smartMode = plan.smartMode;

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

    writeAllDevices(toWrite, plans, myCycle, 0, function () {
      unlock(myCycle);
    });
  });
}

function writeDevice(index, plans, myCycle, callback) {
  if (myCycle !== state.cycleId) {
    debugStale("writeDevice(" + CONFIG.devices[index].label + ") vor dem Schreiben", myCycle);
    return;
  }

  let cfg = CONFIG.devices[index];
  let ds = state.devices[index];
  let plan = plans[index];

  let acMode = plan.acMode;
  let outputLimit = plan.outputLimit;
  let inputLimit = plan.inputLimit;
  let smartMode = plan.smartMode;
  let signedPower = planSignedPower(plan);

  if (CONFIG.debug) memLog("vor write " + cfg.label);

  httpPost(

    "http://" + cfg.ip + "/properties/write",

    {
      sn: ds.serial,

      properties: {
        acMode: acMode,
        outputLimit: outputLimit,
        inputLimit: inputLimit,
        smartMode: smartMode
      }
    },

    function (res, error_code, error_message) {
      if (myCycle !== state.cycleId) {
        debugStale("writeDevice(" + cfg.label + ") Antwort", myCycle);
        return;
      }

      if (CONFIG.debug) memLog("write-Antwort " + cfg.label);

      if (res && res.code === 200) {
        updateRealDirection(ds, acMode, outputLimit, inputLimit);
        ds.acMode = acMode;
        ds.outputLimit = signedPower;
        ds.smartMode = smartMode;

        let stateLabel;
        if (acMode === 2) {
          stateLabel = "Export";
        } else if (inputLimit > 0) {
          stateLabel = "Laden vom Netz";
        } else {
          stateLabel = "Idle";
        }

        print(cfg.label + ": Leistung gesetzt: " + signedPower + " W (" + stateLabel + ", smartMode " + smartMode + ")");
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

function writeAllDevices(indices, plans, myCycle, pos, callback) {
  if (pos >= indices.length) {
    callback();
    return;
  }

  writeDevice(indices[pos], plans, myCycle, function () {
    writeAllDevices(indices, plans, myCycle, pos + 1, callback);
  });
}

// v5.1.8: Netzmessung ZULETZT. Vorher wurde das Netz am Zyklusanfang gelesen
// und die Geraete erst danach per HTTP (je ~0,5-1 s). Rampte ein Geraet
// dazwischen, passten Netzsaldo und zenPower zeitlich nicht zusammen ->
// falsches raw -> Ueberschwingen. Jetzt: erst alle Geraete, dann direkt
// das Netz. Bei gridSource "local" ist der Netzwert damit praktisch
// zeitgleich mit dem letzten Geraetewert.
// Die idleSkip-Entscheidung faellt dafuer VOR den Messungen. Im Skip-Zyklus
// wird wie bisher nur das Netz gelesen.
// v5.2.3: Das regelnde Geraet wird zuletzt abgefragt (siehe buildPollOrder()).
// Vorher lagen bei 3 Geraeten ca. 2 s zwischen dessen Ist und dem Netzwert,
// weil die nicht regelnden Geraete dazwischen abgefragt wurden.
function update() {

  if (state.kvsBusy) {
    // Haengt die KVS-Uebernahme (sollte nie passieren), nach der Watchdog-
    // Zeit trotzdem weiterregeln.
    if (Date.now() - state.kvsBusySince < CONFIG.watchdog) {
      if (CONFIG.debug) print("DEBUG Takt ausgesetzt - KVS-Uebernahme laeuft");
      return;
    }
    print("KVS-Uebernahme haengt seit " + Math.round(Date.now() - state.kvsBusySince) + " ms - Regelung laeuft weiter");
    state.kvsBusy = false;
  }

  if (state.busy) {
    // Vorheriger Zyklus laeuft noch (z.B. langsames Geraet) - Takt verwerfen.
    // Haengt der Zyklus dauerhaft, loest spaeter der Watchdog aus.
    print("Takt uebersprungen - Zyklus " + state.cycleId + " laeuft noch seit " +
      Math.round(Date.now() - state.cycleStartedAt) + " ms");
    state.cySkip = state.cySkip + 1;
    return;
  }

  let myCycle = lock();

  let afterGrid = function (ok) {
    if (!ok) return; // unlock() ist in readGridPower bereits erfolgt

    Timer.set(0, false, function () {
      calculate(myCycle);
    });
  };

    if (CONFIG.idleSkip.enabled && state.idleSkipRemaining > 0) {
      state.idleSkipRemaining = state.idleSkipRemaining - 1;
      state.idleSkipActiveThisCycle = true;

      if (CONFIG.debug) {
        print("DEBUG Sparmodus: Geraete-Poll ausgesetzt (" +
          state.idleSkipRemaining + " Zyklen verbleibend, Netzmessung aktuell)");
      }

    readGridPower(myCycle, afterGrid);
      return;
    }

    state.idleSkipActiveThisCycle = false;

    for (let i = 0; i < CONFIG.devices.length; i++) {
      state.devices[i].available = false;
    }

    // v5.3.3: Netz erst lesen, wenn der HTTP-Callback des letzten Geraets
    // zurueck ist - sonst liegen dessen Antwort und das em-Statusobjekt
    // (~22 Felder) gleichzeitig im Heap. Verzoegerung nur wenige ms.
    readAllDevices(buildPollOrder(), 0, myCycle, function () {
    Timer.set(0, false, function () {
      if (myCycle !== state.cycleId) {
        debugStale("readGridPower", myCycle);
        return;
      }
      readGridPower(myCycle, afterGrid);
    });
  });
}

function setGridReverseDevice(index, value, callback) {
  let cfg = CONFIG.devices[index];
  let ds = state.devices[index];

  if (cfg.dryRun || !ds.serial) { callback(); return; }

  httpPost(
    "http://" + cfg.ip + "/properties/write",
    { sn: ds.serial, properties: { gridReverse: value } },
    function (res, error_code, error_message) {
      if (res && res.code === 200) {
        ds.gridReverse = value;
        print("  " + cfg.label + ": gridReverse=" + value + " gesetzt");
      } else {
        if (CONFIG.debug) {
          print("DEBUG " + cfg.label + "/gridReverse - res: " + JSON.stringify(res) +
            " | error_code: " + error_code + " | error_message: " + error_message);
        }
        print("  " + cfg.label + ": gridReverse=" + value + " fehlgeschlagen");
      }
      callback();
    }
  );
}

function setGridReverseAll(index, value, callback) {
  if (index >= CONFIG.devices.length) { callback(); return; }
  setGridReverseDevice(index, value, function () {
    setGridReverseAll(index + 1, value, callback);
  });
}

// Schreibt CONFIG.devices[index].minSoc (z.B. nach KVS-Live-Override) als
// Hardware-Schutzgrenze aufs Geraet. Sonst bliebe die Geraete-eigene minSoc-Sperre
// auf dem beim Start (syncSocLimitsAll) geschriebenen Wert stehen.
function syncMinSocDevice(index, callback) {
  let cfg = CONFIG.devices[index];
  let ds = state.devices[index];

  if (cfg.dryRun || !ds.serial) {
    if (CONFIG.debug) {
      print("  " + cfg.label + ": minSoc-Sync skip");
    }
    callback();
    return;
  }

  let minSocRaw = Math.round(cfg.minSoc * 10);

  httpPost(
    "http://" + cfg.ip + "/properties/write",
    { sn: ds.serial, properties: { minSoc: minSocRaw } },
    function (res, error_code, error_message) {
      if (res && res.code === 200) {
        print("  " + cfg.label + ": minSoc auf Geraet synchronisiert (" + cfg.minSoc + "%)");
      } else {
        if (CONFIG.debug) {
          print("DEBUG " + cfg.label + "/minSocSync - res: " + JSON.stringify(res) +
            " | error_code: " + error_code + " | error_message: " + error_message);
        }
        print("  " + cfg.label + ": minSoc-Sync fehlgeschlagen beim Schreiben");
      }
      callback();
    }
  );
}

// v4.5.0: Schreibt CONFIG.devices[index].inputLimit (nach KVS-Live-Override)
// als Ladeleistung aufs Geraet - analog syncMinSocDevice(). Reine Zusatz-
// Schnittstelle fuer manuelles AC-Laden; die Regelung bleibt unveraendert.
// Voraussetzung ist, dass der User das Geraet vorher aus der Lastverteilung
// genommen hat (reverse:false, dischargeAllowed:false).
//
// v5.0.3: Schreibt zusaetzlich acMode/outputLimit/smartMode statt nur
// inputLimit. Vorher hing es vom zufaelligen acMode des Geraets im Moment
// des Klicks ab, ob das AC-Laden ueberhaupt anspringt - stand der Hub noch
// auf acMode 2 (Export) o.ae., blieb inputLimit wirkungslos gesetzt und das
// Geraet in seinem bisherigen Modus haengen (sporadisch: Standby oder
// unbemerkt weiterlaufendes Entladen, je nach Ausgangszustand). Jetzt wird
// acMode 1 (Laden) explizit erzwungen, genau wie es writeDevice() fuer den
// automatischen Pfad ohnehin tut.
//
// Nach erfolgreichem Schreiben werden Software-Cache (ds.acMode/outputLimit/
// smartMode) und der Richtungswechsel-Schutz (ds.realDirection via
// updateRealDirection()) nachgezogen. Sonst haette applyOutputs() im naechsten
// regulaeren Zyklus einen veralteten Stand und der Cooldown-Schutz wuerde
// waehrend/nach manuellem Laden nicht mehr greifen bzw. faelschlich ausloesen.
function syncInputLimitDevice(index, callback) {
  let cfg = CONFIG.devices[index];
  let ds = state.devices[index];

  if (cfg.dryRun || !ds.serial) {
    if (CONFIG.debug) {
      print("  " + cfg.label + ": inputLimit-Sync skip");
    }
    callback();
    return;
  }

  httpPost(
    "http://" + cfg.ip + "/properties/write",
    { sn: ds.serial, properties: { acMode: 1, outputLimit: 0, inputLimit: cfg.inputLimit, smartMode: 1 } },
    function (res, error_code, error_message) {
      if (res && res.code === 200) {
        // updateRealDirection() bricht bei outputLimit===0 && inputLimit===0
        // (Beenden des manuellen Ladens) selbst ab - hier also unbedingt
        // aufrufen, kein Sonderfall fuer inputLimit=0 noetig.
        updateRealDirection(ds, 1, 0, cfg.inputLimit);
        ds.acMode = 1;
        ds.outputLimit = cfg.inputLimit * -1;
        ds.smartMode = 1;
        print("  " + cfg.label + ": manuelles Laden erzwungen (acMode 1), inputLimit gesetzt: " + cfg.inputLimit + " W");
      } else {
        if (CONFIG.debug) {
          print("DEBUG " + cfg.label + "/inputLimitSync - res: " + JSON.stringify(res) +
            " | error_code: " + error_code + " | error_message: " + error_message);
        }
        print("  " + cfg.label + ": inputLimit-Sync fehlgeschlagen");
      }
      callback();
    }
  );
}

function syncSocLimitsDevice(index, callback) {
  let cfg = CONFIG.devices[index];
  let ds = state.devices[index];

  if (cfg.dryRun) {
    print("  " + cfg.label + ": [DRYRUN] SoC-Grenzwerte werden nicht geschrieben");

    // WICHTIG: callback() NICHT synchron aufrufen - bei mehreren
    Timer.set(0, false, callback);
    return;
  }

  // v5.3.0: Seriennummer und gridReverse liefert der normale Geraete-Abruf
  // (readDevice) - kein eigener Report-Abruf mehr. Ist das Geraet nicht
  // erreichbar oder die Antwort unlesbar, meldet readDevice das selbst.
  readDevice(index, state.cycleId, function () {
      if (!ds.serial) {
        print("  " + cfg.label + ": SoC-Sync uebersprungen - keine Seriennummer");
        callback();
        return;
      }

      let minSocRaw = Math.round(cfg.minSoc * 10);
      let maxSocRaw = Math.round(cfg.maxSoc * 10);
      if (ds.gridReverse === 2) {state.allMaxedLogged = true;}

      let props = { minSoc: minSocRaw, socSet: maxSocRaw };
      if (CONFIG.gridReverseMode === "always1") props.gridReverse = 1;
      if (CONFIG.gridReverseMode === "always2") props.gridReverse = 2;

      // v5.3.2: Erst schreiben, wenn der Report-Callback zurueck ist - sonst
      // liegen Report-Antwort und POST gleichzeitig im Heap (~1,2 kB Spitze).
      Timer.set(0, false, function () {
      httpPost(

        "http://" + cfg.ip + "/properties/write",

        { sn: ds.serial, properties: props },

        function (res2, error_code, error_message) {
          if (res2 && res2.code === 200) {
            if (props.gridReverse !== undefined) ds.gridReverse = props.gridReverse;
            print("  " + cfg.label + ": SoC-Grenzwerte synchronisiert (minSoc " +
              cfg.minSoc + "%, maxSoc " + cfg.maxSoc + "%)" +
              (props.gridReverse !== undefined ? ", gridReverse=" + props.gridReverse : ""));
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
      });
  });
}

function syncSocLimitsAll(index, callback) {
  if (index >= CONFIG.devices.length) {
    callback();
    return;
  }

  syncSocLimitsDevice(index, function () {
    if (CONFIG.debug) memLog("nach SoC-Sync " + CONFIG.devices[index].label);
    syncSocLimitsAll(index + 1, callback);
  });
}

// ---------------------------------------------------------------
// Banner: Zeilen werden LAZY erzeugt - es liegt immer nur EINE
// fertige Zeile im Heap.
// ---------------------------------------------------------------
let bannerIndex = 0;

function bannerLine(i) {
  let n = CONFIG.devices.length;

  if (i === 0) return "--------------------------------";
  if (i === 1) return "Version " + VERSION;
  if (i === 2) return "Multi-Device Controller gestartet";
  if (i === 3) return "Geraete    : " + n;

  if (i < 4 + n) {
    let k = i - 4;
    let cfg = CONFIG.devices[k];

    return "  - [dev" + k + "] " + cfg.label + " (" + cfg.ip + "): Entladen " +
      (cfg.dischargeAllowed === false ? "nein" : "ja") +
      ", minSoc " + cfg.minSoc +
      "%, maxOutput " + cfg.maxOutput + " W, Laden vom Netz " +
      (cfg.reverse
        ? ("ja (maxInput " + cfg.maxInputPower + " W, maxSoc " + cfg.maxSoc + "%)")
        : "nein") +
      (cfg.dryRun ? "  [DRYRUN]" : "");
  }

  let j = i - 4 - n;

  if (j === 0) return "Grid source: " + CONFIG.gridSource +
    (CONFIG.gridSource === "remote" ? " (" + CONFIG.gridSourceIp + ")" : "") +
    (CONFIG.gridSource === "http_json" ?
      " (" + CONFIG.gridSourceUrl + ", Feld: " + CONFIG.gridSourceField +
      (CONFIG.gridSourceInvert ? ", invertiert" : "") + ")" : "");

  if (j === 1) return "Interval   : " + CONFIG.interval + " ms";
  if (j === 2) return "Watchdog   : " + CONFIG.watchdog + " ms";
  if (j === 3) return "Setpoint   : " + CONFIG.setpoint + " W";
  if (j === 4) return "Hysteresis : " + CONFIG.hysteresis + " W (pro Geraet)";
  if (j === 5) return "Damping    : " + CONFIG.dampingFactor + " (Sprung > " + JUMP_THRESHOLD + " W in Richtung weniger Export: " + JUMP_FACTOR + ")";

  if (j === 6) return "Entladen   : ein Geraet unter " +
    CONFIG.discharge.concentrateBelow + " W, verteilen ueber " +
    CONFIG.discharge.spreadAbove + " W";

  if (j === 7) return "Laden      : ein Geraet unter " +
    CONFIG.charge.concentrateBelow + " W, verteilen ueber " +
    CONFIG.charge.spreadAbove + " W";

  if (j === 8) return "Konzentrieren-Haltezeit: " +
    CONFIG.concentrateHoldMinutes + " min (" + CONCENTRATE_HOLD_CYCLES +
    " Zyklen) - gilt fuer spread->single, discharge+charge";

  if (j === 9) return "Ausgleich  : ab " + CONFIG.rebalance.socMargin +
    " Prozentpunkten Vorsprung, sofort";

  if (j === 10) return "Reverse Start/Stop: " +
    CONFIG.reverseStartupPower + " W / " + CONFIG.reverseStopPower + " W";

  if (j === 11) return "Discharge Start/Stop: " +
    CONFIG.dischargeStartupPower + " W / " + CONFIG.dischargeStopPower + " W";

  if (j === 12) return "Richtungswechsel-Bremse: " +
    (CONFIG.directionChangeHoldCycles > 0 ?
      CONFIG.directionChangeHoldCycles + " Takt(e) (pro Geraet)" : "deaktiviert");

  if (j === 13) return "Err.Thresh : " + CONFIG.errorThreshold;
  if (j === 14) return "Debug      : " + (CONFIG.debug ? "aktiviert" : "deaktiviert");

  if (j === 15) return "Signal     : " + (CONFIG.signal.enabled ?
    ("aktiviert (" + CONFIG.signal.typ + ")") : "deaktiviert");

  if (j === 16) return "KVS-Feature: " +
    (CONFIG.kvsEnabled ? "aktiviert" : "deaktiviert (kein Live-Override)");

  if (j === 17) return "gridReverse-Modus: " + CONFIG.gridReverseMode;

  if (j === 18) return "Sparmodus  : " + (CONFIG.idleSkip.enabled ?
    ("aktiviert (ab " + CONFIG.idleSkip.cyclesUnchanged + " gleichen Zyklen, max. " +
      IDLE_SKIP_CYCLES + " Zyklen aussetzen / " + CONFIG.idleSkip.maxSkipSeconds + " s)") :
    "deaktiviert");

  if (CONFIG.kvsEnabled) {
    if (j === 19) return "KVS-Keys   : " + KVS_MATCH;

    if (j === 20) return "KVS-Force-Reseed  : " + (CONFIG.kvsForceReseed ?
      "AKTIV - ueberschreibt bei JEDEM Start alle Live-Overrides!" :
      "aus (Standard, empfohlen)");

    if (j === 21) return "--------------------------------";
    return null;
  }

  if (j === 19) return "--------------------------------";

  return null;
}

function printBannerLine(onDone) {
  let line = bannerLine(bannerIndex);

  if (line === null) {
    if (onDone) onDone();
    return;
  }

  print(line);
  bannerIndex = bannerIndex + 1;

  Timer.set(150, false, function () {
    printBannerLine(onDone);
  });
}

printBannerLine(function () {

  if (CONFIG.signal.enabled) {
    sendSignalMessage("✅ Multi-Device-Controller " + VERSION + " gestartet (" +
      CONFIG.devices.length + " Geraete).");
  }
  print("--------------------------------");
  if (CONFIG.debug) memLog("nach Banner");
  print("Synchronisiere SoC-Grenzwerte einmalig... ");
  syncSocLimitsAll(0, function () {

    print("SoC-Sync abgeschlossen.");

    // Hilfsfunktion zum Starten des Timers (vermeidet doppelten Code)
    let startController = function () {
      // Einmal-Code der Startphase freigeben. Verzoegert per Timer.set(0),
      // damit keine der Funktionen mehr auf dem Aufruf-Stack liegt.
      Timer.set(0, false, function () {
        try {
          printBannerLine = null;
          bannerLine = null;
          syncSocLimitsDevice = null;
          syncSocLimitsAll = null;
          checkBand = null;

          // Nur Funktionen, deren einzige Aufrufstellen durch die jeweilige
          // (nicht KVS-aenderbare) CONFIG-Einstellung nie erreicht werden.
          if (!CONFIG.kvsEnabled) {
            readKvsOverrides = null;
            kvsKey = null;
            kvsField = null;
            kvsStep = null;
            kvsReadAll = null;
            runKvsSyncs = null;
            applyKvsValue = null;
            syncMinSocDevice = null;
            syncInputLimitDevice = null;
          }
          if (!CONFIG.signal.enabled) msgResult = null;
          if (!CONFIG.signal.enabled || CONFIG.signal.typ != "WEBHOOK") sendWebhookMessage = null;
          if (!CONFIG.signal.enabled || CONFIG.signal.typ == "WEBHOOK") simpleEncode = null;
          if (CONFIG.gridSource === "local") handleGenericGridResponse = null;
          if (CONFIG.gridReverseMode !== "dynamic") {
            setGridReverseAll = null;
            setGridReverseDevice = null;
          }
        } catch (e) {
          // mJS erlaubt das Ueberschreiben evtl. nicht - dann einfach ignorieren
        }
        if (CONFIG.debug) memLog("nach Freigabe Startcode");
      });

      if (CONFIG.debug) memLog("vor Regelbetrieb");
      print("Starte Regelbetrieb.");
      print("--------------------------------");

      Timer.set(CONFIG.interval, true, update);
    };

    // PRÜFUNG: Ist KVS überhaupt aktiviert?
    if (!CONFIG.kvsEnabled) {

      print("KVS-Funktion ist deaktiviert - KVS wird ignoriert.");
      startController();

    } else {

      print("Lade KVS-Overrides (fehlende Keys werden angelegt)...");

        readKvsOverrides(function () {

          // StatusHandler nur registrieren, wenn KVS aktiv ist
          Shelly.addStatusHandler(function (e) {
            if (e.component === "sys" && e.delta && typeof e.delta.kvs_rev !== "undefined") {
              print("KVS-Aenderung erkannt (Rev: " + e.delta.kvs_rev + ")" +
                (state.kvsBusy || state.busy ? " - vorgemerkt" : " - Lade Overrides..."));
              state.kvsPending = true;
              kvsTrigger();
            }
          });

          print("KVS Event-Listener aktiv.");
          startController();
        }, true);
    }
  });
});
