
# standard
import cStringIO
import sys
import time

# vendor
from gevent import socket

E_BADSPEC = "bad sink spec %r: %s"
E_SENDFAIL = 'failed to send stats to %s %s: %s'


class Sink(object):

    """
    A resource to which stats will be sent.
    """

    def error(self, msg):
        sys.stderr.write(msg + '\n')

    def _parse_hostport(self, spec):
        try:
            parts = spec.split(':')
            if len(parts) == 2:
                return (parts[0], int(parts[1]))
            if len(parts) == 1:
                return ('', int(parts[0]))
        except ValueError, ex:
            raise ValueError(E_BADSPEC % (spec, ex))
        raise ValueError("expected '[host]:port' but got %r" % spec)


class GraphiteSink(Sink):

    """
    Sends stats to one or more Graphite servers.
    """

    def __init__(self):
        self._hosts = []

    def add(self, spec):
        self._hosts.append(self._parse_hostport(spec))

    def send(self, stats):
        "Format stats and send to one or more Graphite hosts"
        buf = cStringIO.StringIO()
        now = int(time.time())
        num_stats = 0

        # timer stats
        pct = stats.percent
        timers = stats.timers
        for key, vals in timers.iteritems():
            if not vals:
                continue

            # compute statistics
            num = len(vals)
            vals = sorted(vals)
            vmin = vals[0]
            vmax = vals[-1]
            mean = vmin
            max_at_thresh = vmax
            if num > 1:
                idx = round((pct / 100.0) * num)
                tmp = vals[:int(idx)]
                if tmp:
                    max_at_thresh = tmp[-1]
                    mean = sum(tmp) / idx

            key = 'stats.timers.%s' % key
            buf.write('%s.mean %f %d\n' % (key, mean, now))
            buf.write('%s.upper %f %d\n' % (key, vmax, now))
            buf.write('%s.upper_%d %f %d\n' % (key, pct, max_at_thresh, now))
            buf.write('%s.lower %f %d\n' % (key, vmin, now))
            buf.write('%s.count %d %d\n' % (key, num, now))
            num_stats += 1

        # counter stats
        counts = stats.counts
        for key, val in counts.iteritems():
            buf.write('stats.%s %f %d\n' % (key, val / stats.interval, now))
            buf.write('stats_counts.%s %f %d\n' % (key, val, now))
            num_stats += 1

        # counter stats
        gauges = stats.gauges
        for key, val in gauges.iteritems():
            buf.write('stats.%s %f %d\n' % (key, val, now))
            buf.write('stats_counts.%s %f %d\n' % (key, val, now))
            num_stats += 1

        buf.write('statsd.numStats %d %d\n' % (num_stats, now))

        # TODO: add support for N retries

        for host in self._hosts:
            # flush stats to graphite
            try:
                sock = socket.create_connection(host)
                sock.sendall(buf.getvalue())
                sock.close()
            except Exception, ex:
                self.error(E_SENDFAIL % ('graphite', host, ex))
