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

    def test_shutdown(self):
        """
        This should be the final test. :-)
        """
        r = session.post('http://127.0.0.1:5000/shutdown', data={})
        assert r.text == "Server shutting down...\n"
