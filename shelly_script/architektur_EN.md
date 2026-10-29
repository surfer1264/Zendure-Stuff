[:de: Deutsch](architektur.md) · :gb: **English** · [:fr: Français](architektur_FR.md)

# How the parts work together

The suite has three layers: your devices at the bottom, two Shellys with one fixed job each in the middle, and everything for operating and analysing at the top. Everything runs in your home network – no cloud needed.

![Shelly Suite architecture](img/architektur_EN.svg)

## Bottom: the devices

**Batteries** – Your Zendure batteries have a built-in local interface, the **zenSDK**. The Shellys talk to it directly via its IP address:

- `/properties/report` returns state of charge, power values, cell voltage, temperature and limits such as `minSoc`.
- `/properties/write` accepts commands, e.g. charge or discharge and with how many watts. The Controller sets `smartMode: 1` so the frequent commands are not written to the device's flash memory.

The batteries do not need internet access for normal operation. You can block it in your router.

**Energy meter** – The Controller needs to know how much power is currently drawn from or fed into the grid. The simplest setup runs it directly on a **Shelly Pro 3EM** – meter and Controller Shelly are then the same device. Alternatively it reads another smart meter over the network (`http_json`), see [Controller](Controller/readme_EN.md).

Tip: give the batteries and Shellys fixed IP addresses in your router.

## Middle: two Shellys

**Shelly 1 – Controller** regulates. Every few seconds it measures the grid power and distributes charging and discharging across your batteries so that as little as possible is fed in or drawn. It works completely on its own.

**Shelly 2 – zendash_watch** displays and watches. It provides the data for the dashboard, passes changes from the dashboard on to the Controller and monitors your batteries as a watchdog. Notifications (battery full, overtemperature, undervoltage, failure) are sent via Signal, WhatsApp or webhook. If the cell voltage drops below the threshold, it also blocks discharging.

**KVS** – The settings you change during operation (setpoint, reserve, discharge allowed …) are stored in the KVS of the Controller Shelly. The Controller reads them in every control cycle, so changes take effect within a few seconds, without a restart.

**Exactly one script** runs on each Shelly. Shellys have little script memory; two scripts on one device can crash each other.

## Top: operate and analyse

**Dashboard proxy** – a small program on a PC, Raspberry Pi, NAS or as a Home Assistant app. It serves the [dashboard](zendash_watch_API_ZenSDK/dashboard_EN.md) and forwards its requests to Shelly 2. The browser never talks to the Shellys directly.

**Dashboard (SMDC)** – the web page in the browser or as an app on your phone's home screen: live values, setpoint, reserve, manual charging.

**Cloud statistics (optional)** – On request, the proxy sends the readings every minute to [ThingSpeak](zendash_watch_API_ZenSDK/thingspeak.md) and/or [ThingsBoard](zendash_watch_API_ZenSDK/thingsboard.md) (German) – also self-hosted in your home network. Only readings are transferred, no names, addresses or serial numbers. If no upload is enabled, the proxy does not poll anything. For gap-free history it must run permanently (NAS or Home Assistant).

**Home Assistant (optional)** – reads and writes the Controller's KVS directly via REST (`KVS.GetMany`, `KVS.Set`). This lets you control setpoint, reserve and more from automations.

## Setup and updates

The **[Configurator](Multiconfigurator/readme_EN.md)** with the helper runs on your computer. It checks the free memory of the Shellys, creates the settings, downloads the scripts from GitHub and uploads them. For updates it compares the versions on the Shellys with the current ones on GitHub. It is not needed in everyday operation.

## What happens if something fails?

| If this fails … | Result |
|---|---|
| Proxy or PC | No dashboard, no statistics. **Regulation continues.** |
| Internet | No statistics, no Signal/WhatsApp notifications. Regulation and dashboard continue. |
| Shelly 2 (zendash_watch) | No dashboard, no notifications. **Regulation continues.** |
| One battery | The Controller keeps regulating with the others, the watchdog reports the failure. |
| Shelly 1 (Controller) | No more regulation. The dashboard can no longer change settings. |

## Read more

- [What the suite can do](szscs_EN.md)
- [Controller](Controller/readme_EN.md)
- [zenDash API + Watchdog](zendash_watch_API_ZenSDK/readme_EN.md) · [API reference](zendash_watch_API_ZenSDK/API.md) (German)
- [Compatible devices](kompatible_geraete_EN.md) · [Memory requirements](zendash_speichermodell.md) (German)
