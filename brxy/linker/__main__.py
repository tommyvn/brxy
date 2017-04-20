import asyncio
import logging
from functools import partial
from . import client_pool, Process
import argparse


logger = logging.getLogger(__name__)


async def catch_and_log_exceptions(*args, **kwargs):
    try:
        await client_pool(*args, **kwargs)
    except Exception:
        logger.exception("uncaught exception")

root = logging.getLogger()
root.setLevel(logging.WARNING)
# root.setLevel(logging.INFO)

logger.setLevel(logging.WARNING)
logger.setLevel(logging.INFO)

consoleHandler = logging.StreamHandler()
consoleHandler.setLevel(logging.DEBUG)


def host_port(a):
    try:
        h, p_s = a.split(':')
        return (h, int(p_s))
    except ValueError:
        msg = "Not a valid host and port: '{0}'.".format(a)
        raise argparse.ArgumentTypeError(msg)


parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('route')
parser.add_argument('-p', '--proxy', type=host_port, default=('127.0.0.1', 9080))
parser.add_argument('--check-port', type=int, default=9080)
parser.add_argument('--app-port', type=int, default=9080)
parser.add_argument('--with-certs', action='store_true')
parser.add_argument('start_cmd', nargs='*')

args = parser.parse_args()

formatter = logging.Formatter(
  '%(asctime)s - %(name)s:{}:%(process)d:%(lineno)d - %(levelname)s - %(message)s'.format(args.route))
consoleHandler.setFormatter(formatter)

root.addHandler(consoleHandler)
# logger.addHandler(consoleHandler)
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
