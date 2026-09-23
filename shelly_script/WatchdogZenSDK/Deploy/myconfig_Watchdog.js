let CONFIG = {
  version: "1.4.0",

  devices: [
    { ip: "192.168.178.143", label: "SF2400", enabled: true },
    { ip: "192.168.178.150", label: "SF800", enabled: true }
  ],

  // Warnschwellen (global)
  vollSchwelle: 99,        // %
  entladeReset: 90,        // %
  minVoltWarn: 2.9,        // V
  minVoltReset: 3.1,       // V
  tempWarn: 45.0,          // °C
  tempReset: 30.0,         // °C

  // Astro-Offset
  sunriseOffset: 0,        // Min
  sunsetOffset: 0,

  maxMessageLength: 900,   // Zeichen vor Trim

  // Nachrichtenversand
  signal: {
    enabled: false,
    typ: "SIGNAL",         // "SIGNAL", "WHATSAPP" oder "WEBHOOK"
    phone: "PHONE-STRING",
    apiKey: "YOUR_API_KEY",
    webhookUrl: "http://<IP-ADRESSE>:8123/api/webhook/<id>"
  },

  // Polling & Timer
  pollIntervalMs: 120000,
  httpTimeout: 5,
  watchdog: 15000,
  errorThreshold: 5,

  // Extended Logging
  debug: false,             // true = ausfuehrliche Logging-Ausgaben / false = nur wichtige Logs
  // Banner-Darstellung
  bannerVerbose: false      // true = schrittweises Banner / false = 1 Zeile
};