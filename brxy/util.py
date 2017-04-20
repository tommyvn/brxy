import logging
import asyncio


logger = logging.getLogger(__name__)


def sock_recv(sock, nbytes, _loop=None):
    loop = asyncio.get_event_loop() if _loop is None else _loop
    d_f = loop.sock_recv(sock, nbytes)
    if type(sock) is int:
        fileno = sock
    else:
        fileno = sock.fileno()

    def tidy_read_interest(f):
        if f.cancelled() or f.exception():
            loop.remove_reader(fileno)

    d_f.add_done_callback(tidy_read_interest)
    return d_f
