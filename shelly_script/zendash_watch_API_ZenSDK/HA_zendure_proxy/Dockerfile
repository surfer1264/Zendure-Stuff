ARG BUILD_FROM
FROM $BUILD_FROM

# tzdata: der Zeitplan richtet sich nach der Ortszeit (TZ von Home Assistant)
RUN apk add --no-cache python3 tzdata

COPY zendure_proxy.py /zendure_proxy.py
COPY ts_bridge.py /ts_bridge.py
COPY zeitplan.py /zeitplan.py
COPY zendure-dashboard-neu.html /zendure-dashboard-neu.html

COPY run.sh /etc/services.d/zendure_proxy/run
RUN chmod a+x /etc/services.d/zendure_proxy/run