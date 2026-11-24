import { badge, button, empty, heading, node, select } from '../dom.mjs';
import { duration, explanationLabel, location, reasons, time } from '../display.mjs';
import { table } from '../table.mjs';

function explanationChips(codes) {
  const wrap = node('span', null, 'explanation-chips');
  for (const code of codes) wrap.append(badge(explanationLabel(code), 'neutral'));
  return wrap;
}

function trackPanel(track, events, catalog, openEvent) {
  const pane = node('section', null, 'paper track-pane');
  const title = node('div', null, 'paper-heading');
  title.append(node('h2', track.root),
    node('p', `${track.event_count} 次已确认 · ${track.segments.length} 段有证移动`, 'muted'));
  const list = node('ol', null, 'timeline');
  const rows = [
    ...events.map(event => ({ at: event.observed_at, event })),
    ...track.segments.map(segment => ({ at: segment.start, segment })),
    ...track.gaps.map(gap => ({ at: gap.start, gap })),
  ].sort((a, b) => a.at.localeCompare(b.at) || Number(!a.event) - Number(!b.event));
  for (const row of rows) {
    if (row.event) {
      const event = row.event;
      const item = node('li', null, 'stop');
      item.append(node('time', time(row.at)),
        button(`${location(catalog, event.site)} · ${event.event}`, () => openEvent(event), 'plain'));
      list.append(item);
    } else if (row.segment) {
      const segment = row.segment;
      const item = node('li', null, `segment ${segment.kind}`);
      item.append(badge(segment.kind === 'move' ? '移动' : '驻留', 'good'),
        node('span', `${location(catalog, segment.from_site)} → ${location(catalog, segment.to_site)} · ${duration(segment.elapsed_seconds)}`),
        explanationChips(segment.explanations || []));
      list.append(item);
    } else {
      const item = node('li', null, 'gap');
      item.append(badge('断点', 'warn'), node('span', reasons[row.gap.reason] || row.gap.reason));
      for (const ref of row.gap.events) item.append(button(ref, () => openEvent(ref), 'plain'));
      if (row.gap.explanations) item.append(explanationChips(row.gap.explanations));
      list.append(item);
    }
  }
  pane.append(title, rows.length ? list : empty('该环根下暂时没有可连接的已确认遭遇。'));
  return pane;
}

function pendingPanel(data, openEvent) {
  const moves = data.pending_moves || [];
  const pane = node('section', null, 'paper');
  pane.append(node('h2', `待核移动 · ${moves.length} 段`),
    node('p', '仅在部分可行解释下成立的移动，给出成立与不成立的各一套解释及失证原因。', 'muted'));
  if (!moves.length) {
    pane.append(empty('没有待核移动。'));
    return pane;
  }
  pane.append(table(['起讫遭遇', '成立解释', '不成立解释', '失证原因', '阻断报文'], moves.map(move => {
    const failure = move.failing;
    const report = failure.blocking_report
      ? button(`${failure.blocking_report.source} / ${failure.blocking_report.report}`,
          () => openEvent(failure.blocking_report.event), 'plain')
      : '—';
    return [
      `${move.from_event} → ${move.to_event}`,
      explanationLabel(move.supporting.explanation),
      explanationLabel(failure.explanation),
      reasons[failure.reason] || failure.reason,
      report,
    ];
  }), '待核移动'));
  return pane;
}

function explanationPanel(data) {
  const pane = node('section', null, 'paper');
  pane.append(node('h2', `可行解释 · ${data.explanations.length} 套`),
    node('p', '每套解释含全部生效凭据，并为每个待裁定组选择恰好一张。', 'muted'));
  pane.append(table(['解释', '待裁定组选择', '生效凭据'], data.explanations.map(item => [
    explanationLabel(item.code),
    item.choices.length ? item.choices.map(choice => `${choice.group} → ${choice.proof}`).join('；') : '无待裁定组',
    item.proofs.join('、'),
  ]), '可行解释'));
  return pane;
}

export function tracks(ctx) {
  const { data, openEvent } = ctx;
  const screen = node('div');
  const header = node('div', null, 'headline');
  const held = data.encounters.filter(item => item.state === 'held').length;
  const certified = data.routes.reduce((sum, route) => sum + route.segments.length, 0);
  header.append(heading('移动证据', '按环根串联在所有可行解释下一致的有证移动；部分解释成立的移动单列为待核。'));
  const stats = node('dl', null, 'metrics');
  for (const [label, count] of [
    ['已确认遭遇', data.encounters.length - held], ['待复核', held],
    ['有证段', certified], ['待核移动', (data.pending_moves || []).length],
  ]) {
    const group = node('div');
    group.append(node('dt', label), node('dd', count));
    stats.append(group);
  }
  header.append(stats);
  screen.append(header);
  const body = node('div', null, 'track-grid');
  const details = node('div', null, 'stack');
  const aside = node('aside', null, 'paper coverage');
  aside.append(node('h2', '样地证据分布'), table(['样地', '已确认', '待复核', '离站'], data.coverage.map(row => [
    location(data.catalog, row.site), row.confirmed, row.held_refs.length, row.departures,
  ]), '样地证据分布'));
  const points = new Map();
  for (const event of data.encounters) {
    if (event.state !== 'confirmed') continue;
    if (!points.has(event.root)) points.set(event.root, []);
    points.get(event.root).push(event);
  }
  function draw(root) {
    ctx.trackRoot = root;
    const chosen = data.routes.find(track => track.root === root);
    details.replaceChildren(trackPanel(chosen, points.get(root) || [], data.catalog, openEvent));
  }
  if (data.routes.length) {
    const [label, input] = select('查看环根', data.routes.map(route => [route.root, route.root]), draw);
    screen.append(label);
    input.value = data.routes.some(route => route.root === ctx.trackRoot) ? ctx.trackRoot : data.routes[0].root;
    draw(input.value);
  } else details.append(empty('接收一批报文后，移动证据会出现在这里。'));
  const side = node('div', null, 'stack');
  side.append(explanationPanel(data), pendingPanel(data, openEvent), aside);
  body.append(details, side);
  screen.append(body);
  return screen;
}
