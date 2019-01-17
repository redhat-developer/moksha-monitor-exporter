FROM fedora:29

LABEL maintainer="Filip Valder <fivaldi@redhat.com>"

COPY verified-requirements.txt /tmp/verified-requirements.txt

RUN cd /tmp \
    && dnf update -y \
    && dnf install -y \
       python3-pip \
       python3-flask \
       python3-prometheus_client \
       python3-zmq \
       uwsgi \
       uwsgi-plugin-python3 \
    && dnf clean all \
    && pip3 install --require-hashes -r verified-requirements.txt

EXPOSE 8080

CMD ["bash", "-c", "uwsgi --plugins python3 --http-socket 0.0.0.0:8080 --manage-script-name --mount /=moksha_monitor_exporter.moksha_monitor_exporter:app"]
