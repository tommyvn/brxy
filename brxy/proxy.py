import asyncio
from .util import sock_recv
import logging


logger = logging.getLogger(__name__)


async def simple_proxy(l, r, _loop=None):
    logger.info("proxy from {} to {}".format(l, r))

    async def inny_outy(i, o):
        while True:
            data = await sock_recv(i, 1024, _loop=_loop)
            if data:
                await _loop.sock_sendall(o, data)
            else:
                o.close()
                return

    done, pending = await asyncio.wait([inny_outy(l, r),
                                        inny_outy(r, l)],
                                       return_when='FIRST_COMPLETED')
    [p.cancel() for p in pending]
