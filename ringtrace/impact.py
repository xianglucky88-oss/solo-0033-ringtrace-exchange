from .delta import compare
from .errors import DomainError
from .snapshot import assemble
from .workbench import read_inputs


def preview(connection, proof):
    revision, catalog, batches, reports, links, groups = read_inputs(connection)
    target = next((link for link in links if link['proof'] == proof), None)
    if target is None:
        raise DomainError('unknown_proof', '未找到换环凭据。', 404)
    before = assemble(revision, catalog, batches, reports, links, groups)

    remaining_links = [{**link, 'state': 'excluded'} if link['proof'] == proof else dict(link)
                       for link in links]
    remaining_groups = []
    for group in groups:
        updated = dict(group)
        updated['members'] = [dict(link) for link in group['members'] if link['proof'] != proof]
        if target.get('group_id') == group['group_id'] and not updated['members']:
            continue
        remaining_groups.append(updated)
    hypothetical = assemble(revision, catalog, batches, reports, remaining_links, remaining_groups)
    return {'proof': proof, **compare(before, hypothetical)}
