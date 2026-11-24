from .catalog import KINDS, SITES
from .errors import DomainError
from .fields import exact_fields, token, utc_time


def parse_report(raw):
    exact_fields(raw, 'report event band site kind observed_at')
    if not isinstance(raw['site'], str) or raw['site'] not in SITES:
        raise DomainError('unknown_site', '遭遇样地未登记。')
    if not isinstance(raw['kind'], str) or raw['kind'] not in KINDS:
        raise DomainError('unknown_kind', '遭遇类别须为 mark 或 recapture。')
    return {
        'report': token(raw['report'], '报文编号'), 'event': token(raw['event'], '遭遇引用'),
        'band': token(raw['band'], '环号'), 'site': raw['site'], 'kind': raw['kind'],
        'observed_at': utc_time(raw['observed_at']), 'recorded_at': raw['observed_at'],
    }
