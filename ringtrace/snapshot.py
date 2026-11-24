from .coverage import by_site
from .encounters import adjudicate
from .lineage import BandIndex
from .routes import build_routes


FORMAT_VERSION = 1


def assemble(revision, catalog, batches, reports, links):
    events = adjudicate(reports, BandIndex(links), catalog['sources'])
    tracks = build_routes(events)
    return {'format': FORMAT_VERSION, 'revision': revision, 'catalog': catalog, 'batches': batches,
            'links': links, 'encounters': events, 'routes': tracks,
            'coverage': by_site(catalog['sites'], events, tracks)}
