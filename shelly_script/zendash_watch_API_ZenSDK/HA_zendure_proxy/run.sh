#!/usr/bin/env bash
cd /
# Einstellungen (Shelly-IP, ThingSpeak-Keys) nach /data - nur das
# uebersteht Updates der App.
export ZENDURE_DATA_DIR=/data
exec python3 zendure_proxy.py -q
