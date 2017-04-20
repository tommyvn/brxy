import logging
import asyncio
import heapq


logger = logging.getLogger(__name__)


async def left(queue, proxy, route, seed_fun=None, seq=None, do_seed=False, _loop=None):
    if seq is not None:
        logger.warn("seq passed but isn't used in left")
    if do_seed or queue[route].qsize() == 0:
        seed_fun(route)
    linked_f = await queue[route].get()
    other_side_sock_f = asyncio.Future()
    done_f = asyncio.Future()
    linked_f.set_result((other_side_sock_f, done_f))
    other_sock = await other_side_sock_f

    async def next_server(sock, address):
        await proxy(sock, other_sock, _loop=_loop)
        done_f.set_result(True)

    return next_server


async def right(queue, route, seed_fun=None, seq=1, do_seed=False, _loop=None):
    if do_seed:
        seed_fun(route)
    other_side_linked_f = asyncio.Future()
    queue[route].put_nowait([seq, other_side_linked_f])
    sock_f, other_side_done_f = await other_side_linked_f

    async def next_server(sock, address):
        sock_f.set_result(sock)
        await other_side_done_f

    return next_server


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
