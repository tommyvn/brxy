import logging
import socket
import asyncio
from functools import partial


logger = logging.getLogger(__name__)


class PeekSock(object):
    def __init__(self, sock):
        self._sock = sock

    def recv(self, *args, **kwargs):
        return self._sock.recv(*args, socket.MSG_PEEK, **kwargs)

    def __getattr__(self, name):
        return getattr(self._sock, name)


async def server(address, handler, _loop):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(address)
    sock.listen(5)
    sock.setblocking(0)
    accept_coro = _loop.sock_accept(sock)
    pending = {accept_coro}
    while True:
        done, pending = await asyncio.wait(pending, return_when='FIRST_COMPLETED')
        if accept_coro in done:
            conn, address = accept_coro.result()
            handler_f = _loop.create_task(handler(conn, address))

            def clean_up(conn, f):
                if conn.fileno() != -1:
                    conn.close()

            handler_f.add_done_callback(partial(clean_up, conn))
            accept_coro = _loop.sock_accept(sock)
            pending.add(handler_f)
            pending.add(accept_coro)
        for t in done:
            exc = t.exception()
            if exc:
                _loop.call_exception_handler({"message": "Error in handler", "exception": exc})
