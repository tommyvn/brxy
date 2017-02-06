import asynctest
import pullproxy.proxy
import aioldsplice
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


class TestIncommingConnection(BaseCase):

    async def setUp(self):
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
        await aioldsplice.writer_ready(client_conn)

    async def tearDown(self):
        self.server_listener_conn.close()
        self.client_conn.close()

    async def test_incomming_connection(self):
        async with pullproxy.proxy.IncommingConnection(self.server_listener_conn) as server_conn:
            await aioldsplice.writer_ready(server_conn)
            msg = b"testing 1234"
            server_conn.sendall(msg)
            await aioldsplice.reader_ready(self.client_conn)
            self.assertEquals(msg, self.client_conn.recv(1024))

    async def test_nonblocking(self):
        async with pullproxy.proxy.IncommingConnection(self.server_listener_conn) as server_conn:
            self.assertEquals(server_conn.gettimeout(), 0)

    async def test_conn_closed_out_of_context(self):
        async with pullproxy.proxy.IncommingConnection(self.server_listener_conn) as server_conn:
            pass
        self.assertEquals(self.client_conn.recv(1), b'')
        with self.assertRaises(OSError) as e:
            self.assertEquals(server_conn.recv(1), "")
        self.assertEquals(e.exception.errno, 9)

    async def test_closed_in_context_doesnt_exception(self):
        async with pullproxy.proxy.IncommingConnection(self.server_listener_conn) as server_conn:
            server_conn.close()

    async def test_exception_in_context(self):
        class TestException(Exception):
            pass

        with self.assertRaises(TestException):
            slconn = self.server_listener_conn
            async with pullproxy.proxy.IncommingConnection(slconn) as server_conn:
                raise TestException()
        self.assertEquals(self.client_conn.recv(1), b'')
        with self.assertRaises(OSError) as e:
            self.assertEquals(server_conn.recv(1), "")
        self.assertEquals(e.exception.errno, 9)

    # async def test_await_same_future_twice(self):
    #     import asyncio
    #     f = asyncio.Future()
    #     async def test(f):
    #         result = await f
    #         return result
    #     cl = self.loop.call_later(2, f.set_result("worked"))
    #     done, pending = await asyncio.wait([test(f), test(f)])
    #     # print(dir(asyncio))
    #     result = await f
    #     self.assertEquals(result, "worked")
