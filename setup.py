
import os
from setuptools import setup

from gstatsd import __version__


def main():
    cwd = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(cwd, 'README.txt')
    readme = open(path, 'rb').read()

    setup(
        name = 'gstatsd',
        version = __version__,
        description = 'A statsd service and client in Python + gevent',
        license = 'Apache 2.0',
        author = 'Patrick Hensley',
        author_email = 'spaceboy@indirect.com',
        keywords = ['stats', 'graphite', 'statsd', 'gevent'],
        url = 'http://github.com/phensley/gstatsd',
        packages = ['gstatsd'],
        entry_points = {
            'console_scripts': ['gstatsd=gstatsd.service:main']
            },
        classifiers = [
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Developers",
            "License :: OSI Approved :: Apache Software License",
            "Operating System :: MacOS :: MacOS X",
            "Operating System :: POSIX :: Linux",
            "Operating System :: Unix",
            "Programming Language :: Python",
            "Programming Language :: Python :: 2.6",
            "Programming Language :: Python :: 2.7",
            "Topic :: Software Development :: Libraries :: Python Modules",
            ],
        long_description = readme
        )


if __name__ == '__main__':
    main()

