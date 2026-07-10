// ======================================================
// Zendure Dynamic Output Controller
// Runs on a Shelly Pro 3PM
//
// It tries to output power into the household according to current load
// The aim is to output as little power as possible to the public net and
// use the most inside the household and batteries.
// Everything locally without any cloud involved.
//
// 1. Remove the Zendure from HEMS in the app
// 2. Copy the whole content and paste it into your Shell 3PM Script UI
// 3. Set the Zendure-IP
// 4. Press start (and set it to start on boot time of the Shelly)
// Optional: change parameters in CONFIG to your liking
//
// This is working on a SolarFlow 800 with 2 battery packs
// and might be working on similar setups.
// On Jul. 09th 2026 there was a major outage of the Zendure cloud
// which inspired that script to be more independend from the outside.
// It should even work if the internet connection is down.
//
// ... And ofc. a lot of AI coding aid was involved ;-)
//
// ======================================================


let CONFIG = {

  // Zendure IP address
  zendure: "<IP address of the Zendure device here",

  // Update interval in milliseconds
  interval: 3000,

  // Watchdog timeout in milliseconds
  watchdog: 5000,


  // Minimum battery state of charge required for output
  minSoc: 10,


  // Minimum allowed output power
  minOutput: 50,

  // Maximum allowed output power
  maxOutput: 800

};



let state = {

  gridPower: 0,
  zenOutput: 0,
  soc: 0,

  serial: null,

  outputLimit: -1,

  busy: false,
  watchdogTimer: null

};



// ======================================================
// Lock handling and watchdog
// ======================================================

function lock() {

  state.busy = true;


  if (state.watchdogTimer !== null)
    Timer.clear(state.watchdogTimer);



  state.watchdogTimer = Timer.set(
    CONFIG.watchdog,
    false,
    function () {

      print("Watchdog timeout - resetting lock");

      state.busy = false;
      state.watchdogTimer = null;

    }
  );

}



function unlock() {

  state.busy = false;


  if (state.watchdogTimer !== null) {

    Timer.clear(state.watchdogTimer);
    state.watchdogTimer = null;

  }

}



// ======================================================
// HTTP helper functions
// ======================================================

function httpGet(url, callback) {

  Shelly.call(
    "HTTP.GET",
    {
      url: url
    },
    callback
  );

}



function httpPost(url, body, callback) {

  Shelly.call(
    "HTTP.Request",
    {
      method: "POST",
      url: url,

      headers: {
        "Content-Type": "application/json"
      },

      body: JSON.stringify(body)

    },
    callback
  );

}



// ======================================================
// Read local Shelly power measurement
// ======================================================

function readGridPower() {

  let em = Shelly.getComponentStatus("em:0");


  if (!em) {

    print("No EM data available");
    unlock();
    return;

  }


  state.gridPower = em.total_act_power;

}



// ======================================================
// Read Zendure status
// ======================================================

function readZendure() {


  httpGet(

    "http://" + CONFIG.zendure + "/properties/report",

    function(res) {


      if (!res || res.code !== 200) {

        print("Zendure not reachable");
        unlock();
        return;

      }


      let data;


      try {

        data = JSON.parse(res.body);

      }

      catch(e) {

        print("JSON parsing error");
        unlock();
        return;

      }



      // Get serial number from Zendure response
      if (data.sn) {

        state.serial = data.sn;

      }



      if (!state.serial) {

        print("No Zendure serial number found");
        unlock();
        return;

      }



      state.soc =
        data.packData[0].socLevel;



      state.zenOutput =
        data.properties.outputHomePower;



      calculate();


    }

  );

}



// ======================================================
// Calculate required output power
// ======================================================

function calculate() {


  let output = 0;



  // Only provide output above minimum SOC

  if (state.soc > CONFIG.minSoc) {


    output = Math.round(
      state.gridPower + state.zenOutput
    );



    // Limit lower boundary

    if (output < 0)
      output = 0;



    // Limit maximum output

    if (output > CONFIG.maxOutput)
      output = CONFIG.maxOutput;



    // Apply minimum output only when output is active

    if (output > 0 &&
        output < CONFIG.minOutput)

      output = CONFIG.minOutput;


  }



  // Skip update if value did not change

  if (output === state.outputLimit) {

    unlock();
    return;

  }



  state.outputLimit = output;



  print(
    "Grid:",
    state.gridPower,
    "W | Zendure:",
    state.zenOutput,
    "W | SOC:",
    state.soc,
    "% | SN:",
    state.serial,
    "| Output:",
    output,
    "W"
  );



  writeZendure(output);


}



// ======================================================
// Write output limit to Zendure
// ======================================================

function writeZendure(output) {


  httpPost(

    "http://" + CONFIG.zendure + "/properties/write",


    {

      sn: state.serial,

      properties: {

        outputLimit: output

      }

    },


    function(res) {


      if (res && res.code === 200)

        print("Zendure output set:", output, "W");


      else

        print("Zendure write error");



      unlock();


    }

  );


}



// ======================================================
// Main control loop
// ======================================================

function update() {


  if (state.busy) {

    print("Previous cycle still running");
    return;

  }


  lock();


  // Read power directly from local Shelly meter
  readGridPower();


  // Read Zendure data and calculate output
  readZendure();


}



// ======================================================
// Startup
// ======================================================

print("--------------------------------");
print("Zendure Controller started");
print("Interval :", CONFIG.interval, "ms");
print("Watchdog :", CONFIG.watchdog, "ms");
print("Min SOC  :", CONFIG.minSoc, "%");
print("Min Out  :", CONFIG.minOutput, "W");
print("Max Out  :", CONFIG.maxOutput, "W");
print("--------------------------------");


Timer.set(
  CONFIG.interval,
  true,
  update
);
