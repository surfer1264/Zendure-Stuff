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