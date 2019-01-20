FROM fedora:29

LABEL maintainer="Filip Valder <fivaldi@redhat.com>"

COPY verified-requirements.txt /tmp/verified-requirements.txt

RUN cd /tmp \
    && dnf update -y \
    && dnf install -y \
       nginx \
       python3-pip \
       python3-flask \
       python3-prometheus_client \
       python3-zmq \
       uwsgi \
       uwsgi-plugin-python3 \
    && dnf clean all \
    && pip3 install --require-hashes -r verified-requirements.txt

COPY moksha-monitor-exporter.ini /etc/nginx/moksha-monitor-exporter.ini

COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 8080

CMD ["bash", "-c", "uwsgi --ini /etc/nginx/moksha-monitor-exporter.ini & nginx -c /etc/nginx/nginx.conf"]
