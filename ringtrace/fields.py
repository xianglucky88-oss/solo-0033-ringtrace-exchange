import re
from datetime import datetime, timezone

from .errors import DomainError


TOKEN = re.compile(r'[A-Z0-9][A-Z0-9-]{0,39}', re.ASCII)
TIMESTAMP = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:Z|[+-][0-9]{2}:[0-9]{2})')


def exact_fields(row, names):
    if not isinstance(row, dict) or row.keys() != set(names.split()):
        raise DomainError('invalid_fields', f'字段应为 {names}。')


def token(value, label):
    if not isinstance(value, str) or not TOKEN.fullmatch(value):
        raise DomainError('invalid_token', f'{label}须为 1 至 40 位大写字母、数字或连字符，并以字母或数字开头。')
    return value


def utc_time(value):
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        raise DomainError('invalid_time', '时刻须精确到秒并包含时区，例如 2026-04-03T08:00:00+08:00。')
    try:
        if value[-1] != 'Z' and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
            raise ValueError('invalid offset')
        dt = datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise DomainError('invalid_time', '时刻或时区超出范围。') from None
    return dt.isoformat(timespec='seconds').replace('+00:00', 'Z')


def revision(value):
    if type(value) is not int or not 0 <= value <= 2**63 - 1:
        raise DomainError('invalid_revision', '修订号须为非负整数。')
    return value
