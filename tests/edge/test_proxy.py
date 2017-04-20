from tests import BaseCase
from unittest import mock
import socket
import asyncio
from brxy.edge.proxy import simple_proxy


class TestProxy(BaseCase):
    @mock.patch('brxy.util.sock_recv')
    async def test_proxy(self, sock_recv_mock):
        sock_recv_mock.return_value = asyncio.Future()

        left_socket_mock = mock.MagicMock()
        right_socket_mock = mock.MagicMock()

        loop_mock = mock.MagicMock()

        # with mock.patch(self.loop.sock_sendall) as sock_sendall_mock:
        #     sock_sendall_mock.return_value = asyncio.Future()
        #     proxy_coro = self.loop.create_task(simple_proxy(left_socket_mock, right_socket_mock, _loop=self.loop))
        #     self.loop._run_once()
        #     self.assertFalse(sock_sendall_mock.called)
        #     sock_recv_mock().set_result("testing 123")
        #     await proxy_coro

    async def test_simple_proxy_o(self):
        l, r = socket.socketpair()
        proxy_f = self.loop.create_task(simple_proxy(l, r))
        await self.loop.sock_sendall(l, b'testing')
        data = await self.loop.sock_recv(r, 1024)
        self.assertEqual(b'testing', data)

        await self.loop.sock_sendall(r, b'testing')
        data = await self.loop.sock_recv(l, 1024)
        self.assertEqual(b'testing', data)
        l.close()
        await proxy_f
