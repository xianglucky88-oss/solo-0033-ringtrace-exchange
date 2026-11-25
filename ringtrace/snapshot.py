from .coverage import by_site
from .encounters import adjudicate
from .lineage import BandIndex
from .routes import build_routes


LEGACY_FORMAT = 1
RANGE_FORMAT = 2


def assemble(revision, catalog, batches, reports, links):
    bands = BandIndex(links)
    events = adjudicate(reports, bands, catalog['sources'])
    tracks = build_routes(events)
    range_mode = any(row.get('observed_end') is not None for row in reports)
    return {'format': RANGE_FORMAT if range_mode else LEGACY_FORMAT, 'revision': revision,
            'catalog': catalog, 'batches': batches, 'links': links, 'encounters': events,
            'routes': tracks, 'coverage': by_site(catalog['sites'], events, tracks)}
