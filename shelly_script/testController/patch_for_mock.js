// patch_for_mock.js
// Nimmt eine beliebige Version von zerooutput_multi_kvs.js und schreibt eine
// Testversion, bei der NUR die Verbindungs-Parameter auf den Mock-Server
// umgebogen sind. Alle anderen CONFIG-Werte (minSoc, maxOutput, Hysterese,
// dischargeAllowed, interval, ...) bleiben exakt wie im Original.
//
// Aufruf:
//   node patch_for_mock.js pfad/zur/neuen_version.js zdmc_test.js
"use strict";

const fs = require("fs");

const inPath = process.argv[2];
const outPath = process.argv[3] || "zdmc_test.js";

if (!inPath) {
  console.error("Nutzung: node patch_for_mock.js <input.js> [output.js]");
  process.exit(1);
}

let code = fs.readFileSync(inPath, "utf8");

// --- 1) IPs innerhalb von CONFIG.devices[...] der Reihe nach ersetzen ---
const devicesStart = code.indexOf("devices: [");
if (devicesStart === -1) {
  console.error("WARNUNG: 'devices: [' nicht gefunden - IPs wurden NICHT gepatcht. Bitte manuell pruefen.");
} else {
  // Ende des devices-Arrays suchen (erstes "],\n" auf oberster Klammerebene danach)
  let depth = 0, i = devicesStart + "devices: [".length - 1, end = -1;
  for (; i < code.length; i++) {
    if (code[i] === "[") depth++;
    else if (code[i] === "]") { depth--; if (depth === 0) { end = i; break; } }
  }
  if (end === -1) {
    console.error("WARNUNG: Ende des devices-Arrays nicht gefunden - IPs wurden NICHT gepatcht.");
  } else {
    let block = code.slice(devicesStart, end + 1);
    let devIndex = 0;
    block = block.replace(/ip:\s*"[^"]*"/g, () => {
      const replacement = `ip: "localhost:3900/dev${devIndex}"`;
      devIndex++;
      return replacement;
    });
    if (devIndex > 2) {
      console.error(`WARNUNG: ${devIndex} Geraete gefunden, Mock unterstuetzt aktuell nur 2 (dev0/dev1). ` +
        "Weitere Geraete zeigen ins Leere - mock_server.js muss erweitert werden.");
    }
    code = code.slice(0, devicesStart) + block + code.slice(end + 1);
  }
}

// --- 2) gridSource / gridSourceUrl / gridSourceField auf den Mock umbiegen ---
// (trailing Komma muss VOR dem Kommentar stehen bleiben, sonst JS-Syntaxfehler!)
code = code.replace(
  /gridSource:\s*"[^"]*"(,?)/,
  'gridSource: "http_json"$1 // TEST: automatisch auf Mock umgebogen (patch_for_mock.js)'
);
code = code.replace(
  /gridSourceUrl:\s*"[^"]*"(,?)/,
  'gridSourceUrl: "http://localhost:3900/grid/properties/report"$1'
);
code = code.replace(
  /gridSourceField:\s*"[^"]*"(,?)/,
  'gridSourceField: "total_power"$1 // TEST: muss zum Mock-Response-Feld passen'
);

fs.writeFileSync(outPath, code);
console.log(`Fertig: ${outPath} geschrieben (nur ip/gridSource*-Felder gepatcht, Rest unveraendert).`);
