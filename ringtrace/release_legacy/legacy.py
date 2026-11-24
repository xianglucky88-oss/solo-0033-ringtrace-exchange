"""Deterministic projection used by format-1 sealed releases (single chain, no groups)."""
from ..coverage import by_site
from ..encounters import adjudicate
from ..lineage import BandIndex
from ..routes import build_routes


def assemble_legacy(revision, catalog, batches, reports, links):
    fixed = [link for link in links if not link.get('group_id') and link.get('state', 'active') == 'active']
    events = adjudicate(reports, BandIndex(fixed), catalog['sources'])
    tracks = build_routes(events)
    return {'format': 1, 'revision': revision, 'catalog': catalog, 'batches': batches,
            'links': links, 'encounters': events, 'routes': tracks,
            'coverage': by_site(catalog['sites'], events, tracks)}
