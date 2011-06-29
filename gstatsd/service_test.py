
# standard
import unittest

# local
from gstatsd import service


class StatsServiceTest(unittest.TestCase):

    def setUp(self):
        args = (':8125', [':9100'], 5, 90, 0)
        self.svc = service.StatsDaemon(*args)

    def test_construct(self):
        svc = service.StatsDaemon('8125', ['9100'], 5, 90, 0)
        self.assertEquals(svc._bindaddr, ('', 8125))
        self.assertEquals(svc._interval, 5.0)
        self.assertEquals(svc._percent, 90.0)
        self.assertEquals(svc._debug, 0)
        self.assertEquals(svc._targets[0], (svc._send_graphite, ('', 9100)))

        svc = service.StatsDaemon('bar:8125', ['foo:9100'], 5, 90, 1)
        self.assertEquals(svc._bindaddr, ('bar', 8125))
        self.assertEquals(svc._targets[0], (svc._send_graphite, ('foo', 9100)))
        self.assertEquals(svc._debug, 1)

    def test_backend(self):
        service.StatsDaemon._send_foo = lambda self, x, y: None
        svc = service.StatsDaemon('8125', ['foo:bar:9100'], 5, 90, 0)
        self.assertEquals(svc._targets[0], (svc._send_foo, ('bar', 9100)))

    def test_counters(self):
        pkt = 'foo:1|c'
        self.svc._process(pkt, None)
        self.assertEquals(self.svc._counts, {'foo': 1})
        self.svc._process(pkt, None)
        self.assertEquals(self.svc._counts, {'foo': 2})
        pkt = 'foo:-1|c'
        self.svc._process(pkt, None)
        self.assertEquals(self.svc._counts, {'foo': 1})

    def test_counters_sampled(self):
        pkt = 'foo:1|c|@.5'
        self.svc._process(pkt, None)
        self.assertEquals(self.svc._counts, {'foo': 2})

    def test_timers(self):
        pkt = 'foo:20|ms'
        self.svc._process(pkt, None)
        self.assertEquals(self.svc._timers, {'foo': [20.0]})
        pkt = 'foo:10|ms'
        self.svc._process(pkt, None)
        self.assertEquals(self.svc._timers, {'foo': [20.0, 10.0]})

    def test_key_sanitize(self):
        pkt = '\t\n#! foo . bar \0 ^:1|c'
        self.svc._process(pkt, None)
        self.assertEquals(self.svc._counts, {'foo.bar': 1})


def main():
    unittest.main()


if __name__ == '__main__':
    main()


