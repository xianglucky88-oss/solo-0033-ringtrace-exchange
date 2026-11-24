from . import band_repository as records
from .database import advance
from .fields import exact_fields, token, utc_time
from .lineage import BandIndex


def register(connection, payload):
    exact_fields(payload, 'proof old_band new_band effective_at')
    row = {'proof': token(payload['proof'], '凭据编号'),
           'old_band': token(payload['old_band'], '旧环号'),
           'new_band': token(payload['new_band'], '新环号'),
           'effective_at': utc_time(payload['effective_at'])}
    BandIndex(records.links(connection)).verify_link(row)
    row['revision'] = advance(connection)
    records.insert_link(connection, row)
    return row
