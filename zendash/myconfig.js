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