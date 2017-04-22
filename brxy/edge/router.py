import logging
import re
import asyncio
from urllib.parse import parse_qs
from ..util import sock_recv
from .util import PeekSock


logger = logging.getLogger(__name__)

_host_header_re = re.compile(b'^[Hh]ost:\s+(.*?)(?:\:\d+)?\r?\n', re.MULTILINE)


def http(router, router_timeout=5, discover_route_timeout=0.5, _loop=None):
    async def handle(sock, address):
        async def get_host_header():
            buff = b''
            match = None
            ps = PeekSock(sock)
            while not match and len(buff) < 1024:
                prev_buff = buff
                buff = await sock_recv(ps, 1024, _loop=_loop)
                # Switch back to the event loop for a bit.
                # Without this tools like wrk lock up the event loop
                if buff == prev_buff:
                    await asyncio.sleep(0.1)
                logger.debug("buffer is {}".format(buff))
                match = _host_header_re.search(buff)
            if match is None:
                logger.info("{} no match!".format("{}:{}".format(*address)))
                raise Exception("no match!!")
            (route, ) = match.groups()
            return route
        # TODO we're doubling the timeout here, don't
        route = await asyncio.wait_for(get_host_header(), discover_route_timeout, loop=_loop)
        logger.info("matched {}".format(route))
        # logger.info("matched {}".format(route))
        next_handler = await asyncio.wait_for(router(route), router_timeout, loop=_loop)
        await next_handler(sock, address)
    return handle


def netstring(router, router_timeout=5, discover_route_timeout=0.5, _loop=None):
    latest_seq = 0

    async def handle(sock, address):
        nonlocal latest_seq

        async def get_msg():
            buff = await sock_recv(sock, 5, _loop=_loop)
            msg_len_str, buff = buff.split(b':')
            msg_len = int(msg_len_str)
            while len(buff) < msg_len + 1:
                buff += await sock_recv(sock, msg_len + 1 - len(buff), _loop=_loop)
            msg, _comma = buff[:-1], buff[-1]
            assert _comma == 44
            logger.info("{} received".format(msg))
            r = {k: v[0] for k, v in parse_qs(msg).items()}
            return r
            return {k: v[0] for k, v in parse_qs(msg).items()}

        msg = await asyncio.wait_for(get_msg(), discover_route_timeout, loop=_loop)
        logger.info("matched {}".format(msg))
        seq = int(msg.get(b"seq", "0"))
        do_seed = bool(int(msg.get(b"seed", "0")))
        route = msg[b"route"]
        if seq > latest_seq:
            latest_seq = seq
        is_newest = 0
        if seq == latest_seq:
            latest_seq = seq
            is_newest = 1
        response = "is_newest={}".format(is_newest)
        try:
            next_handler = await asyncio.wait_for(router(route, seq=seq, do_seed=do_seed), router_timeout)
        except asyncio.TimeoutError:
            response = "{}&conn=retry".format(response)
            f = asyncio.Future()

            def next_handler(_a, _b):
                return f

            f.set_result(None)
        else:
            response = "{}&conn=connected".format(response)

        await _loop.sock_sendall(sock, '{}:{},'.format(len(response), response).encode())

        await next_handler(sock, address)
    return handle
