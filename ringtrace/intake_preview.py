from .batch_service import assess, metadata, public
from .delta import compare
from .snapshot import assemble
from .workbench import read_inputs


def predict(connection, payload):
    """Preview a package without writing anything.

    The preview lists each encounter group's conclusion with the rejected line
    numbers and reasons. Only the groups that can be received feed the
    forecast of encounter decisions and movement segments, so a conflicting
    group never leaks into the predicted verdict or route changes. When no
    group can be received there is no proposed receipt, only the refusal
    detail.
    """
    receipt, accepted, acceptable = assess(connection, payload)
    revision, catalog, batches, reports, links = read_inputs(connection)
    view = public(receipt)
    no_change = {'from_revision': revision, 'to_revision': revision, 'encounters': [], 'segments': []}
    base = {'base_revision': revision, 'acceptable': acceptable, 'batch': view['batch'],
            'source': view['source'], 'groups': view['groups'], 'lines': view['lines']}
    if receipt['replayed']:
        return {**base, 'receipt': view, 'diff': no_change}
    if not acceptable:
        return {**base, 'receipt': None, 'diff': no_change}
    additions = [dict(entry['record'], source=receipt['source'], batch=receipt['batch'],
                      position=entry['position']) for entry in accepted]
    metadata_row = metadata(receipt)
    baseline = assemble(revision, catalog, batches, reports, links)
    proposed = assemble(receipt['revision'], catalog, [*batches, metadata_row], [*reports, *additions], links)
    return {**base, 'receipt': view, 'diff': compare(baseline, proposed)}
