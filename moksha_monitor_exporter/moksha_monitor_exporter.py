import json
import threading
import time
import zmq

from flask import Flask, request, abort
from prometheus_client import (
    generate_latest, CollectorRegistry, ProcessCollector, Gauge)
from werkzeug.exceptions import BadRequest, TooManyRequests

ip_allow_shutdown_from = ('127.0.0.1', '::1',)
my_name = 'moksha_monitor_exporter'
metrics_path = '/metrics'
max_threads = 100
worker_thread_prefix = my_name + '_worker_'
app = Flask(__name__)


class MokshaMonitorExporter(threading.Thread):

    def __init__(self, target, port):
        super(MokshaMonitorExporter, self).__init__()
        self.target = target
        self.port = port
        self.name = self.target

        self.prometheus_registry = CollectorRegistry()
        self.prometheus_gauge_producers_last_ran = Gauge(
            my_name + '_producers_last_ran', 'UNIX timestamp of the last run.',
            ['name', 'module'], registry=self.prometheus_registry)
        self.prometheus_gauge_producers_exceptions = Gauge(
            my_name + '_producers_exceptions', 'Exception counter.',
            ['name', 'module'], registry=self.prometheus_registry)
        self.prometheus_gauge_consumers_headcount_in = Gauge(
            my_name + '_consumers_headcount_in', 'Messages coming to workers.',
            ['name', 'module', 'topic'], registry=self.prometheus_registry)
        self.prometheus_gauge_consumers_headcount_out = Gauge(
            my_name + '_consumers_headcount_out', 'Messages picked by workers.',
            ['name', 'module', 'topic'], registry=self.prometheus_registry)
        self.prometheus_gauge_consumers_exceptions = Gauge(
            my_name + '_consumers_exceptions', 'Number of exceptions.',
            ['name', 'module', 'topic'], registry=self.prometheus_registry)
        self.prometheus_gauge_consumers_backlog = Gauge(
            my_name + '_consumers_backlog', 'Backlog queue size.',
            ['name', 'module', 'topic'], registry=self.prometheus_registry)

    def __repr__(self):
        return worker_thread_prefix + self.name

    def run(self):
        """
        Connect to moksha.monitoring.socket and start receiving data.
        """
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect('tcp://{}:{}'.format(self.target, self.port))
        socket.setsockopt_string(zmq.SUBSCRIBE, '')
        while True:
            self.data = json.loads(socket.recv())

    def export(self):
        """
        Return Prometheus export from the received data.
        """
        for producer in self.data['producers']:
            self.prometheus_gauge_producers_last_ran.labels(
                producer['name'], producer['module']).set(
                producer['last_ran'])
            self.prometheus_gauge_producers_exceptions.labels(
                producer['name'], producer['module']).set(
                producer['exceptions'])
        for consumer in self.data['consumers']:
            self.prometheus_gauge_consumers_headcount_in.labels(
                consumer['name'], consumer['module'], consumer['topic']).set(
                consumer['headcount_in'])
            self.prometheus_gauge_consumers_headcount_out.labels(
                consumer['name'], consumer['module'], consumer['topic']).set(
                consumer['headcount_out'])
            self.prometheus_gauge_consumers_exceptions.labels(
                consumer['name'], consumer['module'], consumer['topic']).set(
                consumer['exceptions'])
            self.prometheus_gauge_consumers_backlog.labels(
                consumer['name'], consumer['module'], consumer['topic']).set(
                consumer['backlog'])
        return generate_latest(self.prometheus_registry).decode()


def worker_threads_count():
    """
    Return number of active MokshaMonitorExporter() threads.
    """
    return len(
        [str(thread) for thread in threading.enumerate()
         if str(thread).startswith(worker_thread_prefix)])


def export_my_metrics():
    """
    Return self-metrics as Prometheus export.
    """
    registry = CollectorRegistry()
    g = Gauge(
        my_name + '_threads',
        'Number of threads performing moksha.monitoring.socket connections.',
        registry=registry)
    g.set(worker_threads_count())
    ProcessCollector(namespace=my_name, registry=registry)
    return generate_latest(registry).decode() + (
        '# HELP ' + my_name + '_up Show that we\'re up and running!\n'
        '# TYPE ' + my_name + '_up untyped\n'
        '' + my_name + '_up 1.0\n')


@app.route('/', methods=['GET'])
def root():
    """
    Landing page
    """
    return (
        '<h1>Welcome to moksha.monitoring.socket exporter for Prometheus!</h1>'
        'Please follow this link: '
        '<a href="' + metrics_path + '">' + metrics_path + '</a>')


@app.route('/shutdown', methods=['POST'])
def shutdown():
    if request.remote_addr not in ip_allow_shutdown_from:
        abort(403)
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError("Not running with the Werkzeug Server")
    func()
    return 'Server shutting down...\n'


@app.route(metrics_path, methods=['GET'])
def metrics():
    """
    Provide endpoint for Prometheus.
    """
    if 'target' in request.args and 'port' in request.args:
        try:
            1 / int(1 < int(request.args['port']) < 65536)
        except Exception:
            raise BadRequest("Please provide valid TCP port number.")

        target = request.args['target']
        port = request.args['port']
        for thread in threading.enumerate():
            if worker_thread_prefix + target == str(thread):
                return thread.export() + export_my_metrics()
        if worker_threads_count() >= max_threads:
            raise TooManyRequests("Limit of threads reached.")
        thread = MokshaMonitorExporter(target, port)
        thread.start()
        # Let's wait 5 seconds, because it takes some time to connect
        # to moksha.monitoring.socket and receive data.
        time.sleep(5)
        return thread.export() + export_my_metrics()
    else:
        raise BadRequest("Please provide 'target' and 'port' parameters.")


if __name__ == '__main__':
    app.run()
