from .explanations.engine import evaluate
from .explanations.merge import assemble_projection
from .release_legacy.legacy import assemble_legacy

FORMAT_VERSION = 2


def assemble(revision, catalog, batches, reports, links, groups=None):
    if groups is None:
        return assemble_legacy(revision, catalog, batches, reports, links)
    _, evaluations = evaluate(links, groups, reports, catalog['sources'])
    return assemble_projection(revision, catalog, batches, reports, links, groups, evaluations)
