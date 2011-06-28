
gstatsd - A statsd service implementation in Python + gevent.

License: Apache 2.0

Usage:
------

Show gstatsd help:

    % gstatsd -h

Start gstatsd and send stats to port 9100 every 5 seconds:

    % gstatsd -d :9100 -f 5

Bind listener to host 'hostname' port 8126:

    % gstatsd -b hostname:8126 -d :9100 -f 5

