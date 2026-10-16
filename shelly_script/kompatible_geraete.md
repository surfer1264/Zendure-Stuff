:de: **Deutsch** · [:gb: English](kompatible_geraete_EN.md) · [:fr: Français](kompatible_geraete_FR.md)

# Kompatible Geräte

Was du für die Suite brauchst: zwei Shellys, ein Smartmeter und zenSDK-fähige Zendure-Speicher.

## Shellys

Du brauchst **zwei Shellys** Gen2 oder neuer (Plus, Pro, Gen3, Gen4) mit Script-Funktion – einen für den [Controller](Controller/readme.md), einen für [zenDash-API + Watchdog](zendash_watch_API_ZenSDK/readme.md). Beide Scripte zusammen passen nicht in den Speicher eines Shelly.

Entscheidend ist der **Script-Speicher**: Ab **25 000 Bytes** ist alles gut.

| Gerät | Ergebnis |
|---|---|
| Shelly Pro 3EM | ✅ getestet |
| Shelly 3EM-63W Gen3 | ✅ getestet |
| Shelly 3EM 3ct63 | ✅ getestet |
| Shelly 1PM Gen4 | ✅ getestet |
| Shelly Plus 1PM (PM1Plus) | ✅ getestet |
| Shelly Plus Plug S | ✅ getestet |
| Shelly Plug S Gen3 | ❌ zu wenig Speicher |
| Shelly 1PM Gen3 | ❌ zu wenig Speicher |
| Shelly Mini Gen3 | ❌ zu wenig Speicher |

Dein Gerät fehlt? Prüfe den Speicher selbst:

- **Mit dem Configurator** (Helfer läuft): im Ergebnis-Schritt **„🔍 Speicher prüfen“** – siehe [Speicher eines Shelly prüfen](Multiconfigurator/readme.md#speicher-eines-shelly-prüfen).
- **Im Browser:** `http://<Shelly-IP>/rpc/Script.GetStatus?id=<Script-ID>` aufrufen. Die Antwort enthält `mem_free` – bei einem Shelly ohne laufendes Script sollte der Wert bei mindestens 25 000 liegen.

Wie viele Speicher ein Shelly regeln kann, steht in der [Speicherbedarfsbetrachtung](zendash_speichermodell.md).

!!! warning "Kein Passwortschutz auf dem Controller-Shelly"
    Die zenDash-API liest und schreibt die Einstellungen des Controllers. Mit Passwortschutz auf dem Controller-Shelly geht das nicht.

## Smartmeter

Der Controller braucht den aktuellen Netzbezug:

- **Shelly Pro 3EM** – beste Wahl: Läuft der Controller direkt darauf, liest er die Werte ohne Netzwerkabfrage.
- **Ein anderer Shelly Pro 3EM** im Netz.
- **Messgeräte mit JSON-Schnittstelle** (`http_json`), z. B. Zendure Smart Meter 3CT und D0, everHome EcoTracker, Tasmota-Lesekopf, Shelly 3EM ohne Pro. Für diese Geräte hat der [Configurator](Multiconfigurator/readme.md) fertige Vorlagen.

## Zendure-Speicher

- Nur **zenSDK-fähige Geräte** (ab SolarFlow 800), im selben Netz und am besten mit **fester IP-Adresse** (im Router einstellen).
- Die Speicher in der Zendure-App aus dem **HEMS** entfernen – sonst schickt die Cloud parallel eigene Steuerbefehle. Ausnahme Zendure Smart Meter D0: Dessen lokale Schnittstelle wird einmalig über HEMS freigeschaltet. Das betrifft nur den Zähler, die Speicher bleiben trotzdem aus dem HEMS draußen.
- **Es kann nur einen geben:** Kein zweiter Regler darf dieselben Speicher steuern – also kein HEMS, kein Z-HA, keine andere Automatik.

## Netzwerk

Der Controller-Shelly muss alle Speicher und das Smartmeter im lokalen Netz erreichen (gleiches LAN/WLAN, keine Firewall dazwischen). Die **IP-Adressen** von Speichern und Shellys am besten im Router fest vergeben. Internet braucht der Shelly nur für die optionalen Benachrichtigungen.

## Außerdem

- Ein **Windows-PC oder Mac** (Apple Silicon) für den [Helfer mit Configurator](Multiconfigurator/readme.md). Ohne Helfer reicht jeder Browser – dann lädst du das Script selbst hoch.
- **Optional für Benachrichtigungen:** ein kostenloser API-Key von [CallMeBot](https://www.callmebot.com/blog/free-api-signal-send-messages/) für Signal oder WhatsApp – oder ein Webhook, z. B. in Home Assistant.
