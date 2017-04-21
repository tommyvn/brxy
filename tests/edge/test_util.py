from tests import BaseCase
import socket
import asyncio
from brxy.proxy import simple_proxy
from brxy.edge.util import PeekSock, server


class TestPeekSock(BaseCase):
    async def test_peek(self):
        l, r = socket.socketpair()
        proxy_f = self.loop.create_task(simple_proxy(l, r))
        await self.loop.sock_sendall(l, b'testing')
        data1 = await self.loop.sock_recv(PeekSock(r), 1024)
        data2 = await self.loop.sock_recv(PeekSock(r), 1024)
        self.assertEqual(b'testing', data1)
        self.assertEqual(b'testing', data2)
        l.close()
        await proxy_f


class __TestServer(BaseCase):
    async def test_server(self):
        check_dict = {
            b'a': asyncio.Future(),
            b'b': asyncio.Future()
        }

        async def handler(conn, address):
            data = await self.loop.sock_recv(conn, 1024)
            check_dict[data].set_result(True)

        port = 50000
        server_f = self.loop.create_task(server(('127.0.0.1', port), handler, _loop=self.loop))
        self.loop._run_once()
        # await asyncio.sleep(20)

        r1, w1 = await asyncio.open_connection('127.0.0.1', port, loop=self.loop)
        w1.write(b'a')
        await w1.drain()

        res1 = await check_dict[b'a']
        self.assertTrue(res1)

        r2, w2 = await asyncio.open_connection('127.0.0.1', port, loop=self.loop)
        w2.write(b'b')
        await w2.drain()

        res2 = await check_dict[b'b']
        self.assertTrue(res2)

        server_f.cancel()
        print(server_f)
        await server_f
        print("yolo")
