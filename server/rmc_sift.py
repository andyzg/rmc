"""A wrapper around the Sift Science Python client to asynchronously send
events.
"""

import threading

from hotqueue import HotQueue

import rmc.server.sift_client as sift_client
import rmc.shared.constants as c


class RmcSift(object):
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = sift_client.Client(api_key=api_key)
        self.queue = HotQueue("sift_events", host=c.REDIS_HOST,
                port=c.REDIS_PORT, db=c.REDIS_DB)

        process_thread = threading.Thread(target=self._process_events)
        process_thread.setDaemon(True)
        process_thread.start()

    def track(self, event, params):
        self.queue.put({'event': event, 'params': params})

    def _process_events(self):
        for item in self.queue.consume():
            self.client.track(item['event'], item['params'])