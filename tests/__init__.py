import asynctest
import socket
from contextlib import contextmanager


class BaseCase(asynctest.TestCase):

    @contextmanager
    def socketpair(self):
        server_listener_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_listener_conn = server_listener_conn
        server_listener_conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_listener_conn.bind(('', 0))
        server_listener_conn.listen(5)
        server_listener_conn.setblocking(0)

        self.client_conn = client_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        client_conn.setblocking(0)
        client_conn.connect_ex(server_listener_conn.getsockname())
        server_conn, server_addr = server_listener_conn.accept()
        self.server_conn = server_conn
        server_conn.setblocking(0)
        yield (client_conn, server_conn)
        client_conn.close()
        server_conn.close()
        server_listener_conn.close()
