import socket
import os
import asyncio
import logging
import datetime
import time
import random
import signal
from urllib.parse import parse_qs
from functools import partial
from aioldsplice import proxy, reader_ready, writer_ready


DRIE_BASE_DIR = "/var/drie/apps"
# TESTING_STUFF = False
TESTING_STUFF = True
PROC = "web"

logger = logging.getLogger(__name__)

loop = asyncio.get_event_loop()


async def client(route, proxy_address, start_time=0, do_seed_bool=False,
                 server_address=None, server_conn=None):
    loop = asyncio.get_event_loop()
    do_seed = 1 if do_seed_bool else 0
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client.setblocking(0)
    client.connect_ex(proxy_address)
    address = client.getsockname()
    await writer_ready(client.fileno(), _loop=loop)
    cmd = "seq={}&route={}&seed={}".format(start_time, route, do_seed)
    client.send('{}:{},'.format(len(cmd), cmd).encode())
    await reader_ready(client.fileno(), _loop=loop)
    # TODO massive assumtion that 5 bytes of the NS is ready to read here...
    buff = client.recv(5)
    str_length, buff = buff.split(b':', 1)
    length = int(str_length)
    while len(buff) < length + 1:
        await reader_ready(client.fileno(), _loop=loop)
        buff += client.recv(length + 1 - len(buff))
        logger.debug("{} buffer at {}".format("{}:{}".format(*address), buff))
    assert buff[-1] == 44, "{}:{} not a netstring!!".format(length, buff)
    cmd_r = parse_qs(buff[:-1])
    logger.debug("{} command response received: {}".format("{}:{}".format(*address), cmd_r))
    conn_state = cmd_r[b"conn"][0]
    is_newest = cmd_r[b"is_newest"][0]

    connected = False
    if conn_state == b"connected":
        if server_conn is None:
            server_conn = await asyncio.wait_for(connect_address(server_address), 10)
        logger.info("proxy {} from {} to {}".format(
            route, "{}:{}".format(*client.getsockname()),
            "{}:{}".format(*server_conn.getpeername())))
        await proxy(client, server_conn, _loop=loop)
        connected = True
    client.shutdown(socket.SHUT_RDWR)
    # client.close()
    return {"connected": connected, "is_newest": is_newest}


async def connect_address(address):
    connected = False
    while not connected:
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        conn.setblocking(0)
        conn.connect_ex(address)
        try:
            await writer_ready(conn.fileno(), _loop=loop)
        except asyncio.CancelledError:
            logger.warning("connect cancelled, tidying up connection")
            conn.close()
            return
        err = conn.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
        if not err:
            return conn
        logger.debug("connect {} to {} failed, retrying".format("{}:{}".format(
            *conn.getsockname()), "{}:{}".format(*address)))
        conn.close()
        # TODO not sure if this is necessary, would the await above get the cancelled error?
        try:
            await asyncio.sleep(0.25)
        except asyncio.CancelledError:
            logger.error("connect cancelled, THE LINE I WASN'T SURE WAS NECESSARY IS NECESSARY")
            return


class Process(object):
    def __init__(self, cmd, port):
        self._cmd = cmd
        self._port = port

    async def __aenter__(self):
        print("will run {}".format(self._cmd))
        self._process = await asyncio.create_subprocess_exec(
            *self._cmd, env={"PORT": str(self._port)},
            preexec_fn=os.setsid)
        logger.info("started {} at pid {}".format(self._cmd, self._process.pid))
        return self._process

    async def __aexit__(self, exc_type, exc, tb):
        os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
        try:
            result = await asyncio.wait_for(asyncio.ensure_future(self._process.wait()), 10)
        except asyncio.TimeoutError:
            logger.info("sending SIGKILL to {} {}".format(self._process.pid, self._cmd))
            os.killpg(os.getpgid(self._process.pid), signal.SIGKILL)
        result = await asyncio.wait_for(self._process.wait(), 10)
        logger.info("stopped {} at pid {} with exit code {}".format(self._cmd, self._process.pid, result))
        if exc is not None:
            raise exc
        return result


# TODO get pool_size from app config
async def client_pool(route, process_fun, proxy_address, check_port, app_port, mount_certs, pool_size=10):
    loop = asyncio.get_event_loop()
    last_connect = datetime.datetime.now()
    start_time = int(time.time() * 1000000)

    port = random.randint(60000, 65500)
    c_port = random.randint(50000, 55500) if check_port != app_port else port
    server_address = ('127.0.0.1', port)
    server_check_address = ('127.0.0.1', c_port)
    async with process_fun(port) as process:

        server_conn = await asyncio.wait_for(connect_address(server_check_address), 60)

        address = server_conn.getsockname()
        logger.info("port {} up from {}".format(port, "{}:{}".format(*address)))

        # TODO this might be bad. We connect but then just drop the conn. Are all http servers OK with this?
        #      If it's a non-http service does this mess with any protocols? What I do know is unicorn times
        #      out connections after 15 seconds by default and not doing this certainly messes with that.
        server_conn.close()

        client_partial_fun = partial(client, route, proxy_address=proxy_address, start_time=start_time)

        clients = [client_partial_fun(server_address=server_address)]
        first_client = True

        def do_seed_gen(every=10):
            next_seed = False
            while True:
                seed = True if next_seed is None else next_seed
                for i in range(0, every):
                    next_seed = (yield seed)
                    if seed is True:
                        seed = False
                    if next_seed is not None:
                        yield True
                        break

        do_seed = do_seed_gen(100)

        def flip_sighup():
            # Force seed
            logger.warning("{} sighup'ed, sending seed request".format("{}:{}".format(*address)))
            # TODO figure out why we need to double tap here to make it work
            do_seed.send(True)
            do_seed.send(True)

        loop.add_signal_handler(signal.SIGHUP, flip_sighup)
        is_newest_instance = True
        # TODO this breaks if connections last longer then 30 seconds,
        #      like with websockets and all the other shiz I want to support
        if TESTING_STUFF:
            newest_connect_timeout = 20
            older_connect_timeout = 5
        else:
            newest_connect_timeout = 300
            older_connect_timeout = 10

        while (process.returncode is None and
               ((is_newest_instance and datetime.datetime.now() - last_connect < datetime.timedelta(seconds=newest_connect_timeout)) or
                (datetime.datetime.now() - last_connect < datetime.timedelta(seconds=older_connect_timeout)))):
            done, pending = await asyncio.wait(clients, return_when=asyncio.FIRST_COMPLETED)
            try:
                next(filter(lambda d: d.exception() is not None, done))
            except StopIteration:
                pass
            clients = list(pending)
            done_results = list(map(lambda f: f.result(), done))
            is_newest_instance = True if done_results[0]['is_newest'] == b'1' else False
            logger.debug("{} {} newest instance".format("{}:{}".format(*address), "is" if is_newest_instance else "isn't"))
            if True in map(lambda r: r['connected'], done_results):
                if first_client:
                    first_client = False
                last_connect = datetime.datetime.now()
            # TODO figure out how to append a map to a set
            is_seed_request = next(do_seed)
            if first_client:
                # Force a reset so we stay not seeding for unused instances
                do_seed.send(False)
            number_required = pool_size - len(pending)
            if is_seed_request:
                clients.append(client_partial_fun(do_seed_bool=True, server_address=server_address))
                number_required -= 1
            clients.extend(map(lambda _: client_partial_fun(server_address=server_address),
                               range(0, number_required)))
        logger.info("{} no connections, draining and shutting down".format("{}:{}".format(*address)))
        loop.remove_signal_handler(signal.SIGHUP)
        done, pending = await asyncio.wait(clients)
        try:
            next(filter(lambda d: d.exception() is not None, done))
        except StopIteration:
            pass
    result = await process.wait()
    return result
