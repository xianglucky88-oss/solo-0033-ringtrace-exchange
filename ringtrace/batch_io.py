from .catalog import SOURCES
from .codec import canonical, digest
from .errors import DomainError
from .fields import exact_fields, token
from .observations import parse_report


def split_envelope(raw):
    """Accept either a plain collection package or an envelope carrying routing."""
    if not isinstance(raw, dict):
        raise DomainError('invalid_fields', '请求体须为 JSON 对象。')
    if set(raw) == {'batch', 'source', 'reports'}:
        return raw, []
    exact_fields(raw, 'package routing')
    package, routing = raw['package'], raw['routing']
    if not isinstance(package, dict):
        raise DomainError('invalid_fields', 'package 须为采集包对象。')
    if not isinstance(routing, list) or not all(isinstance(row, dict) for row in routing):
        raise DomainError('invalid_routing', 'routing 须为逐行归属对象数组。')
    return package, routing


def parse_routing(routing, count):
    parsed = []
    seen = set()
    for row in routing:
        exact_fields(row, 'position event')
        if type(row['position']) is not int or not 1 <= row['position'] <= count:
            raise DomainError('invalid_routing', '归属行号须位于采集包行号范围内。')
        if row['position'] in seen:
            raise DomainError('invalid_routing', '同一行不得重复指定归属。')
        seen.add(row['position'])
        parsed.append({'position': row['position'], 'event': token(row['event'], '归属遭遇引用')})
    return sorted(parsed, key=lambda row: row['position'])


def parse_batch(raw):
    package, routing_rows = split_envelope(raw)
    exact_fields(package, 'batch source reports')
    batch = token(package['batch'], '采集包编号')
    source = token(package['source'], '来源编号')
    if source not in SOURCES:
        raise DomainError('unknown_source', '报文来源未登记。')
    if not isinstance(package['reports'], list) or not 1 <= len(package['reports']) <= 500:
        raise DomainError('invalid_batch_size', '每包须含 1 至 500 条报文。')
    seen = set()
    reports = []
    for position, row in enumerate(package['reports'], 1):
        try:
            report = parse_report(row)
            if report['report'] in seen:
                raise DomainError('duplicate_report', '包内报文编号重复。')
        except DomainError as error:
            raise DomainError(error.code, f'第 {position} 条报文：{error}') from None
        seen.add(report['report'])
        reports.append(report)
    routing = parse_routing(routing_rows, len(reports))
    return batch, source, reports, digest(canonical(package)), routing
