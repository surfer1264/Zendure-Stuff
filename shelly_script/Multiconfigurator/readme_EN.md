[:de: Deutsch](readme.md) · [:gb: English](readme_EN.md) · [:fr: Français](readme_FR.md)

# The Configurator

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

A few clicks to local control of your Zendure fleet – set up, update, done.

> 🤖 This English version was translated from the [German original](readme.md) by Claude (Anthropic's AI). If anything is unclear or contradictory, the German version applies. The screenshots show the German interface.

**Contents**

1. [What does the configurator set up?](#1-what-does-the-configurator-set-up)
2. [Where do I find the configurator?](#2-where-do-i-find-the-configurator)
   * [Recommended: the local helper (EXE installer)](#recommended-the-local-helper-exe-installer)
   * [Alternative: web configurator only](#alternative-web-configurator-only)
3. [Initial setup](#3-initial-setup)
   * [The process](#the-process)
   * [Functions in the result step](#functions-in-the-result-step)
4. [Update](#4-update)
   * [How it works](#how-it-works)
   * [What happens to your settings during an update](#what-happens-to-your-settings-during-an-update)
   * [Update without the helper](#update-without-the-helper)
   * [Switching from the old separate scripts](#switching-from-the-old-separate-scripts)
5. [Replacing a Shelly](#5-replacing-a-shelly)
6. [Error messages and problem situations](#6-error-messages-and-problem-situations)
   * [Several scripts on one Shelly](#several-scripts-on-one-shelly)
   * [Messages at a glance](#messages-at-a-glance)
   * [Problems with the helper](#problems-with-the-helper)
7. [How-tos](#7-how-tos)
   * [Importing an existing configuration](#importing-an-existing-configuration)
   * [Uploading a script manually](#uploading-a-script-manually)
   * [Checking a Shelly's memory](#checking-a-shellys-memory)
   * [Backing up your configuration](#backing-up-your-configuration)
   * [Recording a log](#recording-a-log)
   * [Resetting remembered IPs](#resetting-remembered-ips)
   * [Verifying the download](#verifying-the-download)

Recent changes are listed in the [changelog](CHANGELOG.md) (German).

---

## 1. What does the configurator set up?

The configurator is a wizard that guides you step by step through setting up your Zendure control. You answer a few questions about your devices – at the end, the matching scripts are running, fully configured, on your Shellys.

Your system always consists of **two Shellys**:

| Shelly | Script | Task |
|---|---|---|
| **Controller Shelly** | Controller (`zerooutput_multi_kvs`) | the control engine – manages charging and discharging of your batteries and holds the live-adjustable settings (KVS) |
| **Dashboard Shelly** | zenDash-API + Watchdog (`zendash_watch`) | one shared script with two functions that can be switched off individually |

Three functions run on them:

* **Controller** – regulates your grid import/export via your Zendure batteries
* **zenDash-API** – provides the data for the dashboard with a live overview; you can also change the Controller's behaviour through it
* **Watchdog** – reports exceptional situations (battery full, temperature, cell voltage, device unreachable) and sends a summary every morning and evening

The functions can be combined freely – for example, zenDash-API and Watchdog can be added later when the Controller is already running. Information needed by several functions (device list, grid source, notifications) is asked **only once** and written into both scripts accordingly.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/487e63fb-734d-4bb1-b795-19f81921acb6" />

The configurator is available in **German, English and French**.

---

## 2. Where do I find the configurator?

There are two ways. The **local helper** (EXE file) is recommended, because direct upload, update, memory check and log recording only work with it.

### Recommended: the local helper (EXE installer)

A small program for your computer. It opens the configurator in your browser automatically and handles the connection to your Shellys. No installation, no Python required – download, start, done.

👉 **[Current version (latest release)](https://github.com/surfer1264/Zendure-Stuff/releases/latest)**

Direct downloads:

* [Windows (64-bit)](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-windows.exe)
* [Windows (32-bit)](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-windows-x86.exe)
* [macOS](https://github.com/surfer1264/Zendure-Stuff/releases/latest/download/zendure_local_helper-macos)

On first start, your operating system shows a warning because the file is not signed:

* **Windows:** At "Windows protected your PC" (SmartScreen), click "More info" → "Run anyway".
* **macOS:** Right-click the file → "Open" → confirm "Open" again in the dialog.

If you want to make sure the file is unmodified, you can [verify it](#verifying-the-download).

**Important:** The helper window must stay open while you set up or update. Afterwards you can close it (or press `Ctrl+C`).

**What the helper does – and what it doesn't:** It runs only on your own computer (`http://127.0.0.1:8787`) and cannot be reached from your network. After a successful upload it only remembers the **IP addresses** of your two Shellys – no configuration, no passwords. If a Shelly is password-protected, the configurator asks for the password; the helper keeps it only in memory until you close it.

### Alternative: web configurator only

Runs directly in the browser, no download:

👉 [Open the web configurator](https://raw.githack.com/surfer1264/Zendure-Stuff/main/shelly_script/Multiconfigurator/zendure-multi-configurator_multilang.html)

With it you can configure everything and download the finished script – **but you then have to upload it yourself** via the Shelly's web interface ([instructions](#uploading-a-script-manually)). Update and memory check are not available without the helper.

> Tip: If the helper is running in the background, the web configurator detects it as well and unlocks the additional functions.

---

## 3. Initial setup

Start the helper. In the start dialog, choose **"Configure from scratch"**.

### The process

1. **Start** – choose "Configure from scratch"
2. **Functions** – select Controller, zenDash-API and/or Watchdog and enter the **IP addresses of your two Shellys**. If you already have a configuration, you can [import](#importing-an-existing-configuration) it here instead of entering everything again.
3. **Devices** – your Zendure batteries with IP, maximum power and minSoc/maxSoc; for each device, whether the Watchdog should monitor it. **"Test"** next to the IP opens the battery's report (`/properties/report`) in a new tab – so you can see right away whether the IP is correct
4. **Grid source** – where the grid power reading comes from: the Controller runs directly on a Shelly Pro 3EM, another Pro 3EM in the network, or a meter with a JSON interface (e.g. Zendure Smart Meter 3CT, Tasmota, Shelly 3EM without Pro)
5. **Charge from grid** – which devices may absorb surplus from other systems
6. **Notifications** – webhook, Signal or WhatsApp; shared by Controller and Watchdog
7. **Watchdog thresholds** – Watchdog only: from when "battery full", low cell voltage and high temperature are reported, and from which value the message is armed again. Prefilled from your imported config or the defaults (99/90 %, 2.9/3.1 V, 45/30 °C).
8. **Battery full / KVS** – how grid export is handled when the batteries are full, and whether you want to change settings live later (e.g. from the dashboard or Home Assistant)
9. **Control parameters** – setpoint, hysteresis and the thresholds for distributing power, already prefilled with sensible values
10. **Result** – a summary of your input with the version numbers and the finished scripts

Steps that are not needed for your selection are skipped.

**About the control parameters:** The values are taken from your imported configuration or calculated from your device list using a rule of thumb. If you later change devices or power ratings, they are **not** adjusted automatically – please check them yourself. Meaning and recommendations are in the [Controller documentation](https://github.com/surfer1264/Zendure-Stuff/blob/main/shelly_script/Controller/readme.md) (German).

**Without KVS:** If you switch off live settings (KVS), the dashboard can only display values – changes made in the dashboard will then have no effect on the Controller.

### Functions in the result step

For each of the two Shellys you get several options:

**⚡ Upload directly** *(helper only)*

The most convenient way: one click, done. The script automatically goes to the right Shelly (Controller script to the Controller Shelly, zenDash-API + Watchdog to the Dashboard Shelly), is started and set up for autostart. If there are already other scripts on the Shelly, the configurator asks first – see [Several scripts on one Shelly](#several-scripts-on-one-shelly).

After the first successful upload, the helper remembers the IPs and fills them in automatically next time.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/5082cdf4-1a6c-43a1-825c-8fc51bf18173" />

**🔗 Save complete script from GitHub**

Loads the current original script from GitHub, inserts your configuration and offers you the finished script as a file. You then only need to [upload it manually](#uploading-a-script-manually). Requires a brief internet connection.

The file name contains the script version, e.g. `zerooutput_multi_kvs_mini_v5.0.8.js` or `zendash_watch_mini_v3.3.1.js`. This lets you keep several versions side by side and [import](#importing-an-existing-configuration) them again at any time.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/d839f5b2-7433-4941-977c-a7c173ab7af2" />

**📋 Copy / 💾 Save CONFIG block only**

Only the configuration – for anyone who has customised their script or prefers to work by hand. Use it to replace the `let CONFIG = { ... };` block in your script. It is also your **backup copy**: save it, and you can import it again at any time.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/1ccd9b90-9d83-42b8-892b-932ad12df4db" />

**🐞 Debug output**

Above each CONFIG block, a checkbox switches the script's verbose debug output on or off – before uploading or saving. This also works via [Update](#4-update): choose Update, tick the box, upload directly. Debug is meant for troubleshooting only (e.g. together with [Recording a log](#recording-a-log)) and should be switched off again afterwards.

**🔍 Check memory** *(helper only)*

Shows how much script memory is still free on a Shelly – see [Checking a Shelly's memory](#checking-a-shellys-memory).

<img width="800" alt="image" src="https://github.com/user-attachments/assets/49d74a5d-cfd2-4541-932f-54c40b60ff5b" />

---

## 4. Update

When a new version of a script is available, you can bring your Shellys up to date in a few clicks – **your settings are kept**. Updating only works with the [local helper](#recommended-the-local-helper-exe-installer).

### How it works

1. Start the helper and choose **"Update"** in the start dialog.
2. Your Shellys' IPs are normally already filled in (remembered from the last upload). If not, enter them once – at least one.
3. The configurator compares the installed versions with GitHub and shows a table:

   | Status | Meaning |
   |---|---|
   | **Update available** | A newer version exists – the changes are listed directly below. Ticked automatically. |
   | **up to date** | Nothing to do. |
   | **newer than GitHub** | You have a test or pre-release version – nothing to do. |
   | **not installed** / **no unique script** | Update not possible, please use ["Configure from scratch"](#3-initial-setup). |
   | **Shelly not reachable** | see [Error messages](#6-error-messages-and-problem-situations) |

   Below the table you can also see whether there is a new version of the configurator/helper itself – with a download link.
4. Tick the scripts you want → **"Update now"**. The configurator reads your current configuration directly from the Shelly and jumps to the result.
5. There, click **"⚡ Upload directly"**. The new script replaces the old one in the same slot (the script number stays the same – important e.g. for the dashboard proxy) and is started again.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/fb19b123-4555-4be9-bc5d-39c16310bf12" />

### What happens to your settings during an update

Everything is carried over – including values the wizard doesn't ask for (e.g. `dampingFactor`, `interval` or the Watchdog's warning thresholds). New settings that didn't exist in your old version get their default value.

### Update without the helper

Without the helper, use **"Configure from scratch"**: [import](#importing-an-existing-configuration) your configuration, click through, save the new script and [upload it manually](#uploading-a-script-manually).

<img width="800" alt="image" src="https://github.com/user-attachments/assets/e23c3b85-03a4-4502-9868-81c742d8e7c5" />

### Switching from the old separate scripts

zenDash-API and Watchdog are now **one** script (`zendash_watch`). Configurations of the old separate scripts (zenDash-API 2.x, Watchdog 1.x) **cannot** be imported. Here's how to switch:

1. Choose "Configure from scratch" and import the **Controller configuration** – it provides devices, grid source and notifications. You add the rest in the wizard.
2. When uploading directly to the Dashboard Shelly, the configurator detects the old scripts and asks whether they should be deleted → **"Yes, delete others and install"**.
3. If old scripts are on a different Shelly (or you upload manually): **stop them there and switch off autostart** – otherwise they keep running in parallel and messages arrive twice.

---

## 5. Replacing a Shelly

You're replacing a Shelly (defective, new model) or it has a new IP address? Here's how to take your configuration with you:

1. **Back up your configuration.** If you have already saved the CONFIG block, use that. Otherwise, open the script in the old Shelly's web interface under "Scripts" and copy the complete `let CONFIG = { ... };` block.
2. Start the helper and choose **"Configure from scratch"** (update doesn't work here, because nothing is installed on the new Shelly yet).
3. In the "Functions" step, **import** the configuration – ideally Controller and zenDash-API + Watchdog one after the other.
4. **Only then** enter the IP address of the new Shelly. Importing takes over the IPs from the old configuration and would overwrite an IP entered beforehand.
5. Click through the wizard and **upload directly** to the new Shelly. From now on the helper remembers the new IP.
6. On the **old** Shelly, stop the script and switch off autostart (or delete the script) if it stays on the network.

Things to watch out for:

* **Your Controller Shelly is also your Pro 3EM?** Then the grid measurement moves with it. Check in the "Grid source" step whether the setting is still correct.
* **New IP of the Controller Shelly:** The zenDash-API reads its values from the Controller Shelly. So re-upload the script on the Dashboard Shelly as well, so that it knows the new address.
* **New IP of a Zendure battery:** Not a Shelly replacement, but just as quick – "Configure from scratch", import the configuration, change the IP in the "Devices" step, re-upload both scripts.
* Tip: Give your Shellys and batteries a **fixed IP address** in your router, and this won't happen in the first place.

---

## 6. Error messages and problem situations

### Several scripts on one Shelly

⚠️ **Exactly one script should run per Shelly.** Shellys have very little script memory. If there are other scripts on it – even stopped, old or test scripts – the new script may fail to start or crash during operation. For the Controller this means: **your control stops**.

That's why the configurator checks this before every direct upload. If it finds other scripts, it shows you the list (with status "running"/"stopped") and asks:

* **"Yes, delete others and install"** – recommended. The other scripts are removed.
* **"No, keep others and install"** – only if you know for sure that there's enough memory. Check it first with [Check memory](#checking-a-shellys-memory).
* **"Cancel"** – nothing is changed on the Shelly.

If there are several scripts **of the same type** on the Shelly (e.g. two Controllers), "keep" is not possible, because it would be unclear which one should be updated.

For the same reason, Controller and zenDash-API + Watchdog **never** run together on one Shelly. The configurator already checks in the first step that two different IP addresses are entered.

### Messages at a glance

| Message | What does it mean? | What to do? |
|---|---|---|
| "Update" is greyed out: *Only possible with the local helper* | The helper isn't running. | Start the [helper](#recommended-the-local-helper-exe-installer) – it opens the configurator itself. |
| *Your local helper is older than this page …* | An old version of the helper is still running. | Close the helper, download the current version and start it again. |
| *Shelly not reachable* | The Shelly doesn't respond. | Check the IP (in the Shelly app or router). Is the Shelly switched on? Is your computer on the same network (not the guest Wi-Fi)? |
| Window *Password for Shelly …* | The Shelly's password protection is active. | Enter the password (the user is always `admin`). The helper keeps it only in memory until you close it. Without the helper: temporarily switch off password protection, upload manually, switch it back on. |
| *Wrong password* | The password entered does not match. | Enter it again – it is the password from the Shelly app or web interface. |
| *not installed – please use "Configure from scratch"* | There's no matching script on the Shelly. | Set it up via ["Configure from scratch"](#3-initial-setup). |
| *no unique script – please use "Configure from scratch"* | There are several scripts of the same type on the Shelly. | "Configure from scratch" – let the other scripts be deleted when uploading. |
| *Could not read the config from the Shelly* | The configuration can't be found in the script (e.g. edited by hand). | "Configure from scratch" and import the configuration from your backup. |
| *Could not load versions from GitHub* / *GitHub version unknown* | No connection to GitHub. | Check your internet connection, "Check versions" again later. |
| *The script "…" is already installed on … – but this device is set up here for "…". Are the IP addresses swapped?* | Controller and Dashboard IPs are probably swapped. | **Cancel** and check the IPs. Only delete if you really want to repurpose the Shelly. |
| *There are n scripts on …* / *A different script is installed on …* | Other scripts on the Shelly. | see [Several scripts](#several-scripts-on-one-shelly) |
| *Upload aborted – the script on the Shelly is incomplete* | The connection dropped during upload. **The script is not running now.** | Immediately "Upload directly" again. |
| *Uploaded to …, but the script is not running* | The script was transferred but doesn't start. | Look at the log in the Shelly web interface under "Scripts". Common causes: too little memory (remove other scripts) or wrong device IPs. |
| *⚠️ Only … bytes free* | Memory is tight. | Remove other scripts from the Shelly. |
| *This is a config in the old format …* | Configuration of the old separate scripts. | see [Switching](#switching-from-the-old-separate-scripts) |
| *Couldn't tell which product this config belongs to* | Copied incompletely. | Paste the complete block from `let CONFIG = {` to `};`. |
| *Controller Shelly and Dashboard Shelly must be two different devices* | The same IP was entered twice. | Use two different Shellys. |
| *Error: … check your internet connection …* when downloading the script | GitHub not reachable. | Check your internet connection. |

### Problems with the helper

| Situation | What to do? |
|---|---|
| The helper window closes immediately or reports that it could not listen on 127.0.0.1:8787 | The helper is already running (another window, possibly minimised) – use that one, or close it and restart. |
| The browser doesn't open | Open `http://127.0.0.1:8787` in your browser. |
| Windows/macOS blocks the start | see [Where do I find the configurator?](#recommended-the-local-helper-exe-installer) |
| The configurator suggests wrong Shelly IPs | Simply overwrite the IP in the field – or [reset](#resetting-remembered-ips) the remembered IPs. |

---

## 7. How-tos

### Importing an existing configuration

In the "Functions" step, under **"Import an existing config to update it"**, paste a complete `let CONFIG = { ... };` block **or** select a saved file with **"📂 Load file…"**, then click "Import & apply". You can load either the file from "💾 Save CONFIG block only" or a complete script from "🔗 Save complete script from GitHub" – the file first lands in the text field and is only applied when you click. The configurator detects by itself whether it's the Controller or zenDash-API + Watchdog. Ideally import both one after the other – the order doesn't matter. The Shelly IPs are taken over at the same time.

### Uploading a script manually

Without the helper (the instructions are also available as an expandable section in the configurator):

1. In the result step, click "🔗 Save complete script from GitHub".
2. Open the Shelly's IP in your browser (e.g. `http://192.168.178.151`) and go to "Scripts".
3. Stop and delete an old script of the same name. **Remove other scripts as well** (see [Several scripts](#several-scripts-on-one-shelly)).
4. "Add script", give it a name, save.
5. Open the downloaded file in a text editor, copy everything and paste it into the code editor.
6. "Save", then "Start", and enable **"Enable on boot"**.
7. Check in the log that the script runs without errors.

### Checking a Shelly's memory

With the helper running, enter the IP of any Shelly in the result step and click **"🔍 Check memory"**. With **25,000 bytes of total memory** or more, everything is fine. If a script is already running, the free memory is naturally lower – so the configurator then calculates the total as free + used and also shows how much the script uses (and its peak). This also works on a new Shelly without a script.

For reference: the zenDash-API + Watchdog script uses around 13.5 kB in operation with two batteries, and around 17.8 kB at peak.

### Backing up your configuration

After every change, click "💾 Save CONFIG block only" or "🔗 Save complete script from GitHub" in the result step and keep the file. The complete script carries the version in its file name – handy if you want to keep several versions. You can [import](#importing-an-existing-configuration) both files again later with "📂 Load file…". This way you're back up and running within minutes if a Shelly fails or is replaced.

### Recording a log

For troubleshooting – for example when a script doesn't start or behaves oddly – the configurator records a Shelly's messages. This only works with the [local helper](#recommended-the-local-helper-exe-installer).

1. In the start dialog, choose **"Record log"**.
2. Enter the Shelly's IP (or click Controller Shelly / Dashboard Shelly) and click **"Show scripts"**.
3. Select the script you want.
4. Choose the duration: **140 seconds** or **600 seconds** (10 minutes).
5. Click **"Start recording"**.

The helper stops the script, restarts it and records for the chosen duration. The log is then saved automatically as a file, e.g. `zerooutput_multi_kvs_v5.0.8_260927-1432.log`. You can see the last lines directly in the configurator. If the script is not running after the recording, the configurator points this out – the cause is then usually in the log.

* **Filtered (default):** "Record only output of the selected script" is ticked – the log only contains what the script itself prints.
* **Unfiltered:** remove the tick – then all messages from the Shelly are added, including system messages. You need this if the script does not start, because the Shelly reports start errors or low memory as system messages. Lines from the script are then marked with `[Script 8]`.

About size: for the Controller, 600 seconds are around 150 control cycles. Filtered, the log is roughly 100–300 KB depending on the number of batteries, unfiltered correspondingly more – no problem for a text editor.

**Masking:** webhook IDs, tokens, API keys, passwords and phone numbers are replaced by `***` during recording; only the last 4 characters of serial numbers remain. IP addresses are kept because they are needed for troubleshooting. This makes it easier to share the log in an issue or forum – still, skim it briefly first.

⚠️ For the Controller, control pauses for a few seconds during the restart. Keep the page and the helper open until the end. If the debug log is switched off on the Shelly, the helper switches it on only for the recording and off again afterwards.

Tip: for more detail, switch on the script's [debug output](#functions-in-the-result-step) beforehand.

For recordings over several hours, use the [WebSocket log grabber](https://github.com/surfer1264/Zendure-Stuff/tree/main/shelly_script/Script_poller) (German).

### Resetting remembered IPs

The helper stores the IPs in the file `zendure_helper_config.json` – either next to the helper file or, if it can't write there, here:

* **Windows:** `%APPDATA%\ZendureHelper\`
* **macOS:** `~/Library/Application Support/ZendureHelper/`

Delete the file, and the configurator will ask for the IPs again next time.

### Verifying the download

For every file, the [releases page](https://github.com/surfer1264/Zendure-Stuff/releases/latest) has a `.sha256` file with the same name. Use it to verify that your download is exactly the file produced by the build.

**Windows (PowerShell)** – prints `True` or `False`:

```powershell
(Get-FileHash .\zendure_local_helper-windows.exe -Algorithm SHA256).Hash -eq (Get-Content .\zendure_local_helper-windows.exe.sha256).Split(' ')[0]
```

For the 32-bit version, use `zendure_local_helper-windows-x86.exe`.

**macOS (Terminal):**

```bash
shasum -a 256 -c zendure_local_helper-macos.sha256
```

`OK` = all good. `FAILED` = do **not** run the file, download it again.
