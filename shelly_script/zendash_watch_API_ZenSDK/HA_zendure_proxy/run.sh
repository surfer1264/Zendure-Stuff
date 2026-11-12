#!/usr/bin/with-contenv bash
# with-contenv: s6 startet Dienste ohne die Umgebung des Containers. Erst so
# kommt TZ (Zeitzone von Home Assistant) bei Python an - sonst laeuft der
# Proxy in UTC und der Zeitplan schaltet zur falschen Uhrzeit.
cd /
# Einstellungen (Shelly-IP, ThingSpeak-Keys) nach /data - nur das
# uebersteht Updates der App.
export ZENDURE_DATA_DIR=/data
# Bericht der Log-Auswertung (bericht.html) unter /bericht_zendure: Datei hier ablegen
export ZENDURE_BERICHT=/share/zendure/bericht.html
exec python3 zendure_proxy.py -q
