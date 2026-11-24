"""Find every mid-track absence of a movement segment shared by two releases.

A shared root and shared endpoint events anchor a segment that the reviewer can
recognise in both sealed revisions. Whenever that segment is missing from an
intermediate ledger revision the bird was temporarily absent from the
workbench. Consecutive missing revisions form one absence episode; batches and
reband proofs unrelated to the bird never split an episode because they simply
do not change the segment set.

Every episode is rebuilt only from inputs that had been admitted at the time,
so a backfilled observation, no matter how early its own event time, can never
close a gap that was open before it arrived.
"""
from .codec import decode
from . import history, release_repository
from .errors import DomainError


def segment_index(snapshot):
    return {(track['root'], segment['from_event'], segment['to_event']): segment
            for track in snapshot['routes'] for segment in track['segments']}


def anchor_key(key):
    root, from_event, to_event = key
    return f'{root}:{from_event}->{to_event}'


def shared_anchor_segments(before, after):
    left, right = segment_index(before), segment_index(after)
    return sorted(key for key in left if key in right)


def segment_origin(snapshot, key):
    root, from_event, to_event = key
    segment = segment_index(snapshot)[key]
    track = next(item for item in snapshot['routes'] if item['root'] == root)
    return {'root': root, 'from_event': from_event, 'to_event': to_event,
            'from_site': segment['from_site'], 'to_site': segment['to_site'],
            'start': segment['start'], 'end': segment['end'],
            'kind': segment['kind'], 'event_count': track['event_count']}


def sealed_snapshots(connection, left, right):
    return (decode(release_repository.find_or_404(connection, left)['payload']),
            decode(release_repository.find_or_404(connection, right)['payload']))


def presence_table(connection, before, after, keys):
    """Rebuild every intermediate revision and record which anchors survive."""
    table = []
    for revision in range(before, after + 1):
        available = segment_index(history.snapshot_at(connection, revision))
        table.append({'revision': revision,
                      'anchors': {anchor_key(key): key in available for key in keys}})
    return table


def episode_cause(connection, causes, revision, direction):
    """Trace the batch or proof responsible for a segment disappearing or returning."""
    detail = {'revision': revision, 'direction': direction, 'cause': causes.get(revision)}
    cause = causes.get(revision)
    if not cause:
        return detail
    if cause['kind'] == 'proof':
        link = connection.execute('SELECT * FROM band_link WHERE proof = ?', (cause['identifier'],)).fetchone()
        detail['proof'] = dict(link) if link else None
        return detail
    receipt = connection.execute('SELECT * FROM input_batch WHERE batch = ?', (cause['identifier'],)).fetchone()
    detail['batch'] = dict(receipt) if receipt else None
    if receipt:
        detail['reports'] = [dict(row) for row in connection.execute(
            'SELECT * FROM observation WHERE batch = ? ORDER BY position', (cause['identifier'],))]
    return detail


def finalize(connection, causes, key, missing, before):
    first_missing, last_missing = missing[0], missing[-1]
    return {
        'anchor': segment_origin(before, key),
        'anchor_key': anchor_key(key),
        'missing_revisions': missing,
        'first_missing': first_missing,
        'last_missing': last_missing,
        'recovered_revision': last_missing + 1,
        'loss': episode_cause(connection, causes, first_missing, 'loss'),
        'recovery': episode_cause(connection, causes, last_missing + 1, 'recovery'),
    }


def build(connection, left, right):
    before, after = sealed_snapshots(connection, left, right)
    if left > right:
        raise DomainError('invalid_order', '基准修订须不晚于对照修订。', 400)
    anchors = shared_anchor_segments(before, after)
    if not anchors:
        raise DomainError('shared_anchor_missing', '两版封存没有同环根、同起止遭遇的共有移动段，无法统计中途缺席。', 409)
    presence = presence_table(connection, left, right, anchors)
    available = {row['revision']: row['anchors'] for row in presence}
    causes = history.admitted_identifiers(connection)
    episodes = []
    for key in anchors:
        label = anchor_key(key)
        run_missing = []
        for revision in range(left, right + 1):
            if not available[revision][label]:
                run_missing.append(revision)
            elif run_missing:
                episodes.append(finalize(connection, causes, key, run_missing, before))
                run_missing = []
        if run_missing:
            episodes.append(finalize(connection, causes, key, run_missing, before))
    episodes.sort(key=lambda item: (item['anchor']['start'], item['anchor']['root'], item['first_missing']))
    return {'from_revision': left, 'to_revision': right,
            'anchors': [segment_origin(before, key) for key in anchors],
            'presence': presence, 'episodes': episodes}
