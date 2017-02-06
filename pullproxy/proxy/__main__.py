#!/usr/bin/env python3

import socket
from collections import defaultdict
import asyncio
import logging
from .router.left import http
from .router.right import netstring
from . import FuturesQueue, acceptor_loop
import argparse


logger = logging.getLogger(__name__)


logger.setLevel(logging.WARNING)
# logger.setLevel(logging.DEBUG)

root = logging.getLogger()
root.setLevel(logging.WARNING)
# TODO figure out logging. If this is unhashed it double logs because something simple is wrong
consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.WARNING)
# TODO don't stay at INFO
consoleHandler.setLevel(logging.INFO)
# consoleHandler.setLevel(logging.DEBUG)

formatter = logging.Formatter(
  '%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s')
consoleHandler.setFormatter(formatter)

logger.addHandler(consoleHandler)


parser = argparse.ArgumentParser()
parser.add_argument('-p', '--frontend-port', type=int, default=80)
parser.add_argument('--backend-port', type=int, default=9080)
parser.add_argument('seed_cmd', nargs='*', default=["provisioner-files/usr/local/bin/old_splice_linker.py"])
args = parser.parse_args()

print(args.seed_cmd)


def seed_fun(r):
    # loop.create_task(asyncio.create_subprocess_exec(*(c.format(route=r) for c in args.seed_cmd), env={"ROUTE": r.decode()}))
    loop.create_task(asyncio.create_subprocess_exec(*args.seed_cmd, env={"ROUTE": r.decode()}))
    # loop.create_task(asyncio.create_subprocess_exec(*args.seed_cmd + [r.decode()]))


loop = asyncio.get_event_loop()
http_pools = defaultdict(lambda: FuturesQueue(loop=loop))

http_client_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
http_client_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
http_client_server.bind(('', args.frontend_port))
http_client_server.listen(5)


r = http.router(http_pools, seed_fun)

loop.create_task(acceptor_loop(http_client_server, r))

http_server_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
http_server_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# TODO this has to shift to TLS auth to stop randoms from grabbing other
#      peeps traffic off the proxy
http_server_server.bind(('', args.backend_port))
http_server_server.listen(5)
r = netstring.router(http_pools, seed_fun)
loop.create_task(acceptor_loop(http_server_server, r))

loop.run_forever()
