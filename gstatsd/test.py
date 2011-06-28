
from client import StatsClient


def main():
    cli = StatsClient()
    for num in range(1, 11):
        cli.timer('foo', num)
    return
    cli.increment('baz', 0.5)
    cli.increment('baz', 0.5)
    cli.timer('t3', 100, 0.5)
    return

    cli.increment('foo')
    cli.counter(['foo', 'bar'], 2)
    cli.timer('t1', 12)
    cli.timer('t2', 30)

if __name__ == '__main__':
    main()

