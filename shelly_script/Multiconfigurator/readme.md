# Der Configurator

<a href="https://ko-fi.com/surfer1264">
  <img width="400" alt="image" src="https://github.com/user-attachments/assets/73f858ad-fb66-4f07-8d15-da2ff328c756" />
</a>
---
<img width="800" alt="image" src="https://github.com/user-attachments/assets/8a656b38-bdb9-4c26-84a6-0fec60db02f8" />


Die HTML-Seite auf eine Laufwerk laden und aufrufen

oder

[NEU der Multi-Tool-Konfigurator](https://raw.githack.com/surfer1264/Zendure-Stuff/main/shelly_script/Multiconfigurator/zendure-multi-configurator.html)

Für alle drei Tools wird eine passende Konfiguration erstellt

* Conreoller - die Regelmaschine
* Watchdog - Der Kommunikator von Regel- und AUsnahmesituationen
* ZenDash - Das kleine Dahsboard mit einem Live-Überblick und der Möglichkeit den Controller in seinem Verhalten zu ändern

Alle drei Tools können:

* einezeln und unabhängig voneinander eingesetzt werden und erfordern daher ihre eigene Konfiguration, die aber auch zum Teil redundant ist.

Der Configurator fragt die wesentlichen insbedondere geräteabhängigen Paraneter aber und erzeugt drei Konfiguratoonsfiles, die abgespeichert werden können

**ACHTUNG**

Diese Konfigurationen müssen in den jeweiligen Shelly-Script-Code übernommen werden. Der Shelly Script-Code enthält eine anonyme Konfiguration, die aber ausgetauscht werden muss!

Der Configurator **erzeugt nur die Konfiguration**, übernehmen müsst Ihr sie selbst !!

Bei jedem Code-Update ist dieser Schritt erneut durchzuführen.


Mit folgenden Tools https://github.com/surfer1264/Zendure-Stuff/tree/main/shelly_script/Upload_Controller können diese manuellen Schritte automatisiert werden.


**Neu**

Es können nun auch alte Konfigurationen eingelesen und verändert/erneuert werden. 
Damit kann sichergestellt werden, dass gleiche Konfigurationen auch für andere Scripte wertgleich übernimmen werden.
