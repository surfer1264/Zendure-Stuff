ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache python3

COPY zendure_local_helper.py /zendure_local_helper.py
COPY zendure-multi-configurator_multilang.html /zendure-multi-configurator_multilang.html

COPY run.sh /etc/services.d/zendure_installer/run
RUN chmod a+x /etc/services.d/zendure_installer/run
