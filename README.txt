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
      -b BIND_ADDR, --bind=BIND_ADDR
                            bind [host]:port (host defaults to '')
      -s SINK, --sink=SINK  a graphite service to which stats are sent
                            ([host]:port).
      -v                    increase verbosity (currently used for debugging)
      -f INTERVAL, --flush=INTERVAL
                            flush interval, in seconds (default 10)
      -p PERCENT, --percent=PERCENT
                            percent threshold (default 90)
      -D, --daemonize       daemonize the service
      -h, --help

Start gstatsd listening on the default port 8125, and send stats to
graphite server on port 2003 every 5 seconds:

::

    % gstatsd -s 2003 -f 5

Bind listener to host 'foo' port 8126, and send stats to the
Graphite server on host 'bar' port 2003 every 20 seconds:

::

    % gstatsd -b foo:8126 -s bar:2003 -f 20

To send the stats to multiple graphite servers, specify '-s'
multiple times:

::

    % gstatsd -b :8125 -s stats1:2003 -s stats2:2004

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


