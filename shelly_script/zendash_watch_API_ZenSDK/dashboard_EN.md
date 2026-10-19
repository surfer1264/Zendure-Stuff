[:de: Deutsch](dashboard.md) · :gb: **English** · [:fr: Français](dashboard_FR.md)

# Setting up and using the dashboard

[← back to zenDash API + Watchdog](readme_EN.md)

The dashboard shows you live grid draw, state of charge and power of your batteries. You can also use it to change Controller settings and to charge a battery manually from the grid.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/ef6db2a0-6913-443e-af8f-65e0b327064c" />

**Contents**

- [Setting up and using the dashboard](#setting-up-and-using-the-dashboard)
    - [How it fits together](#how-it-fits-together)
    - [Operation](#operation)
        - [Page layout](#page-layout)
        - [Locking and unlocking](#locking-and-unlocking)
        - ["View" menu](#view-menu)
        - [What you can set](#what-you-can-set)
        - [What the display shows](#what-the-display-shows)
    - [Which option suits you?](#which-option-suits-you)
    - [Requirements](#requirements)
    - [Dashboard in 4 steps](#dashboard-in-4-steps)
    - [As a program on Windows or macOS](#as-a-program-on-windows-or-macos)
    - [Continuous operation on a Synology](#continuous-operation-on-a-synology)
    - [As an app in Home Assistant](#as-an-app-in-home-assistant)
    - [Start options](#start-options)
    - [Good to know](#good-to-know)
    - [If it does not work](#if-it-does-not-work)

> The proxy's console output and its setup page are in German. The dashboard page itself can be switched to English (button DE/EN/FR at the top right).

---

## How it fits together

The browser is not allowed to query the data directly from the Shelly – the Shelly firmware rejects such requests coming from a foreign web page. That is why a small **proxy** runs on a computer in your home network: it serves the dashboard page and queries the Shelly on its behalf.

```text
Browser  ──►  Proxy (PC/NAS/HA/Raspi)  ──►  Dashboard Shelly (zenDash API)  ──►  Controller Shelly (KVS)
```

---

## Operation

This describes the default layout at `http://<proxy-address>:8000/`. The previous layout at `/b` has the same functions, just arranged differently.

### Page layout

| Area | Content |
|---|---|
| **Header** | connection status (e.g. "Live · polling every 4s"), time and date, the **padlock** and the **⚙ View** menu |
| **Overview – Now** | readings: grid import/export and Solarflow power (sum of all batteries) with history curve |
| **Overview – Control** | settings for all batteries: setpoint and fixed discharge |
| **Devices** | one card per battery with readings, status, "Controls" and "Manual charging" |
| **Footer** | versions, time of the last update, **Help** link (this page), raw data and cloud upload |

Tapping the **"▾ Overview"** line collapses the overview. When collapsed, a short summary is shown there, e.g. `Target 0 W · Grid 12 W · Storage 340 W` – handy on small screens when only the device cards matter. The state is remembered.

### Locking and unlocking

The page starts **locked** – it then only displays, with the note "View only" below the control section. Tapping the **padlock** in the header enables the controls, and the icon changes to an open padlock. After 60 seconds without input the page locks itself again, and also after every reload. This is meant for dashboards that stay open permanently on a tablet or second monitor.

On touch devices the **Reserve (min. SoC)** slider additionally has its own small padlock next to the value. It only ever releases this one slider and locks it again after 5 seconds without touch, after saving or when scrolling. The value only changes by dragging the knob – tapping or swiping on the bar is reverted.

### "View" menu

| Entry | Effect |
|---|---|
| **View size** (A1–A4) | text and controls in four levels: Normal, Large (default), Extra large, Maximum |
| **Day/night view** | light or dark display. Without switching, the page follows the device setting. |
| **Language** | DE → EN → FR. Default is the browser language. |
| **Full screen** | hides the browser bars; only shown if the browser supports it |
| **Technical details** | shows KVS keys (e.g. `zdmc_setpoint`), IP addresses and raw codes (`acMode`, `socLimit`, `gridReverse`). Without this switch the dashboard shows plain language only. |
| **Reset view** ↺ | size, day/night, technical details and overview back to default. The language is kept. |

All entries are remembered **per browser** – so a wall tablet comes back in its own view after a reload. The lock is deliberately not remembered.

### What you can set

All settings go to the Controller and take effect on its next control cycle. After saving, a short confirmation appears, e.g. "Saved: Battery 1 · Reserve (min. SoC) 20 %".

**In the overview under "Control"** (for all batteries together):

| Control | Effect | Range |
|---|---|---|
| **Setpoint** | Target value for the grid draw. Negative = feed in a little, positive = draw a little. Below it is the tolerance (hysteresis): the grid draw may deviate this far before the Controller readjusts. | −40 to +40 W, in 5 W steps |
| **Fixed discharge** | Fixed discharge power instead of control. Type the value into the field and confirm with ↵ or "Done". While it is active, the setpoint tile notes that the setpoint is currently not being regulated. | `0` = off, otherwise from `dischargeStartupPower` (e.g. 35 W) |

**On each device card under "Controls":**

| Control | Effect | Range |
|---|---|---|
| **Discharge allowed** | May this battery supply the house? If the watchdog has locked discharging because of undervoltage, the switch is off and has to be switched on again by hand ([discharge lock](readme_EN.md#discharge-lock-on-undervoltage)). | on/off |
| **Charging from grid allowed** | May this battery absorb surplus from the grid? | on/off |
| **Reserve (min. SoC)** | Below this state of charge there is no discharging. Is additionally set in the battery itself. The upper limit is shown below the value ("max … %"). | 10 % up to 1 % below the lower of charge target (`maxSoc`) and the charge limit set on the device (`socSet`) |

**On each device card under "Manual charging":**

| Control | Effect | Range |
|---|---|---|
| **Grid charging power** | only selects the power, no effect yet | 0 to `maxInputPower`, in 50 W steps |
| **Start / stop manual charging** | starts or stops charging with the selected power | – |

On start, the dashboard asks for confirmation once and then switches "Discharge allowed" and "Charging from grid allowed" off for this battery – the battery is thus taken out of control, and the note next to the button shows "Active at … W". On stop it restores the previous state. When the battery is full, the script ends charging by itself, even with the dashboard closed ([auto-stop](readme_EN.md#manual-charging-and-auto-stop)). If the process is interrupted halfway (Shelly not reachable), a warning appears – then check the switches and charging power on the card.

After an input, the respective control is locked for 4 seconds so that nothing is triggered twice.

Not changeable in the dashboard are the **hysteresis** (only shown below the setpoint) and the **charge target** (`maxSoc`). You set both in the Configurator or in the CONFIG block.

### What the display shows

- **Grid import / export:** current grid balance with direction ("import" or "export") and comparison with the setpoint, plus a history curve of the last 2 minutes.
- **Solarflow power:** sum of all batteries (+ = supplying, − = charging), below it the average state of charge ("Avg. charge … %"), also with a history curve. The two curves have different scales and start from scratch after reloading the page.
- **One card per battery** with:
    - name and status dot (green = reachable); with "Technical details" also `[devN]` and IP address
    - state of charge as battery icon and number, next to it the power with direction ("supplying", "charging", "standby")
    - below it the operating window, e.g. `Range 15–100 %` (reserve to charge target)
    - PV input, off-grid power (only on devices with an off-grid socket), device temperature in °C and weakest cell ("Cell min 3.28 V") – which is only meaningful under load. For batteries monitored by the watchdog, the lock threshold follows, e.g. "lock < 2.90 V", and the colour follows the watchdog thresholds: yellow below `minVoltReset`, red below `minVoltWarn`. Otherwise: yellow below 3.0 V, red below 2.8 V.
    - "100 %: N days ago" – when the battery was last completely full; tapping shows the date ([more on this](readme_EN.md#last-full-charge))
    - status in plain language, e.g. "feeding in", "full, charging blocked", "empty, discharge blocked", "export blocked". This explains the most common "Why is the battery doing nothing?" cases. With "Technical details" the raw code is shown in front (`socLimit 1`, `gridReverse 2` …).
    - notes when something different is set on the device than in the configuration, e.g. "Charge limit 90 % · differs, configuration 100 %" (`socSet` ≠ `maxSoc`) or "Reserve on device 15 % · differs, KVS 20 %". Usually the value was changed externally (app, Home Assistant).
    - below that "Discharge: allowed · Grid charging: blocked" as a summary of the two switches
- **Footer:** versions of page and script (yellow if they do not match), time of the last update, **Help** link to this guide. `config_api` and `status_api` open the raw data as JSON in a new tab. **ThingSpeak** and **ThingsBoard** lead to the setup pages for the cloud upload ([ThingSpeak](thingspeak.md), [ThingsBoard](thingsboard.md), German).

**Explanations on tap:** Many labels and values have a dotted underline – setpoint, fixed discharge, the two overview tiles, power, operating window, extra line, lock threshold; the status tags too. Tapping (or hovering with the mouse) shows a short explanation.

The page refreshes the measurements every 4 seconds. Settings changed by someone else (e.g. via Home Assistant) appear after about half a minute at the latest. While the tab is in the background or the window is minimised, polling pauses.

Technical details on polling rate, interface and value ranges are in the [API description](API.md) (German).

---

## Which option suits you?

There is **one** proxy (`zendure_proxy.py`) that works the same everywhere. Only the way you start it differs:

| Option | Suitable for | Start | Browser opens by itself |
|---|---|---|---|
| **Ready-made program** | Windows or Mac with Apple Silicon, without Python | double-click | yes |
| **Python script** | PC, laptop, Raspberry Pi | `python3 zendure_proxy.py` | yes (only with a screen) |
| **Synology** | continuous operation on the NAS | Task Scheduler | no |
| **Home Assistant** | anyone already running Home Assistant OS | as its own app | no |

Setup is the same in all cases: start the proxy, open it in the browser, enter the IP and script number of the Dashboard Shelly on the setup page. You do not need a text editor for this.

Any computer will do for occasional viewing. If the dashboard should **always** be reachable, use something that runs permanently: NAS, Home Assistant, Raspberry Pi or mini PC. A laptop that gets closed is not a good fit.

---

## Requirements

- The script [zenDash API + Watchdog](readme_EN.md) runs on your Dashboard Shelly with **`api.enabled: true`**.
- To also **change settings** in the dashboard (setpoint, reserve, manual charging …), `kvsEnabled: true` and `kvsForceReseed: false` must be set in the Controller. Without KVS the dashboard only displays.
- For the Python script and the Synology: **Python 3.7 or newer** ([python.org](https://www.python.org/downloads/)). Nothing else needs to be installed.
- Except for the ready-made program, the two files from [this folder](.):
    - [`zendure_proxy.py`](zendure_proxy.py) – the proxy
    - [`zendure-dashboard.html`](zendure-dashboard.html) – the dashboard page

  The HTML file may be **in the same folder** as the proxy or **one level up**. If there is one in both places, the one in the same folder wins.

> **Important:** The dashboard page and the script on the Shelly must have **the same version number**. When you update the script, also get the matching `zendure-dashboard.html` (or the new program). If the versions drift apart, the note in the dashboard footer turns yellow.

---

## Dashboard in 4 steps

**1. Look up the script number**

The proxy needs to know the IP address of the Dashboard Shelly and which number the script has there. You find the number in the web interface of the Dashboard Shelly under **Scripts** (e.g. `id: 1`). When uploaded via the Configurator, the script is called `zd`.

**2. Quickly test whether the script answers**

Open directly in the browser (insert IP and number):

```link
http://<IP-of-Dashboard-Shelly>/script/<script-number>/status_api
```

A line of data should appear. If you get an error, the script is not running or the number is wrong.

**3. Start the proxy**

Ready-made program: double-click (see [below](#as-a-program-on-windows-or-macos)). Python script: open a terminal (Windows: Command Prompt) in the folder with the files and start:

```bash
python3 zendure_proxy.py
```

On Windows the command is often `python` or `py` instead of `python3`. The window must stay open as long as the dashboard is used; quit with `Ctrl+C`.

On start the proxy shows a short overview (in German):

```text
Zendure Dashboard Proxy
  Shelly:   noch nicht eingerichtet - Einrichtungsseite oeffnet automatisch
  HTML:     /home/pi/zendure/zendure-dashboard.html
  Konfig:   /home/pi/zendure/zendure_proxy_config.json
  Lokal:    http://localhost:8000/
  Im Netz:  http://192.168.178.21:8000/  (von jedem Rechner im selben Netzwerk)
(Strg+C zum Beenden)
```

- **Shelly** – "noch nicht eingerichtet" means not set up yet; the setup page opens automatically.
- **HTML** shows which dashboard file was found.
- **Konfig** shows where the settings are stored.
- **Im Netz** ("on the network") is the address for phone, tablet and other computers.

On a computer with a screen the browser opens automatically.

**4. Set up**

The first time you open `http://localhost:8000/`, the **setup page** appears instead of the dashboard. Enter there:

- **Shelly-IP** – the IP of the **Dashboard Shelly** (not the Controller Shelly!)
- **Script-ID** – the number from step 1

A click on **"Speichern & testen"** (save & test) immediately checks whether the script really answers at this address. If there is a typo, an error message appears and nothing is saved. If the test succeeds, the page forwards you directly to the dashboard.

The settings are stored in the file `zendure_proxy_config.json` next to the proxy. On the next start they are back – so setup is only needed once. You can change them at any time under:

```link
http://<proxy-address>:8000/setup
```

After that the dashboard is also reachable from any other device in your home network – with the address from the **"Im Netz"** line, e.g. `http://192.168.178.21:8000/`.

- always `http://`, not `https://`
- the page starts **locked** – the padlock at the top right enables the controls
- if Windows asks about the firewall on first start: **"Allow access"** (private network)

---

## As a program on Windows or macOS

For computers without Python the proxy is available as a ready-made program. The dashboard page is already built in – you only need this one file:

- [Windows](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_proxy-windows.exe)
- [macOS](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_proxy-macos) – only Macs with Apple Silicon (M1 or newer)

1. Put the file into its **own folder** where you have write access, e.g. `C:\Users\<name>\zendure\`. Not under `C:\Program Files` – the proxy cannot save its settings there.
2. Start with a **double-click**. A console window opens (leave it open), plus the browser with the setup page.
3. If Windows SmartScreen warns about an unknown app: **"More info" → "Run anyway"**. On macOS the same steps apply as for the helper – see the [macOS guide](../Multiconfigurator/local_helper/mcos_helper.md) (German; use the file name `zendure_proxy-macos` there).
4. If the Windows firewall asks: **"Allow access"** (private network), otherwise the dashboard cannot be reached from your phone.
5. Set up as described in [step 4](#dashboard-in-4-steps). The file `zendure_proxy_config.json` is created next to the program.

Quit: close the console window or press `Ctrl+C`.

For each file there is a `.sha256` file on the [releases page](https://github.com/surfer1264/Zendure-Stuff/releases/latest) for verification – as described for the helper under [Verifying the download](../Multiconfigurator/readme_EN.md#verifying-the-download).

---

## Continuous operation on a Synology

1. **Check Python.** DSM usually ships one already:

    ```bash
    which python3 && python3 --version
    ```

    3.7 or newer is enough – the proxy only uses the standard library. The interpreter is often at `/bin/python3`. If nothing shows up, install **Python 3** in the Package Center; the path is then `/var/packages/Python3*/target/bin/python3`.

2. **Place the files.** Put `zendure_proxy.py` into its own folder, e.g. `/volume1/homes/<user>/zendure`, and `zendure-dashboard.html` next to it or one level up. Not into the `web` folder – that belongs to Web Station.
3. **Create a task.** Control Panel → Task Scheduler → Create → **Triggered Task** → User-defined script. Event **Boot-up**, user **root**, and as command the full path:

    ```bash
    /bin/python3 /volume1/homes/<user>/zendure/zendure_proxy.py -q
    ```

4. **Start right away**, without rebooting: select the task → **Run**.
5. **Firewall.** If it is active under Control Panel → Security → Firewall, create a rule for TCP **8000**. Port 8000 does not collide with DSM itself (5000/5001).
6. **Set up.** From a PC or phone open `http://<IP-of-Synology>:8000/` and enter IP and script number as in [step 4](#dashboard-in-4-steps).

The task permanently shows as "running" because the proxy does not end. That is how it should be.

Because the task runs as `root`, the resulting `zendure_proxy_config.json` is also owned by `root`. That does not matter for operation; only if you want to delete or edit the file by hand later do you need administrator rights.

The Task Scheduler starts the task at boot, but does **not restart it if the process crashes**. If you want that, use a container in Container Manager instead of the task (`python:3-slim`, folder as volume, port 8000, restart policy "always"). The settings are then stored in the mounted folder and survive even re-creating the container.

---

## As an app in Home Assistant

If you run Home Assistant OS, you can run the proxy there as its own app. It then starts together with Home Assistant and is restarted automatically after a crash.

👉 **[Guide for the Home Assistant app](HA_zendure_proxy/readme.md)** (German)

In short: install the app from the local folder, start it, open `http://<IP-of-Home-Assistant>:8000/` and set up as in [step 4](#dashboard-in-4-steps).

> **Note:** In Home Assistant the settings are stored inside the app's container. If the app is uninstalled and reinstalled (e.g. for a new dashboard version), setup has to be done once more.

---

## Start options

Applies to the Python script (and to the program if you start it from a console):

| Option | Effect |
|---|---|
| *(none)* | normal, with one log line per request |
| `-q` | quiet: start overview yes, log no – handy for continuous operation |
| `-s` | silent: no output at all (errors still appear) |
| `--browser` | always open the browser on start |
| `--no-browser` | never open the browser on start |
| `-h` | show help |

Without `--browser`/`--no-browser` the proxy decides by itself: on Windows, macOS and a Linux desktop it opens the browser; on a Synology, in Home Assistant or in an SSH session it does not.

Port (`PORT`, default 8000) and network interface (`BIND_ADDRESS`) can be changed at the top of the Python script if needed.

---

## Good to know

- **No password protection:** Anyone in your home network who knows the address can open the dashboard and change settings – including the Shelly address under `/setup`. So **never** expose the proxy to the internet via port forwarding.
- **Script number:** When **updating** via the Configurator, the number stays the same. If the script is **created anew** (first installation, "delete others", Shelly replacement or manual upload), it gets a new number. If the dashboard stops working after that, enter the new number under `http://<proxy-address>:8000/setup`. Restarting the proxy is not necessary.
- **New layout, previous one at `/b`:** At `http://<proxy-address>:8000/` the dashboard now uses the new layout – more clearly structured, clearly marked lock button, status in plain language, collapsible overview, technical details (KVS keys, IP addresses) only on request via the “View” menu. Settings chosen there are remembered – see [Operation](#operation). The previous layout with the same functions is still available at `http://<proxy-address>:8000/b`. This needs `zendure-dashboard-b.html` next to `zendure-dashboard.html`; the ready-made program and the Home Assistant app include it.
- **New dashboard version:** With the Python script and on the Synology, simply replace `zendure-dashboard.html` and reload the page in the browser – the proxy reads the file fresh on every request. In the ready-made program the page is built in; it comes with a new download. In Home Assistant the app has to be rebuilt.

---

## If it does not work

| Symptom | Solution |
|---|---|
| Page empty, "Failed to fetch" | The HTML file was opened by double-click. Always open it via `http://localhost:8000/`. |
| The setup page appears instead of the dashboard | The proxy is not set up yet, or `zendure_proxy_config.json` is missing or damaged. Simply set it up again. |
| "Speichern & testen" reports an error | IP or script number is wrong – check with the test from [step 2](#dashboard-in-4-steps). The IP must be that of the **Dashboard Shelly**. |
| Red note "Error loading configuration" | The Shelly is not reachable (any more) or the script number has changed – check under `/setup`. |
| Version note in the footer is yellow | Dashboard page and script have different versions. Get the matching `zendure-dashboard.html` or the new program. |
| 404 at `http://localhost:8000/` | `zendure-dashboard.html` is neither next to the proxy nor one level up. On start the proxy lists all places where it looked. |
| Setup cannot be saved | The proxy is not allowed to write in its folder (e.g. under `C:\Program Files`). Choose a folder with write access. |
| Settings have no effect | Set `kvsEnabled: true` in the Controller. |
| Settings gone after restarting the Controller | Set `kvsForceReseed: false` in the Controller. |
| Not reachable from the phone | `http://` instead of `https://`, correct IP from the "Im Netz" line, check the firewall rule. |
| Nothing can be operated | The page is locked – tap the padlock in the header. |
| KVS keys, IP addresses or `acMode`/`socLimit` are missing | Switch on **Technical details** in the “View” menu. |
| "Konnte Port 8000 nicht oeffnen" (could not open port 8000) | The proxy is already running (e.g. in a second window), or another program is using the port. |
