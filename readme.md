
![Flow](/Flows_kalibrierung.JPG)

# Herbeiführen einer Kalibrierung und Überwachung der Zellspannung
## Ziel
LiFePO-Akkus müssen regelmäßig kalibriert werden. Dies bedeutet ein Zellabgleich ist herbeizuführen durch das LAden der Akkus auf 100%.
Es gibt in den Zendure Systemen (SF1200/SF2000) aber keinen Mechanismus, der dies automatisch organisiert. 
Erzwungen kann das Laden auf 100% nur (insbesondere im WInter) durch Deaktivieren aller Einspeisemodis.

Mein Ziel war es über eine externe Automatisierung die Ladung auf 100% zu erzwingen, wenn x Tage (x = konfigurierbar) kein Zellableich stattgefunden hat.
Wenn x Tage keine Kalibierung stattfand, wird die Einspeisung über den Wechselrichter unterbunden. Damit findet keine Entladung statt. Jegliche Energie der Panels wird in die Akkus eingespeist. 
Nach Erreichen der 100% Grenze wird die Einspeisung wieder freigegeben.

Da der SOC sehr unzuverlässig ist, wollte ich zusätzlich die minimale Zellspannung überwachen und die Einspeisung stoppen bei Unterschreitung eines definierten Wertes.

## Disclaimer
Dies ist ein experimentelles Projekt. Anwendung auf eigene Gefahr.
Anpassungen werden ggf erforderlich sein bezugnehmend auf Eure Gesamtkonfiguration.

## Meine Konfiguration
 - SF1200
 - AB2000
 - Hoymiles HM8002T
 - Shelly 3EM

## Voraussetzungen
 - eine Home Assistent Installation
 - eine Node-Red HA-Installation (über Addon)
 - eine Hoymiles Integration (https://github.com/suaveolent/ha-hoymiles-wifi)
 - eine Zendure Integration (https://www.justiot.de/smart-home/anleitung-zendure-solarflow-superbase-in-home-assistent-einbinden/)
      - Wichtig ist die Einbindugn der MQTT-Daten von Zendure, dies gelingt mit der vorliegenden Beschreibung 
      - eine sehr gute Beschreibung findet sich auch hier: https://github.com/z-master42/solarflow/wiki/Einbindung-in-Home-Assistant
 - Optional: für das Auslesen der Zellspannungen _minVol_ sind Anpassungen an der mqtt.yaml im HA vorzunehmen.

Für _min_vol_ müssen Anpassungen an der MQTT.yaml vorgenommen werden, um die Daten aus dem MQTT-packdata-String herauszulösen.
Eine MQTT.yaml ist im Codebereich angefügt und enthält die Werte minVol, maxVol, SOC Level und Akkutemperatur. (Danke an bzach)
Ersetzt werden müssen in der MQTT.yaml folgende Strings mit Euren Daten !!!

 - deviceID
 - appKey/deviceID
 - EurePVHubSeriennummer
 
Wenn Ihr obige Voraussetzungen abgearbeitet habt, dann habt Ihr diese Werte bereits schon verfügbar
Nicht vergessen!! eine Zeile in die configuration.yaml im Home Assistent zu setzen:

mqtt: !include mqtt.yaml

## Vorbereitungen im HA
Im HomeAssistent sind zwei Helfervariablen anzulegen:
 - Anlegen einer numerischen Helfervariable (_Letzte Kalibrierung_). Diese Variable gibt die Anzahl der Tage wieder, die vergangen sind, seit der letzten Kalibierung.
 - Anlegen einer Zählvariable - (_counter.akku_voll_). Wenn Akku voll, dann +1.  Ich will damit zählen wie oft der Akku auf 100% geht.  

Folgende Entities werden verwendet:
 - sensor.electriclevel (Akku-Ladezustand, AB2000 SoC)
 - number.wechselrichter_leistungsbegrenzung (Hoymiles WR) (seit letztem Update in 11/24 der hoymiles Integration im HA nicht mehr verfügbar als Entität)
 - button.wechselrichter_ausschalten (Hoymiles WR)
 - button.wechselrichter_ansschalten (Hoymiles WR)
 - minVol (AB2000, MQTT)

## Dokumentation
Die Umsetzung erfolgte in Node-Red.
Sie besteht aus 4 Flows (und ein paar Hilfsflows)

### 1. (drei) Hilfsflows
 1. Der erste Hilfsflow setzt den Helfer _Letzte Kalibrierung_ auf den Wert 0 (eine Art Reset). Dieser Flow kann auch verwendet werden, um jeden anderen Wert einzustellen.
 2. Mit dem zweiten Hilfsflow wird der WR auf AUS gesetzt. (_button.wechselrichter_ausschalten_)
 3. Mit dem dritten Hilfsflow lässt sich der Akku abfragen (_electriclevel_)
 Alle drei Hilfsflows sind experimentell, anpassbar und werden für den Betrieb nicht benötigt.

### 2. Überwachungsflow Akku 100%
Der Flow wird mit Statuswechsel des Akkus auf 100% automatisch angestoßen. daercStaus muss min. 10 Min bestehen.

Ist er = 100% 
 - wird der Helfer _Letzte Kalibierung_ auf "0" (heute) gesetzt.
 - wird die _wechselrichter_leistungsbegrenzung_ auf 100 gesetzt. Dies bedeutet der WR wird vollständig geöffnet
 - wird der Wechselrichter auf AN gesetzt.
 - wird eine Nachricht in die Konsole geschrieben zum Akkustand 100%
 - wird eine Mail versendet zum AKkustand 100%
 - wird der Counter-Helfer _counter.akku_voll_ inkementiert.  Ich will damit zählen wie oft der Akku auf 100% geht.

Dieser Flow hebt damit eine (mögliche) Einspeisesperre auf, die im FLow 4 "Überprüfung kritischer Werte" und FLow 5 "kritische Zellspannung" gesetzt wird.

### 3. Lade und Update des Helfers _Letzte Kalibrierung_
Dieser FLow wird täglich eine Stunde nach Sonnenaufgang ausgeführt.
Bedeutung: Wieviel Tage sind vergangen seit letzter Ladung auf 100%.
Hier wird der Helfer _Letzte Kalibierung_
- um den Wert 1 erhöht

### 4. Überprüfung kritischer Werte
 - wenn die minimale Zellspannung _minVol_ einen Wert unterschreitet (3,1V), oder
 - wenn der Wert der Helfervariable _letzte Kalibierung_ einen bestimmten Wert erreicht (hier im Beispiel den Wert 6), dann 
    - wird die _wechselrichter_leistungsbegrenzung_ auf 0 gesetzt. Dies bedeutet der WR wird vollständig geschlossen.
    - wird der Wechselrichter auf AUS gesetzt
    
Die Vergleichswerte für _minVol_ und _letzte_Kalibierung_ können natürlich in der entsprechenden Node geändert werden.

Die Werte Wechselrichter AN/AUS und _wechselrichter_leistungsbegrenzug_ sind flüchtig. 
Der WR  geht z.B.: in den Standby wenn keine Eingangsspannung anliegt. Die Einstellungen sind daher flüchtig. 
Um die Funktion sicherzustellen wird dieser Flow daher alle 60 Minuten aufgerufen. 
Sind die Eingangsvoraussetzungen unverändert, werden die Einstellungen daher aufgefrischt.

### 5. Alarm, wenn Zellspannung kritisch (unter 3,1V)
Dieser Flow überprüft die Zellspannung minVol.
Liegt die Zellspannung unterhalb 3,1V

- wird die _wechselrichter_leistungsbegrenzung_ auf 0 gesetzt. Dies bedeutet der WR wird vollständig geschlossen.
- wird der Wechselrichter auf AUS gesetzt
- wird eine Nachricht in die Konsole geschrieben
- wird eine Alarm-E-Mail versendet

Der FLow kann auch manuell angesoßen werden, zur Überprüfung.
Dieser Flow setzt voraus, dass die Zellspannungsdaten des AB2000 im HA verfügbar gemacht werden.


## Installation
Importiere den Quellcode des Flows in Deine Node-Red-Instanz und passe die Namen der Entitäten an die NAmensgebung in Deiner HA-Instanz an.
Passe die Parameter nach Deinen Wünschen an.
