import { request } from './client.mjs';
import { differences } from './differences.mjs';
import { openDetail } from './dialog.mjs';
import { button, node } from './dom.mjs';
import { location, time } from './display.mjs';

function groupSelect(initial) {
  const select = node('select');
  for (const [value, text] of [['A', '第一组'], ['B', '第二组']]) {
    const option = node('option', text);
    option.value = value;
    select.append(option);
  }
  select.value = initial;
  return select;
}

function buildPayload(event, revision, firstInput, secondInput, choices) {
  const groups = [
    { event: firstInput.value.trim(), reports: [] },
    { event: secondInput.value.trim(), reports: [] },
  ];
  for (const [key, select] of choices) {
    const [source, report] = key;
    groups[select.value === 'A' ? 0 : 1].reports.push({ source, report });
  }
  return { event, base_revision: revision, groups };
}

export function openCorrection(eventRow, { data, catalog, change }) {
  const choices = new Map();
  const detail = node('div', null, 'stack');
  detail.append(node('p', `把留置遭遇 ${eventRow.event} 的全部已收报文一次分入两个未使用的新号；两组都须非空，漏分、重分或占号都会被整次驳回。`, 'muted'));
  const numberRow = node('div', null, 'entry-inline');
  const firstLabel = node('label', '第一组新号');
  const firstInput = node('input');
  firstInput.value = `${eventRow.event}A`;
  firstInput.required = true;
  const secondLabel = node('label', '第二组新号');
  const secondInput = node('input');
  secondInput.value = `${eventRow.event}B`;
  secondInput.required = true;
  firstLabel.append(firstInput);
  secondLabel.append(secondInput);
  numberRow.append(firstLabel, secondLabel);
  const table = node('table');
  table.setAttribute('aria-label', '报文分组');
  const head = table.createTHead().insertRow();
  for (const title of ['来源 / 报文', '采集包 / 行号', '环号', '时刻', '样地', '归入']) {
    const cell = node('th', title);
    cell.scope = 'col';
    head.append(cell);
  }
  const body = table.createTBody();
  eventRow.candidates.forEach((row, index) => {
    const select = groupSelect(index === 0 ? 'A' : 'B');
    choices.set([row.source, row.report], select);
    const tr = body.insertRow();
    for (const value of [
      `${catalog.sources[row.source].label} · ${row.report}`,
      `${row.batch} / ${row.position}`,
      `${row.band}${row.original_event !== row.event ? `（原 ${row.original_event}）` : ''}`,
      time(row.observed_at), location(catalog, row.site),
    ]) {
      tr.insertCell().textContent = value;
    }
    tr.insertCell().append(select);
  });
  const result = node('div', null, 'stack');
  const previewButton = button('试算更正', async () => {
    result.replaceChildren();
    const payload = buildPayload(eventRow.event, data.revision, firstInput, secondInput, choices);
    if (!payload.groups[0].reports.length || !payload.groups[1].reports.length) {
      result.append(node('p', '两个分组都须至少包含一条报文。', 'error-text'));
      return;
    }
    const preview = await request('/api/event-correction-previews', payload);
    const commit = button('确认执行更正', async () => {
      commit.disabled = true;
      await change(async () => {
        const out = await request('/api/event-corrections', payload, { revision: data.revision });
        document.getElementById('details').close();
        return `已把 ${out.event} 拆分为 ${out.events.join('、')}，共重分 ${out.count} 条报文。`;
      });
    }, 'primary');
    result.append(node('h3', `试算结果 · 修订 ${preview.base_revision} → ${preview.revision}`),
      differences(preview.diff, catalog), commit);
  }, 'primary');
  detail.append(numberRow, table, previewButton, result);
  openDetail(`遭遇更正 · ${eventRow.event}`, detail);
}
