from . import band_repository, batch_repository, catalog
from .database import current_revision
from .snapshot import assemble


def read_inputs(connection, *, sealed=False):
    return (current_revision(connection), catalog.describe(),
            batch_repository.batches(connection, sealed=sealed),
            batch_repository.reports(connection), band_repository.links(connection))


def current(connection, *, sealed=False):
    return assemble(*read_inputs(connection, sealed=sealed))
