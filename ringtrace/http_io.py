from http import HTTPStatus

from .codec import canonical, decode
from .errors import DomainError


MAX_BODY = 2 * 1024 * 1024


def body(environ):
    if environ.get('CONTENT_TYPE', '').partition(';')[0].strip().lower() != 'application/json':
        raise DomainError('content_type', '请求须使用 application/json。', 415)
    try:
        size = int(environ.get('CONTENT_LENGTH', ''))
    except ValueError:
        raise DomainError('invalid_size', '请求须包含有效的内容长度。', 411) from None
    if not 0 <= size <= MAX_BODY:
        raise DomainError('body_too_large', '请求内容须小于或等于 2 MiB。', 413)
    return decode(environ['wsgi.input'].read(size))


def bytes_response(start, data, media, status=200, headers=()):
    start(f'{status} {HTTPStatus(status).phrase}', [
        ('Content-Type', media), ('Content-Length', str(len(data))),
        ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff'),
        ('Content-Security-Policy', "default-src 'self'; object-src 'none'; frame-ancestors 'none'"),
        *headers,
    ])
    return [data]


def json_response(start, data, status=200):
    return bytes_response(start, canonical(data), 'application/json; charset=utf-8', status)


def attachment(start, data, media, filename):
    return bytes_response(start, data, media, headers=[('Content-Disposition', f'attachment; filename="{filename}"')])
