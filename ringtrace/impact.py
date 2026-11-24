from .delta import compare
from .errors import DomainError
from .snapshot import assemble
from .workbench import read_inputs


def preview(connection, proof):
    revision, catalog, batches, reports, links = read_inputs(connection)
    remaining = [link for link in links if link['proof'] != proof]
    if len(remaining) == len(links):
        raise DomainError('unknown_proof', '未找到换环凭据。', 404)
    before = assemble(revision, catalog, batches, reports, links)
    hypothetical = assemble(revision, catalog, batches, reports, remaining)
    return {'proof': proof, **compare(before, hypothetical)}
