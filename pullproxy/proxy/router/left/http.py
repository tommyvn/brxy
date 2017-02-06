#!/usr/bin/env python3

import socket
import re
import asyncio
import logging
from aioldsplice import proxy, reader_ready


logger = logging.getLogger(__name__)


# works with carraige returns and newlines
# ignores port numbers after host name
host_header_re = re.compile(b'^[Hh]ost:\s+(.*?)(?:\:\d+)?\r?\n', re.MULTILINE)


async def get_http_route(conn, _loop=None):
    loop = _loop if _loop is not None else asyncio.get_event_loop()
    buff = b''
    match = None
    while not match and len(buff) < 1024:
        await reader_ready(conn.fileno(), _loop=loop)
        buff = conn.recv(1024, socket.MSG_PEEK)
        match = host_header_re.search(buff)
    if match is None:
        address = conn.getpeername()
        logger.info("{} no match!".format("{}:{}".format(*address)))
        raise Exception("no match!!")
    (route, ) = match.groups()
    return route


def router(pools, seed_fun, _loop=None):
    loop = _loop if _loop is not None else asyncio.get_event_loop()

    async def http_router_inner(conn):
        address = conn.getpeername()
        try:
            route = await asyncio.wait_for(get_http_route(conn), 2.5)
        except asyncio.TimeoutError:
            logger.debug("Host header not found in 2.5 seconds in {}".format(
                conn.recv(1024, socket.MSG_PEEK)))
            return
        logger.debug("{} route {} matched".format("{}:{}".format(*address), route))
        f = asyncio.Future()
        while True:
            try:
                if pools[route].qsize() == 0:
                    seed_fun(route)
                other_side_future = await asyncio.wait_for(pools[route].get(), 30)
            except asyncio.TimeoutError:
                logger.warning(
                    "{} timed out waiting for server side".format("{}:{}".format(*address)))
                return
            pools[route].task_done()
            if not other_side_future.cancelled():
                break
        logger.debug("{} other side found, getting connection".format("{}:{}".format(*address)))
        proxy_done_future = asyncio.Future()
        other_side_future.set_result((proxy_done_future, f))
        other_conn = await f
        logger.debug("{} other side found at {}".format("{}:{}".format(*address),
                                                        "{}:{}".format(*other_conn.getpeername())))
        the_proxy = asyncio.ensure_future(proxy(conn, other_conn, _loop=loop))
        the_proxy.add_done_callback(proxy_done_future.set_result)
        conn_fileno = conn.fileno()
        conn_peername = "{}:{}".format(*conn.getpeername())
        other_conn_fileno = other_conn.fileno()
        other_conn_peername = "{}:{}".format(*other_conn.getpeername())
        logger.info("proxy {} from {} ({}) to {} ({}) started".format(
            route.decode(), conn_fileno, conn_peername, other_conn_fileno, other_conn_peername))
        await the_proxy
        logger.info("proxy {} from {} ({}) to {} ({}) complete".format(
            route.decode(), conn_fileno, conn_peername, other_conn_fileno, other_conn_peername))
        return
    return http_router_inner
