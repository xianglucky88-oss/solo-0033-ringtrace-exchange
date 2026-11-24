from . import correction_repository as records
from . import correction_engine
from .database import advance
from .delta import compare
from .errors import DomainError
from .fields import exact_fields, revision, token
from .snapshot import assemble
from .workbench import read_inputs


def _payload(payload):
    exact_fields(payload, 'event groups base_revision')
    event = token(payload['event'], '原遭遇引用')
    groups = payload['groups']
    if not isinstance(groups, list) or len(groups) != 2:
        raise DomainError('invalid_groups', '更正须恰好提供两个新号分组。')
    parsed, targets = [], []
    for index, group in enumerate(groups, 1):
        exact_fields(group, 'event reports')
        target = token(group['event'], f'第 {index} 组新遭遇引用')
        rows = group['reports']
        if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
            raise DomainError('empty_group', f'第 {index} 组须至少归入一条报文。')
        members = []
        for row in rows:
            exact_fields(row, 'source report')
            members.append((token(row['source'], '来源编号'), token(row['report'], '报文编号')))
        parsed.append({'event': target, 'reports': members})
        targets.append(target)
    if len(set(targets)) != 2:
        raise DomainError('event_taken', '两个新号须互不相同。')
    base = payload['base_revision']
    if type(base) is not int:
        raise DomainError('invalid_revision', '试算修订号须为非负整数。')
    revision(base)
    return event, parsed, base


def _validate(connection, event, groups, base):
    revision_now, catalog, batches, reports, links, corrections = read_inputs(connection)
    if base != revision_now:
        raise DomainError('stale_revision', '试算所用修订已变化，请刷新后重新试算。', 409)
    occupied = correction_engine.live_events(reports)
    for target in (group['event'] for group in groups):
        if target == event or target in occupied:
            raise DomainError('event_taken', f'新号 {target} 已被占用，整次更正无效。', 409)
    current = correction_engine.reports_of_event(reports, event)
    if not current:
        raise DomainError('unknown_event', '未找到仍在使用该引用的遭遇。', 404)
    members = {(row['source'], row['report']) for row in current}
    chosen, seen = [], set()
    for group in groups:
        for key in group['reports']:
            if key in seen:
                raise DomainError('duplicate_assignment', f'报文 {key[1]} 被重复分入分组，整次更正无效。')
            seen.add(key)
            if key not in members:
                raise DomainError('foreign_report',
                                  f'报文 {key[1]} 不属于遭遇 {event}，混入其他遭遇时整次更正无效。')
            chosen.append(key)
    if set(chosen) != members:
        raise DomainError('missing_assignment',
                          f'遭遇 {event} 的已收报文须一次全部分完，漏分使整次更正无效。')
    return revision_now, catalog, batches, reports, links, corrections, current


def plan(connection, payload):
    event, groups, base = _payload(payload)
    revision_now, catalog, batches, reports, links, corrections, current = _validate(
        connection, event, groups, base)
    rerouted = {(row['source'], row['report']): row['original_event']
                for row in records.routed_reports(connection)}
    next_revision = revision_now + 1
    assignments = []
    for group in groups:
        for source, report in group['reports']:
            original = rerouted.get((source, report), event)
            assignments.append({'source': source, 'report': report,
                                'correction_revision': next_revision,
                                'original_event': original, 'event': group['event']})
    moved = {(item['source'], item['report']): item['event'] for item in assignments}
    proposed_reports = [{**row, 'event': moved.get((row['source'], row['report']), row['event'])}
                        for row in reports]
    baseline = assemble(revision_now, catalog, batches, reports, links, corrections)
    proposed = assemble(next_revision, catalog, batches, proposed_reports, links, corrections)
    return {'event': event, 'groups': groups, 'base_revision': revision_now,
            'revision': next_revision, 'assignments': assignments,
            'baseline': baseline, 'proposed': proposed}


def preview(connection, payload):
    result = plan(connection, payload)
    return {'base_revision': result['base_revision'], 'revision': result['revision'],
            'event': result['event'], 'groups': result['groups'],
            'diff': compare(result['baseline'], result['proposed'])}


def commit(connection, payload, expected=None):
    event, groups, base = _payload(payload)
    if expected is not None and expected != base:
        raise DomainError('stale_revision', '试算所用修订已变化，请刷新后重新试算。', 409)
    result = plan(connection, payload)
    number = advance(connection)
    if number != result['revision']:
        raise DomainError('stale_revision', '修订推进与试算不一致，请刷新后重试。', 409)
    row = {'revision': number, 'source_event': event,
           'first_event': groups[0]['event'], 'second_event': groups[1]['event'],
           'assignments': result['assignments']}
    records.insert_correction(connection, row)
    return {'revision': number, 'event': event,
            'events': [groups[0]['event'], groups[1]['event']],
            'count': len(result['assignments']), 'replayed': False}
