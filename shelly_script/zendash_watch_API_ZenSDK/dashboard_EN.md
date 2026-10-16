[:de: Deutsch](dashboard.md) · :gb: **English** · [:fr: Français](dashboard_FR.md)

# Setting up and using the dashboard

[← back to zenDash API + Watchdog](readme_EN.md)

The dashboard shows you live grid draw, state of charge and power of your batteries. You can also use it to change Controller settings and to charge a battery manually from the grid.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/ca41b303-7e07-4182-9bc3-f003360f0fd6" />


**Contents**

- [How it fits together](#how-it-fits-together)
- [Which option suits you?](#which-option-suits-you)
- [Requirements](#requirements)
- [Dashboard in 4 steps](#dashboard-in-4-steps)
- [As a program on Windows or macOS](#as-a-program-on-windows-or-macos)
- [Continuous operation on a Synology](#continuous-operation-on-a-synology)
- [As an app in Home Assistant](#as-an-app-in-home-assistant)
- [Start options](#start-options)
- [Good to know](#good-to-know)
- [If it does not work](#if-it-does-not-work)
- [Operation](#operation)

> The proxy's console output and its setup page are in German. The dashboard page itself can be switched to English (button DE/EN/FR at the top right).

---

## How it fits together

The browser is not allowed to query the data directly from the Shelly – the Shelly firmware rejects such requests coming from a foreign web page. That is why a small **proxy** runs on a computer in your home network: it serves the dashboard page and queries the Shelly on its behalf.

```
Browser  ──►  Proxy (PC/NAS/HA/Raspi)  ──►  Dashboard Shelly (zenDash API)  ──►  Controller Shelly (KVS)
```

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

```
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

```
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

```
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
- **New layout, previous one at `/b`:** At `http://<proxy-address>:8000/` the dashboard now uses the new layout – more clearly structured, lock button with text and remaining time, status in plain language, technical details (KVS keys, IP addresses) only on request via the “View” menu. View size and day/night chosen there are remembered. The previous layout with the same functions is still available at `http://<proxy-address>:8000/b`. This needs `zendure-dashboard-b.html` next to `zendure-dashboard.html`; the ready-made program and the Home Assistant app include it.
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
| Nothing can be operated | The page is locked – tap the padlock at the top right. |
| "Konnte Port 8000 nicht oeffnen" (could not open port 8000) | The proxy is already running (e.g. in a second window), or another program is using the port. |

---

## Operation

The page starts **locked**. The padlock at the top right enables the controls; after 60 seconds without input it locks itself again. This is meant for dashboards that stay open permanently on a tablet or second monitor.

### What you can set

All settings go to the Controller and take effect on its next control cycle.

| Control | Effect | Range |
|---|---|---|
| **Setpoint** | Target value for the grid draw. Negative = feed in a little, positive = draw a little. | −40 to +40 W |
| **Fixed discharge** | Fixed discharge power instead of control, for all batteries together. `0` = off, normal control. | 0 or from `dischargeStartupPower` |
| **Discharge allowed** | May this battery supply the house? If the watchdog has locked discharging because of undervoltage, the switch is off and has to be switched on again by hand ([discharge lock](readme_EN.md#discharge-lock-on-undervoltage)). | on/off |
| **Charging from grid allowed** | May this battery absorb surplus from the grid? | on/off |
| **Reserve (min. SoC)** | Below this state of charge there is no discharging. Is additionally set in the battery itself. On touch devices the slider has its own small padlock next to the value and only reacts to dragging the knob, so it is not changed by accident. | 10 % up to 1 % below the lower of charge target (`maxSoc`) and the charge limit set on the device (`socSet`) |
| **Manual charging** | Charges this battery from the grid with the selected power until you stop it or the battery is full. | 0 to `maxInputPower` |

**Manual charging** consists of two parts: the slider only selects the power, the button below starts or stops charging. On start, the dashboard switches "Discharge allowed" and "Charging from grid allowed" off for this battery; on stop it restores the previous state. When the battery is full, the script ends charging by itself ([auto-stop](readme_EN.md#manual-charging-and-auto-stop)). If the process is interrupted halfway (Shelly not reachable), a warning appears – then check the battery's card.

After an input, the respective control is locked for 4 seconds so that nothing is triggered twice.

Not changeable in the dashboard are the **hysteresis** (only shown next to the setpoint) and the **charge target** (`maxSoc`). You set both in the Configurator or in the CONFIG block.

### What the display shows

- **Top:** grid balance and sum of the batteries, each with a small history curve of the last 2 minutes. The two curves have different scales. After reloading the page they start from scratch.
- **Next to the setpoint** is the hysteresis: the grid draw may deviate this far before the Controller readjusts.
- **One card per battery** with:
  - state of charge and below it the operating window, e.g. `SoC · 15–100 %` (reserve to charge target)
  - power, PV input, off-grid power (only on devices with an off-grid socket), device temperature in °C and weakest cell voltage – which is only meaningful under load. For batteries monitored by the watchdog, the lock threshold follows, e.g. "min 3.31 V (lock < 2.90 V)", and the colour follows the watchdog thresholds: yellow below `minVoltReset`, red below `minVoltWarn`. Otherwise: yellow below 3.0 V, red below 2.8 V.
  - notes when something different is set on the device than in the configuration: `socSet` (upper charge limit on the device) differs from `maxSoc`, or `minSoc` on the device differs from the reserve in the KVS. Usually the value was changed externally (app, Home Assistant). Tapping explains the remedy.
  - "100 %: N days ago" – when the battery was last completely full ([more on this](readme_EN.md#last-full-charge))
  - raw status `acMode`, `socLimit`, `gridReverse`. This explains the most common "Why is the battery doing nothing?" cases: `socLimit 1` = battery full, charging blocked; `socLimit 2` = discharging blocked; `gridReverse 2` = feed-in blocked.
- **Footer:** versions of page and script. Yellow if they do not match.

The page refreshes the measurements every 4 seconds. Settings changed by someone else (e.g. via Home Assistant) appear after about half a minute at the latest.

### Buttons at the top right

| Button | Effect |
|---|---|
| 🔒 Padlock | enable / lock the controls |
| DE/EN/FR | switch language (default: browser language) |
| Light/Dark | day or night view. Without switching, the page follows the device setting. |
| A | font size in three levels: Normal, Large (default), Extra large |
| ⛶ | full screen (only if the browser supports it) |

Technical details on polling rate, interface and value ranges are in the [API description](API.md) (German).
