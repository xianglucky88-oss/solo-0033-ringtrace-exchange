import { request } from '../client.mjs';
import { empty, heading, node } from '../dom.mjs';
import { table } from '../table.mjs';

export function correctionsView({ data, run }) {
  const screen = node('div', null, 'stack');
  screen.append(heading('遭遇更正', '每次更正只推进一个修订，把一个留置遭遇的全部已收报文分入两个未使用的新号；原编号随报文永久保留。'));
  const body = node('div', null, 'paper');
  screen.append(body);
  run(async () => {
    const detail = await request('/api/corrections');
    const rows = [...detail.corrections].reverse();
    if (!rows.length) {
      body.replaceChildren(empty('尚未执行遭遇更正。在「遭遇裁决」中对待复核遭遇使用「拆分更正」。'));
      return;
    }
    body.replaceChildren(table(['修订', '原遭遇', '新号一', '新号二', '报文归属（报文 → 新号）'], rows.map(row => {
      const list = node('ul', null, 'assignment-list');
      for (const item of row.assignments || []) {
        list.append(node('li', `${item.source} / ${item.report}（原 ${item.original_event}）→ ${item.event}`));
      }
      return [row.revision, row.source_event, row.first_event, row.second_event, list];
    }), '更正记录'));
  });
  return screen;
}
