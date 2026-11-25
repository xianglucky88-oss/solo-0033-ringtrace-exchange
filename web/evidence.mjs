import { badge, node } from './dom.mjs';
import { location, reasons, timeRange } from './display.mjs';
import { table } from './table.mjs';

function observedWindow(row) {
  return timeRange(row.observed_at, row.observed_end);
}

function validity(row) {
  if (!('valid_from' in row)) {
    return `${row.valid_band ? '在有效期' : '时刻不符'}${row.proofs.length ? ` · ${row.proofs.join('、')}` : ''}`;
  }
  if (row.valid_from > row.valid_until) {
    return `区间内环号始终失效${row.proofs.length ? ` · ${row.proofs.join('、')}` : ''}`;
  }
  return `有效秒 ${timeRange(row.valid_from, row.valid_until)}${row.proofs.length ? ` · ${row.proofs.join('、')}` : ''}`;
}

export function showEvidence(event, catalog) {
  const detail = node('div');
  const header = node('p', null, 'evidence-state');
  header.append(badge(event.state === 'confirmed' ? '已确认' : '待复核', event.state === 'confirmed' ? 'good' : 'warn'));
  if (event.reason) header.append(node('span', reasons[event.reason], 'muted'));
  detail.append(header, table(['报文 / 采集包', '来源 / 优先级', '环号 / 环根', '观测秒（原时区拼写）', '样地', '环号凭据与有效秒'],
    event.candidates.map(row => [
      `${row.report} / ${row.batch}`, `${catalog.sources[row.source].label} / ${row.priority}`,
      `${row.band} / ${row.root}`, observedWindow(row), location(catalog, row.site), validity(row),
    ]), '遭遇候选报文'));
  if (event.feasible_from) {
    detail.append(node('p', `共同可行观测秒：${timeRange(event.feasible_from, event.feasible_until)}`, 'muted'));
  }
  if (event.blocked_from) {
    detail.append(node('p', `留置阻断闭区间：${timeRange(event.blocked_from, event.blocked_until)}`, 'muted'));
  }
  return detail;
}
