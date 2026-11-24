from argparse import ArgumentParser
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, make_server

from .api import Application
from .database import Database
from .seed import populate


class LocalServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def main():
    parser = ArgumentParser(description='翎迹环志证据台')
    parser.add_argument('--port', type=int, default=8864, help='本机 HTTP 端口，0 表示自动选择')
    parser.add_argument('--db', default='var/ringtrace.sqlite3', help='本机 SQLite 文件路径')
    parser.add_argument('--demo', action='store_true', help='仅在空库载入合成资料')
    args = parser.parse_args()
    database = Database(args.db)
    database.initialize()
    if args.demo:
        populate(database)
    with make_server('127.0.0.1', args.port, Application(database), server_class=LocalServer) as server:
        print(f'翎迹已启动：http://127.0.0.1:{server.server_port}', flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
