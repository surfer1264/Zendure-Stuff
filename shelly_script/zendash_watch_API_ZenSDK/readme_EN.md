# zenDash API + Watchdog

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

🌐 [Deutsch](readme.md) · **English** · [Français](readme_FR.md)

A Shelly script for your **Dashboard Shelly** that takes on two tasks around your Zendure batteries:

- **API for the dashboard** – The [dashboard](dashboard.md) (German) uses it to show grid draw, state of charge and power of your batteries. You can also change Controller settings and start manual charging.
- **Watchdog** – The script notifies you via Signal, WhatsApp or webhook when a battery is full, gets too warm, a cell voltage is too low or a battery can no longer be reached. In addition, you receive a short summary in the morning and in the evening.

Both parts can be switched on and off individually. A single script queries the batteries and shares the data between both tasks – this saves memory on the Shelly and reduces the load on your Zendure devices. Previously there were two separate scripts (zenDash API 2.x and AkkuVolt Watchdog 1.x) which, depending on the number of batteries, together hit the Shelly's memory limit.

The current version and all changes are listed in the [changelog](CHANGELOG.md).

---

## Contents

- [What you need](#what-you-need)
- [How the script works](#how-the-script-works)
- [Installation](#installation)
- [Configuration](#configuration)
- [Dashboard](#dashboard)
- [Messages](#messages)
- [Manual charging and auto-stop](#manual-charging-and-auto-stop)
- [Last full charge](#last-full-charge)
- [Switching from the old scripts](#switching-from-the-old-scripts)
- [Memory usage](#memory-usage)
- [Troubleshooting](#troubleshooting)

---

## What you need

- **A dedicated Shelly** with script support (generation 2 or newer: Plus, Pro, Gen3 …). The script always runs on a different Shelly than the Controller – both together do not fit into the memory of one Shelly.
- **Zendure batteries with local interface** (zenSDK), reachable at `http://<battery-IP>/properties/report`. Tested with SolarFlow 2400 Pro and SolarFlow 800.
- **The [Controller](../Controller/readme.md)** (German) on your Controller Shelly if you want to use the dashboard. The dashboard reads and writes its settings. If you only use the watchdog, you don't need it.
- **For messages** (optional):
  - Signal or WhatsApp: a free API key from [CallMeBot](https://www.callmebot.com)
  - or a webhook, for example in Home Assistant

> **Note:** **No password protection** may be active on the Controller Shelly. Otherwise this script cannot read and write the settings there.

---

## How the script works

The script adjusts its pace depending on whether someone is watching:

| Situation | What happens |
|---|---|
| **Dashboard is open** | The grid meter and all batteries are queried every 8 seconds. The watchdog checks these values at the same time. |
| **Manual charging is running** | Also every 8 seconds, even if the dashboard is closed. This way the script detects when the battery is full. |
| **Nobody is watching** | Only the watchdog queries the monitored batteries every 120 seconds. The grid meter is not queried. |

Queries, write operations and messages always run **one after another**, never simultaneously. This keeps memory usage on the Shelly low.

---

## Installation

### Recommended: with the Configurator

The [Configurator](../Multiconfigurator/readme_EN.md) asks for everything, takes over the device list, grid source and notifications from the Controller configuration and uploads the script directly to your Dashboard Shelly using the helper (script name `zd`). Updates also work this way.

### Manually via the Shelly web interface

1. Download the **minified** version [`zendash_watch_mini.js`](zendash_watch_mini.js). Only this one fits into the Shelly – `zendash_watch_src.js` is the readable source version.
2. Adjust the `let CONFIG = { ... };` block (see [Configuration](#configuration)).
3. Open the web interface of the Dashboard Shelly (`http://<Shelly-IP>`) → **Scripts**. Stop and delete other scripts on this Shelly.
4. Create a new script ("Create script", "Add script" on older firmware), give it a name (e.g. `zd`), paste the code, **Save**, then **Start**.
5. Enable **"Run on startup"** so that the script restarts by itself after a power failure.

### For advanced users: with `deploy.cmd`

The [Deploy](Deploy) folder contains tools that insert your own configuration, minify the script and upload it:

1. Put your configuration into a separate file, for example `myconfig_zenDash_watch.js`. It only contains the `let CONFIG = { ... };` block.
2. Enter in `deploy.cmd`: the Shelly's IP, the script name, `QUELLE=..\zendash_watch_src.js` and `MEINE_CONFIG=myconfig_zenDash_watch.js`.
3. Run `deploy.cmd`.

> **Important:** `deploy.cmd` always takes the CONFIG block from **your** file. Changes you make directly in `zendash_watch_src.js` will be overwritten.

### After starting

An overview appears in the script log (the script output is in German). Check there whether everything is set up the way you want:

```
--------------------------------
zenDash-API + Watchdog v3.4.1 (Dashboard muss ebenfalls v3.4.1 sein)
Module     : API AN | Watchdog AN
Geraete    : SF2400[W] SF800[W]
Watchdog   : alle 120 s, Offline-Alarm nach 10 min
Nachrichten: SIGNAL -> callmebot | Debug: AUS
--------------------------------
```

`[W]` after a device means: the watchdog monitors it. The version number is that of your script; the dashboard must have the same version.

If messages are enabled, you will also receive the message **"✅ zenDash/Watchdog v… gestartet"** (started). This tells you immediately that the notification path works.

---

## Configuration

All settings are at the top of the script in the `let CONFIG = { ... }` block. If you use the Configurator, you don't need to change anything here by hand.

### Devices (`devices`)

Enter **the same batteries as in the Controller** – same IP addresses, **same order**. The order matters: the first device is "device 0" in the Controller, the second "device 1" and so on.

```js
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
    watch: true          // true = watchdog monitors this device
  },
  // ... more devices
],
```

| Setting | Meaning |
|---|---|
| `ip` | IP address of the battery |
| `label` | Name for display and messages. Only the first 6 characters appear in the morning/evening update. |
| `minSoc`, `maxSoc`, `maxInputPower`, `maxOutput`, `dischargeAllowed`, `reverse` | Values as in the Controller. The dashboard uses them as start values and limits for the sliders. |
| `inputLimit` | Charging power from the grid at startup, normally `0`. Does not exist in the Controller CONFIG – there the value only comes via the KVS. |
| `watch` | `true`: the watchdog monitors this device. `false`: it only appears in the dashboard. If the entry is missing, `true` applies. |

If you copy the device block from the Controller, `dryRun` may remain – the entry is ignored here.

### Dashboard part (`api`)

```js
api: {
  enabled: true,
  kvsHost: "192.168.178.117",
  hysteresis: 12,
  dischargeStartupPower: 35,
  gridSource: "remote",
  gridSourceIp: "192.168.178.117",
  gridSourceEmId: 0,
  gridSourceUrl: "http://<IP-of-your-meter>/properties/report",
  gridSourceField: "total_power",
  gridSourceInvert: false,
  pollIntervalSec: 8
},
```

| Setting | Meaning |
|---|---|
| `enabled` | `true`: dashboard interface on. `false`: watchdog only. |
| `kvsHost` | **IP of the Controller Shelly** – that's where the Controller's settings are stored. |
| `hysteresis` | For display in the dashboard only. Must have **the same value** as in the Controller. |
| `dischargeStartupPower` | Smallest allowed value for fixed discharge (except 0). Must have **the same value** as in the Controller. |
| `gridSource` | Where does the grid measurement come from? `"remote"`: a Shelly Pro 3EM on the network (usually the Controller Shelly), `"http_json"`: another meter with a JSON interface, `"local"`: only if this Shelly itself is a Pro 3EM. |
| `gridSourceIp`, `gridSourceEmId` | for `"remote"`: IP of the meter and channel (usually 0) |
| `gridSourceUrl`, `gridSourceField`, `gridSourceInvert` | for `"http_json"`: address, field name of the total power, invert sign yes/no |
| `pollIntervalSec` | Query interval while the dashboard is open, in seconds. Default 8. |

To be able to **change settings** in the dashboard as well, `kvsEnabled: true` and `kvsForceReseed: false` must be set in the Controller. Without KVS, the dashboard only displays values.

### Watchdog (`watchdog`)

```js
watchdog: {
  enabled: true,
  intervalSec: 120,
  vollSchwelle: 99,
  entladeReset: 90,
  minVoltWarn: 2.9,
  minVoltReset: 3.1,
  tempWarn: 45.0,
  tempReset: 30.0,
  offlineAlarmMin: 10,
  sunriseOffset: 0,
  sunsetOffset: 0
},
```

| Setting | Meaning |
|---|---|
| `enabled` | Watchdog on or off |
| `intervalSec` | How often the watchdog checks when the dashboard is not open, in seconds (at least 60) |
| `vollSchwelle` / `entladeReset` | "Full" message from this state of charge. The next message only comes after the battery has dropped below `entladeReset` in between. |
| `minVoltWarn` / `minVoltReset` | Warning when a cell drops below this voltage (volts). Another warning only after it has been above `minVoltReset` again in between. |
| `tempWarn` / `tempReset` | Warning when the device temperature exceeds `tempWarn` (°C). Another warning only after it has been below `tempReset` in between. |
| `offlineAlarmMin` | Message when a battery has been unreachable for this many **minutes** |
| `sunriseOffset` / `sunsetOffset` | Shift of the morning and evening update relative to sunrise and sunset in minutes, e.g. `30` = half an hour later |

> For the sunrise and sunset times to be correct, the **location** must be set in the Shelly (Settings → Location or time zone).

### Messages (`notify`)

```js
notify: {
  enabled: true,
  typ: "SIGNAL",
  phone: "+4917XXXXXXXX",
  apiKey: "DEIN_CALLMEBOT_KEY",
  webhookUrl: "http://192.168.178.50:8123/api/webhook/DEINE_ID",
  maxMessageLength: 900,
  apiEvents: true
},
```

| Setting | Meaning |
|---|---|
| `enabled` | Messages on or off. Even if they are off, all messages appear in the script log. |
| `typ` | `"SIGNAL"`, `"WHATSAPP"` or `"WEBHOOK"` |
| `phone`, `apiKey` | only for Signal and WhatsApp: your number with country code and the CallMeBot key |
| `webhookUrl` | only for webhook: complete address |
| `maxMessageLength` | Longer messages are truncated |
| `apiEvents` | `true`: also send messages about the auto-stop during manual charging |

In the Controller this block is called `signal`, here `notify`. `enabled`, `typ`, `phone`, `apiKey` and `webhookUrl` mean the same in both; `maxMessageLength` and `apiEvents` only exist here. If an old configuration still contains a `signal` block, the script uses it when there is no `notify`.

**Webhook format:** The script sends a POST request with the content `{"message": "…"}`. In Home Assistant, the text is then available in an automation with a webhook trigger under `{{ trigger.json.message }}`.

### General

| Setting | Meaning |
|---|---|
| `httpTimeout` | Maximum number of seconds the script waits for a response. Default 5. |
| `debug` | `false`: normal output. `true`: detailed log for troubleshooting (see [Troubleshooting](#troubleshooting)). |

---

## Dashboard

The dashboard is a web page that gets its data from this script. You open it via a small proxy on a PC, NAS (e.g. Synology), Home Assistant or Raspberry Pi – for Windows and Mac it is also available as a ready-made program.

👉 **[Set up and use the dashboard](dashboard.md)** (German)

The interface for your own integrations (e.g. Home Assistant, Node-RED) is documented in the [API description](API.md) (German).

### History in ThingSpeak

The proxy can additionally send the readings of your batteries to ThingSpeak every minute. There you get a permanent history with charts. The upload is optional and only needs one additional file next to the proxy. As long as a dashboard is open, the proxy only reads along with its queries. If the upload is switched off, it does not send a single request to the script.

👉 **[Set up the ThingSpeak upload](thingspeak.md)** (German)

---

## Messages

The script can send the following messages. The message texts are in German; the meaning is given in the right-hand column.

| Message | When |
|---|---|
| ✅ zenDash/Watchdog v… gestartet (2/2 ueberwacht) | after each start of the script (started, 2 of 2 monitored) |
| 🔋 SF2400 voll (99%) | state of charge has reached `vollSchwelle` (full) |
| 🔥 SF800 Temp hoch: 46.2C | device temperature above `tempWarn` (temperature high) |
| ⚠️ SF800 Zelle BO1234… nur 2.85V | a cell below `minVoltWarn`, with the serial number of the battery pack |
| ❌ SF800: nicht erreichbar seit 10 min | battery no longer responds (unreachable for 10 min) |
| ❌ SF800: Report unlesbar seit 10 min | battery responds, but with incomplete or unusable data (report unreadable) |
| ✅ SF800: wieder erreichbar | after one of the two previous messages (reachable again) |
| ⚠️ SF800 seit 20 Tagen nicht voll | checked once a day with the morning update (not full for 20 days), see [Last full charge](#last-full-charge) |
| 🌅 Morgen-Update / 🌇 Abend-Update | at sunrise and sunset: state of charge, temperature and lowest cell voltage per device |
| ✅ SF2400: manuelles Laden beendet (voll) … | auto-stop worked (with `apiEvents: true`) |
| ⚠️ SF2400: Auto-Stop fehlgeschlagen … | auto-stop could not reset the settings. Please check in the dashboard. |

Each warning comes **once**, not with every query. Only when the value has returned to normal can it come again.

In the morning and evening update, `n/a` appears if no current values are available for a device, for example because it is currently unreachable.

> **Tip:** The morning and evening update is also a sign of life. If it fails to arrive, the script has probably stopped running.

---

## Manual charging and auto-stop

In the dashboard you can have a battery charged manually from the grid. For this, the script switches off discharging and grid charging for this device in the Controller and sets a fixed charging power.

**Auto-stop:** As soon as the battery reports that it is full, the script ends manual charging by itself and restores the previous state. This also works when the dashboard is closed.

Good to know:
- The script only keeps the previous state in RAM. If the Shelly restarts during manual charging, discharging and grid charging are switched **on** again when it ends.
- You can end manual charging yourself in the dashboard at any time.

---

## Last full charge

Lithium batteries should be fully charged now and then so that the battery estimates its state of charge correctly. The script therefore remembers, per battery, when it last reached **a real 100 %**:

- The date is saved in the Controller Shelly at most once a day (KVS entry `zdmc_dev{number}_lastFull`) and therefore survives a restart.
- The **dashboard** shows "100 %: N days ago" per battery – green under 7 days, yellow up to 20 days, red above. Tapping shows the date.
- The **watchdog** reports once if a monitored battery has not been full for 20 days.

---

## Switching from the old scripts

If you have been using the separate scripts zenDash API 2.x and AkkuVolt Watchdog 1.x so far:

1. Do the switch with the Configurator – the steps are described there under [Switching from the old separate scripts](../Multiconfigurator/readme_EN.md#switching-from-the-old-separate-scripts). Old configurations of these scripts cannot be imported directly; however, the Controller configuration provides most of it.
2. **Stop the old scripts and switch off "Run on startup"** (or delete them) – otherwise they keep running and messages arrive twice.
3. If you use the dashboard: if the new script has a different script number, enter it in the proxy under `/setup`.

---

## Memory usage

A Shelly script has about **25 kB** of RAM. Measured on a real device with two batteries (version 3.1):

| | used at rest | peak value |
|---|---|---|
| Dashboard closed | approx. 13.5 kB | approx. 17.8 kB |
| Dashboard open | approx. 13.5 kB | approx. 17.7–18.0 kB |

Since version 3.4 the base load is about 0.9 kB lower. So even at the worst moment, a good **7 kB** remain free. For comparison: the two old scripts together already needed almost 25 kB at peak.

You can measure it yourself with "🔍 Speicher prüfen" (check memory) in the [Configurator](../Multiconfigurator/readme_EN.md#checking-a-shellys-memory).

---

## Troubleshooting

### Enabling debug output

Set `debug: true` and restart the script – or tick "Debug-Ausgaben" (debug output) in the Configurator when updating. The log then additionally shows:

- every call of the dashboard interface with the values passed
- every write operation to the Controller's settings with result
- start and end of manual charging
- switching between fast polling (dashboard open) and idle
- sending of every message
- memory usage at the most important points
- in each watchdog round, one line per battery with all battery packs, for example:
  ```
  [DEBUG] SF800: SoC 91%, 26.0C | Packs: CO1234…:91%/3.31V, BO5678…:91%/3.31V
  ```

Switch `debug` off again afterwards. Otherwise the log becomes very long. For recording, "Log aufzeichnen" (record log) in the [Configurator](../Multiconfigurator/readme_EN.md#recording-a-log) is useful.

### Common problems

**The log shows a different type under "Nachrichten" (messages) than I set.**
The script only applies changes after a **restart** (Stop → Start). If you use `deploy.cmd`: the setting must be in **your** config file, not in the script itself. Also check that `notify:` appears only **once** in the CONFIG block.

**I don't get any messages at all.**
Look at the "Nachrichten" line in the banner:
- `aus` (off) means: `notify.enabled` is `false`, or `typ` is unknown. In the second case, a WARNUNG (warning) appears directly above it.
- For Signal/WhatsApp: are the phone number (with `+49…`) and API key correct?
- For webhook: is the address reachable from the Shelly?

With `debug: true` you can see in the log whether and how each message was sent.

**I get every message twice.**
The old watchdog is still running. Stop it and switch off "Run on startup" for it.

**The dashboard shows a connection error.**
- Is the script running? (web interface → Scripts)
- Are the IP **and** script number of the Dashboard Shelly correct in the proxy under `/setup`? See [Dashboard – Wenn es nicht klappt](dashboard.md#wenn-es-nicht-klappt) (German, "if it doesn't work").
- Is `api.enabled` set to `true`?

**The dashboard only shows default values, changes are not applied.**
The script cannot reach the Controller's settings. Check `api.kvsHost` (IP of the Controller Shelly), whether `kvsEnabled: true` is set in the Controller and whether password protection is active on the Controller Shelly. With `debug: true`, the log shows `KVS NICHT lesbar` (KVS not readable) or `KVS.Set … -> FEHLER` (error).

**Message "Report unlesbar" (report unreadable).**
The battery responded, but the data was incomplete or had an unexpected format. This happens occasionally and usually disappears by itself. If it persists, the battery's data format may have changed after a firmware update. In that case, please open an [issue](https://github.com/surfer1264/Zendure-Stuff/issues) with the response from `http://<battery-IP>/properties/report`. Remove the serial numbers first.

**The morning and evening update comes at the wrong time or not at all.**
Check location and time zone in the Shelly settings. The script creates two schedules at startup. Other schedules on the Shelly remain untouched.
