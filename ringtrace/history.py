"""Rebuild the workbench as it was at any past revision.

Every admitted batch and every reband proof carries the revision that created
it, so a past projection is rebuilt solely from inputs already on the ledger at
that revision. Later backfilled observations never enter an older snapshot and
cannot fill a gap that was genuinely open at the time.
"""
from . import catalog
from .errors import DomainError
from .snapshot import assemble


def inputs_at(connection, revision):
    batches = [dict(row) for row in connection.execute(
        'SELECT * FROM input_batch WHERE revision <= ? ORDER BY revision', (revision,))]
    reports = [dict(row) for row in connection.execute(
        'SELECT * FROM observation WHERE batch IN (SELECT batch FROM input_batch WHERE revision <= ?) '
        'ORDER BY event, source, report', (revision,))]
    links = [dict(row) for row in connection.execute(
        'SELECT * FROM band_link WHERE revision <= ? ORDER BY effective_at, proof', (revision,))]
    return revision, catalog.describe(), batches, reports, links


def snapshot_at(connection, revision):
    current = connection.execute('SELECT revision FROM ledger_meta WHERE singleton = 1').fetchone()[0]
    if revision <= 0 or revision > current:
        raise DomainError('unknown_revision', '该修订尚不存在。', 404)
    snapshot = assemble(*inputs_at(connection, revision))
    if not snapshot['encounters']:
        raise DomainError('empty_release', '该修订尚无遭遇报文，不能封存或对账。', 409)
    return snapshot


def admitted_identifiers(connection):
    """Map each ledger revision to the batch or proof that advanced it."""
    causes = {}
    for row in connection.execute('SELECT revision, batch AS identifier FROM input_batch'):
        causes[row['revision']] = {'kind': 'batch', 'identifier': row['identifier']}
    for row in connection.execute('SELECT revision, proof AS identifier FROM band_link'):
        causes[row['revision']] = {'kind': 'proof', 'identifier': row['identifier']}
    return causes
