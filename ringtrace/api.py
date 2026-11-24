import re
import sqlite3

from . import (
    band_service, batch_archive, batch_service, correction_repository,
    correction_service, exports, impact, intake_preview, provenance, release_repository,
    release_service, search_query, static, workbench,
)
from .errors import DomainError
from .fields import exact_fields, revision
from .http_io import attachment, body, json_response


IDENTIFIER = r'([A-Z0-9][A-Z0-9-]{0,39})'
REV = r'(\d{1,19})'


def batch_precondition(header):
    if header is None:
        return None
    match = re.fullmatch(f'"{REV}"', header, re.ASCII)
    if not match:
        raise DomainError('invalid_revision', 'If-Match 须为双引号内的试算修订号。')
    return revision(int(match[1]))


class Application:
    def __init__(self, database):
        self.database = database

    def __call__(self, environ, start):
        try:
            host = environ.get('HTTP_HOST', 'localhost').split(':', 1)[0].lower()
            if host not in {'localhost', '127.0.0.1'}:
                raise DomainError('invalid_host', '此服务仅用于本机。', 403)
            method, path = environ['REQUEST_METHOD'], environ['PATH_INFO']
            if method == 'GET' and (path == '/' or path.startswith('/assets/')):
                return static.respond(path, start)
            if method == 'GET':
                return self.read(path, environ, start)
            if method == 'POST':
                return self.write(path, environ, start)
            raise DomainError('method', '此请求方法不可用。', 405)
        except DomainError as error:
            return json_response(start, {'error': error.code, 'message': str(error)}, error.status)
        except sqlite3.OperationalError as error:
            if (error.sqlite_errorcode & 255) != sqlite3.SQLITE_BUSY:
                raise
            return json_response(start, {'error': 'busy', 'message': '资料库正忙，请稍后重试。'}, 503)

    def read(self, path, environ, start):
        with self.database.transaction() as connection:
            if path == '/api/workspace':
                return json_response(start, workbench.current(connection))
            if path == '/api/provenance':
                query = search_query.parse(environ.get('QUERY_STRING', ''))
                return json_response(start, provenance.search(connection, query))
            if path == '/api/releases':
                return json_response(start, release_repository.headers(connection))
            if path == '/api/corrections':
                return json_response(start, {'corrections': correction_repository.list_with_assignments(connection)})
            if match := re.fullmatch('/api/batches/' + IDENTIFIER + r'/source\.json', path):
                receipt = batch_service.receipt(connection, match[1])
                payload = batch_archive.verified_payload(receipt, receipt['reports'])
                return attachment(start, payload, 'application/json; charset=utf-8', f'ringtrace-{match[1]}-source.json')
            if match := re.fullmatch('/api/batches/' + IDENTIFIER, path):
                return json_response(start, batch_service.receipt(connection, match[1]))
            if match := re.fullmatch('/api/links/' + IDENTIFIER + '/impact', path):
                return json_response(start, impact.preview(connection, match[1]))
            if match := re.fullmatch(f'/api/releases/{REV}/compare/{REV}', path, re.ASCII):
                return json_response(start, release_service.reconcile(connection, revision(int(match[1])), revision(int(match[2]))))
            if match := re.fullmatch(rf'/api/releases/{REV}/(verify|evidence\.json|routes\.csv)', path, re.ASCII):
                number = revision(int(match[1]))
                if match[2] == 'verify':
                    return json_response(start, release_service.verify(connection, number))
                payload = release_service.read(connection, number)['payload']
                if match[2] == 'routes.csv':
                    return attachment(start, exports.routes_csv(payload), 'text/csv; charset=utf-8', f'ringtrace-{number}-routes.csv')
                return attachment(start, payload, 'application/json; charset=utf-8', f'ringtrace-{number}-evidence.json')
        raise DomainError('not_found', '未找到请求入口。', 404)

    def write(self, path, environ, start):
        if path not in {'/api/batches', '/api/batch-previews', '/api/links', '/api/releases',
                        '/api/event-corrections', '/api/event-correction-previews'}:
            raise DomainError('not_found', '未找到请求入口。', 404)
        data = body(environ)
        if path == '/api/batch-previews':
            with self.database.transaction() as connection:
                return json_response(start, intake_preview.predict(connection, data))
        if path == '/api/event-correction-previews':
            with self.database.transaction() as connection:
                return json_response(start, correction_service.preview(connection, data))
        with self.database.transaction(write=True) as connection:
            if path == '/api/batches':
                expected = batch_precondition(environ.get('HTTP_IF_MATCH'))
                result = batch_service.ingest(connection, data, expected)
            elif path == '/api/links':
                result = band_service.register(connection, data)
            elif path == '/api/event-corrections':
                expected = batch_precondition(environ.get('HTTP_IF_MATCH'))
                result = correction_service.commit(connection, data, expected)
            else:
                exact_fields(data, 'revision')
                result = release_service.freeze(connection, revision(data['revision']))
        return json_response(start, result, 200 if result.get('replayed') else 201)
