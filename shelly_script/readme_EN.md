<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

🌐 [Deutsch](readme.md) · **English** · [Français](readme_FR.md)

# Control Zendure batteries locally – with two Shellys

Your Zendure batteries (zenSDK-capable devices from SolarFlow 800 onwards) are controlled without the cloud: one Shelly keeps your grid draw at zero, a second one provides the data for a dashboard and alerts you when something is wrong.

## 👉 Start here

1. **[Download the helper](https://github.com/surfer1264/Zendure-Stuff/releases/latest)** (Windows or Mac with Apple Silicon) and start it.
2. The Configurator opens in your browser. Choose **"Configure from scratch or update manually"** and answer the questions.
3. Finally click **"⚡ Upload directly"** – done.

Detailed instructions (including updates, replacing a Shelly and error messages) can be found with the **[Configurator](Multiconfigurator/readme_EN.md)** · [Deutsch](Multiconfigurator/readme.md) · [Français](Multiconfigurator/readme_FR.md)

## How the system is structured

| Shelly | Script | Task |
|---|---|---|
| **Controller Shelly** | [Controller](Controller/readme.md) (German) | controls charging and discharging of your batteries |
| **Dashboard Shelly** | [zenDash API + Watchdog](zendash_watch_API_ZenSDK/readme_EN.md) | provides the data for the dashboard and reports battery full, overtemperature, undervoltage or failures |

On top of that there is the **[Configurator](Multiconfigurator/readme_EN.md)** with the helper on your computer: it handles initial configuration, updates and log recording for both Shellys.

**Exactly one script** runs on each Shelly. Shellys have little script memory – two scripts on one device can crash each other.

The **[Dashboard](zendash_watch_API_ZenSDK/dashboard.md)** (German) itself is a web page that you open via a small proxy on a PC, NAS or Home Assistant.

## Further tools

| Folder | Purpose |
|---|---|
| [Script_poller](Script_poller/readme.md) (German) | long-term measurement of memory and CPU of a Shelly script, log recording over hours (for troubleshooting and development) |
| [testController](testController/README.md) (German) | test environment for the Controller (for developers) |
| [thingsboard](thingsboard) | ready-made dashboards and rule chains for import into ThingsBoard, matching the [ThingsBoard upload](zendash_watch_API_ZenSDK/thingsboard.md) (German) |
| [Einordnung](Einordnung.md) (German) | comparison with other multi-device solutions (ioBroker, Z-HA, EMS SolarFlow …) |

## Deprecated – please do not use anymore

These folders are kept for reference only and are no longer developed:

| Folder | Replaced by |
|---|---|
| AkkuWatchDogMulti, WatchdogZenSDK | [zenDash API + Watchdog](zendash_watch_API_ZenSDK/readme_EN.md) |
| zendash | [zenDash API + Watchdog](zendash_watch_API_ZenSDK/readme_EN.md) |
| Upload_Controller | [Configurator with helper](Multiconfigurator/readme_EN.md) (direct upload and update) |
| [Datenmonitor](Datenmonitor/readme.md) | – (basic data monitor via MQTT and zenSDK, without support) |

## Terms

| Term | Meaning |
|---|---|
| **Battery** | your Zendure device (SolarFlow 800, SolarFlow 2400 Pro …) |
| **Controller** | the control script `zerooutput_multi_kvs` |
| **Helper** | small program for your computer that starts the Configurator and uploads the scripts to the Shellys |
| **KVS** | key-value store in the Shelly for settings you can change during operation (e.g. from the dashboard) |

More background can be found in the [Wiki](https://github.com/surfer1264/Zendure-Stuff/wiki/Simple-Zendure-Shelly-Cloudless-System_EN).
