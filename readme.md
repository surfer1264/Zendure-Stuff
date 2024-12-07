
![Flow](/Flows_kalibrierung.JPG)

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
- eine Home Assistent Installation
- eine Node-Red HA-Installation (über Addon)
- eine Hoymiles Integration (https://github.com/suaveolent/ha-hoymiles-wifi)
- eine Zendure Integration (https://www.justiot.de/smart-home/anleitung-zendure-solarflow-superbase-in-home-assistent-einbinden/)
    - Wichtig ist die Einbindugn der MQTT-Daten von Zendure, dies gelingt mit der vorliegenden Beschreibung 
    - eine sehr gute Beschreibung findet sich auch hier: https://github.com/z-master42/solarflow/wiki/Einbindung-in-Home-Assistant

## Vorbereitungen
- Anlegen einer numerischen Helfervariable (_Letzte Kalibrierung_). Diese Variable gibt die Anzahl der Tage wieder, die vergangen sind, seit der letzten Kalibierung.
Verwendung findet 
- Anlegen einer Zählvariable - (_counter.akku_voll_). Wenn Akku voll, dann +1.   

Folgende Sensoren werden verwendet:
- sensor.electriclevel (Akku-Ladezustand, AB2000 SoC)
- number.wechselrichter_leistungsbegrenzung (Hoymiles WR) 

## Dokumentation
Die Umsetzung erfolgte in Node-Red.
Sie besteht aus 5 Flows

### 1. (drei) Hilfsflows
Der erste Hilfsflow setzt den Helfer _Letzte Kalibrierung_ auf den Wert 0 (eine Art Reset). Dieser Flow kann auch verwendet werden, um jeden anderen Wert einzustellen.
Mit dem zweiten Hilfsflow wird der WR auf AUS gesetzt. (_button.wechselrichter_ausschalten_)
Mit dem dritten Hilfsflow lässt sich der Akku abfragen (electriclevel)
Alle drei Hilfsflows sind experimentell, anpassbar.

### 2. Überwachungsflow Akku 100%
Hier wird der SoC des Akkus abgefragt. (electricevel)
Ist er kleiner als 100%
- endet der Flow.
Ist er = 100% 
- wird der Helfer _Letzte Kalibierung_ auf "0" (heute) gesetzt.
- wird die _wechselrichter_leistungsbegrenzung_ auf 100 gesetzt. Dies bedeutet der WR wird vollständig geöffnet
- wird der Wechselrichter auf AN gesetzt.
- wird eine Nachricht in die Konsole geschrieben zum Akkustand 100%
- wird der Counter-Helfer _counter.akku_voll_ inkementiert.

### 3. Überwachungsflow Zeit seit letzter Kalibrierung
Dieser FLow wird täglich um 09:15 einmalig ausgeführt.
Hier wird der Helfer _Letzte Kalibierung_
- um den Wert 1 erhöht
- wenn der Wert der Helfervariable einen bestimmten Wert erreicht (hier im Beispiel den Wert 6), dann 
    - wird die _wechselrichter_leistungsbegrenzung_ auf 0 gesetzt. Dies bedeutet der WR wird vollständig geschlossen.
    - wird der Wechselrichter auf AUS gesetzt
    - wird eine Nachricht in die Konsole geschrieben

Der Vergleichswert nach wieviel Tagen der Ladezyklus erzwungen wird, kann natürlich in der entsprechenden Node geändert werden.

Die Werte Wechselrichter AN/AUS und _wechselrichter_leistungsbegrenzug_ sind flüchtig. Der WR  geht in den Standby wenn keine Eingangsspannung anliegt. Die Einstellungen sind daher flüchtig
Alle 60 Minuten werden die Einstellungen daher aufgefrischt.

### 4. Alarm, wenn Zellspannung unter 3,1V
Dieser Flow überprüft die Zellspannung minVol.
Liegt die Zellspannung unterhalb 3,1V
- wird die _wechselrichter_leistungsbegrenzung_ auf 0 gesetzt. Dies bedeutet der WR wird vollständig geschlossen.
- wird der Wechselrichter auf AUS gesetzt
- wird eine Nachricht in die Konsole geschrieben
- wird eine Alarm-EMail versendet

Der FLow kann auch manuell angesoßen werden, zur Überprüfung.
Dieser Flow setzt voraus, dass die Zellspannungsdaten des AB2000 im HA verfügbar gemacht werden.
Dies ist durch die obign MQTT Integrationen nicht automatisch der Fall.
Es müssen Anpssungen an der MQTT.yaml vorgenommen werden, um die Daten aus dem MQTT-packdata-String herauszulösen.

## Installation
Importiere den Quellcode des Flows in Deine Node-Red-Instanz und passe die Namen der Entitäten an die NAmensgebung in Deiner HA-Instanz an.
Passe die Parameter nach Deinen Wünschen an.
