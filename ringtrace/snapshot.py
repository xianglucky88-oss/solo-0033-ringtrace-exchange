from . import correction_engine
from .coverage import by_site
from .encounters import adjudicate
from .lineage import BandIndex
from .routes import build_routes


FORMAT_VERSION = 2


def assemble(revision, catalog, batches, reports, links, corrections):
    events = adjudicate(reports, BandIndex(links), catalog['sources'])
    tracks = build_routes(events)
    return {'format': FORMAT_VERSION, 'revision': revision, 'catalog': catalog, 'batches': batches,
            'links': links, 'corrections': corrections,
            'aliases': correction_engine.event_aliases(corrections, reports),
            'encounters': events, 'routes': tracks,
            'coverage': by_site(catalog['sites'], events, tracks)}
