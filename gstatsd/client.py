

import random
import socket


class StatsClient(object):

    "Simple client to exercise the statsd server."

    HOSTPORT = ('', 8125)

    def __init__(self, hostport=None):
        if hostport is None:
            hostport = StatsClient.HOSTPORT
        self._hostport = hostport
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
    def timer(self, key, timestamp, sample_rate=1):
        self._send('%s:%d|ms' % (key, timestamp), sample_rate)

    def increment(self, key, sample_rate=1):
        return self.counter(key, 1, sample_rate)

    def decrement(self, key, sample_rate=1):
        return self.counter(key, -1, sample_rate)

    def counter(self, keys, magnitude=1, sample_rate=1):
        if not isinstance(keys, (list, tuple)):
            keys = [keys]
        for key in keys:
            self._send('%s:%s|c' % (key, magnitude), sample_rate)

    def _send(self, data, sample_rate=1):
        packet = None
        if sample_rate < 1.0:
            if random.random() < sample_rate:
                packet = data + '|@%s' % sample_rate
        else:
            packet = data
        if packet:
            self._sock.sendto(packet, self._hostport)

