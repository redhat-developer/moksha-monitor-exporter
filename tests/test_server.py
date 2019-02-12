import requests
import threading

from moksha_monitor_exporter.moksha_monitor_exporter import app
from requests.packages.urllib3.util.retry import Retry

session = requests.Session()
session.mount('http://', requests.adapters.HTTPAdapter(
    max_retries=Retry(
        total=3,
        backoff_factor=0.5,
    )))


class TestServer():
    def setup_class(self):

        def flask_thread():
            app.debug = True
            app.run(use_reloader=False)
        threading.Thread(target=flask_thread).start()

    def test_my_metrics(self):
        """
        Test whether we can export basic metrics from
        moksha-monitor-exporter itself.
        """
        r = session.get('http://127.0.0.1:5000/my-metrics')
        assert 'moksha_monitor_exporter_threads 0.0' in r.text
        assert 'moksha_monitor_exporter_up 0.0' in r.text

    def test_nonexisting_target(self):
        """
        Test some nonexisting target.
        """
        r = session.get('http://127.0.0.1:5000/metrics?target='
                        'moksha.monitoring.socket.example.com&port=10040')
        assert 'moksha_monitor_exporter_threads 1.0' in r.text
        assert 'moksha_monitor_exporter_up 0.0' in r.text

    def test_shutdown(self):
        """
        This should be the final test. :-)
        """
        r = session.post('http://127.0.0.1:5000/shutdown', data={})
        assert r.text == "Server shutting down...\n"
