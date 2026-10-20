#!/usr/bin/env bash
cd /
# Im Netz lauschen (Ingress und optional freigegebener Port), keinen
# Browser oeffnen. Die gemerkten Shelly-IPs nach /data - nur das
# uebersteht Updates der App. 172.30.32.2 ist der Ingress-Proxy von
# Home Assistant: Anfragen von dort hat HA bereits angemeldet, der
# Origin (HA-Adresse) wird deshalb nicht geprueft.
export ZENDURE_HELPER_BIND=0.0.0.0
export ZENDURE_HELPER_PORT=8787
export ZENDURE_HELPER_DATA_DIR=/data
export ZENDURE_HELPER_NO_BROWSER=1
export ZENDURE_HELPER_TRUSTED_PEERS=172.30.32.2
export PYTHONUNBUFFERED=1
exec python3 zendure_local_helper.py
