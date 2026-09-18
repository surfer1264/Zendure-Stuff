let CONFIG = {
  // ------------------------------------------------------------------
  // GERAETEBLOCK - 1:1 identisch zum Controller-Block (gleiche
  // Reihenfolge = gleicher Index i wie "zdmc_dev{i}_..." in der KVS)
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
      maxInputPower: 1000,
      maxOutput: 800,
      inputLimit: 0,
      dryRun: false
    }
  ],

  kvsHost: "192.168.178.117",

  hysteresis: 12,

  dischargeStartupPower: 35,

  // ------------------------------------------------------------------
  // SMARTMETER SECTION - zeigt auf dieselbe Quelle wie der Controller;
  // "local" wird hier zu "remote" auf dieselbe IP uebersetzt, da die
  // zenDash-API in aller Regel auf einem eigenen Geraet laeuft.
  gridSource: "remote",
  gridSourceIp: "192.168.178.117",
  gridSourceEmId: 0,
  gridSourceUrl: "http://<IP-of-your-meter>/properties/report",
  gridSourceField: "total_power",
  gridSourceInvert: false,

  httpTimeout: 5,

  pollIntervalSec: 8
};