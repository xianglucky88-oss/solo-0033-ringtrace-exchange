import hashlib
import json

from .errors import DomainError


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(content):
    return hashlib.sha256(content).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result


def invalid_constant(value):
    raise ValueError(value)


def decode(content):
    try:
        value = json.loads(content.decode('utf-8'), object_pairs_hook=unique_object,
                           parse_constant=invalid_constant)
        canonical(value)
        return value
    except (UnicodeError, ValueError, RecursionError):
        raise DomainError('invalid_json', '请输入有效的 UTF-8 JSON，键不能重复。') from None
