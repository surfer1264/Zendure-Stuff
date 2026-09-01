# Upload Controller to Shelly 

Das deploy Script ersetzt die generische Konfig mit deiner konkreten Config, lädt den Controller auf den Shelly und startet den Controller. Update erfolgt nach gleichem Muster.

* Voraussetzung ist eine Python Umgebung
	* gibt es für jede Umgebung, einfach nach installieren

**Nur geeignet für den Upload auf ein Shelly-Device**

* Lade die drei Dateien in ein Verzeichnis
* Lade den Shelly Multi-Device-Controller in das gleiche Verzeichnis
* Bennene den Controller zerooutput_multi_kvs_mini.js
* Stelle sicher, dass Deine myconfig.js im gleichen Verzeichnis liegt
    * die myconfig.js erzeuge Dir zuvor aus dem Webkonfigurator
* Editiere die deploy.cmd
    * Trage die IP-Adresse des Shelly-Smartmeters ein
* Fertig
* deploy.cmd starten 
    * das Script wird in den Shelly geladen und gestartet
    * Updateprozess erfolgt analog
    * deploy stoppt das Script, aktualsiiert und startet
