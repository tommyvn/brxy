import logging
import argparse
import asyncio
from functools import partial
from collections import defaultdict
from brxy.edge.router import http as http_router, netstring as netstring_router
from brxy.edge.linker import left as left_linker, right as right_linker, FuturesQueue
from brxy.proxy import simple_proxy as proxy
from brxy.edge.util import server
import os


logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument('-p', '--frontend-port', type=int, default=80)
parser.add_argument('--backend-port', type=int, default=9080)
parser.add_argument('-d', '--debug', action='count', default=0)
parser.add_argument('seed_cmd', nargs='*')
args = parser.parse_args()

log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[args.debug]
logging.basicConfig(format='%(asctime)s %(name)s.%(funcName)s:%(lineno)d %(levelname)s: %(message)s',
                    level=log_level)
logger.warning("logging warning")
logger.info("logging info")
logger.debug("logging debug")


loop = asyncio.get_event_loop()

# TODO remove empty entries
qs = defaultdict(lambda: FuturesQueue(loop=loop))


if args.seed_cmd:
    def seed_fun(r):
        loop.create_task(asyncio.create_subprocess_exec(*args.seed_cmd,
                                                        env=dict(list(os.environ.items()) + list({"ROUTE": r.decode()}.items()))))
else:
    def seed_fun(r):
        pass


l_r = partial(left_linker, qs, proxy, seed_fun=seed_fun, _loop=loop)
server_coro = server(('0.0.0.0', args.frontend_port), http_router(l_r, router_timeout=10, _loop=loop), _loop=loop)
loop.create_task(server_coro)

r_r = partial(right_linker, qs, seed_fun=seed_fun, _loop=loop)
r_server_coro = server(('0.0.0.0', args.backend_port), netstring_router(r_r, router_timeout=1, _loop=loop), _loop=loop)
loop.create_task(r_server_coro)

loop.run_forever()
