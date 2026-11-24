import { request } from './client.mjs';
import { button, empty, node } from './dom.mjs';
import { location, time } from './display.mjs';
import { table } from './table.mjs';

function anchorLabel(anchor, catalog) {
  return `${anchor.root} · ${location(catalog, anchor.from_site)} ${anchor.from_event} → `
    + `${location(catalog, anchor.to_site)} ${anchor.to_event} · ${time(anchor.start)} → ${time(anchor.end)}`;
}

function causeLabel(cause) {
  if (!cause) return '工作修订未推进（无新包或凭据）';
  if (cause.kind === 'proof') return `换环凭据 ${cause.identifier}`;
  return `采集包 ${cause.identifier}`;
}

function causeDetail(episode, direction, catalog) {
  const box = node('div');
  const info = episode[direction];
  box.append(node('p', `修订 ${info.revision} · ${causeLabel(info.cause)}`));
  if (info.proof) {
    const proof = info.proof;
    box.append(node('p', `换环：${proof.old_band} → ${proof.new_band}，生效 ${time(proof.effective_at)}`, 'muted'));
  }
  if (info.batch) {
    box.append(node('p', `来源 ${info.batch.source} · 报文 ${info.batch.count} 条`, 'muted'));
    const list = node('ul');
    for (const row of info.reports || []) {
      list.append(node('li', `${row.report} · ${row.band} · ${location(catalog, row.site)} ${row.event} · ${time(row.observed_at)}`));
    }
    box.append(list);
  }
  return box;
}

export function absenceView(gaps, catalog, onBackfill) {
  const panel = node('div', null, 'stack');
  const anchors = node('p', `共有同环根、同起止移动段 ${gaps.anchors.length} 条；发现中途缺席 ${gaps.episodes.length} 段。`, 'muted');
  panel.append(node('h3', `中途缺席 · ${gaps.episodes.length}`), anchors);
  if (!gaps.episodes.length) {
    panel.append(empty('共有移动段在两版之间全程在案，没有中途缺席。'));
    return panel;
  }
  const rows = gaps.episodes.map(episode => {
    const cell = node('div');
    cell.append(node('p', anchorLabel(episode.anchor, catalog)));
    cell.append(node('p', `缺席修订：${episode.missing_revisions.join('、')}（首次失证修订 ${episode.first_missing}，连续缺席最后一版 ${episode.last_missing}，恢复修订 ${episode.recovered_revision}）`, 'muted'));
    const actions = node('div', null, 'actions');
    for (const revision of episode.missing_revisions) {
      actions.append(button(`正式补封修订 ${revision}`, () => onBackfill(revision), 'plain'));
    }
    cell.append(actions);
    return [
      cell,
      causeDetail(episode, 'loss', catalog),
      causeDetail(episode, 'recovery', catalog),
    ];
  });
  panel.append(table(['移动段与缺席修订', '失证凭据 / 采集包', '恢复采集包 / 凭据'], rows, '中途缺席'));
  return panel;
}

export async function loadAbsences(left, right, catalog, onBackfill) {
  const gaps = await request(`/api/releases/${left}/compare/${right}/absences`);
  return absenceView(gaps, catalog, onBackfill);
}
