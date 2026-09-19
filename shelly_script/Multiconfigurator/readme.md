# Der Configurator

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>

---

<img width="800" alt="image" src="https://github.com/user-attachments/assets/8a656b38-bdb9-4c26-84a6-0fec60db02f8" />


Die HTML-Seite auf ein Laufwerk laden und aufrufen

oder

[NEU der Multi-Tool-Konfigurator](https://raw.githack.com/surfer1264/Zendure-Stuff/main/shelly_script/Multiconfigurator/zendure-multi-configurator.html)

[NEU Multi Language Multi-Tool-Konfigurator](https://raw.githack.com/surfer1264/Zendure-Stuff/main/shelly_script/Multiconfigurator/zendure-multi-configurator_multilang.html)

Für alle drei Tools wird in einem einzigen Durchgang eine passende Konfiguration erstellt:

* **Controller** – die Regelmaschine
* **Watchdog** – meldet sich bei Regel- und Ausnahmesituationen
* **ZenDash** – das kleine Dashboard mit Live-Überblick und der Möglichkeit, das Verhalten des Controllers zu ändern

Alle drei Tools können einzeln und unabhängig voneinander eingesetzt werden. Jedes braucht dafür seine eigene Konfiguration – vieles darin ist aber gleich (z. B. die Geräteliste). Der Configurator fragt die wichtigsten, vor allem geräteabhängigen Angaben deshalb nur einmal ab und erstellt daraus passend für jedes ausgewählte Tool eine eigene Konfiguration.

## So kommt die Konfiguration in dein Script

Am Ende bietet dir der Configurator für jedes Tool zwei Wege an:

**Der einfache Weg**

Ein Klick auf den Button lädt das passende Original-Script direkt herunter, trägt deine Konfiguration automatisch darin ein und bietet dir das fertige, sofort einsatzbereite Script zum Speichern an. Du musst es danach nur noch auf deinen Shelly hochladen – fertig. Dafür brauchst du kurz eine Internetverbindung.

**Der manuelle Weg**

Falls du das Script bereits selbst angepasst hast oder aus anderen Gründen lieber von Hand arbeiten möchtest: Der Configurator zeigt dir die Konfiguration auch zum Kopieren an bzw. als kleine Datei zum Speichern. Diese musst du dann selbst in dein Shelly-Script einfügen und die dort vorhandene (Platzhalter-)Konfiguration damit ersetzen.

**Wichtig:** Bei jedem Update eines Shelly-Scripts sollte dieser Schritt wiederholt werden, damit deine Konfiguration erhalten bleibt.

Mit folgenden Tools https://github.com/surfer1264/Zendure-Stuff/tree/main/shelly_script/Upload_Controller lässt sich auch das Hochladen auf den Shelly automatisieren.

## Bestehende Konfiguration ändern

Du kannst eine schon vorhandene Konfiguration wieder in den Configurator einlesen, statt alles neu einzugeben. So lassen sich vorhandene Einstellungen bequem aktualisieren – und gleiche Angaben (z. B. die Geräteliste) bleiben automatisch über alle drei Tools hinweg konsistent.
