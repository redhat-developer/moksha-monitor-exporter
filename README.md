# moksha-monitor-exporter
A nanoservice written in Python providing Prometheus export(s) from moksha.monitoring.socket data.

## I'm not lazy at all

```
$ git clone git@github.com:redhat-developer/moksha-monitor-exporter.git
$ # or https://github.com/redhat-developer/moksha-monitor-exporter.git
```

## I am a bit lazy

```
$ pip3 install moksha-monitor-exporter
```

## I am super-lazy

```
$ docker pull quay.io/factory2/moksha-monitor-exporter
$ docker run -p 8080:8080/tcp quay.io/factory2/moksha-monitor-exporter:latest
```

[![Docker Repository on Quay](https://quay.io/repository/factory2/moksha-monitor-exporter/status "Docker Repository on Quay")](https://quay.io/repository/factory2/moksha-monitor-exporter)

## I made it! :-)

Query it:
```
$ curl http://127.0.0.1:8080/metrics?target=<host-providing-moksha-monitoring-socket>&port=<tcp-port-number>
$ curl http://127.0.0.1:8080/metrics?target=<another-host-providing-moksha-monitoring-socket>&port=<tcp-port-number>
$ ...
```

Content of `/etc/fedmsg.d/<your-config>.py` on host providing *moksha.monitoring.socket*:
```
config = {
    ...
    'moksha.monitoring.socket': 'tcp://<typically-0.0.0.0>:<tcp-port-number>',
}
```
