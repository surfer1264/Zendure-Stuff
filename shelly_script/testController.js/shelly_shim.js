// Minimaler Shim fuer Shelly.call / Timer.set / Timer.clear / print,
// damit das unveraenderte mJS-Skript (bis auf CONFIG-IPs) unter Node laeuft.
"use strict";

const http = require("http");
const vm = require("vm");
const fs = require("fs");

// Wiederverwendete Keep-Alive-Verbindung statt fuer jeden Request neu
// aufzubauen - reduziert den Overhead pro Zyklus deutlich (v.a. auf Windows).
const keepAliveAgent = new http.Agent({ keepAlive: true, maxSockets: 8 });

function doHttp(method, urlStr, headers, body, timeoutSec, callback) {
  const u = new URL(urlStr);
  const opts = {
    hostname: u.hostname,
    port: u.port || 80,
    path: u.pathname + u.search,
    method: method,
    headers: headers || {},
    timeout: (timeoutSec || 5) * 1000,
    agent: keepAliveAgent, // wiederverwendete TCP-Verbindung statt Neuaufbau pro Request
  };
  const req = http.request(opts, (res) => {
    let chunks = [];
    res.on("data", (c) => chunks.push(c));
    res.on("end", () => {
      callback({ code: res.statusCode, body: Buffer.concat(chunks).toString("utf8") }, 0, "");
    });
  });
  req.on("timeout", () => { req.destroy(); callback(null, -104, "timeout"); });
  req.on("error", (e) => { callback(null, -1, String(e)); });
  if (body) req.write(body);
  req.end();
}

function buildSandbox(logPrefix) {
  const timers = new Map();
  let timerId = 1;
  // Beschleunigt NUR wiederkehrende Timer (repeat=true, das ist der Haupt-
  // Regelzyklus). Einmalige Timer (Watchdog, Timer.set(0,...), Banner-
  // Verzoegerungen) laufen unveraendert in echter Zeit - sonst wuerde der
  // Watchdog faelschlich anschlagen, bevor die echten HTTP-Roundtrips
  // zum Mock fertig sind.
  const SPEED_FACTOR = Number(process.env.SPEED_FACTOR || 1);
  const MIN_REAL_MS = Number(process.env.MIN_REAL_MS || 15);

  const Shelly = {
    call: function (method, params, callback) {
      if (method === "HTTP.GET") {
        doHttp("GET", params.url, {}, null, params.timeout, callback);
      } else if (method === "HTTP.Request") {
        doHttp(params.method || "GET", params.url, params.headers || {}, params.body || null, params.timeout, callback);
      } else if (method === "KVS.GetMany") {
        callback({ items: [] }, 0, "");
      } else if (method === "KVS.Set") {
        callback({}, 0, "");
      } else {
        callback(null, -1, "unbekannte Methode im Shim: " + method);
      }
    },
    getComponentStatus: function () { return null; },
    addStatusHandler: function () {},
  };

  const Timer = {
    set: function (ms, repeat, cb) {
      const id = timerId++;
      const realMs = repeat
        ? Math.max(MIN_REAL_MS, Math.round(ms / SPEED_FACTOR))
        : ms; // Einmal-Timer NICHT beschleunigen (Watchdog etc.)
      const handle = repeat
        ? setInterval(cb, realMs)
        : setTimeout(cb, realMs);
      timers.set(id, { handle, repeat });
      return id;
    },
    clear: function (id) {
      const t = timers.get(id);
      if (!t) return;
      if (t.repeat) clearInterval(t.handle); else clearTimeout(t.handle);
      timers.delete(id);
    },
  };

  const sandbox = {
    Shelly, Timer,
    print: function (...args) { console.log("[" + logPrefix + "]", ...args); },
    Date, Math, JSON, console,
    setTimeout, clearTimeout, setInterval, clearInterval,
  };
  vm.createContext(sandbox);
  return sandbox;
}

function runScript(path, logPrefix) {
  const code = fs.readFileSync(path, "utf8");
  const sandbox = buildSandbox(logPrefix || "zdmc");
  vm.runInContext(code, sandbox, { filename: path });
  return sandbox;
}

module.exports = { runScript };
