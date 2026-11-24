"""Run bounded public workflows against a disposable database."""
from argparse import ArgumentParser
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from wsgiref.simple_server import WSGIRequestHandler, make_server

from ringtrace.__main__ import LocalServer
from ringtrace.api import Application
from ringtrace.database import Database
from tools.requester import BrowserlessClient, Client, LoopbackClient
from tools.workflows import STEPS


class QuietRequests(WSGIRequestHandler):
    def log_message(self, format, *args):
        pass


@contextmanager
def live_client(app):
    with make_server('127.0.0.1', 0, app, server_class=LocalServer, handler_class=QuietRequests) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield LoopbackClient(server.server_port)
        finally:
            server.shutdown()
            thread.join(timeout=5)


def exercise(client, until):
    for scenario in STEPS:
        scenario(client)
        print(f'通过 {scenario.__name__}')
        if scenario.__name__ == until:
            return


def main():
    parser = ArgumentParser(description='真实入口工作流演练')
    parser.add_argument('--through', choices=[step.__name__ for step in STEPS])
    parser.add_argument('--http', action='store_true', help='在临时本机端口上演练')
    options = parser.parse_args()
    with TemporaryDirectory(prefix='ringtrace-check-') as folder:
        database = Database(Path(folder) / 'field.sqlite3')
        database.initialize()
        app = Application(database)
        if options.http:
            with live_client(app) as client:
                exercise(Client(client), options.through)
        else:
            exercise(Client(BrowserlessClient(app)), options.through)


if __name__ == '__main__':
    main()
