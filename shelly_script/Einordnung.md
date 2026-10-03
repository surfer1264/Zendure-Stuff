# Vergleich: ioBroker-Adapter (Nograx) – Z-HA (ex Fireson)– SMDC (surfer1264(2nd) )

## Technik und Funktionen

| Aspekt | ioBroker-Adapter (nograx) | Z-HA (fireson) | SMDC (surfer1264) |
|---|---|---|---|
| Rolle | Schnittstelle | Integration mit Regler | Regler + Live-Dashboard + Nachrichtenmodul |
| Läuft auf | ioBroker-Server | HA-Server | Controller-Shelly (Gen2+), Dashboard-Shelly (Gen2+) |
| Regelung eingebaut | nein | ja (Zendure Manager) | ja |
| Skalierung  | nein, selber bauen | ja  | ja |
| Geräte | alle (zenSDK, Legacy via MQTT) | alle (zenSDK, Legacy via MQTT) | nur zenSDK-Geräte |
| Smartmeter | beliebig (Skript) | jeder HA-Sensor | beliebig, alle mit REST-Schnittstelle, Shelly Pro3EM, Shelly 3EM;  lokal/remote oder HTTP-JSON (z. B. 3CT, Tasmota,  Ecotracker) |
| Sollwert | frei im Skript | fest auf 0 | einstellbar, live per KVS |
| Hysterese | frei im Skript | fest im Code | einstellbar |
| Mehrgeräte-Logik | selbst bauen | ja, gestufet Zu- und Abschaltung, SoC Balancing  | Concentrate/Spread, Water-Fill, Sticky-Device mit SoC-Marge, SoC Balancing |
| Effizienz | selbst bauen | grundsätzlich ja, aber schlechte Voreinstellung und nicht konfigurierbar, erfordert KnowHow im Code | auf Effizenz ausgerichtet, parametrisierbar|
| Stellschrauben | unbegrenzt | wenige | viele (Hysterese, Dämpfung, Start-/Stopp-Schwellen, Richtungs-Cooldown) |
| Bypass / Einspeisesperre | selbst bauen | intern | gridReverse dynamisch mit Hysterese, Bypass-Überschusskorrektur, einmaliges geräteübergreifendes Bypass-Management |
| Tarif / Prognose | im Skript | über Automationen in HA bauen | über externe Automationen von außen über KVS Schnittstelle |
| Benachrichtigung | ioBroker | HA | eingebaut (Webhook, Signal, WhatsApp) |
| Schnittstellen | ioBroker | HA | über Key Value Store (KVS) ist Regelung beeinflussbar  |
| Dashboard | nein, selber bauen | nein, selber bauen | Live Dashboard verfügbar  |
| Statistik | ioBroker Datenpunkte und Historie | HA Datenpunkte, Recorder und Historie | nur extern möglich: Thingboard oder Thingspeak als mächtige Data-Analytics Plattform sind angebunden  |
| Batterieschutz | Funktion des Adapters | selber Bauen | integriert über Watchdog  |  
| Voraussetzungen | lauffähige iobroker Plattform| lauffähige HA Plattform | zwei Shelly Devices, sonst nichts| 
| Installation | ioBroker typisch über Adaptereinstellseite| über HACS installierbar | Installer für Windows und Apple mit leichtgewichtigen Konfig- und Update-Service, in 10 Minuten am Start, ontop Installer für Dashboard, flexibel betreibbar auf NAS, HA, PI oder PC | 
| Konfigurierbarkeit | Adapter Einstiegsseite | KOnfigurationsdialog  | Configurator-Assistent mit vorgeschlagenen Regelparanmetern | 
| Einstiegshürde | mittel (Regelung muss selbst gebaut werden), oder Nutzung bekannter Community-Projekte,  zusätzlicher Plattformbetrieb| mittel bis hoch (komplexe Integration, knappe und veraltete Doku)  zusätzlicher Plattformbetrieb | niedrig bis mittel, durch den Configurations-Assistenten sehr leichtgewichtig | 
|Support | aktive Weiterentwicklung | Weiterentwicklung in letzter Zeit stark verlangsamt | schnelle Weiterentwicklung und aktiver Usersupport  |
|Dokumentation | Die Doku besteht im Wesentlichen aus dem README, das inhaltlich solide ist (Modi, Geräte, Offline-Betrieb, Hinweis auf setDeviceAutomationInOutLimit). Das GitHub-Wiki ist angelegt, enthält aber nur eine Begrüßungsseite. Das eigentliche Praxiswissen steckt im sehr langen Thread im ioBroker-Forum. | Readme mit 9 Seiten, um Drittquellen erweitert, leider alles sehr veraltet | Die Doku ist am umfangreichsten. Jede Komponente hat ein eigenes README (24 Markdown-Dateien im Repo), dazu kommen API.md, Anleitungen für Dashboard, ThingSpeak, ThingsBoard und Script-Poller. Im Wiki gibt es eigene SMDC-Seiten wie Getting Started, Benutzerdokumentation, Gesamtdokumentation, Prinzipien und Development Inside. Die Configurator-Anleitung liegt auch auf Englisch und Französisch vor.  |
| Fazit | Baukasten im Server, keine Regelung  | fertige Regelung im Server, aber leider nicht konfigurierbar| fertige, transparent parametrierbare Regelung im Shelly Device, extrem einfacher Einstieg |


