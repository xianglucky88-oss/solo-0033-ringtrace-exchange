import { empty, node } from './dom.mjs';
import { location, reasons, time } from './display.mjs';
import { table } from './table.mjs';

function eventLabel(event, catalog) {
  if (!event) return '—';
  const decision = event.state === 'held' ? '待复核' : `${event.root} · ${location(catalog, event.site)} · ${time(event.observed_at)}`;
  const reason = event.reason ? ` · ${reasons[event.reason]}` : '';
  const evidence = node('ul');
  for (const row of event.candidates) {
    const proofs = row.proofs.length ? ` · 凭据 ${row.proofs.join('、')}` : '';
    const identity = `${row.band} ${row.valid_band ? '有效' : '失效'} · 环根 ${row.root}`;
    const observation = `${location(catalog, row.site)} · ${time(row.observed_at)}`;
    evidence.append(node('li', `${row.source} / ${row.report} · ${identity} · ${observation}${proofs}`));
  }
  const label = node('div');
  label.append(node('p', `${decision}${reason}`), evidence);
  return label;
}

function segmentLabel(segment, catalog) {
  if (!segment) return '—';
  return `${location(catalog, segment.from_site)} → ${location(catalog, segment.to_site)} · ${time(segment.start)} → ${time(segment.end)}`;
}

export function differences(diff, catalog) {
  const result = node('div', null, 'stack');
  const events = diff.encounters.map(row => [row.key, eventLabel(row.before, catalog), eventLabel(row.after, catalog)]);
  const segments = diff.segments.map(row => [row.key.join(' / '), segmentLabel(row.before, catalog), segmentLabel(row.after, catalog)]);
  result.append(node('h3', `遭遇变化 · ${events.length}`),
    events.length ? table(['引用', '变更前', '变更后'], events, '遭遇变化') : empty('没有遭遇变化。'),
    node('h3', `移动证据变化 · ${segments.length}`),
    segments.length ? table(['环根 / 起讫引用', '变更前', '变更后'], segments, '移动证据变化') : empty('没有移动证据变化。'));
  return result;
}
