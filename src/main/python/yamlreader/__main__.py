import sys
from . import parse_cmdline, __main

if __name__ == '__main__':
    (opts, args) = parse_cmdline()
    sys.exit(__main(opts, args))
