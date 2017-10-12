import sys
from __init__ import parse_cmdline, main

(opts, args) = parse_cmdline()
sys.exit(main(opts, args))
