// Zendure Dynamic Output Controller - Multi-Device Version
// Shelly mJS: Balancing mehrerer Zendure-Geraete gegen Pro 3EM/JSON-Zaehler
// Konfiguration erfolgt ausschliesslich im CONFIG-Block unten
//
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
  // Damping / gain factor for the COMBINED control signal (0 < factor <= 1),
  dampingFactor: 0.65,

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
  // KVS-Live-Override an/aus (false = CONFIG fix, kein GetMany)
  kvsEnabled: false,
  // true = Start ueberschreibt KVS mit CONFIG, danach false
  kvsForceReseed: false,
  // operation to keep the console output clean.
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
