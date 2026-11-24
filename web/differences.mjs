import { empty, node } from './dom.mjs';
import { explanationLabel, location, reasons, time } from './display.mjs';
import { table } from './table.mjs';

function viewLine(view) {
  const detail = view.state === 'confirmed'
    ? `环根 ${view.root} · ${location({}, view.site)} · ${time(view.observed_at)}`
    : (reasons[view.reason] || view.reason);
  return `${explanationLabel(view.explanation)}：${detail}`;
}

function eventLabel(event, catalog) {
  if (!event) return '—';
  const decision = event.state === 'held' ? '待复核' : `${event.root} · ${location(catalog, event.site)} · ${time(event.observed_at)}`;
  const reason = event.reason ? ` · ${reasons[event.reason] || event.reason}` : '';
  const evidence = node('ul');
  for (const row of event.candidates) {
    const proofs = row.proofs.length ? ` · 凭据 ${row.proofs.join('、')}` : '';
    const root = row.root ?? '多解释';
    const identity = `${row.band} ${row.valid_band ? '有效' : '失效'} · 环根 ${root}`;
    const observation = `${location(catalog, row.site)} · ${time(row.observed_at)}`;
    evidence.append(node('li', `${row.source} / ${row.report} · ${identity} · ${observation}${proofs}`));
  }
  const label = node('div');
  label.append(node('p', `${decision}${reason}`));
  if (event.views && event.views.length > 1) {
    label.append(node('p', event.views.map(viewLine).join('；'), 'muted'));
  }
  label.append(evidence);
  return label;
}

function segmentLabel(segment, catalog) {
  if (!segment) return '—';
  if (segment.supporting || segment.failing) {
    const failure = segment.failing;
    const blocker = failure.blocking_report
      ? `，阻断 ${failure.blocking_report.source}/${failure.blocking_report.report}` : '';
    return `待核 ${segment.from_event} → ${segment.to_event} · ${explanationLabel(segment.supporting.explanation)} 成立，`
      + `${explanationLabel(failure.explanation)} 不成立（${reasons[failure.reason] || failure.reason}${blocker}）`;
  }
  const scope = segment.explanations ? ` · ${segment.explanations.map(explanationLabel).join('、')}` : '';
  return `${location(catalog, segment.from_site)} → ${location(catalog, segment.to_site)} · `
    + `${time(segment.start)} → ${time(segment.end)}${scope}`;
}

export function differences(diff, catalog) {
  catalog = catalog || { sources: {}, sites: {} };
  const result = node('div', null, 'stack');
  const events = diff.encounters.map(row => [row.key, eventLabel(row.before, catalog), eventLabel(row.after, catalog)]);
  const segments = diff.segments.map(row => [
    Array.isArray(row.key) ? row.key.join(' / ') : row.key,
    segmentLabel(row.before, catalog), segmentLabel(row.after, catalog)]);
  result.append(node('h3', `遭遇变化 · ${events.length}`),
    events.length ? table(['引用', '变更前', '变更后'], events, '遭遇变化') : empty('没有遭遇变化。'),
    node('h3', `移动证据变化 · ${segments.length}`),
    segments.length ? table(['环根 / 起讫引用', '变更前', '变更后'], segments, '移动证据变化') : empty('没有移动段变化。'));
  return result;
}
