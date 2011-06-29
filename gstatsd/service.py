
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
from core import __version__

# vendor
import gevent, gevent.socket
socket = gevent.socket


# constants
INTERVAL = 10.0
PERCENT = 90.0
MAX_PACKET = 2048

DESCRIPTION = '''
A statsd service in Python + gevent.
'''

# table to remove invalid characters from keys
ALL_ASCII = set(chr(c) for c in range(256))
KEY_VALID = string.ascii_letters + string.digits + '_-.'
KEY_TABLE = string.maketrans(KEY_VALID + '/', KEY_VALID + '_')
KEY_DELETIONS = ''.join(ALL_ASCII.difference(KEY_VALID + '/'))

# error messages
E_BADADDR = 'invalid bind address specified %r'
E_BADTARGET = 'invalid target specified %r'
E_BADBACKEND = 'invalid backend specified %r'
E_NOTARGETS = 'you must specify at least one stats destination'
E_SENDFAIL = 'failed to send stats to %s %s: %s'


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

    def __init__(self, bindaddr, targets, interval, percent, debug=0):
        # parse and validate
        _, host, port = parse_addr(bindaddr)
        if port is None:
            self._exit(E_BADADDR % bindaddr)
        self._bindaddr = (host, port)

        # parse backend targets
        if not targets:
            self._exit(E_NOTARGETS)
        self._targets = []
        for target in targets:
            backend, host, port = parse_addr(target)
            if backend is None:
                backend = 'graphite'
            if port is None:
                self._exit(E_BADTARGET % target)
            func = getattr(self, '_send_%s' % backend, None)
            if not func:
                self._exit(E_BADBACKEND % backend)
            self._targets.append((func, (host, port)))

        self._interval = float(interval)
        self._percent = float(percent)
        self._debug = debug
        self._timers = defaultdict(list)
        self._counts = defaultdict(float)
        self._sock = None
        self._flush_task = None

    def _exit(self, msg, code=1):
        self._error(msg)
        sys.exit(code)

    def _error(self, msg):
        sys.stderr.write(msg + '\n')

    def start(self):
        "Start the service"
        # register signals
        gevent.signal(signal.SIGINT, self._shutdown)

        # spawn the flush trigger
        def _flush_impl():
            while 1:
                gevent.sleep(self._interval)
                for func, hostport in self._targets:
                    try:
                        func(hostport)
                    except Exception, ex:
                        self._error(traceback.format_tb(sys.exc_info()[-1]))

        self._flush_task = gevent.spawn(_flush_impl)

        # start accepting connections
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 
            socket.IPPROTO_UDP)
        self._sock.bind(self._bindaddr)
        while 1:
            try:
                self._process(*self._sock.recvfrom(MAX_PACKET))
            except Exception, ex:
                self._error(str(ex))

    def _shutdown(self):
        "Shutdown the server"
        self._exit("service exiting", code=0)

    def _process(self, data, _):
        "Process a single packet"
        parts = data.split(':')
        if self._debug:
            self._error('packet: %r' % data)
        if not parts:
            return
        key = parts[0].translate(KEY_TABLE, KEY_DELETIONS)
        for part in parts[1:]:
            srate = 1.0
            fields = part.split('|')
            length = len(fields)
            if length < 2:
                continue
            value = fields[0]
            stype = fields[1].strip()

            # timer (milliseconds)
            if stype == 'ms':
                self._timers[key].append(float(value if value else 0))

            # counter with optional sample rate
            elif stype == 'c':
                if length == 3 and fields[2].startswith('@'):
                    srate = float(fields[2][1:])
                value = float(value if value else 1) * (1 / srate)
                self._counts[key] += value

    def _send_graphite(self, dest):
        "Send blob of stats data to graphite server"
        buf = cStringIO.StringIO()
        now = int(time.time())
        num_stats = 0

        # timer stats
        pct = self._percent
        timers = self._timers
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
        counts = self._counts
        for key, val in counts.iteritems():
            buf.write('stats.%s %f %d\n' % (key, val / self._interval, now))
            buf.write('stats_counts.%s %f %d\n' % (key, val, now))
            num_stats += 1

        buf.write('statsd.numStats %d %d\n' % (num_stats, now))

        # reset
        self._timers = defaultdict(list)
        self._counts = defaultdict(float)
        del timers
        del counts

        # XXX: add support for N retries

        # flush stats to graphite
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(dest)
            sock.sendall(buf.getvalue())
            sock.close()
        except Exception, ex:
            self._error(E_SENDFAIL % ('graphite', dest, ex))


def main():
    opts = optparse.OptionParser(description=DESCRIPTION, version=__version__)
    opts.add_option('-b', '--bind', dest='bind_addr', default=':8125', 
        help="bind [host]:port (host defaults to '')")
    opts.add_option('-d', '--dest', dest='dest_addr', action='append',
        default=[],
        help="receiver [backend:]host:port (backend defaults to 'graphite')")
    opts.add_option('-v', dest='verbose', action='count', default=0,
        help="increase verbosity (currently used for debugging)")
    opts.add_option('-f', '--flush', dest='interval', default=INTERVAL,
        help="flush interval, in seconds (default 10)")
    opts.add_option('-p', '--percent', dest='percent', default=PERCENT,
        help="percent threshold (default 90)")
    opts.add_option('-l', '--list', dest='list_backends', action='store_true',
        help="list supported backends")
    opts.add_option('-D', '--daemonize', dest='daemonize', action='store_true',
        help='daemonize the service')

    (options, args) = opts.parse_args()

    if options.list_backends:
        for key in [k for k in dir(StatsDaemon) if k.startswith('_send_')]:
            print(key[6:])
        sys.exit()

    if options.daemonize:
        daemonize()

    sd = StatsDaemon(options.bind_addr, options.dest_addr, options.interval,
        options.percent, options.verbose)
    sd.start()
 

if __name__ == '__main__':
    main()

