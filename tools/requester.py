from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from wsgiref.util import setup_testing_defaults
import io
from urllib.parse import urlsplit

from ringtrace.codec import canonical, decode


@dataclass
class Response:
    status: int
    headers: dict
    body: bytes

    def json(self):
        return decode(self.body)


class BrowserlessClient:
    """Drive the production WSGI application without requiring a listening socket."""

    def __init__(self, app):
        self.app = app

    def fetch(self, method, path, mime, data, headers):
        url = urlsplit(path)
        environ = {}
        setup_testing_defaults(environ)
        environ.update(REQUEST_METHOD=method, PATH_INFO=url.path, QUERY_STRING=url.query,
                       HTTP_HOST='localhost', CONTENT_TYPE=mime, CONTENT_LENGTH=str(len(data)))
        environ['wsgi.input'] = io.BytesIO(data)
        environ.update({'HTTP_' + key.upper().replace('-', '_'): value for key, value in headers.items()})
        head = []

        def start(status, response_headers):
            head.extend((int(status.split()[0]), dict(response_headers)))

        response = self.app(environ, start)
        return Response(*head, b''.join(response))


class LoopbackClient:
    def __init__(self, port):
        self.url = f'http://127.0.0.1:{port}'

    def fetch(self, method, path, mime, data, headers):
        req = Request(self.url + path, data=data if method == 'POST' else None,
                      headers={'Content-Type': mime, **headers}, method=method)
        try:
            result = urlopen(req, timeout=5)
        except HTTPError as error:
            result = error
        with result:
            return Response(result.status, dict(result.headers.items()), result.read())


class Client:
    def __init__(self, transport):
        self.transport = transport

    def call(self, path, *, body=None, raw=None, expect=200, headers=None, mime='application/json'):
        payload = raw if raw is not None else canonical(body) if body is not None else None
        response = self.transport.fetch('POST' if payload is not None else 'GET', path, mime,
                                        payload if payload is not None else b'', headers or {})
        if response.status != expect:
            raise AssertionError(f'{path}: HTTP {response.status}, expected {expect}. {response.body[:300]!r}')
        return response

    def read(self, path):
        return self.call(path).json()

    def post(self, path, body, expect=201, headers=None):
        return self.call(path, body=body, expect=expect, headers=headers).json()

    def reject(self, path, body, expect, code, headers=None):
        actual = self.post(path, body, expect=expect, headers=headers)['error']
        assert actual == code, (path, code, actual)

    def workspace(self):
        return self.read('/api/workspace')
