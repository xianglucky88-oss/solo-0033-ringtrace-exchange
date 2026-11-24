import { badge, button, empty, heading, node, select } from '../dom.mjs';
import { duration, location, reasons, time } from '../display.mjs';
import { table } from '../table.mjs';

function trackPanel(track, events, catalog, openEvent) {
  const pane = node('section', null, 'paper track-pane');
  const title = node('div', null, 'paper-heading');
  title.append(node('h2', track.root), node('p', `${track.event_count} 次已确认 · ${track.segments.length} 段证据`, 'muted'));
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
      item.append(node('time', time(row.at)), button(`${location(catalog, event.site)} · ${event.event}`, () => openEvent(event), 'plain'));
      list.append(item);
    } else if (row.segment) {
      const segment = row.segment;
      const item = node('li', null, `segment ${segment.kind}`);
      item.append(badge(segment.kind === 'move' ? '移动' : '驻留', 'good'),
        node('span', `${location(catalog, segment.from_site)} → ${location(catalog, segment.to_site)} · ${duration(segment.elapsed_seconds)}`));
      list.append(item);
    } else {
      const item = node('li', null, 'gap');
      item.append(badge('断点', 'warn'), node('span', reasons[row.gap.reason]));
      for (const ref of row.gap.events) item.append(button(ref, () => openEvent(ref), 'plain'));
      list.append(item);
    }
  }
  pane.append(title, rows.length ? list : empty('该环根下暂时没有可连接的已确认遭遇。'));
  return pane;
}

export function tracks(ctx) {
  const { data, openEvent } = ctx;
  const screen = node('div');
  const header = node('div', null, 'headline');
  const held = data.encounters.filter(item => item.state === 'held').length;
  header.append(heading('移动证据', '按环根串联已确认遭遇。在同刻冲突或中间遭遇待复核时，时间轴保留断点。'));
  const stats = node('dl', null, 'metrics');
  for (const [label, count] of [['已确认遭遇', data.encounters.length - held], ['待复核', held], ['证据段', data.routes.reduce((sum, route) => sum + route.segments.length, 0)]]) {
    const group = node('div');
    group.append(node('dt', label), node('dd', count));
    stats.append(group);
  }
  header.append(stats);
  screen.append(header);
  const body = node('div', null, 'track-grid');
  const details = node('div');
  const aside = node('aside', null, 'paper coverage');
  aside.append(node('h2', '样地证据分布'), table(['样地', '已确认', '待复核', '移出'], data.coverage.map(row => [
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
  body.append(details, aside);
  screen.append(body);
  return screen;
}
