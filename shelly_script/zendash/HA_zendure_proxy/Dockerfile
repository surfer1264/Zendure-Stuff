ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache python3

COPY zendure_proxy.py /zendure_proxy.py
COPY zendure-dashboard.html /zendure-dashboard.html

COPY run.sh /etc/services.d/zendure_proxy/run
RUN chmod a+x /etc/services.d/zendure_proxy/run