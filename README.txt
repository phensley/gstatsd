gstatsd - A statsd service implementation in Python + gevent.

If you are unfamiliar with statsd, you can read
`why statsd exists <http://codeascraft.etsy.com/2011/02/15/measure-anything-measure-everything/>`_,
or look at the
`NodeJS statsd implementation <https://github.com/etsy/statsd>`_.

License:
`Apache 2.0 <http://www.apache.org/licenses/LICENSE-2.0>`_

Requirements
------------


-  `Python <http://www.python.org/>`_ - I'm testing on 2.6/2.7 at
   the moment.
-  `gevent <http://www.gevent.org/>`_ - A libevent wrapper.
-  `distribute <http://pypi.python.org/pypi/distribute>`_ - (or
   setuptools) for builds.

Using gstatsd
-------------

Show gstatsd help:

::

    % gstatsd -h

Options:

::

    Usage: gstatsd [options]
    
     A statsd service in Python + gevent.
    
    Options:
      --version             show program's version number and exit
      -h, --help            show this help message and exit
      -b BIND_ADDR, --bind=BIND_ADDR
                            bind [host]:port (host defaults to '')
      -d DEST_ADDR, --dest=DEST_ADDR
                            receiver [backend:]host:port (backend defaults to
                            'graphite')
      -v                    increase verbosity (currently used for debugging)
      -f INTERVAL, --flush=INTERVAL
                            flush interval, in seconds (default 10)
      -p PERCENT, --percent=PERCENT
                            percent threshold (default 90)
      -l, --list            list supported backends
      -D, --daemonize       daemonize the service

Start gstatsd and send stats to port 9100 every 5 seconds:

::

    % gstatsd -d :9100 -f 5

Bind listener to host 'hostname' port 8126:

::

    % gstatsd -b hostname:8126 -d :9100 -f 5

To send the stats to multiple graphite servers, specify multiple
destinations:

::

    % gstatsd -b :8125 -d stats1:9100 stats2:9100

Using the client
----------------

The code example below demonstrates using the low-level client
interface:

::

    from gstatsd import client
    
    # location of the statsd server
    hostport = ('', 8125)
    
    raw = client.StatsClient(hostport)
    
    # add 1 to the 'foo' bucket
    raw.increment('foo')
    
    # timer 'bar' took 25ms to complete
    raw.timer('bar', 25)

You may prefer to use the stateful client:

::

    # wraps the raw client
    cli = client.Stats(raw)
    
    timer = cli.get_timer('foo')
    timer.start()
    
    ... do some work ..
    
    # when .stop() is called, the stat is sent to the server
    timer.stop()


