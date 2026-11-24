from . import band_repository, batch_repository, catalog
from .database import current_revision
from .snapshot import assemble


def read_inputs(connection):
    revision = current_revision(connection)
    catalog_card = catalog.describe()
    batches = batch_repository.batches(connection)
    reports = batch_repository.reports(connection)
    groups = band_repository.groups(connection)
    pending = {group['group_id'] for group in groups if group['state'] == 'pending'}
    links = [{**link, 'group_pending': link.get('group_id') in pending}
             for link in band_repository.links(connection)]
    return revision, catalog_card, batches, reports, links, groups


def current(connection):
    return assemble(*read_inputs(connection))
