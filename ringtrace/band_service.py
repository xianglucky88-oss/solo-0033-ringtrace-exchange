from . import band_repository as records
from .database import advance, current_revision
from .errors import DomainError
from .explanations.engine import enumerate_explanations, fixed_links
from .fields import exact_fields, revision as parse_revision, token, utc_time
from .lineage import BandIndex


def _proof_row(raw, revision, group_id):
    return {'proof': token(raw['proof'], '凭据编号'),
            'old_band': token(raw['old_band'], '旧环号'),
            'new_band': token(raw['new_band'], '新环号'),
            'effective_at': utc_time(raw['effective_at']),
            'revision': revision, 'group_id': group_id}


def _unique_proofs(connection, rows, existing):
    known = {link['proof'] for link in existing}
    seen = set()
    for row in rows:
        if row['proof'] in known or row['proof'] in seen:
            raise DomainError('link_overlap', '凭据编号须唯一，已被占用。', 409)
        seen.add(row['proof'])


def _require_feasible(links, groups, required_proofs):
    """Every alternative that must stay selectable needs a complete explanation."""
    explanations = enumerate_explanations(links, groups)
    if not explanations:
        raise DomainError('no_explanation', '不存在满足谱系规则的完整解释，整次登记不入账。', 409)
    covered = {proof for explanation in explanations for link in explanation.links for proof in [link['proof']]}
    missing = sorted(set(required_proofs) - covered)
    if missing:
        raise DomainError(
            'unexplained_proof',
            f'凭据 {missing[0]} 无法进入任何完整解释，整次登记不入账。', 409)
    return explanations


def _selectable_proofs(links):
    return [link['proof'] for link in links if link.get('state', 'active') == 'active']


def register(connection, payload):
    """Register an ordinary standalone proof (the original single-link flow)."""
    exact_fields(payload, 'proof old_band new_band effective_at')
    existing = records.links(connection)
    groups = records.groups(connection)
    row = _proof_row(payload, current_revision(connection) + 1, None)
    _unique_proofs(connection, [row], existing)
    BandIndex(fixed_links(existing, groups)).verify_link(row)
    candidate_links = [*existing, row]
    _require_feasible(candidate_links, groups, _selectable_proofs(candidate_links))
    row['revision'] = advance(connection)
    records.insert_link(connection, row)
    return {key: row[key] for key in ('proof', 'old_band', 'new_band', 'effective_at', 'revision')}


def register_group(connection, payload):
    """Open a new mutually-exclusive group for one new band."""
    exact_fields(payload, 'new_band proofs')
    new_band = token(payload['new_band'], '新环号')
    raw_proofs = payload['proofs']
    if not isinstance(raw_proofs, list) or not 2 <= len(raw_proofs) <= 50:
        raise DomainError('invalid_fields', '一个互斥组须含 2 至 50 张凭据。')
    existing = records.links(connection)
    groups = records.groups(connection)
    if any(link['new_band'] == new_band and link.get('state', 'active') == 'active' for link in existing):
        raise DomainError('link_overlap', '该新环已被有效凭据或互斥组占用。', 409)
    if any(group['new_band'] == new_band for group in groups):
        raise DomainError('link_overlap', '该新环已登记互斥凭据组。', 409)
    revision = current_revision(connection) + 1
    group_id = f'GROUP-{new_band}'
    rows = []
    old_bands = set()
    for position, raw in enumerate(raw_proofs, 1):
        exact_fields(raw, 'proof old_band effective_at')
        row = _proof_row({**raw, 'new_band': new_band}, revision, group_id)
        if row['old_band'] in old_bands:
            raise DomainError('link_overlap', '同组凭据须指向不同旧环。', 409)
        old_bands.add(row['old_band'])
        rows.append(row)
    _unique_proofs(connection, rows, existing)
    candidate_links = [*existing, *rows]
    candidate_groups = [*groups, {'group_id': group_id, 'new_band': new_band, 'state': 'pending',
                                  'chosen_proof': None, 'revision': revision, 'excluded_note': None,
                                  'members': rows}]
    _require_feasible(candidate_links, candidate_groups, _selectable_proofs(candidate_links))
    new_revision = advance(connection)
    records.insert_group(connection, {'group_id': group_id, 'new_band': new_band, 'state': 'pending',
                                      'chosen_proof': None, 'revision': new_revision, 'excluded_note': None})
    for row in rows:
        row['revision'] = new_revision
        records.insert_link(connection, row)
    return {'group': group_id, 'new_band': new_band, 'revision': new_revision,
            'proofs': [row['proof'] for row in rows]}


def add_alternative(connection, payload):
    """Add another mutually-exclusive proof to a still-pending group."""
    exact_fields(payload, 'group proof old_band effective_at')
    group_id = token(payload['group'], '互斥组编号')
    group = records.find_group(connection, group_id)
    if not group:
        raise DomainError('unknown_group', '未找到互斥凭据组。', 404)
    if group['state'] != 'pending':
        raise DomainError('group_decided', '该组已正式定案，不能再登记凭据。', 409)
    existing = records.links(connection)
    groups = records.groups(connection)
    row = _proof_row({**payload, 'new_band': group['new_band']},
                     current_revision(connection) + 1, group_id)
    _unique_proofs(connection, [row], existing)
    if any(link['old_band'] == row['old_band'] and link.get('group_id') == group_id
           and link.get('state', 'active') == 'active' for link in existing):
        raise DomainError('link_overlap', '同组凭据须指向不同旧环。', 409)
    candidate_links = [*existing, row]
    _require_feasible(candidate_links, groups, _selectable_proofs(candidate_links))
    row['revision'] = advance(connection)
    records.insert_link(connection, row)
    return {key: row[key] for key in ('proof', 'old_band', 'new_band', 'effective_at', 'revision', 'group_id')}


def decide(connection, payload):
    """Formally select one still-feasible proof of a pending group."""
    exact_fields(payload, 'group proof revision')
    expected = parse_revision(payload['revision'])
    if current_revision(connection) != expected:
        raise DomainError('stale_revision', '工作修订已变化，请刷新后再裁定。', 409)
    group_id = token(payload['group'], '互斥组编号')
    proof = token(payload['proof'], '凭据编号')
    group = records.find_group(connection, group_id)
    if not group:
        raise DomainError('unknown_group', '未找到互斥凭据组。', 404)
    if group['state'] != 'pending':
        raise DomainError('group_decided', '该组已正式定案，重复裁定不会推进修订。', 409)
    links = records.links(connection)
    groups = records.groups(connection)
    member_proofs = {link['proof'] for link in links
                     if link.get('group_id') == group_id and link.get('state', 'active') == 'active'}
    if proof not in member_proofs:
        raise DomainError('proof_unavailable', '该凭据不在组内或已被排除，不能选为正式凭据。', 409)

    trial_links = [{**link, 'state': 'excluded'} if link.get('group_id') == group_id and link['proof'] != proof
                   else dict(link) for link in links]
    trial_groups = [{**item, 'state': 'decided', 'chosen_proof': proof} if item['group_id'] == group_id
                    else dict(item) for item in groups]
    explanations = enumerate_explanations(trial_links, trial_groups)
    if not any(proof in (item['proof'] for item in explanation.links) for explanation in explanations):
        raise DomainError('proof_unavailable', '所选凭据当前没有可行解释，不能定案。', 409)

    feasible_proofs = {item['proof'] for explanation in explanations for item in explanation.links}
    new_revision = advance(connection)
    records.decide_group(connection, group_id, proof, new_revision)
    for link in links:
        if link['proof'] == proof or link.get('state', 'active') != 'active':
            continue
        if link.get('group_id') == group_id:
            note = (f'组 {group_id} 正式选定 {proof}，该凭据未被选中'
                    if link['proof'] in feasible_proofs
                    else f'组 {group_id} 正式选定 {proof} 后该凭据不再有可行解释')
            records.mark_link(connection, link['proof'], 'excluded', note)
        elif link['proof'] not in feasible_proofs:
            records.mark_link(connection, link['proof'], 'excluded',
                              f'组 {group_id} 裁定 {proof} 后不再存在可行解释')
    return {'group': group_id, 'proof': proof, 'revision': new_revision,
            'feasible_proofs': sorted(feasible_proofs)}
