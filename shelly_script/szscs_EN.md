[:de: Deutsch](szscs.md) · :gb: **English** · [:fr: Français](szscs_FR.md)

# Simple Zendure Shelly Cloudless System

**Buy me a coffee!**

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

<img width="1000" alt="image" src="https://github.com/user-attachments/assets/0267db3d-7941-472e-87de-e134ada66dea" />

* You have **one** or **several** SolarFlows (SF800 or newer, zenSDK-capable)?
* You have a Shelly Pro 3EM or another smart meter with a local interface? See [Compatible devices](kompatible_geraete_EN.md)
* You want local control – without the cloud?
* You want little effort and something that simply works?
* Home Assistant & co. are not (yet) an option for you?

_Principle_: **Install** – **Run** – **Forget**

🎉 HERE YOU ARE 🎉

---

## Three functions on two Shellys – without the cloud

The **Controller Shelly** runs the control, the **Dashboard Shelly** runs the zenDash API and watchdog – both functions there can be switched off individually. Which script goes where: [How the system is structured](readme_EN.md#how-the-system-is-structured).

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

📖 [Setting up and using the dashboard](zendash_watch_API_ZenSDK/dashboard_EN.md)

### 3. The watchdog – the notifications

* **morning and evening summary** with state of charge, temperature and cell voltage
* notification when a **battery is full**
* **warning** when a cell voltage is too low or the temperature too high
* notification when a SolarFlow is **unreachable** – and an all-clear as soon as it's back
* notice when a battery **hasn't been full for 20 days**
* delivery via **Signal**, **WhatsApp** or **webhook**; configurable per SolarFlow whether it is monitored

📖 [zenDash API + watchdog](zendash_watch_API_ZenSDK/readme_EN.md)

---

## Setup

### With a Shelly Pro 3EM

The Pro 3EM is also the controller Shelly. A second Shelly is added as the dashboard Shelly.

<img width="350" alt="IMG_1246" src="https://github.com/user-attachments/assets/c8821089-7e87-437f-ad29-6715f1554cfb" />

### With another smart meter

The controller runs on any Shelly and reads the smart meter over the network. The dashboard Shelly is added – so here too, two Shellys.

<img width="600" alt="IMG_1247" src="https://github.com/user-attachments/assets/4758a842-f361-47d7-8260-c23fc1ae1bde" />

---

## 👉 How to get started

Download the helper, answer the questions, upload – after 10 minutes your control is running. The three steps are on the **[start page](readme_EN.md#-start-here)**, the detailed instructions with the **[Configurator](Multiconfigurator/readme_EN.md)**.

---

## What you need

Two Shellys (ideally one of them a **Shelly Pro 3EM**, which measures the grid power as well), a smart meter and zenSDK-capable SolarFlows in the same network. Which devices work and what else is needed is listed under **[Compatible devices](kompatible_geraete_EN.md)**.

**Important:** Remove your SolarFlows from **HEMS** in the Zendure app, otherwise the cloud sends its own control commands in parallel.

---

## Downloads

All programs are on the **[releases page](https://github.com/surfer1264/Zendure-Stuff/releases/latest)**. What you need for what, and how to allow the files on first start:

- **Helper with configurator** – sets everything up, uploads the scripts to the Shellys, runs updates: [Configurator → download](Multiconfigurator/readme_EN.md#recommended-the-local-helper-exe-installer)
- **Dashboard proxy** – opens the dashboard in your browser, no Python installation needed: [Dashboard → as a program](zendash_watch_API_ZenSDK/dashboard_EN.md#as-a-program-on-windows-or-macos)
- **Without the helper:** the [web configurator](Multiconfigurator/readme_EN.md#alternative-web-configurator-only) in your browser – you then upload the script yourself.

---

## Update

Start the helper, choose **"Update"** – your settings are kept. Details, including switching from the old separate scripts: [Configurator → update](Multiconfigurator/readme_EN.md#4-update). If you use the dashboard, the dashboard page and the script must have the same version number ([Dashboard](zendash_watch_API_ZenSDK/dashboard_EN.md)).

---

**Attention:** The configurator is no substitute for reading the documentation – especially for the control parameters.

## Conclusion

* Everything local
* no cloud
* no more excuses: "My system isn't working, the cloud is broken again"
* for all hubs with zenSDK
