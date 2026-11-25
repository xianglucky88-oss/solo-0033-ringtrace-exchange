from .catalog import KINDS, SITES
from .errors import DomainError
from .fields import observation_window, token, utc_time

INSTANT_FIELDS = 'report event band site kind observed_at'
RANGE_FIELDS = 'report event band site kind observed_start observed_end'


def parse_report(raw):
    if not isinstance(raw, dict) or raw.keys() not in (set(INSTANT_FIELDS.split()), set(RANGE_FIELDS.split())):
        raise DomainError('invalid_fields', f'字段应为 {INSTANT_FIELDS}，或闭合区间 {RANGE_FIELDS}。')
    if not isinstance(raw['site'], str) or raw['site'] not in SITES:
        raise DomainError('unknown_site', '遭遇样地未登记。')
    if not isinstance(raw['kind'], str) or raw['kind'] not in KINDS:
        raise DomainError('unknown_kind', '遭遇类别须为 mark 或 recapture。')
    record = {
        'report': token(raw['report'], '报文编号'), 'event': token(raw['event'], '遭遇引用'),
        'band': token(raw['band'], '环号'), 'site': raw['site'], 'kind': raw['kind'],
    }
    if 'observed_at' in raw:
        record.update({'observed_at': utc_time(raw['observed_at']), 'observed_end': None,
                       'recorded_at': raw['observed_at'], 'recorded_end': None})
    else:
        start_utc, end_utc = observation_window(raw['observed_start'], raw['observed_end'])
        record.update({'observed_at': start_utc, 'observed_end': end_utc,
                       'recorded_at': raw['observed_start'], 'recorded_end': raw['observed_end']})
    return record
