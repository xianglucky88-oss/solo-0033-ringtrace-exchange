from urllib.parse import parse_qs

from .catalog import SOURCES
from .errors import DomainError
from .fields import revision, token, utc_time


QUERY_KEYS = {'reference', 'band', 'band_mode', 'source', 'from', 'until', 'offset', 'at'}


def number(raw, key):
    if len(raw) > 19 or not raw.isascii() or not raw.isdecimal():
        raise DomainError('invalid_query', f'查询参数 {key} 须是非负整数。')
    return revision(int(raw))


def parse(raw):
    try:
        values = parse_qs(raw, strict_parsing=True, keep_blank_values=True, encoding='utf-8',
                          errors='strict', max_num_fields=len(QUERY_KEYS))
    except (UnicodeError, ValueError):
        raise DomainError('invalid_query', '无法解析追溯索引的查询参数。') from None
    if not values.keys() <= QUERY_KEYS or any(len(items) != 1 for items in values.values()):
        raise DomainError('invalid_query', '追溯查询包含未知参数或重复参数。')
    query = {key: items[0] for key, items in values.items()}
    for key, label in [('reference', '遭遇引用'), ('band', '环号'), ('source', '来源编号')]:
        if key in query:
            query[key] = token(query[key], label)
    mode = query.get('band_mode', 'recorded')
    if mode not in {'recorded', 'root'}:
        raise DomainError('invalid_query', '环号匹配类型须为报文环号或当前环根。')
    if 'source' in query and query['source'] not in SOURCES:
        raise DomainError('unknown_source', '报文来源未登记。')
    for key in ('from', 'until'):
        if key in query:
            query[key] = utc_time(query[key])
    if 'from' in query and 'until' in query and query['from'] >= query['until']:
        raise DomainError('invalid_interval', '开始时刻须早于结束时刻。')
    query['offset'] = number(query.get('offset', '0'), 'offset')
    if 'at' in query:
        query['at'] = number(query['at'], 'at')
    elif query['offset']:
        raise DomainError('missing_revision', '翻页须携带首页返回的修订号。')
    return query
