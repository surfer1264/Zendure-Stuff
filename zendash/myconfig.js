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
      label: "Fatamorgana",
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
  //   <IP>     - dieses Script laeuft auf einem EIGENEN Shelly; die KVS
  //              wird per nativer RPC ueber HTTP gelesen und geschrieben:
  //              http://<IP>/rpc/KVS.GetMany bzw. /rpc/KVS.Set
  //
  // Die getrennte Variante ist die empfohlene: Espruino teilt sich einen
  // Variablenpool von rund 1600 Eintraegen fuer ALLE Scripte eines Geraets.
  // Laufen Regel-Script und dieses Script zusammen, fragen beide dieselben
  // Hubs ab, und zwei gleichzeitige Antworten von je ~1,3 kB sprengen den
  // Pool - es stirbt, wer als naechstes Speicher anfordert. Auf einem
  // eigenen Geraet entfaellt das. Die RPC-Anfragen bedient drueben die
  // Firmware, nicht ein Script, kosten dort also keine Variablen.
  //
  // Bei getrenntem Betrieb ausserdem gridSource auf "remote" stellen und
  // gridSourceIp auf den Shelly mit der EM-Messung zeigen lassen.
  // Voraussetzung: auf dem KVS-Geraet ist keine Authentifizierung aktiv.
  // ------------------------------------------------------------------
  kvsHost: "192.168.178.117",

  // Hysterese ist im Regel-Script NICHT ueber die KVS veraenderbar. Der Wert
  // wird hier nur gespiegelt, damit das Dashboard ihn anzeigen kann (gleicher
  // Wert wie CONFIG.hysteresis im Regel-Script eintragen).
  hysteresis: 12,

  // ------------------------------------------------------------------
  // SMARTMETER SECTION - 1:1 Struktur/Feldnamen wie in zerooutput_multi_kvs.js
  // Where to read the household grid power from, there are three options
  gridSource: "remote", // "local", "remote", "http_json"
  // ------------------------------------------------------------------
  // ONLY required/used when gridSource = "remote".
  // IP address of the Shelly Pro 3EM providing the grid measurement.
  gridSourceIp: "192.168.178.117",
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

  // Bewusst langsamer als die Dashboard-Seite (4 s). Auf demselben Geraet
  // laeuft das Regel-Script mit eigenem Zyklus und fragt DIESELBEN Hubs ab.
  // Beide Scripte teilen sich einen Variablenpool von rund 1600 Eintraegen;
  // treffen zwei Hub-Antworten von je ~1,3 kB gleichzeitig ein, reisst er.
  // Ein langsamerer Takt senkt die Wahrscheinlichkeit dieser Kollision.
  // Die Anzeige wird dadurch bis zu 8 s alt - das ist der Preis.
  pollIntervalSec: 8
};
