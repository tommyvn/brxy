#!/usr/bin/env python

import argparse
import http.server
import os

class SimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(*args, **kwargs): pass

parser = argparse.ArgumentParser()
parser.add_argument('port', action='store',
                    # default=8000, type=int,
                    default=int(os.environ.get("PORT", "8000")), type=int,
                    nargs='?',
                    help='Specify alternate port [default: 8000]')
args = parser.parse_args()
http.server.test(HandlerClass=SimpleHTTPRequestHandler, port=args.port)
