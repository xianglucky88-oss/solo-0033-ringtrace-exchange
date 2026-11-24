import { badge, button, node } from './dom.mjs';
import { location, reasons, time } from './display.mjs';
import { openCorrection } from './correction.mjs';
import { table } from './table.mjs';

export function showEvidence(event, catalog, ctx) {
  const detail = node('div');
  const header = node('p', null, 'evidence-state');
  header.append(badge(event.state === 'confirmed' ? '已确认' : '待复核', event.state === 'confirmed' ? 'good' : 'warn'));
  if (event.reason) header.append(node('span', reasons[event.reason], 'muted'));
  detail.append(header, table(['报文 / 采集包', '来源 / 优先级', '环号 / 环根', '时间', '样地', '原遭遇编号', '环号凭据'],
    event.candidates.map(row => [
      `${row.report} / ${row.batch}`, `${catalog.sources[row.source].label} / ${row.priority}`,
      `${row.band} / ${row.root}`, time(row.observed_at), location(catalog, row.site),
      row.original_event && row.original_event !== row.event ? row.original_event : '—',
      `${row.valid_band ? '在有效期' : '时刻不符'}${row.proofs.length ? ` · ${row.proofs.join('、')}` : ''}`,
    ]), '遭遇候选报文'));
  if (ctx && event.state === 'held') {
    detail.append(button('按所见拆分更正此遭遇', () => openCorrection(event, ctx), 'primary'));
  }
  return detail;
}
