
# standard
import unittest

# local
from gstatsd import service


class StatsServiceTest(unittest.TestCase):

    def setUp(self):
        args = (':8125', [':2003'], 5, 90, 0)
        self.svc = service.StatsDaemon(*args)
        self.stats = self.svc._stats

    def test_construct(self):
        svc = service.StatsDaemon('8125', ['2003'], 5, 90, 0)
        stats = svc._stats
        self.assertEquals(svc._bindaddr, ('', 8125))
        self.assertEquals(svc._interval, 5.0)
        self.assertEquals(svc._debug, 0)
        self.assertEquals(stats.percent, 90.0)
        self.assertEquals(svc._sink._hosts, [('', 2003)])

        svc = service.StatsDaemon('bar:8125', ['foo:2003'], 5, 90, 1)
        self.assertEquals(svc._bindaddr, ('bar', 8125))
        self.assertEquals(svc._sink._hosts, [('foo', 2003)])
        self.assertEquals(svc._debug, 1)

    def test_backend(self):
        service.StatsDaemon._send_foo = lambda self, x, y: None
        svc = service.StatsDaemon('8125', ['bar:2003'], 5, 90, 0)
        self.assertEquals(svc._sink._hosts, [('bar', 2003)])

    def test_counters(self):
        pkt = 'foo:1|c'
        self.svc._process(pkt)
        self.assertEquals(self.stats.counts, {'foo': 1})
        self.svc._process(pkt)
        self.assertEquals(self.stats.counts, {'foo': 2})
        pkt = 'foo:-1|c'
        self.svc._process(pkt)
        self.assertEquals(self.stats.counts, {'foo': 1})

    def test_counters_sampled(self):
        pkt = 'foo:1|c|@.5'
        self.svc._process(pkt)
        self.assertEquals(self.stats.counts, {'foo': 2})

    def test_timers(self):
        pkt = 'foo:20|ms'
        self.svc._process(pkt)
        self.assertEquals(self.stats.timers, {'foo': [20.0]})
        pkt = 'foo:10|ms'
        self.svc._process(pkt)
        self.assertEquals(self.stats.timers, {'foo': [20.0, 10.0]})

    def test_key_sanitize(self):
        pkt = '\t\n#! foo . bar \0 ^:1|c'
        self.svc._process(pkt)
        self.assertEquals(self.stats.counts, {'foo.bar': 1})

    def test_key_prefix(self):
        args = (':8125', [':2003'], 5, 90, 0, 'pfx')
        svc = service.StatsDaemon(*args)
        pkt = 'foo:1|c'
        svc._process(pkt)
        self.assertEquals(svc._stats.counts, {'pfx.foo': 1})


def main():
    unittest.main()


if __name__ == '__main__':
    main()


