from tests import BaseCase
from pullproxy.proxy.router.right import netstring


class TestParseNetstringFromSocket(BaseCase):

    async def setUp(self):
        pass

    def tearDown(self):
        pass

    async def test_ns(self):
        with self.socketpair() as (client_conn, server_conn):
            client_conn.send(b"4:yolo,")
            ns = await netstring.parse_netstring_from_socket(server_conn)
            self.assertEqual(b"yolo", ns)

    async def test_ns_with_extra_data(self):
        extradata = "extradata"
        with self.socketpair() as (client_conn, server_conn):
            client_conn.send("4:yolo,{}".format(extradata).encode())
            ns = await netstring.parse_netstring_from_socket(server_conn)
            self.assertEqual(b"yolo", ns)
            remaining = await self.loop.sock_recv(server_conn, len(extradata))
            self.assertEqual(extradata.encode(), remaining)

    async def test_patial_ns(self):
        extradata = "extradata"
        with self.socketpair() as (client_conn, server_conn):
            ns_f = netstring.parse_netstring_from_socket(server_conn)
            client_conn.send("4:yol".encode())
            client_conn.send("o,{}".format(extradata).encode())
            ns = await ns_f
            self.assertEqual(b"yolo", ns)
            remaining = await self.loop.sock_recv(server_conn, len(extradata))
            self.assertEqual(extradata.encode(), remaining)

    async def test_bad_ns(self):
        extradata = "extradata"
        with self.socketpair() as (client_conn, server_conn):
            client_conn.send("4yoloooo,{}".format(extradata).encode())
            with self.assertRaises(ValueError):
                await netstring.parse_netstring_from_socket(server_conn)
        with self.socketpair() as (client_conn, server_conn):
            client_conn.send("4:yoloooo,{}".format(extradata).encode())
            with self.assertRaises(ValueError) as e:
                await netstring.parse_netstring_from_socket(server_conn)
            self.assertEqual("4:yoloo not a netstring!!", e.exception.args[0])
