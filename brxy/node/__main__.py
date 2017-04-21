import asyncio
import logging
from functools import partial
from brxy.node import client_pool, Process
import argparse
import os


logger = logging.getLogger(__name__)


async def catch_and_log_exceptions(*args, **kwargs):
    try:
        await client_pool(*args, **kwargs)
    except Exception:
        logger.exception("uncaught exception")


def host_port(a):
    try:
        h, p_s = a.split(':')
        return (h, int(p_s))
    except ValueError:
        msg = "Not a valid host and port: '{0}'.".format(a)
        raise argparse.ArgumentTypeError(msg)


parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('-r', '--route', default=os.getenv('ROUTE', None), required='ROUTE' not in os.environ)
parser.add_argument('-p', '--proxy', type=host_port, default=('127.0.0.1', 9080))
parser.add_argument('--check-port', type=int, default=9080)
parser.add_argument('--app-port', type=int, default=9080)
parser.add_argument('--with-certs', action='store_true')
parser.add_argument('-d', '--debug', action='count', default=0)
parser.add_argument('start_cmd', nargs='*')
args = parser.parse_args()

log_level = (logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG)[args.debug]
logging.basicConfig(format='%(asctime)s %(name)s.%(funcName)s:%(lineno)d %(levelname)s: %(message)s',
                    level=log_level)
logger.warning("logging warning")
logger.info("logging info")
logger.debug("logging debug")

logger.info("connecting to proxy at {}".format(args.proxy))

loop = asyncio.get_event_loop()

server = catch_and_log_exceptions(
    route=args.route,
    process_fun=partial(Process, args.start_cmd),
    proxy_address=args.proxy,
    check_port=args.check_port,
    app_port=args.app_port,
    mount_certs=args.with_certs)
loop.run_until_complete(server)
loop.close()
logger.info("shutting down")
