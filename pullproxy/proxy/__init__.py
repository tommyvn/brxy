#!/usr/bin/env python3

import asyncio
import logging
import heapq
from aioldsplice import reader_ready


logger = logging.getLogger(__name__)


# TODO instead of readyness style can I replace this with the completion style sock_accept?
class IncommingConnection(object):
    def __init__(self, conn, _loop=None):
        self._loop = _loop if _loop is not None else asyncio.get_event_loop()
        self._server_conn = conn

    async def __aenter__(self):
        await reader_ready(self._server_conn, _loop=self._loop)
        self._client_conn, self._peer_address = self._server_conn.accept()
        self._fileno = self._client_conn.fileno()
        self._sock_address = self._client_conn.getsockname()
        self._client_conn.setblocking(0)
        logger.debug("fd {} opened, {}:{} -> {}:{}".format(
            self._client_conn.fileno(), *self._peer_address, *self._client_conn.getsockname()))
        return self._client_conn

    async def __aexit__(self, exc_type, exc, tb):
        logger.debug("fd {} closed, {}:{} -> {}:{}".format(
            self._fileno, *self._peer_address, *self._sock_address))
        self._client_conn.close()


class FuturesQueue(asyncio.Queue):

    class PrioList(list):
        def __lt__(self, other):
            # This is really __gt__ but it's done for ghetto max heap instead of default min heap
            return self[0] > other[0]

    def _init(self, maxsize):
        self._queue = []

    def _get(self):
        time, f = heapq.heappop(self._queue)
        f.remove_done_callback(self._clean_cancelled_future)
        return f

    def _clean_cancelled_future(self, item):
        time, f = item
        if f.cancelled():
            logger.debug("cleaning the queue")
            self._queue.remove(item)
            heapq.heapify(self._queue)

    def _put(self, item):
        time, f = item
        f.add_done_callback(lambda _: self._clean_cancelled_future(item))
        heapq.heappush(self._queue, self.PrioList(item))

    def highest_priority(self):
        return self._queue[0][0]


async def acceptor_loop(conn, _r):
    async with IncommingConnection(conn) as client_conn:
        loop = asyncio.get_event_loop()
        loop.create_task(acceptor_loop(conn, _r))
        try:
            await _r(client_conn)
        except Exception:
            logger.exception("uncaught exception")
            raise
