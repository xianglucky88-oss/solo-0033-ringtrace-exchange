from .catalog import SOURCES
from .codec import canonical, digest
from .errors import DomainError
from .fields import exact_fields, token
from .observations import parse_report


def parse_batch(raw):
    exact_fields(raw, 'batch source reports')
    batch = token(raw['batch'], '采集包编号')
    source = token(raw['source'], '来源编号')
    if source not in SOURCES:
        raise DomainError('unknown_source', '报文来源未登记。')
    if not isinstance(raw['reports'], list) or not 1 <= len(raw['reports']) <= 500:
        raise DomainError('invalid_batch_size', '每包须含 1 至 500 条报文。')
    seen = set()
    reports = []
    for position, row in enumerate(raw['reports'], 1):
        try:
            report = parse_report(row)
            if report['report'] in seen:
                raise DomainError('duplicate_report', '包内报文编号重复。')
        except DomainError as error:
            raise DomainError(error.code, f'第 {position} 条报文：{error}') from None
        seen.add(report['report'])
        reports.append(report)
    return batch, source, reports, digest(canonical(raw))
