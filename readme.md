
![FLow](/Flows_kalibrierung.JPG)

# Herbeiführen einer Kalibrierung mit Zendure
## Ziel
LiFePO-Akkus müssen regelmäßig kalibriert werden. Dies bedeutet ein Zellabgleich ist herbeizuführen durch das Laden der Akkus auf 100%.
Es gibt in den Zendure Systemen (SF1200/SF2000) aber keinen Mechanismus, der dies automatisch und zeitgesteuert organisiert. 
Erzwungen kann das Laden auf 100% nur (insbesondere im Winter) durch Deaktivieren aller Einspeisemodis, also manuelle Eingriffe.

Mein Ziel war es, über eine externe Automatisierung die Ladung auf 100% zu erzwingen, wenn x Tage (x = konfigurierbar) kein Zellableich stattgefunden hat.
Wenn x Tage keine Kalibierung stattfand, wird die Einspeisung über den Wechselrichter unterbunden. Damit findet keine Entladung statt. Jegliche Energie der Panels wird in die Akkus eingespeist. 
Nach Erreichen der 100% Grenze wird die Einspeisung wieder freigegeben.

Die Lösung ist dabei, Daten des Akkus auszuwerten und dann den Wechselrichter anzusteuern. Beim Hoymiles Wechserichter kann über einen Parameter die Ausgangsleistung zw. 0% und 100% gesteuert werden.
Die Parameter des Hubs lassen sich über diesen Weg nicht beeinflussen. 


## Meine Konfiguration
 - Zendure SF1200
 - Zendure AB2000
 - Hoymiles HM8002T mit DTU WLite-S
 - Shelly 3EM (hierfür nicht erforderlich)

## Voraussetzungen
- eine Home Assistent Installation (https://www.home-assistant.io/installation/)
- eine Node-Red HA-Installation (über Addon)
- eine Hoymiles Integration (https://github.com/suaveolent/ha-hoymiles-wifi)
- eine Zendure Integration (https://www.justiot.de/smart-home/anleitung-zendure-solarflow-superbase-in-home-assistent-einbinden/)

## Vorbereitungen
- Anlegen einer numerischen Helfervariable (_Letzte Kalibrierung_). Diese Variable gibt die Anzahl der Tage wieder, die vergangen sind, seit der letzten Kalibierung.
- Verwendung finden folgende Entitäten:
  - sensor.electriclevel (Akku-Ladezustand, SoC) (Zendure Akku)
  - number.wechselrichter_leistungsbegrenzung (Hoymiles WR)

## Dokumentation
Die Umsetzung erfolgte in Node-Red.
Sie besteht aus drei Flows.

### Disclamier
Ich übernehme keine Garantie für das korrekte Funktionieren. Die unten aufgeführten Parameter sind in den Nodes anzupassen. Die Flows sollen einen Impuls zur externen Überwachung des Ladezustandes samt Sicherstellung eines regelmäßigen Ladzyklus geben.

### 1. Hilfsflow
Dies ist ein (nur) Hilfsflow, der den Helfer _Letzte Kalibrierung_ auf den Wert 0 setzt. Dieser Flow kann auch verwendet werden, um jeden anderen Wert einzustellen.

### 2. Überwachungsflow Akku 100%
Dieser FLow wird täglich zw. 10:00 und 19:00 ausgeführt (Alle 20 Minuten). Diese Zeit kann angepasst werden im ersten Node.
Hier wird der SoC des Akkus abgefragt. (electricevel)
Ist er kleiner als 100%:
- endet der Flow.

Ist er = 100%:
- wird der Helfer _Letzte Kalibierung_ auf "0" (heute) gesetzt.
- wird die _wechselrichter_leistungsbegrenzung_ auf 100 gesetzt. Dies bedeutet der WR wird vollständig geöffnet
- wird eine Nachricht in die Konsole geschrieben zum Akkustand 100%

### 3. Überwachungsflow Zeit seit _letzter Kalibrierung_
Dieser Flow wird täglich um 09:00 einmalig ausgeführt. Diese Zeit kann angepasst werden im ersten Node.
Hier wird der Helfer _Letzte Kalibierung_
- um den Wert 1 erhöht (z.B. steht dann ein Wert 5 für: seit 5 Tagen fand keine Kalibrierung statt)
- wenn der Wert der Helfervariable einen bestimmten Wert erreicht (hier im Beispiel den Wert 7), dann 
  - wird die _wechselrichter_leistungsbegrenzung_ auf 0 gesetzt. Dies bedeutet der WR wird vollständig geschlossen.
  - wird eine Nachricht in die Konsole geschrieben

Der Vergleichswert nach wieviel Tagen der Ladezyklus erzwungen wird, kann natürlich in der entsprechenden Node geändert werden.

## Installation
Importiere den Quellcode des Flows in Deine Node-Red-Instanz und passe die Namen der Entitäten an die NAmensgebung in Deiner HA-Instanz an.
Passe die Parameter nach Deinen Wünschen an.


