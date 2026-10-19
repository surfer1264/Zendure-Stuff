[:de: Deutsch](readme.md) · :gb: **English** · [:fr: Français](readme_FR.md)

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

# Controller – Getting Started

The Controller (`zerooutput_multi_kvs`) is the control script on your **Controller Shelly**. It measures your grid draw and distributes charging and discharging across your Zendure batteries so that as little as possible comes from the grid and nothing goes unused into the grid.

This page gets you to the **first working run**. How to check and change it in everyday use is described in [Controller day-to-day](benutzerdoku.md) (German), all details are in the [full documentation](gesamtdoku.md) (German). What changed recently is in the [changelog](CHANGELOG.md).

> 🤖 This English version was translated from the [German original](readme.md) by Claude (Anthropic's AI). If anything is unclear or contradictory, the German version applies. Log messages of the script are in German and are quoted here as they appear.

---

## Checklist before you start

- [ ] **Two Shellys** Gen2 or newer with script support ([compatible devices](../kompatible_geraete_EN.md)) – one for the Controller, one for zenDash API + Watchdog. The Controller always runs **alone** on its Shelly.
- [ ] **Batteries with zenSDK** (from SolarFlow 800 onwards) in the same network, ideally with a fixed IP address (set in your router).
- [ ] **Important:** Remove the batteries from **HEMS** (Home Energy Management System) in the Zendure app – otherwise the cloud sends its own control commands in parallel. Exception Zendure Smart Meter D0: its local interface is enabled once via HEMS. This only concerns the meter, the batteries still stay out of HEMS.
- [ ] A **smart meter** for the grid draw. Simplest option: the Controller runs directly on a Shelly Pro 3EM.

---

## Setting up with the Configurator (recommended)

1. **[Download the helper](https://github.com/surfer1264/Zendure-Stuff/releases/latest)** and start it. The Configurator opens in your browser.
2. Choose **"Configure from scratch or update manually"** and answer the questions: batteries, grid source, notifications, control parameters.
3. In the result, click **"⚡ Upload directly"**. The script lands on the Controller Shelly, starts and is set up for autostart.
4. Continue with [Start & check](#start--check).

The complete guide – including updates, replacing a Shelly and error messages – is with the [Configurator](../Multiconfigurator/readme_EN.md).

---

## Without the Configurator (by hand)

Only for those who want to maintain their script themselves.

### 1. Get the script

Download the **minified** version [`zerooutput_multi_kvs_mini.js`](zerooutput_multi_kvs_mini.js). Only this one can be loaded onto the Shelly. The source version `zerooutput_multi_kvs_src.js` is meant for reading – it is too large for the Shelly.

### 2. Adjust the CONFIG block

At the top of the script is the block `let CONFIG = { ... };`. You must adjust at least these parts:

**Batteries** – one entry per Zendure device in `devices`, separated by commas:

```js
devices: [
  {
    ip: "192.168.178.143",   // IP address of the battery
    label: "SF2400",         // short name for log and messages
    minSoc: 15,              // reserve in %
    maxSoc: 100,             // charge target in %
    dischargeAllowed: true,  // may discharge
    reverse: true,           // may absorb surplus from the grid
    maxInputPower: 1000,     // max. charging power in W
    maxOutput: 800,          // max. discharging power in W
    dryRun: false            // true = calculate only, write nothing (test)
  },
  // ... more batteries
],
```

For the first run it is usually enough to set `ip`, `label`, `maxInputPower` and `maxOutput` to match your device. More on this: [chapter 4b](gesamtdoku.md#4b-mehrere-solarflow-geräte-einpflegen) (German).

**Smart meter** – `gridSource`:

- `"local"` (default): the script runs directly on a **Shelly Pro 3EM**. Nothing else to do.
- `"remote"`: **another** Shelly Pro 3EM in the network, also set `gridSourceIp`.
- `"http_json"`: a meter with a JSON interface (e.g. Zendure Smart Meter 3CT or D0, everHome EcoTracker, Tasmota, Shelly 3EM non-Pro), also set `gridSourceUrl` and `gridSourceField`. Nested fields as an array, e.g. `["StatusSNS","DVS7420","power"]`. The Configurator has ready-made templates for this.

Details: [chapter 5](gesamtdoku.md#5-smartmeter-anbindung---die-drei-grid-quellen-im-überblick) (German).

**Thresholds** – the default values are enough to start with. They appear twice in the CONFIG block, separately for discharging (`discharge: { ... }`) and charging (`charge: { ... }`). If you want them right straight away ([chapter 7b](gesamtdoku.md#7b-empfehlung-für-ersteinstellung), German):

- `spreadAbove` ≈ rated power of one battery (e.g. 800 W for an SF800, 2400 W for an SF2400)
- `concentrateBelow` ≈ 0.6 × `spreadAbove`

### 3. Upload

1. Open the web interface of the Controller Shelly (`http://<IP-of-the-Shelly>`) → **Scripts**.
2. Stop and delete other scripts on this Shelly – the Controller needs the memory to itself.
3. Create a new script ("Create script", on older firmware "Add script"), give it a name, paste the code, **Save**.

What this looks like in detail: [Install and Run Shelly Script](https://github.com/surfer1264/Zendure-Stuff/wiki/Install-and-Run-Shelly-Script).

### For advanced users: with `deploy.cmd`

The [Deploy](Deploy) folder contains tools (Windows, Python 3 required) that insert your own configuration, minify the script and upload it:

1. In the `Deploy` folder (next to `deploy.cmd`), **create the file `myconfig.js` yourself** – it is intentionally not in the repository. It contains only your `let CONFIG = { ... };` block. The easiest way to get it is from the [Configurator](../Multiconfigurator/readme_EN.md#functions-in-the-result-step) via "💾 Save CONFIG block only"; alternatively copy the block from `zerooutput_multi_kvs_src.js` and adjust it. Comment lines before or after it do no harm.

    ```js
    // myconfig.js – only the CONFIG block
    let CONFIG = {
      devices: [ /* your batteries */ ],
      gridSource: "local",
      // ... all other settings
    };
    ```

    `myconfig.js` is listed in the repository's `.gitignore`. This way your IPs and credentials don't accidentally end up in a commit.

2. Enter in `deploy.cmd`: `SHELLY_IP` (Controller Shelly) and `SKRIPTNAME` (default `ctrl`). `MEINE_CONFIG` is already set to `myconfig.js` – only change it if your file has a different name.
3. Run `deploy.cmd`. Sequence: insert CONFIG (`swap_config.py`) → minify (`minify_keep_config.py`) → upload and start (`upload_shelly.py`).

> **Important:** `deploy.cmd` always takes the CONFIG block from **your** file. It writes the minified version to `..\zerooutput_multi_kvs_mini.js` – i.e. over the file from the repository. If you update the folder via Git, don't commit this change, or point `FERTIG` to a file of your own. `minify.cmd` only creates the minified version without your own configuration.

---

## Start & check

1. Click **Start** for the script and enable **"Run on startup"** (with direct upload this happens automatically). On the first start the Controller syncs `minSoc`/`maxSoc` with the devices once and then controls every 4 seconds.
2. Open the log and check the start banner: it begins with `Version …` and `Multi-Device Controller gestartet` and shows all active values at a glance ([chapter 8.7](gesamtdoku.md#87-startprotokoll-banner), German).
3. If a line like this appears regularly

    ```text
    Netzsaldo: 12 W | Ist-Summe: 340 W | Regelsignal: 352 W | Ladekorrektur: 0 W
    ```

    (grid balance | actual total | control signal | charge correction)

    ✅ Done – the Controller is regulating.

4. With `"http_json"`, **check the sign** once: switch on a larger load – the grid value in the log must **rise**. If it falls, set `gridSourceInvert: true`.

If the grid draw stays calm for a longer time, the Controller reports "Sparmodus" (power-saving mode) and polls the batteries less often. This is normal.

---

## Going further (optional)

- Live settings via KVS, e.g. from the [dashboard](../zendash_watch_API_ZenSDK/dashboard_EN.md) or Home Assistant – [chapter 13](gesamtdoku.md#13-live-override-der-regelparameter-per-kvs-z-b-home-assistant) (German)
- Signal/WhatsApp notification – [chapter 8.5](gesamtdoku.md#85-signal-benachrichtigung-callmebot--inkl-whatsapp) (German)
- Test mode `dryRun` – [chapter 4c](gesamtdoku.md#4c-testmodus-dryrun) (German)
- Messages and dashboard: [zenDash API + Watchdog](../zendash_watch_API_ZenSDK/readme_EN.md) on the second Shelly

---

## How is the Shelly doing?

Open in your browser, replacing `<IP>` with the Shelly's address:

| Purpose | Call |
| --- | --- |
| List scripts (number, name, status) | `http://<IP>/rpc/Script.List` |
| Memory usage of a script | `http://<IP>/rpc/Script.GetStatus?id=<number>` |
| Uptime, RAM of the whole system | `http://<IP>/rpc/Sys.GetStatus` |

More convenient with the helper: "🔍 Check memory" and "Recording a log" in the [Configurator](../Multiconfigurator/readme_EN.md#7-how-tos).

---

## What else is in the folder

| File / folder | Purpose |
|---|---|
| [`zerooutput_multi_kvs_src.js`](zerooutput_multi_kvs_src.js) | readable source version of the Controller |
| [`zerooutput_multi_kvs_mini.js`](zerooutput_multi_kvs_mini.js) | minified version for uploading |
| [`CHANGELOG.md`](CHANGELOG.md) | changes per version |
| [`Deploy`](Deploy) | your own deploy pipeline, see [above](#for-advanced-users-with-deploycmd) |
| [`yaml`](yaml) | Example for Home Assistant: reads the Controller's KVS values via REST (`rest.yaml`), writes them back via `rest_command` (`rest_commands.yaml`) and provides them as sliders (`template/kvs.yaml`). Replace the IP `192.168.178.117` with that of your Controller Shelly. `configuration.yaml` includes the `templates/` folder in Home Assistant (`!include_dir_merge_list templates/`) – that's where the file `kvs.yaml` from the repository folder `template` belongs. Background: [chapter 13.6](gesamtdoku.md#136-nutzung-über-home-assistant) (German) |

---

## Download

**View** opens the file on GitHub, **Download** delivers the plain file. If the browser only opens it as text: right-click → "Save link as …".

| File | Purpose | Links |
|---|---|---|
| `zerooutput_multi_kvs_mini.js` | for uploading to the Shelly | [View](https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Controller/zerooutput_multi_kvs_mini.js) · [Download](https://raw.githubusercontent.com/surfer1264/Zendure-Stuff/main/shelly_script/Controller/zerooutput_multi_kvs_mini.js) |
| `zerooutput_multi_kvs_src.js` | readable source version | [View](https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Controller/zerooutput_multi_kvs_src.js) · [Download](https://raw.githubusercontent.com/surfer1264/Zendure-Stuff/main/shelly_script/Controller/zerooutput_multi_kvs_src.js) |
| `CHANGELOG.md` | changes per version | [View](https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Controller/CHANGELOG.md) · [Download](https://raw.githubusercontent.com/surfer1264/Zendure-Stuff/main/shelly_script/Controller/CHANGELOG.md) |
