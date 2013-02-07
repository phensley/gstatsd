
# standard
import unittest

# local
from gstatsd import client


class StatsDummyClient(client.StatsClient):

    def __init__(self, hostport=None):
        client.StatsClient.__init__(self, hostport)
        self.packets = []

    def _send(self, data, sample_rate=1):
        self.packets.append((data, sample_rate))


class StatsClientTest(unittest.TestCase):

    def setUp(self):
        self._cli = StatsDummyClient()

    def test_timer(self):
        self._cli.timer('foo', 15, 1)
        self.assertEquals(self._cli.packets[-1], ('foo:15|ms', 1))
        self._cli.timer('bar.baz', 1.35, 1)
        self.assertEquals(self._cli.packets[-1], ('bar.baz:1|ms', 1))
        self._cli.timer('x', 1.99, 1)
        self.assertEquals(self._cli.packets[-1], ('x:2|ms', 1))
        self._cli.timer('x', 1, 0.5)
        self.assertEquals(self._cli.packets[-1], ('x:1|ms', 0.5))

    def test_increment(self):
        self._cli.increment('foo')
        self.assertEquals(self._cli.packets[-1], ('foo:1|c', 1))
        self._cli.increment('x', 0.5)
        self.assertEquals(self._cli.packets[-1], ('x:1|c', 0.5))

    def test_decrement(self):
        self._cli.decrement('foo')
        self.assertEquals(self._cli.packets[-1], ('foo:-1|c', 1))
        self._cli.decrement('x', 0.2)
        self.assertEquals(self._cli.packets[-1], ('x:-1|c', 0.2))

    def test_counter(self):
        self._cli.counter('foo', 5)
        self.assertEquals(self._cli.packets[-1], ('foo:5|c', 1))
        self._cli.counter('foo', -50)
        self.assertEquals(self._cli.packets[-1], ('foo:-50|c', 1))
        self._cli.counter('foo', 5.9)
        self.assertEquals(self._cli.packets[-1], ('foo:6|c', 1))
        self._cli.counter('foo', 1, 0.2)
        self.assertEquals(self._cli.packets[-1], ('foo:1|c', 0.2))

    def test_gauge(self):
        self._cli.gauge('foo', 5)
        self.assertEquals(self._cli.packets[-1], ('foo:5|g', 1))
        self._cli.counter('foo', -50)
        self.assertEquals(self._cli.packets[-1], ('foo:-50|g', 1))
        self._cli.counter('foo', 5.9)
        self.assertEquals(self._cli.packets[-1], ('foo:5.9|g', 1))


class StatsTest(unittest.TestCase):

    def setUp(self):
        self._cli = StatsDummyClient()
        self._stat = client.Stats(self._cli)

    def test_timer(self):
        timer = self._stat.get_timer('foo')
        timer.start()
        timer.stop()
        data, sr = self._cli.packets[-1]
        pkt = data.split(':')
        self.assertEquals(pkt[0], 'foo')

        # ensure warning is raised for mismatched start/stop
        timer = self._stat.get_timer('foo')
        self.assertRaises(UserWarning, timer.stop)

    def test_counter(self):
        count = self._stat.get_counter('foo')
        count.increment()
        count.decrement()
        count.add(5)
        self.assertEquals(self._cli.packets[-1], ('foo:5|c', 1))


def main():
    unittest.main()


if __name__ == '__main__':
    main()
