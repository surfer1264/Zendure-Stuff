#!/usr/bin/env bash
cd /
# Einstellungen (Shelly-IP, ThingSpeak-Keys) nach /data - nur das
# uebersteht Updates der App.
export ZENDURE_DATA_DIR=/data
# Bericht der Log-Auswertung (bericht.html) unter /bericht_zendure: Datei hier ablegen
export ZENDURE_BERICHT=/share/zendure/bericht.html
exec python3 zendure_proxy.py -q
