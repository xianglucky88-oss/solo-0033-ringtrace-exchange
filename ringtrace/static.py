from pathlib import Path

from .errors import DomainError
from .http_io import bytes_response


ROOT = Path(__file__).resolve().parents[1] / 'web'
TYPES = {'.html': 'text/html', '.css': 'text/css', '.mjs': 'text/javascript'}


def respond(path, start):
    relative = 'index.html' if path == '/' else path.removeprefix('/assets/')
    asset = ROOT.joinpath(relative).resolve()
    if not asset.is_relative_to(ROOT) or not asset.is_file() or asset.suffix not in TYPES:
        raise DomainError('not_found', '页面或资源不存在。', 404)
    return bytes_response(start, asset.read_bytes(), TYPES[asset.suffix] + '; charset=utf-8')
