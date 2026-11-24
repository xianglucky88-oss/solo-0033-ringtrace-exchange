"""Enumerate the feasible explanations of a ledger containing exclusive groups.

An explanation fixes every ordinary (standalone) proof and chooses exactly one
alternative from each pending group. A choice is feasible only when the
resulting chain keeps unique predecessor/successor bands, stays acyclic and has
strictly increasing effective moments — the same rules as a single chain.
"""
from dataclasses import dataclass
from itertools import product

from ..encounters import adjudicate
from ..errors import DomainError
from ..lineage import BandIndex
from ..routes import build_routes


def fixed_links(links, groups=()):
    """Ordinary proofs plus the formally selected proof of decided groups."""
    pending_ids = {group['group_id'] for group in groups if group['state'] == 'pending'}
    return [link for link in links
            if link.get('state', 'active') == 'active'
            and not link.get('group_pending')
            and link.get('group_id') not in pending_ids]


def pending_groups(links, groups):
    pending_ids = {group['group_id'] for group in groups if group['state'] == 'pending'}
    grouped = {}
    for link in links:
        group_id = link.get('group_id')
        if group_id and (group_id in pending_ids or link.get('group_pending')) \
                and link.get('state', 'active') == 'active':
            grouped.setdefault(group_id, []).append(link)
    return [sorted(members, key=lambda link: (link['effective_at'], link['proof']))
            for _, members in sorted(grouped.items())]


@dataclass(frozen=True)
class Explanation:
    code: str
    choices: tuple          # (group_id, proof) pairs, sorted by group_id
    links: tuple            # full chain of links for this explanation
    index: BandIndex


def _all_links(index):
    seen = {}
    for link in (*index.incoming.values(), *index.outgoing.values()):
        seen[link['proof']] = link
    return list(seen.values())


def enumerate_explanations(links, groups):
    base = fixed_links(links, groups)
    options = pending_groups(links, groups)
    if not options:
        chain = tuple(sorted(base, key=lambda link: (link['effective_at'], link['proof'])))
        return [Explanation('X1', (), chain, BandIndex(chain))]

    explanations = []
    counter = 0
    for combo in product(*options):
        chain_links = [*base, *combo]
        index = BandIndex(chain_links)
        probe = BandIndex(base)
        for candidate in combo:
            try:
                probe.verify_link(candidate)
            except DomainError:
                break
            probe = BandIndex([*_all_links(probe), candidate])
        else:
            counter += 1
            choices = tuple((candidate['group_id'], candidate['proof']) for candidate in combo)
            chain = tuple(sorted(chain_links, key=lambda link: (link['effective_at'], link['proof'])))
            explanations.append(Explanation(f'X{counter}', choices, chain, index))
    return explanations


def evaluate(links, groups, reports, sources):
    """Run the existing adjudication/routing pipeline once per explanation."""
    explanations = enumerate_explanations(links, groups)
    evaluations = []
    for explanation in explanations:
        events = adjudicate(reports, explanation.index, sources)
        routes = build_routes(events)
        evaluations.append({'explanation': explanation, 'events': events, 'routes': routes})
    return explanations, evaluations
