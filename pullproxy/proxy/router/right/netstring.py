#!/usr/bin/env python3

import asyncio
import logging
from urllib.parse import parse_qs


logger = logging.getLogger(__name__)


async def parse_netstring_from_socket(sock, _loop=None):
    loop = _loop if _loop is not None else asyncio.get_event_loop()
    # There's an assumption that
    #  1) the netstring is at least two characters long
    #  1) the netstring is less then 999 characters long (or maybe 9999??)
    buff = await loop.sock_recv(sock, 5)
    str_length, buff = buff.split(b':', 1)
    buff += await loop.sock_recv(sock, int(str_length) + 1 - len(buff))
    logger.debug("{} buffer at {}".format("{}:{}".format(*sock.getpeername()), buff))
    try:
        assert buff[-1] == 44, "{}:{} not a netstring!!".format(str_length.decode(), buff.decode())
    except AssertionError as e:
        raise ValueError(*e.args)
    return buff[:-1]


def router(pools, seed_fun):
    loop = asyncio.get_event_loop()

    async def netstring_router_inner(conn):
        address = conn.getpeername()
        ns = await parse_netstring_from_socket(conn, _loop=loop)
        cmd = parse_qs(ns)
        logger.debug("{} command received: {}".format("{}:{}".format(*address), cmd))
        route = cmd[b"route"][0]
        seed = int(cmd.get(b"seed", ["0"])[0])
        seq = int(cmd.get(b"seq", ["0"])[0])
        if seed:
            seed_fun(route)
        logger.debug("{} route {} matched".format("{}:{}".format(*address), route))
        conn_future = asyncio.Future()
        # TODO this is perhaps the point to turn away workers, QueueFull exceptions to re-jig???
        pools[route].put_nowait([seq, conn_future])
        logger.debug("{} new conn ready".format("{}:{}".format(*address)))
        response = "is_newest={}".format(1 if pools[route].highest_priority() == seq else 0)
        try:
            proxy_done_future, next_conn_future = await asyncio.wait_for(conn_future, 5)
        except asyncio.TimeoutError:
            logger.debug("{} server timed out".format("{}:{}".format(*address)))
            response = "{}&conn=retry".format(response)
            conn.send('{}:{},'.format(len(response), response).encode())
            return
        logger.debug("{} new conn connected".format("{}:{}".format(*address)))
        response = "{}&conn=connected".format(response)
        conn.send('{}:{},'.format(len(response), response).encode())
        next_conn_future.set_result(conn)
        logger.debug("server side waiting")
        await proxy_done_future
        logger.debug("server side done")
    return netstring_router_inner
