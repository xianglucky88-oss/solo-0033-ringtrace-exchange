from .batch_service import prepare
from .delta import compare
from .snapshot import assemble
from .workbench import read_inputs


def predict(connection, payload):
    receipt, records, routing = prepare(connection, payload)
    revision, catalog, batches, reports, links, corrections = read_inputs(connection)
    if receipt['replayed']:
        return {'base_revision': revision, 'receipt': receipt,
                'diff': {'from_revision': revision, 'to_revision': revision, 'encounters': [], 'segments': []}}
    additions = [dict(record, source=receipt['source'], batch=receipt['batch'], position=index,
                      original_event=routing[index - 1]['original_event'],
                      event=routing[index - 1]['event'])
                 for index, record in enumerate(records, 1)]
    metadata = {key: value for key, value in receipt.items() if key != 'replayed'}
    baseline = assemble(revision, catalog, batches, reports, links, corrections)
    proposed = assemble(receipt['revision'], catalog, [*batches, metadata], [*reports, *additions], links, corrections)
    return {'base_revision': revision, 'receipt': receipt, 'routing': routing,
            'diff': compare(baseline, proposed)}
