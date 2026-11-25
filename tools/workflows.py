"""Walk through the public example and its distinct failure paths."""
import csv
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode

from ringtrace.codec import canonical, decode, digest
from ringtrace.seed import EXAMPLES


def sample(filename):
    return decode((EXAMPLES / filename).read_bytes())


def track(data, root='RING-A'):
    return next(item for item in data['routes'] if item['root'] == root)


def event(data, reference):
    return next(item for item in data['encounters'] if item['event'] == reference)


def edges(data):
    return {(r['from_event'], r['to_event']) for r in track(data)['segments']}


class PageAssets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = []

    def handle_starttag(self, tag, attributes):
        fields = dict(attributes)
        if tag == 'script' and fields.get('type') == 'module':
            self.paths.append(fields['src'])
        if tag == 'link' and fields.get('rel') == 'stylesheet':
            self.paths.append(fields['href'])


def shell(client):
    page = client.call('/')
    assert b'lang="zh-CN"' in page.body
    parser = PageAssets()
    parser.feed(page.body.decode())
    assert len(parser.paths) == 5
    for url in parser.paths:
        assert client.call(url).headers['X-Content-Type-Options'] == 'nosniff'
    root = Path(__file__).resolve().parents[1] / 'web'
    for module in root.rglob('*.mjs'):
        asset = client.call(f'/assets/{module.relative_to(root)}')
        assert asset.headers['Content-Type'].startswith('text/javascript')
    client.call('/assets/does-not-exist.mjs', expect=404)


def ingest(client):
    client.reject('/api/releases', {'revision': 0}, 409, 'empty_release')
    payload = sample('dune.json')
    receipt = client.post('/api/batches', payload)
    assert (receipt['count'], receipt['revision'], receipt['replayed']) == (6, 1, False)
    retried = client.post('/api/batches', payload, expect=200)
    assert retried['sha256'] == receipt['sha256'] and retried['replayed']
    altered = {**payload, 'reports': payload['reports'][1:]}
    client.reject('/api/batches', altered, 409, 'batch_conflict')
    duplicated = {**payload, 'batch': 'CONFLICTING-BATCH'}
    client.reject('/api/batches', duplicated, 409, 'report_conflict')
    broken = {**sample('field.json'), 'reports': [*sample('field.json')['reports'], {'report': 'BAD'}]}
    client.reject('/api/batches', broken, 400, 'invalid_fields')
    malformed = client.call('/api/batches', raw=b'{"batch":1,"batch":2}', expect=400)
    assert malformed.json()['error'] == 'invalid_json'
    assert client.workspace()['revision'] == 1
    client.post('/api/batches', sample('field.json'))


def receipts(client):
    receipt = client.read('/api/batches/DUNE-APR03')
    assert receipt['reports'][0]['event'] == 'E50' and receipt['reports'][0]['position'] == 1
    assert receipt['reports'][1]['recorded_at'].endswith('+08:00')
    assert receipt['reports'][1]['observed_at'] == '2026-04-03T00:00:00Z'
    raw = client.call('/api/batches/DUNE-APR03/source.json').body
    assert raw == canonical(sample('dune.json'))
    assert digest(raw) == receipt['sha256']
    client.call('/api/batches/ABSENT/source.json', expect=404)


def link(client):
    row = client.post('/api/links', sample('reband.json'))
    assert row['effective_at'] == '2026-04-03T22:00:00Z' and row['revision'] == 3
    base = {'proof': 'REJECTED', 'effective_at': '2026-04-07T00:00:00Z'}
    client.reject('/api/links', {**base, 'old_band': 'RING-A', 'new_band': 'RING-C'}, 409, 'link_overlap')
    client.reject('/api/links', {**base, 'old_band': 'RING-B', 'new_band': 'RING-A'}, 409, 'link_cycle')
    client.reject('/api/links', {**base, 'old_band': 'RING-C', 'new_band': 'RING-A'}, 409, 'link_order')
    assert client.workspace()['revision'] == 3


def encounters(client):
    state = client.workspace()
    early, boundary = event(state, 'E10'), event(state, 'E30')
    assert early['reason'] is None and len(early['candidates']) == 2
    assert (boundary['root'], boundary['reason']) == ('RING-A', 'lower_disagreement')
    results = {row['band']: row['valid_band'] for row in boundary['candidates']}
    assert results == {'RING-A': False, 'RING-B': True}
    old = next(row for row in boundary['candidates'] if row['band'] == 'RING-A')
    assert old['proofs'] == ['LINK-APR04']


def routes(client):
    state = client.workspace()
    assert edges(state) == {('E10', 'E20'), ('E20', 'E30'), ('E30', 'E40'), ('E40', 'E50')}
    stay = next(row for row in track(state)['segments'] if row['kind'] == 'stay')
    assert (stay['from_event'], stay['to_event'], stay['elapsed_seconds']) == ('E20', 'E30', 3600)


def coverage(client):
    rows = {row['site']: row for row in client.workspace()['coverage']}
    assert rows['SAND-ISLET']['confirmed'] == 2 and rows['SAND-ISLET']['departures'] == 1
    assert rows['SAND-ISLET']['roots'] == ['RING-A'] and not rows['SAND-ISLET']['held_refs']
    assert rows['SALT-FLAT']['roots'] == ['RING-A', 'RING-C']


def impact(client):
    before = client.workspace()
    report = client.read('/api/links/LINK-APR04/impact')
    assert report['from_revision'] == report['to_revision'] == before['revision']
    changes = {row['key']: row for row in report['encounters']}
    assert changes['E30']['before']['root'] == 'RING-A' and changes['E30']['after']['root'] == 'RING-B'
    assert any(row['key'] == ['RING-A', 'E20', 'E30'] and row['after'] is None for row in report['segments'])
    assert client.workspace() == before
    client.call('/api/links/ABSENT/impact', expect=404)


def provenance(client):
    params = {'band': 'RING-A', 'band_mode': 'root', 'from': '2026-04-04T06:00:00+08:00',
              'until': '2026-04-05T01:00:00Z'}
    results = client.read('/api/provenance?' + urlencode(params))
    assert results['revision'] == 3 and results['next_offset'] is None
    assert {row['report'] for row in results['items']} == {'D30', 'F22'}
    assert {row['valid_band'] for row in results['items']} == {True, False}
    client.call('/api/provenance?offset=25&at=2', expect=409)
    client.call('/api/provenance?offset=25', expect=400)
    invalid = urlencode({'from': params['until'], 'until': params['from']})
    client.call('/api/provenance?' + invalid, expect=400)
    client.call('/api/provenance?band=RING-A&band=RING-B', expect=400)


def preview(client):
    payload = sample('mud-late.json')
    hypothetical = client.post('/api/batch-previews', payload, expect=200)
    assert hypothetical['base_revision'] == 3 and hypothetical['receipt']['revision'] == 4
    example = next(row for row in hypothetical['diff']['encounters'] if row['key'] == 'E40')
    assert example['after']['state'] == 'held' and example['after']['reason'] == 'peer_conflict'
    assert client.workspace()['revision'] == 3
    client.reject('/api/batches', payload, 409, 'stale_revision', headers={'If-Match': '"2"'})
    client.reject('/api/batch-previews', {**payload, 'source': 'ABSENT'}, 400, 'unknown_source')
    assert client.workspace()['revision'] == 3


def freeze(client):
    first = client.post('/api/releases', {'revision': 3})
    assert client.post('/api/releases', {'revision': 3}, expect=200)['sha256'] == first['sha256']
    late = sample('mud-late.json')
    projection = client.post('/api/batch-previews', late, expect=200)['diff']
    client.post('/api/batches', late, headers={'If-Match': '"3"'})
    replay = client.post('/api/batches', late, expect=200, headers={'If-Match': '"3"'})
    assert replay['replayed'] and replay['revision'] == 4
    after = client.workspace()
    row = event(after, 'E40')
    assert row['state'] == 'held' and row['reason'] == 'peer_conflict'
    assert edges(after) == {('E10', 'E20'), ('E20', 'E30')}
    assert track(after)['gaps'][0]['events'] == ['E40']
    assert {row['site'] for row in after['coverage'] if row['held_refs']} == {'REED-INLET', 'SALT-FLAT'}
    client.reject('/api/releases', {'revision': 3}, 409, 'stale_revision')
    client.post('/api/releases', {'revision': 4})
    assert client.read('/api/releases/3/compare/4') == projection
    assert [c['revision'] for c in client.read('/api/releases')] == [4, 3]


def compare(client):
    diff = client.read('/api/releases/3/compare/4')
    changed = {row['key']: row for row in diff['encounters']}
    assert changed['E40']['before']['state'] == 'confirmed' and changed['E40']['after']['state'] == 'held'
    assert len(diff['segments']) == 2 and all(row['after'] is None for row in diff['segments'])
    client.call('/api/releases/3/compare/9', expect=404)


def export(client):
    for revision, batches in ((3, 2), (4, 3)):
        evidence = client.call(f'/api/releases/{revision}/evidence.json')
        assert evidence.headers['Content-Disposition'].startswith('attachment;')
        check = client.read(f'/api/releases/{revision}/verify')
        assert check['matches'] and check['verified_batches'] == batches
        assert check['sha256'] == digest(evidence.body)
        assert event(evidence.json(), 'E40')['state'] == ('confirmed' if revision == 3 else 'held')
    exported = client.call('/api/releases/4/routes.csv')
    rows = list(csv.reader(exported.body.decode('utf-8-sig').splitlines()))
    assert rows[0][0] == '环根' and {(row[1], row[2]) for row in rows[1:]} == {('E10', 'E20'), ('E20', 'E30')}
    client.call('/api/releases/8/routes.csv', expect=404)
    client.call('/api/releases/4/routesXcsv', expect=404)


def late_boundaries(client):
    late = {'batch': 'COINCIDENT', 'source': 'DUNE-DESK', 'reports': [
        dict(sample('dune.json')['reports'][2], report='D20B', event='E21'),
    ]}
    client.post('/api/batches', late)
    state = client.workspace()
    assert edges(state) == set()
    root = track(state)
    assert root['gaps'][0]['reason'] == 'same_time' and root['gaps'][0]['events'] == ['E20', 'E21']
    assert root['gaps'][1]['reason'] == 'held_between'
    assert client.read('/api/releases/4/verify')['matches']


def concurrent_replay(client):
    original = sample('dune.json')['reports'][0]
    records = [dict(original, report=f'D-PAGE-{number:02}', event=f'P-{number:02}', band='RING-Z')
               for number in range(27)]
    new = {'batch': 'NEXT-PAGE', 'source': 'DUNE-DESK', 'reports': records}
    before = client.workspace()['revision']
    gate = Barrier(2, timeout=5)

    def receive():
        gate.wait()
        return client.transport.fetch('POST', '/api/batches', 'application/json', canonical(new), {})

    with ThreadPoolExecutor(max_workers=2) as threads:
        jobs = [threads.submit(receive) for _ in range(2)]
        outcomes = [job.result(timeout=10) for job in jobs]
    assert sorted(row.status for row in outcomes) == [200, 201]
    assert {row.json()['revision'] for row in outcomes} == {before + 1}
    page = client.read('/api/provenance?band=RING-Z')
    assert (page['total'], page['next_offset']) == (27, 25)
    next_page = client.read(f'/api/provenance?band=RING-Z&at={page["revision"]}&offset=25')
    assert [row['report'] for row in next_page['items']] == ['D-PAGE-25', 'D-PAGE-26']
    assert next_page['next_offset'] is None


def range_intake(client):
    payload = sample('sandbar-range.json')
    receipt = client.post('/api/batches', payload)
    assert receipt['count'] == 2 and not receipt['replayed']
    batch = client.read('/api/batches/DUNE-E30-RANGE')
    row = next(item for item in batch['reports'] if item['report'] == 'DR30')
    assert row['recorded_at'].endswith('+08:00') and row['recorded_end'].endswith('+08:00')
    assert (row['observed_at'], row['observed_end']) == ('2026-04-03T21:59:50Z', '2026-04-03T22:00:10Z')
    raw = client.call('/api/batches/DUNE-E30-RANGE/source.json').body
    assert raw == canonical(payload) and digest(raw) == receipt['sha256']
    malformed = {'batch': 'BAD-RANGE', 'source': 'DUNE-DESK', 'reports': [
        {'report': 'X1', 'event': 'EX', 'band': 'RING-B', 'site': 'SAND-ISLET', 'kind': 'recapture',
         'observed_start': '2026-04-04T08:00:00Z', 'observed_end': '2026-04-04T07:00:00Z'}]}
    client.reject('/api/batches', malformed, 400, 'inverted_range')
    half = {'batch': 'BAD-HALF', 'source': 'DUNE-DESK', 'reports': [
        {'report': 'X2', 'event': 'EX', 'band': 'RING-B', 'site': 'SAND-ISLET', 'kind': 'recapture',
         'observed_start': '2026-04-04T08:00:00Z'}]}
    client.reject('/api/batches', half, 400, 'invalid_fields')


def range_encounters(client):
    state = client.workspace()
    assert state['format'] == 2
    e30 = event(state, 'E30')
    # The existing single-second reports pin 22:00:00; the range report can only confirm the same
    # common second, so the intersection stays a single feasible second while all reports remain.
    assert e30['state'] == 'confirmed'
    assert e30['feasible_from'] == e30['feasible_until'] == '2026-04-03T22:00:00Z'
    ranged = next(row for row in e30['candidates'] if row['report'] == 'DR30')
    assert (ranged['valid_from'], ranged['valid_until']) == ('2026-04-03T22:00:00Z', '2026-04-03T22:00:10Z')
    instant = next(row for row in e30['candidates'] if row['report'] == 'D30')
    assert (instant['valid_from'], instant['valid_until']) == ('2026-04-03T22:00:00Z', '2026-04-03T22:00:00Z')
    # Old band before the switch and new band after it share no valid second: the event is held.
    split = {'batch': 'SPLIT', 'source': 'MUD-DESK', 'reports': [
        {'report': 'S1', 'event': 'E70', 'band': 'RING-A', 'site': 'SAND-ISLET', 'kind': 'recapture',
         'observed_start': '2026-04-03T21:59:40Z', 'observed_end': '2026-04-03T21:59:59Z'},
        {'report': 'S2', 'event': 'E70', 'band': 'RING-B', 'site': 'SAND-ISLET', 'kind': 'recapture',
         'observed_start': '2026-04-03T22:00:00Z', 'observed_end': '2026-04-03T22:00:20Z'}]}
    client.post('/api/batches', split)
    state = client.workspace()
    e70 = event(state, 'E70')
    assert e70['state'] == 'held' and e70['reason'] == 'no_common_second'
    assert (e70['blocked_from'], e70['blocked_until']) == ('2026-04-03T21:59:40Z', '2026-04-03T22:00:20Z')
    # A lower-priority range report keeps its source without narrowing the feasible seconds.
    narrow = {'batch': 'NARROW', 'source': 'FIELD-NOTE', 'reports': [
        {'report': 'N1', 'event': 'E32', 'band': 'RING-B', 'site': 'SAND-ISLET', 'kind': 'recapture',
         'observed_start': '2026-04-03T23:00:05Z', 'observed_end': '2026-04-03T23:00:08Z'}]}
    client.post('/api/batches', narrow)
    e32 = event(client.workspace(), 'E32')
    assert e32['state'] == 'confirmed'
    assert (e32['feasible_from'], e32['feasible_until']) == ('2026-04-03T23:00:00Z', '2026-04-03T23:00:30Z')
    assert len(e32['candidates']) == 2


def range_routes(client):
    state = client.workspace()
    root = track(state)
    # The E70 blocking window [21:59:40, 22:00:20] touches both spans around the ring change,
    # so neither E20→E30 nor E30→E32 can stand as provable movements.
    pairs = {(row['from_event'], row['to_event']) for row in root['segments']}
    assert ('E20', 'E30') not in pairs and ('E30', 'E32') not in pairs
    assert any('E70' in gap['events'] and gap['reason'] == 'held_between' for gap in root['gaps'])
    # A clean same-site pair on an untouched root demonstrates feasible bounds and a stay.
    clean = {'batch': 'CLEAN', 'source': 'DUNE-DESK', 'reports': [
        {'report': 'C1', 'event': 'E80', 'band': 'RING-K', 'site': 'SAND-ISLET', 'kind': 'mark',
         'observed_start': '2026-04-05T00:00:00Z', 'observed_end': '2026-04-05T00:00:10Z'},
        {'report': 'C2', 'event': 'E81', 'band': 'RING-K', 'site': 'SAND-ISLET', 'kind': 'recapture',
         'observed_start': '2026-04-05T01:00:00Z', 'observed_end': '2026-04-05T01:00:20Z'}]}
    client.post('/api/batches', clean)
    clean_track = next(item for item in client.workspace()['routes'] if item['root'] == 'RING-K')
    stay = next(row for row in clean_track['segments'] if (row['from_event'], row['to_event']) == ('E80', 'E81'))
    assert stay['kind'] == 'stay'
    assert (stay['start'], stay['start_until'], stay['end'], stay['end_until']) == (
        '2026-04-05T00:00:00Z', '2026-04-05T00:00:10Z', '2026-04-05T01:00:00Z', '2026-04-05T01:00:20Z')
    assert (stay['min_elapsed_seconds'], stay['max_elapsed_seconds']) == (3590, 3620)
    # A third confirmed encounter that can share a span leaves an explicit break point.
    third = {'batch': 'THIRD', 'source': 'DUNE-DESK', 'reports': [
        {'report': 'T1', 'event': 'E82', 'band': 'RING-K', 'site': 'SALT-FLAT', 'kind': 'recapture',
         'observed_start': '2026-04-05T00:30:00Z', 'observed_end': '2026-04-05T00:30:05Z'}]}
    client.post('/api/batches', third)
    clean_track = next(item for item in client.workspace()['routes'] if item['root'] == 'RING-K')
    assert any(gap['reason'] == 'intervening_event' and 'E82' in gap['events'] for gap in clean_track['gaps'])
    assert not any((row['from_event'], row['to_event']) == ('E80', 'E81') for row in clean_track['segments'])


def range_release(client):
    state = client.workspace()
    revision = state['revision']
    client.post('/api/releases', {'revision': revision})
    check = client.read(f'/api/releases/{revision}/verify')
    assert check['matches'] and check['recalculated_sha256']
    evidence = client.call(f'/api/releases/{revision}/evidence.json')
    assert digest(evidence.body) == check['sha256'] and evidence.json()['format'] == 2
    exported = client.call(f'/api/releases/{revision}/routes.csv').body.decode('utf-8-sig').splitlines()
    assert exported[0].startswith('环根,起点引用,终点引用,起点样地,终点样地,起点最早 UTC')
    # Legacy releases with only definite instants still recompute and export the old columns.
    legacy = client.read('/api/releases/3/verify')
    assert legacy['matches']
    legacy_csv = client.call('/api/releases/3/routes.csv').body.decode('utf-8-sig').splitlines()
    assert legacy_csv[0] == '环根,起点引用,终点引用,起点样地,终点样地,起点 UTC,终点 UTC,秒数,类型'


STEPS = (shell, ingest, receipts, link, encounters, routes, coverage, impact, provenance, preview, freeze,
         compare, export, late_boundaries, concurrent_replay, range_intake, range_encounters,
         range_routes, range_release)
