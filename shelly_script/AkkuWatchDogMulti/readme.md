# AkkuVolt Watchdog — Multi-Device (zenSDK) — Schnellstart

> ⚠️ Beobachtet nur, greift nicht aktiv ein. Auf eigene Verantwortung nutzen, ordentlich testen.

Überwacht **beliebig viele** lokale zenSDK-Zendure-Hubs (SF800 bis SF2400Pro u. a.) gleichzeitig über einen Shelly Gen2/3/4. Meldet Akku-voll, Unterspannung und Übertemperatur **pro Gerät einzeln**, und schickt zweimal täglich (Sonnenaufgang/-untergang) **eine kompakte Sammel-Nachricht** mit allen Geräten.

Ausführliche Hintergründe (Zendure-Zugangsdaten für ältere Geräte, CallMeBot-Einrichtung, MQTT-Setup) stehen in der Gesamtdoku: **`Shelly-Script-Akkudaten-auslesen.md`**. Dieses Dokument hier ist bewusst kurz gehalten und deckt nur die Multi-Device-Variante ab.

## Voraussetzungen

- Shelly Gen2/3/4 Gerät im selben Netzwerk wie die Zendure-Hubs
- IP-Adresse(n) der Hub(s) (zenSDK-Geräte werden lokal per REST angesprochen, keine Cloud-Zugangsdaten nötig)
- Optional: CallMeBot-API-Key (Signal/WhatsApp) oder eine Webhook-URL (z. B. Home Assistant) — siehe Gesamtdoku Abschnitt 3
- [Dokumentation](https://github.com/surfer1264/Zendure-Stuff/wiki/Shelly-Script-Akkudaten-auslesen)

## Schnellstart

**1. Geräte eintragen** — im `CONFIG`-Block am Scriptanfang:

```js
devices: [
  { ip: "192.168.178.143", label: "SF2400",     enabled: true },
  { ip: "192.168.178.144", label: "Fatamorgana", enabled: true }
],
```

Beliebig viele Einträge, `enabled: false` schaltet ein Gerät ohne Löschen ab.

**2. Nachrichtenkanal wählen:**

```js
signal: {
  enabled: true,
  typ: "SIGNAL",   // "SIGNAL", "WHATSAPP" oder "WEBHOOK"
  phone: "PHONE-STRING",
  apiKey: "YOUR_API_KEY",
  webhookUrl: "http://<IP>:8123/api/webhook/<id>"
},
```

**3. Schwellwerte prüfen** (gelten global für alle Geräte — `vollSchwelle`, `minVoltWarn`, `tempWarn` usw.). Defaults sind konservativ, zum Testen ruhig kurzzeitig enger stellen.

**4. Script in die Shelly Script-Engine laden und starten.** Erste Konsolenausgaben erscheinen nach kurzer Zeit, bei mehreren Geräten etwas verzögert (sequentielle Abfrage).

## Meldung ohne Warten testen

Über die Shelly-RPC-Schnittstelle `Script.Eval` lässt sich jede Meldung sofort auslösen, ohne auf einen echten Grenzwert zu warten. Script-ID steht in der Shelly-UI in der URL beim geöffneten Script.

Unter Windows `cmd.exe` müssen JSON-Strings in doppelten Anführungszeichen stehen (PowerShell ist entspannter mit Quoting):

```
curl -X POST http://<shelly-ip>/rpc/Script.Eval -H "Content-Type: application/json" -d "{\"id\": 1, \"code\": \"sendAstroStatus('sunrise')\"}"
```

Voll-Meldung simulieren (Gerät 0):
```
curl -X POST http://<shelly-ip>/rpc/Script.Eval -H "Content-Type: application/json" -d "{\"id\": 1, \"code\": \"state.devices[0].soc = 100; checkSocFull(0);\"}"
```

Übertemperatur simulieren:
```
curl -X POST http://<shelly-ip>/rpc/Script.Eval -H "Content-Type: application/json" -d "{\"id\": 1, \"code\": \"state.devices[0].hyperTemp = 99; checkHyperTemp(0);\"}"
```

Unterspannung simulieren (legt kurz einen Test-Pack an):
```
curl -X POST http://<shelly-ip>/rpc/Script.Eval -H "Content-Type: application/json" -d "{\"id\": 1, \"code\": \"state.devices[0].packs['TEST01'] = {minV: 2.5}; checkPackVoltage(0, 'TEST01');\"}"
```

Danach jeweils das zugehörige `*MsgSent`-Flag zurücksetzen (sonst blockiert es die nächste echte Meldung), oder das Script einmal neu starten — dann ist der komplette State wieder sauber.

## Typische Stolperfallen

- **Leerer Webhook-Antwort-Body im Debug-Log:** normal bei Home Assistant, das antwortet by design ohne Inhalt. Nur der HTTP-Statuscode zählt (sollte 200 sein).
- **`????` statt Geräte-Kennung in der Sammel-Nachricht:** Die Seriennummer wird erst nach dem ersten erfolgreichen Poll-Zyklus bekannt — kurz warten, dann erneut testen.
- **Persistente Anzeige in Home Assistant statt flüchtiger Push:** `persistent_notification.create` mit fester `notification_id` statt (oder zusätzlich zu) `notify.notify` verwenden.

Für alles Weitere (Zendure-Zugangsdaten für SF1200/2000/Hyper, CallMeBot-Einrichtung im Detail, Bilderserie zum Script-Upload) → **Gesamtdoku `Shelly-Script-Akkudaten-auslesen.md`**.
