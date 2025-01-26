
![Flow](/Flows_kalibrierung.JPG)

# Herbeiführen einer Kalibrierung und Überwachung der Zellspannung
## Ziel
LiFePO-Akkus müssen regelmäßig kalibriert werden. Dies bedeutet ein Zellabgleich ist herbeizuführen durch das Laden der Akkus auf 100%.
Es gibt in den Zendure Systemen (SF1200/SF2000) aber keinen Mechanismus, der dies automatisch organisiert. 
Erzwungen kann das Laden auf 100% nur (insbesondere im Winter) durch Deaktivieren aller Einspeisemodis.

Mein Ziel war es über eine externe Automatisierung die Ladung auf 100% zu erzwingen, wenn x Tage (x = konfigurierbar) kein Zellableich stattgefunden hat.
Wenn x Tage keine Kalibierung stattfand, wird die Einspeisung über den Wechselrichter unterbunden. Damit findet keine Entladung statt. Jegliche Energie der Panels wird in die Akkus eingespeist. 
Nach Erreichen der 100% Grenze wird die Einspeisung wieder freigegeben.

Mittlerweile hat sich mein Ansatz leicht gewandelt. **Die Zellspannung ist der entscheidende Faktor.** Mein Akku konnte im Dezember 2024 26 Tage ohne das Aufladen auf 100% überleben.
Die untere Zellspannung über 3V zu halten ist zielführender.

Die folgende Überwachung und Steuerung orintiert sich daher ehr an der unteren Zellspannung, als der zurückliegenden Dauer der letzten Kalibrierung auf 100%.

## Disclaimer
Dies ist ein experimentelles Projekt. Anwendung auf eigene Gefahr.
Anpassungen werden ggf erforderlich sein bezugnehmend auf Eure Gesamtkonfiguration.

## Meine Konfiguration
 - SF1200
 - AB2000
 - Hoymiles HMS8002T
 - Shelly 3EM
 - HomeAssistent-HW: Home Assistent Green (https://www.home-assistant.io/green/)

## Voraussetzungen
 - eine Home Assistent Installation
 - eine Node-Red HA-Installation (über Addon)
 - eine Hoymiles Integration (https://github.com/suaveolent/ha-hoymiles-wifi)
 - eine Zendure Integration (https://www.justiot.de/smart-home/anleitung-zendure-solarflow-superbase-in-home-assistent-einbinden/)
      - hier ist beschrieben wie man sich einen Zugang zu MQTT-Daten generiert und diesen dann im Home Assistent einbindet.
      - eine vertiefende Beschreibung findet sich hier: https://github.com/z-master42/solarflow/wiki/Einbindung-in-Home-Assistant
 - Für das Benutzen der Zellspannungen _minVol_ sind Anpassungen an der mqtt.yaml im HA vorzunehmen.
 - ein anpassbares Beispiel findet sich hier: https://pastebin.com/4Qf6VbrU (diese habe ich als Vorlage verwendet)

Die MQTT_Daten liefern die _min_vol_ nicht als Einzelwert sondern in der _packdata_-Entität zusammen mit weiteren Werten. 
Für _min_vol_ müssen Anpassungen also an der MQTT.yaml vorgenommen werden, um die Daten aus dem MQTT-packdata-String herauszulösen.
Eine MQTT.yaml ist im Codebereich angefügt und enthält die Werte minVol, maxVol, SOC Level und Akkutemperatur. (Danke an bzach)
Ersetzt werden müssen in der MQTT.yaml folgende Strings mit Euren Daten !!!

 - deviceID
 - appKey/deviceID
 - EurePVHubSeriennummer
 
Wenn Ihr obige Voraussetzungen abgearbeitet habt, dann habt Ihr diese Werte bereits schon verfügbar.

Nicht vergessen!! eine Zeile in die configuration.yaml im Home Assistent zu setzen:

`mqtt: !include mqtt.yaml`

## Vorbereitungen im HA
Um meine Flows verwenden zu können sind im HomeAssistent folgende Helfervariablen anzulegen (Bereich Geräte und Dienste):
 - Anlegen einer numerischen Helfervariable (_Letzte Kalibrierung_). Diese Variable gibt die Anzahl der Tage wieder, die vergangen sind, seit der letzten Kalibierung.
 - Anlegen einer Helfer-Zählvariable - (_counter.akku_voll_). Wenn Akku voll, dann +1.  Ich will damit zählen wie oft der Akku auf 100% geht.  
 - Anlegen einer Helfer-Boolean-Variable (Button) _ladung_erreicht_ . Am Tag der 100% Ladung wird die Variable auf TRUE gesetzt ansonsten FALSE.
 - Anlegen einer Helfer-Boolean-Variable (Button) _batterie_kritisch_. Die Variable wird auf _True_ gesetzt, wenn minVol unter einen Schwellwert fällt.

Folgende Entities werden verwendet:
 - sensor.electriclevel (Akku-Ladezustand, AB2000 SoC)
 - button.wechselrichter_ausschalten (Hoymiles WR)
 - button.wechselrichter_ansschalten (Hoymiles WR)
 - minVol (AB2000, MQTT)

## Dokumentation
Die Umsetzung erfolgte in Node-Red.


### 1. Hilfsflows
 1. Der erste Hilfsflow setzt den Helfer _Letzte Kalibrierung_ auf den Wert 0 (eine Art Reset). Dieser Flow kann auch verwendet werden, um jeden anderen Wert einzustellen.
 2. Mit dem zweiten Hilfsflow wird der WR auf AUS gesetzt. (_button.wechselrichter_ausschalten_)
 3. Mit dem dritten Hilfsflow lässt sich der Akku abfragen (_electriclevel_)
 Alle drei **Hilfsflows** sind experimentell, anpassbar und werden für den Betrieb **nicht** benötigt.

### 2. Überwachungsflow Akku 100%
Der Flow wird mit Statuswechsel des Akkus auf 100% automatisch angestoßen.

Ist er = 100% 
 - wird der Helfer _Letzte Kalibierung_ auf "0" (heute) gesetzt.
 - wird der Helfer _ladung_erreicht_ auf TRUE gesetzt.
 - wird der Wechselrichter auf AN gesetzt.
 - wird eine Nachricht in die Konsole geschrieben zum Akkustand 100%
 - wird der Kommunikationsflow aufgerufen
 - wird der Counter-Helfer _counter.akku_voll_ inkementiert. Ich will damit zählen wie oft der Akku auf 100% geht.

Dieser Flow hebt damit eine (mögliche) Einspeisesperre auf, die im FLow 5 "Überprüfung kritischer Werte" und FLow 6 "kritische Zellspannung" gesetzt wird.

### 3. Lade und Update des Helfers _Letzte Kalibrierung_
Dieser FLow wird täglich eine Stunde nach Sonnenaufgang ausgeführt.
Bedeutung: Wieviel Tage sind vergangen seit letzter Ladung auf 100%?
Hier wird der Helfer _Letzte Kalibierung_
- um den Wert 1 erhöht
- der Kommunikationsflow wird aufgerufen

### 4. Kommunikationsflow
In diesem FLow werden folgende Daten zu einer Nachricht zusammengefasst:
 -  _minVol_
 -  _akku_voll_
 -  _electriclevel_
 -  _letzte_Kalibierung_
 -  _ladung_erreicht_

 Es wird eine Mal aufbereitet und versendet.
 
 Es wird eine Nachricht in die Konsole geschrieben.

 Es wird ein Datensatz (CSV-Datei) erzeugt im Verzeichnis: /addon_configs/a0d7b954_nodered zur externen Weiterverarbeitung.

### 5. Alarm, wenn Zellspannung kritisch (unter 3,1V)

Dieser Flow überprüft die Zellspannung minVol.
Liegt die Zellspannung unterhalb 3,1V
 -  wird der Wechselrichter auf AUS gesetzt
 -  wird _batterie_kritisch_ auf TRUE gesetzt
 -  wird eine Nachricht in die Konsole geschrieben
 -  der Kommunikationsflow aufgerufen

Dieser Flow setzt voraus, dass die Zellspannungsdaten des AB2000 im HA verfügbar gemacht wurden !! (siehe Vorbereitungen)

Dieser Flow wurde bei mir noch nie ausgelöst!

### 6. Überprüfung kritischer Werte

Der Wert Wechselrichter AN/AUS scheint flüchtig zu sein.
Der WR  geht z.B. in den Standby wenn keine Eingangsspannung anliegt. Die Einstellungen sind daher flüchtig. 

Um die Funktion sicherzustellen, wird dieser Flow daher alle 60 Minuten aufgerufen und überprüft die Einstellungen. Sind die Eingangsvoraussetzungen unverändert, 
werden die Einstellungen daher aufgefrischt.

Überprüft werden:

 -  die minimale Zellspannung _minVol_ (Unterschreitung z.B: 3,1V)
 -  der _electriclevel_ (SOC Unterschreitet z.B. 21%),
 -  _letzte_kalibrierung_ (z.B. länger her, als 30 Tage)
 -  _batterie_kritisch_ (Wert True)

Die Überprüfung ist ODER verknüpft. Trifft einer der Bedingungen zu, wird
 -   der Wechselrichter auf AUS gesetzt
    
Alle Vergleichswerte für _minVol_ und _letzte_Kalibierung_ _electric_Level_ können natürlich in der entsprechenden function-Node geändert werden.

Aktuell nutze ich nur _batterie_kritisch_== _true_ ODER _letzte_kalibrierung_ > 30 Tage zur Überwachung.

Dieser Flow wurde bei mir noch nie ausgelöst!


## Installation
Importiere den Quellcode des Flows in Deine Node-Red-Instanz und passe die Namen der Entitäten an die NAmensgebung in Deiner HA-Instanz an.
Passe die Parameter nach Deinen Wünschen an.
