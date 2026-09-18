let CONFIG = {
  devices: [
     {
      ip: "192.168.178.143",    
      label: "SF2400",          
      minSoc: 20,               
      maxSoc: 100,              
      dischargeAllowed: true,   
      reverse: true,            
      maxInputPower: 1200,       
      maxOutput: 800,          
      dryRun: false            
     },
     {
      ip: "192.168.178.150",   
      label: "SF800",          
      minSoc: 20,              
      maxSoc: 100,             
      dischargeAllowed: true,  
      reverse: true,           
      maxInputPower: 1200,      
      maxOutput: 800,          
      dryRun: false            
    },
  ],
  // ------------------------------------------------------------------
  // SMARTMETER SECTION
  gridSource: "local", // "local", "remote", "http_json"
  // ------------------------------------------------------------------
  // ONLY required/used when gridSource = "remote".
  gridSourceIp: "192.168.178.117",
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
  hysteresis: 13,
  // Damping / gain factor for the COMBINED control signal (0 < factor <= 1),
  dampingFactor: 0.65,

  // ------------------------------------------------------------------
  // THRESHOLD SECTION ONLY RELEVANT FOR MULTI DEVICES
  discharge: {
    concentrateBelow: 500,  // W - below this combined target, use ONE device
    spreadAbove: 790        // W - above this, split across all devices
  },

  charge: {
    concentrateBelow: 500,
    spreadAbove: 790
  },
  // Time-coupled hysteresis for  (only) spread -> single 
  concentrateHoldMinutes: 1,

  // ------------------------------------------------------------------
  // SOC-BALANCING Max. SOC-Differenz zwischen Geraeten (%)
  rebalance: {
    socMargin: 6        // percentage points of advantage required to switch
  },

  // ------------------------------------------------------------------
  // REVERSE-Hysterese, nur bei reverse:true relevant
  reverseStartupPower: 40,
  // Ladeleistung, unter der gestoppt wird 
  reverseStopPower: 25,
  // gridReverse-Modus: dynamic / always1 / always2
  gridReverseMode: "dynamic",
  chargeResetMargin: 10, // nur relevant bei gridReverseMode: "dynamic"

  // ------------------------------------------------------------------
  // DISCHARGE MODE SECTION
  dischargeStartupPower: 40,
  // Entladeleistung, unter der gestoppt wird 
  dischargeStopPower: 25,

  // ------------------------------------------------------------------
  // INTERNAL SECTION BE CAREFUL
  // Update interval (milliseconds)
  interval: 4000,
  // Dont Change It
  // Anzahl Fehler bis Benachrichtigung
  errorThreshold: 15,
  // Cooldown-Takte Laden/Entladen-Wechsel
  directionChangeHoldCycles: 5,
  // true->smartMode 0, false->1
  standbySmartModeZero: false,
  // KVS-Live-Override an/aus (false = CONFIG fix, kein GetMany)
  kvsEnabled: true,
  // true = Start ueberschreibt KVS mit CONFIG, danach false
  kvsForceReseed: false,
  // operation to keep the console output clean.
  debug: false,
  // Idle skip section
  idleSkip: {
    enabled: true,       // false = Funktion komplett aus, Verhalten wie vorher
    cyclesUnchanged: 3,  // so viele Zyklen in Folge gleicher Output, bevor ausgesetzt wird
    maxSkipSeconds: 48   // max. Alter der Geraete-Daten (SOC/socLimit) waehrend des Aussetzens
  },
  // ------------------------------------------------------------------
  // MESSAGE SECTION
  signal: {
    enabled: true,          // set to true to activate notifications
    typ: "WEBHOOK",	    // "SIGNAL", "WHATSAPP" oder "WEBHOOK"
    phone: "bddd4bab-ddc1-435c-8df6-fe06cacd91b5",   // e.g. +4917XXXXXXXX (nur SIGNAL/WHATSAPP)
    apiKey: "988780",      // CallMeBot API key
    webhookUrl: "http://192.168.178.50:8123/api/webhook/-1fhzv1ksfMHbOOCWxPeTaz7Q" // nur WEBHOOK
  }
};
