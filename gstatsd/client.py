

# standard
import random
import socket
import time


E_NOSTART = 'you must call start() before stop(). ignoring.'


class StatsClient(object):

    "Simple client to exercise the statsd server."

    HOSTPORT = ('', 8125)

    def __init__(self, hostport=None):
        if hostport is None:
            hostport = StatsClient.HOSTPORT
        self._hostport = hostport
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def timer(self, key, timestamp, sample_rate=1):
        self._send('%s:%d|ms' % (key, round(timestamp)), sample_rate)

    def gauge(self, key, value, sample_rate=1):
        self._send('%s:%d|g' % (key, value), sample_rate)

    def increment(self, key, sample_rate=1):
        return self.counter(key, 1, sample_rate)

    def decrement(self, key, sample_rate=1):
        return self.counter(key, -1, sample_rate)

    def counter(self, keys, magnitude=1, sample_rate=1):
        if not isinstance(keys, (list, tuple)):
            keys = [keys]
        for key in keys:
            self._send('%s:%d|c' % (key, round(magnitude)), sample_rate)

    def _send(self, data, sample_rate=1):
        packet = None
        if sample_rate < 1.0:
            if random.random() < sample_rate:
                packet = data + '|@%s' % sample_rate
        else:
            packet = data
        if packet:
            self._sock.sendto(packet, self._hostport)


class StatsCounter(object):

    def __init__(self, client, key, sample_rate=1):
        self._client = client
        self._key = key
        self._sample_rate = sample_rate

    def increment(self):
        self._client.increment(self._key, self._sample_rate)

    def decrement(self):
        self._client.decrement(self._key, self._sample_rate)

    def add(self, val):
        self._client.counter(self._key, val, self._sample_rate)


class StatsTimer(object):

    def __init__(self, client, key):
        self._client = client
        self._key = key
        self._started = 0
        self._timestamp = 0

    def start(self):
        self._started = 1
        self._timestamp = time.time()

    def stop(self):
        if not self._started:
            raise UserWarning(E_NOSTART)
            return
        elapsed = time.time() - self._timestamp
        self._client.timer(self._key, int(elapsed * 1000.0))
        self._started = 0


class StatsGauge(object):

    def __init__(self, client, key, sample_rate=1):
        self._client = client
        self._key = key
        self._sample_rate = sample_rate

    def set(self, value):
        self._client.gauge(self._key, value, self._sample_rate)


class Stats(object):

    def __init__(self, client):
        self._client = client

    def get_counter(self, key, sample_rate=1):
        return StatsCounter(self._client, key, sample_rate)

    def get_timer(self, key):
        return StatsTimer(self._client, key)

    def get_gauge(self, key):
        return StatsGauge(self._client, key)
