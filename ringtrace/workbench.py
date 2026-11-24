from . import band_repository, batch_repository, catalog, correction_engine, correction_repository
from .database import current_revision
from .snapshot import assemble


def read_inputs(connection):
    return (current_revision(connection), catalog.describe(), batch_repository.batches(connection),
            correction_engine.effective_reports(connection), band_repository.links(connection),
            correction_repository.corrections(connection))


def current(connection):
    return assemble(*read_inputs(connection))
