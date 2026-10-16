🌐 [Deutsch](szscs.md) · **English** · [Français](szscs_FR.md)

# Simple Zendure Shelly Cloudless System

**Buy me a coffee!**

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

<img width="1000" alt="image" src="https://github.com/user-attachments/assets/0267db3d-7941-472e-87de-e134ada66dea" />

* You have **one** or **several** SolarFlows (SF800 or newer, zenSDK-capable)?
* You have a Shelly Pro 3EM or another smart meter with a local interface?
* You want local control – without the cloud?
* You want little effort and something that simply works?
* Home Assistant & co. are not (yet) an option for you?

_Principle_: **Install** – **Run** – **Forget**

🎉 HERE YOU ARE 🎉

---

## 👉 How to get started

1. **Download the helper** (see [Downloads](#downloads)) and start it. The configurator opens in your browser.
2. Choose **"Configure from scratch"** and answer the questions about your batteries, your smart meter and notifications.
3. At the end, **"⚡ Upload directly"** – the scripts land fully set up on your two Shellys.

Detailed instructions: **[Configurator](Multiconfigurator/readme_EN.md)**

---

## What you need

* **Two Shellys** (Gen2 or newer). Ideally one of them is a **Shelly Pro 3EM** – it then measures the grid power as well. Alternatively another smart meter with a JSON interface, e.g. Zendure Smart Meter 3CT, a Tasmota reading head or a Shelly 3EM (without Pro).
* The **IP addresses** of your SolarFlows and Shellys – ideally fixed in your router.
* A **Windows PC or Mac** for the helper. Without the helper, any browser will do.
* **Optional for notifications:** a free API key from [CallMeBot](https://www.callmebot.com) for Signal or WhatsApp – or a webhook, e.g. in Home Assistant.

**Important:** Remove your SolarFlows from **HEMS** in the Zendure app, otherwise the cloud sends its own control commands in parallel.

---

## Three functions on two Shellys – without the cloud

| Shelly | Script | Task |
|---|---|---|
| **Controller Shelly** | Controller (`zerooutput_multi_kvs`) | controls charging and discharging of your SolarFlows |
| **Dashboard Shelly** | zenDash API + watchdog (`zendash_watch`) | provides the data for the dashboard and sends notifications – both functions can be switched off individually |

**Exactly one script** runs on each Shelly. Shellys have little script memory – that's why the controller and the dashboard script always run on two separate devices.

### 1. The controller – the control

* controls to a **setpoint** (e.g. 0 W grid draw)
* with **hysteresis** and **damping**, so nothing oscillates
* **charging & discharging**, distributed across all SolarFlows
* settings can be changed during operation (KVS) – from the dashboard or e.g. from Home Assistant

📖 [Getting started](Controller/readme.md) · [User documentation](Controller/benutzerdoku.md) · [All the details](Controller/gesamtdoku.md) (German)

### 2. The dashboard – the overview

* **live display** of grid power, state of charge and power per SolarFlow
* **take action:** setpoint, reserve (minSoc), allow discharging/charging, fixed discharge power
* **manual charging with auto-stop** – once the battery is full, the SolarFlow goes back to control by itself (even with the dashboard closed)
* **"100 %: N days ago"** – shows when each battery was last completely full
* in German, English and French, on PC, tablet or phone

The dashboard is a web page that runs through a small **proxy** – as a ready-made program for Windows and Mac (see [Downloads](#downloads)), as a Python script, on a Synology or as an app in Home Assistant.

📖 [Setting up and using the dashboard](zendash_watch_API_ZenSDK/dashboard_EN.md) (German)

### 3. The watchdog – the notifications

* **morning and evening summary** with state of charge, temperature and cell voltage
* notification when a **battery is full**
* **warning** when a cell voltage is too low or the temperature too high
* notification when a SolarFlow is **unreachable** – and an all-clear as soon as it's back
* notice when a battery **hasn't been full for 20 days**
* delivery via **Signal**, **WhatsApp** or **webhook**; configurable per SolarFlow whether it is monitored

📖 [zenDash API + watchdog](zendash_watch_API_ZenSDK/readme_EN.md) (German)

---

## Setup

### With a Shelly Pro 3EM

The Pro 3EM is also the controller Shelly. A second Shelly is added as the dashboard Shelly.

<img width="350" alt="IMG_1246" src="https://github.com/user-attachments/assets/c8821089-7e87-437f-ad29-6715f1554cfb" />

### With another smart meter

The controller runs on any Shelly and reads the smart meter over the network. The dashboard Shelly is added – so here too, two Shellys.

<img width="600" alt="IMG_1247" src="https://github.com/user-attachments/assets/4758a842-f361-47d7-8260-c23fc1ae1bde" />

---

## Downloads

**Helper with configurator** – sets everything up, uploads the scripts to the Shellys, runs updates, checks memory and records a log when something goes wrong. No installation needed: download, start, done.

| Helper | for |
|---|---|
| **[⬇️ zendure_local_helper-windows.exe](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-windows.exe)** | Windows 64-bit |
| **[⬇️ zendure_local_helper-windows-x86.exe](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-windows-x86.exe)** | Windows 32-bit |
| **[⬇️ zendure_local_helper-macos](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-macos)** | Mac with Apple Silicon (M1 or newer) |

**Dashboard proxy** – opens the dashboard in your browser, no Python installation needed.

| Dashboard proxy | for |
|---|---|
| **[⬇️ zendure_proxy-windows.exe](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_proxy-windows.exe)** | Windows 64-bit |
| **[⬇️ zendure_proxy-macos](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_proxy-macos)** | Mac with Apple Silicon (M1 or newer) |

On first start, your operating system shows a warning because the files are not signed – how to start them anyway is explained in the [configurator docs](Multiconfigurator/readme_EN.md#recommended-the-local-helper-exe-installer). All files and checksums: [Releases](https://github.com/surfer1264/Zendure-Stuff/releases/latest).

**Without the helper:** The [web configurator](https://raw.githack.com/surfer1264/Zendure-Stuff/main/shelly_script/Multiconfigurator/zendure-multi-configurator_multilang.html) runs directly in your browser. You can configure everything and save the finished script – but you then have to upload it yourself via the Shelly's web interface. Update, memory check and log recording are only available with the helper.

---

## Update

When a new version is available, start the helper and choose **"Update"**. It compares the versions on your Shellys with GitHub, reads your settings directly from the Shelly and installs the new version – your settings are kept.

If you use the dashboard, also get the new dashboard proxy or dashboard page after an update: both must have the same version number as the script.

**Switching from the old separate scripts:** The zenDash API and watchdog used to be two separate scripts. How to switch to the shared script is explained in the [configurator docs](Multiconfigurator/readme_EN.md#switching-from-the-old-separate-scripts).

---

**Attention:** The configurator is no substitute for reading the documentation – especially for the control parameters.

## Conclusion

* Everything local
* no cloud
* no more excuses: "My system isn't working, the cloud is broken again"
* for all hubs with zenSDK
