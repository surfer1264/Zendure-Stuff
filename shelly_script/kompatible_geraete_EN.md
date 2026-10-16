[:de: Deutsch](kompatible_geraete.md) · :gb: **English** · [:fr: Français](kompatible_geraete_FR.md)

# Compatible devices

What you need for the suite: two Shellys, a smart meter and zenSDK-capable Zendure batteries.

## Shellys

You need **two Shellys** Gen2 or newer (Plus, Pro, Gen3, Gen4) with script support – one for the [Controller](Controller/readme.md), one for [zenDash API + Watchdog](zendash_watch_API_ZenSDK/readme_EN.md). Both scripts together do not fit into the memory of one Shelly.

What matters is the **script memory**: with **25,000 bytes** or more, everything is fine.

| Device | Result |
|---|---|
| Shelly Pro 3EM | ✅ tested |
| Shelly 3EM-63W Gen3 | ✅ tested |
| Shelly 3EM 3ct63 | ✅ tested |
| Shelly 1PM Gen4 | ✅ tested |
| Shelly Plus 1PM (PM1Plus) | ✅ tested |
| Shelly Plus Plug S | ✅ tested |
| Shelly Plug S Gen3 | ❌ not enough memory |
| Shelly 1PM Gen3 | ❌ not enough memory |
| Shelly Mini Gen3 | ❌ not enough memory |

Your device is missing? Check the memory yourself:

- **With the configurator** (helper running): in the result step, **"🔍 Check memory"** – see [Checking a Shelly's memory](Multiconfigurator/readme_EN.md#checking-a-shellys-memory).
- **In the browser:** open `http://<Shelly-IP>/rpc/Script.GetStatus?id=<script-ID>`. The answer contains `mem_free` – on a Shelly without a running script the value should be at least 25,000.

How many batteries one Shelly can control is explained in the [memory requirements](zendash_speichermodell.md) (German).

!!! warning "No password protection on the Controller Shelly"
    The zenDash API reads and writes the Controller's settings. With password protection on the Controller Shelly, this does not work.

## Smart meter

The Controller needs the current grid power:

- **Shelly Pro 3EM** – best choice: if the Controller runs directly on it, it reads the values without a network request.
- **Another Shelly Pro 3EM** in the network.
- **Meters with a JSON interface** (`http_json`), e.g. Zendure Smart Meter 3CT and D0, everHome EcoTracker, Tasmota IR reader, Shelly 3EM non-Pro. The [configurator](Multiconfigurator/readme_EN.md) has ready-made templates for these devices.

## Zendure batteries

- Only **zenSDK-capable devices** (SolarFlow 800 and newer), in the same network and ideally with a **fixed IP address** (set it in your router).
- Remove the batteries from **HEMS** in the Zendure app – otherwise the cloud sends its own control commands in parallel. Exception Zendure Smart Meter D0: its local interface is enabled once via HEMS. This only concerns the meter, the batteries still stay out of HEMS.
- **There can be only one:** no second controller may control the same batteries – no HEMS, no Z-HA, no other automation.

## Network

The Controller Shelly must reach all batteries and the smart meter in the local network (same LAN/Wi-Fi, no firewall in between). Ideally give the batteries and Shellys **fixed IP addresses** in your router. The Shelly only needs internet for the optional notifications.

## Also needed

- A **Windows PC or Mac** (Apple Silicon) for the [helper with configurator](Multiconfigurator/readme_EN.md). Without the helper any browser will do – you then upload the script yourself.
- **Optional for notifications:** a free API key from [CallMeBot](https://www.callmebot.com/blog/free-api-signal-send-messages/) for Signal or WhatsApp – or a webhook, e.g. in Home Assistant.
