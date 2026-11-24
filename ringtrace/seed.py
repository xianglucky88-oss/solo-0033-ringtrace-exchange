from pathlib import Path

from .band_service import register
from .batch_service import ingest
from .codec import decode
from .database import current_revision


EXAMPLES = Path(__file__).resolve().parents[1] / 'examples'


def populate(database):
    with database.transaction(write=True) as connection:
        if current_revision(connection):
            return
        for filename in ('dune.json', 'field.json'):
            ingest(connection, decode((EXAMPLES / filename).read_bytes()))
        register(connection, decode((EXAMPLES / 'reband.json').read_bytes()))
