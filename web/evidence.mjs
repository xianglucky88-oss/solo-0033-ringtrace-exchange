import { badge, node } from './dom.mjs';
import { explanationLabel, location, reasons, time } from './display.mjs';
import { table } from './table.mjs';

function viewRow(view, catalog) {
  const identity = view.state === 'confirmed'
    ? `环根 ${view.root} · ${location(catalog, view.site)} · ${time(view.observed_at)}`
    : reasons[view.reason] || view.reason;
  return [explanationLabel(view.explanation), view.state === 'confirmed' ? '已确认' : '留置', identity];
}

function candidateRow(row, catalog) {
  const views = (row.views || []).map(view =>
    `${explanationLabel(view.explanation)}：环根 ${view.root} · ${view.valid_band ? '在有效期' : '时刻不符'}`
    + (view.proofs.length ? ` · ${view.proofs.join('、')}` : '')).join('；');
  return [
    `${row.report} / ${row.batch}`,
    `${catalog.sources[row.source].label} / ${row.priority}`,
    `${row.band} / ${row.root ?? '多解释'}`,
    time(row.observed_at), location(catalog, row.site), views,
  ];
}

export function showEvidence(event, catalog) {
  const detail = node('div');
  const header = node('p', null, 'evidence-state');
  header.append(badge(event.state === 'confirmed' ? '已确认' : '待复核', event.state === 'confirmed' ? 'good' : 'warn'));
  if (event.reason) header.append(node('span', reasons[event.reason] || event.reason, 'muted'));
  detail.append(header);
  if (event.views && event.views.length > 1) {
    detail.append(node('h3', '各可行解释下的结论'),
      table(['解释', '状态', '结论'], event.views.map(view => viewRow(view, catalog)), '解释结论'));
  }
  detail.append(node('h3', '候选报文'),
    table(['报文 / 采集包', '来源 / 优先级', '环号 / 环根', '时间', '样地', '各解释下的凭据'],
      event.candidates.map(row => candidateRow(row, catalog)), '遭遇候选报文'));
  return detail;
}
