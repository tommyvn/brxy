from wsgiref.simple_server import make_server, demo_app
from time import sleep
import argparse
from functools import partial
import os


def slow_server(delay, *args, **kwargs):
    sleep(delay)
    return demo_app(*args, **kwargs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=int(os.getenv('PORT', '8000')))
    parser.add_argument('-d', '--delay', type=float, default=0)
    args = parser.parse_args()
    port = int(os.getenv('PORT', '8000'))

    httpd = make_server('', args.port, partial(slow_server, args.delay))
    print("Serving HTTP on port {}...".format(args.port))
    httpd.serve_forever()
    httpd.handle_request()
