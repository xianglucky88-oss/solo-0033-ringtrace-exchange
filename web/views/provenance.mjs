import { request } from '../client.mjs';
import { badge, button, empty, heading, node, select } from '../dom.mjs';
import { location, time } from '../display.mjs';
import { field, submit } from '../forms.mjs';
import { table } from '../table.mjs';

function filters(catalog) {
  const form = node('form', null, 'paper entry');
  const [modeLabel, mode] = select('环号匹配', [['recorded', '报文环号'], ['root', '当前环根']]);
  mode.name = 'band_mode';
  form.append(modeLabel);
  for (const [name, label, placeholder] of [
    ['band', '环号', 'RING-A'], ['reference', '遭遇引用', 'E30'],
    ['from', '时间起点（含）', '2026-04-03T00:00:00Z'], ['until', '时间终点（不含）', '2026-04-06T00:00:00Z'],
  ]) {
    field(form, name, label, placeholder).required = false;
  }
  const [sourceLabel, source] = select('来源', [['', '任意来源'], ...Object.entries(catalog.sources).map(([key, row]) => [key, row.label])]);
  source.name = 'source';
  form.append(sourceLabel);
  return form;
}

function results(page, catalog) {
  if (!page.items.length) return empty('没有符合条件的原始报文。');
  return table(['来源报文', '原包 / 行号', '遭遇', '报文环号 → 当前环根', '标准时刻', '样地', '裁决'], page.items.map(row => [
    `${catalog.sources[row.source].label} · ${row.report}`, `${row.batch} / ${row.position}`, row.event,
    `${row.band} → ${row.root}`, time(row.observed_at), location(catalog, row.site),
    badge(row.decision === 'confirmed' ? '已确认' : '待复核', row.decision === 'confirmed' ? 'good' : 'warn'),
  ]), '报文追溯结果');
}

export function provenance({ data, run }) {
  const screen = node('div', null, 'stack');
  screen.append(heading('报文追溯', '从环号、遭遇引用或时段找回原始报文。按当前环根查询时会同时保留不在有效期的记录。'));
  const form = filters(data.catalog);
  const output = node('div', null, 'stack');
  const status = node('p', '', 'muted');
  status.setAttribute('aria-live', 'polite');
  let latest = 0;
  function load(params, offset = 0, revision) {
    const ticket = ++latest;
    return run(async () => {
      const requestParams = new URLSearchParams(params);
      if (revision !== undefined) requestParams.set('at', revision);
      requestParams.set('offset', offset);
      const page = await request(`/api/provenance?${requestParams}`);
      if (ticket !== latest) return;
      const caption = page.total
        ? `第 ${page.offset + 1}–${page.offset + page.items.length} 条，共 ${page.total} 条 · 修订 ${page.revision}`
        : `共 0 条 · 修订 ${page.revision}`;
      status.textContent = caption;
      const nav = node('div', null, 'actions');
      if (page.offset > 0) nav.append(button('上一页', () => load(params, Math.max(0, page.offset - 25), page.revision)));
      if (page.next_offset !== null) nav.append(button('下一页', () => load(params, page.next_offset, page.revision)));
      output.replaceChildren(results(page, data.catalog), nav);
    });
  }
  submit(form, '检索报文', () => {
    const params = new URLSearchParams();
    for (const [key, value] of new FormData(form)) {
      if (value.trim()) params.set(key, value.trim());
    }
    return load(params);
  });
  screen.append(form, status, output);
  return screen;
}
