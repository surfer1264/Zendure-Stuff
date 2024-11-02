# Herbeiführen einer Kalibrierung Zendure
## Ziel
LiFePO-Akkus müssen regelmäßig kalibriert werden. Dies bedeutet ein Zellabgleich ist herbeizuführen durch das Laden der Akkus auf 100%.
Es gibt in den Zendure Systemen (SF1200/SF2000) aber keinen Mechanismus, der dies automatisch organisiert. 
Erzwungen kann das Laden auf 100% nur (insbesondere im Winter) durch Deaktivieren aller Einspeisemodis.

Mein Ziel war es, über eine externe Automatisierung die Ladung auf 100% zu erzwingen, wenn x Tage (x = konfigurierbar) kein Zellableich stattgefunden hat.
Wenn x Tage keine Kalibierung stattfand, wird die Einspeisung über den Wechselrichter unterbunden. Damit findet keine Entladung statt. Jegliche Energie der Panels wird in die Akkus eingespeist. 
Nach Erreichen der 100% Grenze wird die Einspeisung wieder freigegeben.

## Meine Konfiguration
 - Zendure SF1200
 - Zendure AB2000
 - Hoymiles HM8002T
 - Shelly 3EM

## Voraussetzungen
- eine Home Assistent Installation
- eine Node-Red HA-Installation (über Addon)
- eine Hoymiles Integration (https://github.com/suaveolent/ha-hoymiles-wifi)
- eine Zendure Integration (https://www.justiot.de/smart-home/anleitung-zendure-solarflow-superbase-in-home-assistent-einbinden/)

## Vorbereitungen
- Anlegen einer numerischen Helfervariable (_Letzte Kalibrierung_). Diese Variable gibt die Anzahl der Tage wieder, die vergangen sind, seit der letzten Kalibierung.
- Verwendung findet
  - sensor.electriclevel (Akku-Ladezustand, SoC) (Zendure Akku)
  - number.wechselrichter_leistungsbegrenzung (Hoymiles WR)

## Dokumentation
Die Umsetzung erfolgte in Node-Red.
Sie besteht aus drei Flows.

### Disclamier
Ich übernehme keine Garantie für das korrekte Funktionieren. Die unten aufgeführten Parameter sind in den Nodes anzupassen.

### 1. Hilfsflow
Dies ist ein Hilfsflow, der den Helfer _Letzte Kalibrierung_ auf den Wert 0 setzt. Dieser Flow kann auch verwndet werden, um jeden anderen Wert einzustellen.

### 2. Überwachungsflow Akku 100%
Dieser FLow wird täglich zw. 10:00 und 19:00 ausgeführt (Alle 20 Minuten)
Hier wird der SoC des Akkus abgefragt. (electricevel)
Ist er kleiner als 100%
- endet der Flow.
Ist er = 100% 
- wird der Helfer _Letzte Kalibierung_ auf "0" (heute) gesetzt.
- wird die _wechselrichter_leistungsbegrenzung_ auf 100 gesetzt. Dies bedeutet der WR wird vollständig geöffnet
- wird eine Nachricht in die Konsole geschrieben zum Akkustand 100%

### 3. Überwachungsflow Zeit seit letzter Kalibrierung
Dieser FLow wird täglich um 09:00 einmalig ausgeführt.
Hier wird der Helfer Letzte Kalibierung
- um den Wert 1 erhöht
- wenn der Wert der Helfervariable einen bestimmten Wert erreicht (hier im Beispiel den Wert 7), dann 
  - wird die _wechselrichter_leistungsbegrenzung_ auf 0 gesetzt. Dies bedeutet der WR wird vollständig geschlossen.
  - wird eine Nachricht in die Konsole geschrieben




