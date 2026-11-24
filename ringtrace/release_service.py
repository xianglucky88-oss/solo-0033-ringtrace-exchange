from . import history, release_repository as records
from .batch_archive import verify_input_batches
from .codec import canonical, decode, digest
from .delta import compare
from .errors import DomainError
from .snapshot import assemble
from .workbench import current


def header(row):
    return {key: row[key] for key in ('revision', 'sha256', 'created_at')}


def freeze(connection, revision):
    """Seal a revision.

    The current revision follows the original capture path. A past revision is
    rebuilt solely from the batches and proofs already admitted at that time:
    backfilling it never advances the working revision, and later batches cannot
    enter the older snapshot. Repeating either kind of seal replays one receipt.
    """
    snapshot = current(connection)
    if not snapshot['encounters']:
        raise DomainError('empty_release', '接收至少一批遭遇报文后才能封存。', 409)
    if revision <= 0 or revision > snapshot['revision']:
        raise DomainError('stale_revision' if revision > snapshot['revision'] else 'unknown_revision',
                          '工作数据已变化，请刷新后再封存。' if revision > snapshot['revision'] else '该修订尚不存在。',
                          409 if revision > snapshot['revision'] else 404)
    if revision == snapshot['revision']:
        backfilled = False
    else:
        snapshot = history.snapshot_at(connection, revision)
        backfilled = True
    previous = records.find(connection, revision)
    if previous:
        return {**header(previous), 'replayed': True, 'backfilled': backfilled}
    payload = canonical(snapshot)
    return {**header(records.add(connection, revision, digest(payload), payload)),
            'replayed': False, 'backfilled': backfilled}


def read(connection, revision):
    row = records.find_or_404(connection, revision)
    if digest(row['payload']) != row['sha256']:
        raise DomainError('damaged_release', '封存摘要不匹配。', 409)
    return row


def verify(connection, revision):
    row = read(connection, revision)
    snapshot = decode(row['payload'])
    reports = []
    for event in snapshot['encounters']:
        for candidate in event['candidates']:
            reports.append({key: value for key, value in candidate.items()
                            if key not in ('root', 'proofs', 'priority', 'valid_band')})
    verified_batches = verify_input_batches(snapshot['batches'], reports)
    rebuilt = assemble(revision, snapshot['catalog'], snapshot['batches'], reports, snapshot['links'])
    recalculated = digest(canonical(rebuilt))
    return {**header(row), 'matches': recalculated == row['sha256'], 'recalculated_sha256': recalculated,
            'verified_batches': verified_batches}


def reconcile(connection, left, right):
    before = decode(read(connection, left)['payload'])
    after = decode(read(connection, right)['payload'])
    return compare(before, after)
