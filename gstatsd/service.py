
# standard
import cStringIO
import optparse
import os
import resource
import signal
import string
import sys
import time
import traceback
from collections import defaultdict

# local
import sink
from core import __version__

# vendor
import gevent, gevent.socket
socket = gevent.socket
# protect stats  
from gevent.thread import allocate_lock as Lock
stats_lock = Lock()

# constants
INTERVAL = 10.0
PERCENT = 90.0
MAX_PACKET = 2048

DESCRIPTION = '''
A statsd service in Python + gevent.
'''
EPILOG = '''

'''

# table to remove invalid characters from keys
ALL_ASCII = set(chr(c) for c in range(256))
KEY_VALID = string.ascii_letters + string.digits + '_-.'
KEY_TABLE = string.maketrans(KEY_VALID + '/', KEY_VALID + '_')
KEY_DELETIONS = ''.join(ALL_ASCII.difference(KEY_VALID + '/'))

# error messages
E_BADADDR = 'invalid bind address specified %r'
E_NOSINKS = 'you must specify at least one stats sink'


class Stats(object):

    def __init__(self):
        self.timers = defaultdict(list)
        self.counts = defaultdict(float)
        self.gauges = defaultdict(float)
        self.percent = PERCENT
        self.interval = INTERVAL


def daemonize(umask=0027):
    if gevent.fork():
        os._exit(0)
    os.setsid()
    if gevent.fork():
        os._exit(0)
    os.umask(umask)
    fd_limit = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
    if fd_limit == resource.RLIM_INFINITY:
        fd_limit = 1024
    for fd in xrange(0, fd_limit):
        try:
            os.close(fd)
        except:
            pass
    os.open(os.devnull, os.O_RDWR)
    os.dup2(0, 1)
    os.dup2(0, 2)
    gevent.reinit()


def parse_addr(text):
    "Parse a 1- to 3-part address spec."
    if text:
        parts = text.split(':')
        length = len(parts)
        if length== 3:
            return parts[0], parts[1], int(parts[2])
        elif length == 2:
            return None, parts[0], int(parts[1])
        elif length == 1:
            return None, '', int(parts[0])
    return None, None, None


class StatsDaemon(object):

    """
    A statsd service implementation in Python + gevent.
    """

    def __init__(self, bindaddr, sinkspecs, interval, percent, debug=0,
                 key_prefix=''):
        _, host, port = parse_addr(bindaddr)
        if port is None:
            self.exit(E_BADADDR % bindaddr)
        self._bindaddr = (host, port)

        # TODO: generalize to support more than one sink type.  currently
        # only the graphite backend is present, but we may want to write
        # stats to hbase, redis, etc. - ph

        # construct the sink and add hosts to it
        if not sinkspecs:
            self.exit(E_NOSINKS)
        self._sink = sink.GraphiteSink()
        errors = []
        for spec in sinkspecs:
            try:
                self._sink.add(spec)
            except ValueError, ex:
                errors.append(ex)
        if errors:
            for err in errors:
                self.error(str(err))
            self.exit('exiting.')

        self._percent = float(percent)
        self._interval = float(interval)
        self._debug = debug
        self._sock = None
        self._flush_task = None
        self._key_prefix = key_prefix

        self._reset_stats()

    def _reset_stats(self):
        with stats_lock:
            self._stats = Stats()
            self._stats.percent = self._percent
            self._stats.interval = self._interval

    def exit(self, msg, code=1):
        self.error(msg)
        sys.exit(code)

    def error(self, msg):
        sys.stderr.write(msg + '\n')

    def start(self):
        "Start the service"
        # register signals
        gevent.signal(signal.SIGINT, self._shutdown)

        # spawn the flush trigger
        def _flush_impl():
            while 1:
                gevent.sleep(self._stats.interval)

                # rotate stats
                stats = self._stats
                self._reset_stats()

                # send the stats to the sink which in turn broadcasts
                # the stats packet to one or more hosts.
                try:
                    self._sink.send(stats)
                except Exception, ex:
                    trace = traceback.format_tb(sys.exc_info()[-1])
                    self.error(''.join(trace))

        self._flush_task = gevent.spawn(_flush_impl)

        # start accepting connections
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM,
            socket.IPPROTO_UDP)
        self._sock.bind(self._bindaddr)
        while 1:
            try:
                data, _ = self._sock.recvfrom(MAX_PACKET)
                for p in data.split('\n'):
                    if p:
                        self._process(p)
            except Exception, ex:
                self.error(str(ex))

    def _shutdown(self):
        "Shutdown the server"
        self.exit("service exiting", code=0)

    def _process(self, data):
        "Process a single packet and update the internal tables."
        parts = data.split(':')
        if self._debug:
            self.error('packet: %r' % data)
        if not parts:
            return

        # interpret the packet and update stats
        stats = self._stats
        key = parts[0].translate(KEY_TABLE, KEY_DELETIONS)
        if self._key_prefix:
            key = '.'.join([self._key_prefix, key])
        for part in parts[1:]:
            srate = 1.0
            fields = part.split('|')
            length = len(fields)
            if length < 2:
                continue
            value = fields[0]
            stype = fields[1].strip()

            with stats_lock:
                # timer (milliseconds)
                if stype == 'ms':
                    stats.timers[key].append(float(value if value else 0))

                # counter with optional sample rate
                elif stype == 'c':
                    if length == 3 and fields[2].startswith('@'):
                        srate = float(fields[2][1:])
                    value = float(value if value else 1) * (1 / srate)
                    stats.counts[key] += value
                elif stype == 'g':
                    value = float(value if value else 1)
                    stats.gauges[key] = value


def main():
    opts = optparse.OptionParser(description=DESCRIPTION, version=__version__,
        add_help_option=False)
    opts.add_option('-b', '--bind', dest='bind_addr', default=':8125',
        help="bind [host]:port (host defaults to '')")
    opts.add_option('-s', '--sink', dest='sink', action='append', default=[],
        help="a graphite service to which stats are sent ([host]:port).")
    opts.add_option('-v', dest='verbose', action='count', default=0,
        help="increase verbosity (currently used for debugging)")
    opts.add_option('-f', '--flush', dest='interval', default=INTERVAL,
        help="flush interval, in seconds (default 10)")
    opts.add_option('-x', '--prefix', dest='key_prefix', default='',
        help="key prefix added to all keys (default None)")
    opts.add_option('-p', '--percent', dest='percent', default=PERCENT,
        help="percent threshold (default 90)")
    opts.add_option('-D', '--daemonize', dest='daemonize', action='store_true',
        help='daemonize the service')
    opts.add_option('-h', '--help', dest='usage', action='store_true')

    (options, args) = opts.parse_args()

    if options.usage:
        # TODO: write epilog. usage is manually output since optparse will
        # wrap the epilog and we want pre-formatted output. - ph
        print(opts.format_help())
        sys.exit()

    if options.daemonize:
        daemonize()

    sd = StatsDaemon(options.bind_addr, options.sink, options.interval,
                     options.percent, options.verbose, options.key_prefix)
    sd.start()


if __name__ == '__main__':
    main()
