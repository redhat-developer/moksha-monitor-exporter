import json
import threading
import time
import zmq

from flask import Flask, request, abort, Response
from prometheus_client import (
    generate_latest, CollectorRegistry, ProcessCollector, Gauge,
    CONTENT_TYPE_LATEST)
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
        self.name = worker_thread_prefix + self.target

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

    def run(self):
        """
        Connect to moksha.monitoring.socket and start receiving data.
        """
        context = zmq.Context()
        socket = context.socket(zmq.SUB)
        socket.connect('tcp://{}:{}'.format(self.target, self.port))
        try:
            # Python 2
            socket.setsockopt(zmq.SUBSCRIBE, b'')
        except TypeError:
            # Python 3
            socket.setsockopt_string(zmq.SUBSCRIBE, b'')
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
        [thread.name for thread in threading.enumerate()
         if thread.name.startswith(worker_thread_prefix)])


@app.route('/my-metrics', methods=['GET'])
def export_my_metrics(backend_connected=False):
    """
    Return self-metrics as Prometheus export.
    """
    backend_up_value = '1.0' if backend_connected else '0.0'
    registry = CollectorRegistry()
    g = Gauge(
        my_name + '_threads',
        'Number of threads performing moksha.monitoring.socket connections.',
        registry=registry)
    g.set(worker_threads_count())
    ProcessCollector(namespace=my_name, registry=registry)
    return generate_latest(registry).decode() + (
        '# HELP ' + my_name + '_up Show that we\'re connected to the backend!\n'
        '# TYPE ' + my_name + '_up untyped\n'
        '' + my_name + '_up ' + backend_up_value + '\n')


def export_all(thread):
    """
    Return full Prometheus export for a given thread incl. self-metrics.
    """
    try:
        return Response(
            thread.export() + export_my_metrics(backend_connected=True),
            content_type=CONTENT_TYPE_LATEST)
    except Exception:
        return Response(export_my_metrics(), content_type=CONTENT_TYPE_LATEST)


@app.route('/', methods=['GET'])
def root():
    """
    Landing page
    """
    return (
        '<h1>Welcome to moksha.monitoring.socket exporter for Prometheus!</h1>'
        'Please follow this link: '
        '<a href="' + metrics_path + '">' + metrics_path + '</a>\n')


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
    if not ('target' in request.args and 'port' in request.args):
        raise BadRequest("Please provide 'target' and 'port' parameters.")

    try:
        1 / int(1 < int(request.args['port']) < 65536)
    except Exception:
        raise BadRequest("Please provide valid TCP port number.")

    target = request.args['target']
    port = request.args['port']
    for thread in threading.enumerate():
        if worker_thread_prefix + target == thread.name:
            return export_all(thread)
    if worker_threads_count() >= max_threads:
        raise TooManyRequests("Limit of threads reached.")
    thread = MokshaMonitorExporter(target, port)
    thread.start()
    # Let's wait for 5 seconds, because it takes some time to connect
    # to moksha.monitoring.socket and receive data.
    time.sleep(5)
    return export_all(thread)


if __name__ == '__main__':
    app.run()
