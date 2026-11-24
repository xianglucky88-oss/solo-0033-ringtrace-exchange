import { badge, button, empty, heading, node, select } from '../dom.mjs';
import { location, reasons, time } from '../display.mjs';
import { openCorrection } from '../correction.mjs';
import { table } from '../table.mjs';

export function encounters(ctx) {
  const { data, openEvent } = ctx;
  const screen = node('div', null, 'stack');
  screen.append(heading('遭遇裁决', '按事件引用比较来源。同级来源的时刻、样地或身份不一致时，留待复核；复核员可把留置遭遇拆分为两个新号。'));
  const output = node('div', null, 'paper');
  function draw(filter) {
    const rows = data.encounters.filter(event => filter === 'all' || event.state === filter);
    output.replaceChildren(rows.length ? table(['遭遇引用', '状态', '已确认样地', '已确认时刻', '分歧说明', '证据', '更正'], rows.map(event => {
      const actions = node('div', null, 'actions');
      actions.append(button(`报文 ${event.candidates.length} 条`, () => openEvent(event), 'plain'));
      if (event.state === 'held') {
        actions.append(button('拆分更正', () => openCorrection(event, ctx), 'primary'));
      }
      return [
        event.event, badge(event.state === 'held' ? '待复核' : '已确认', event.state === 'held' ? 'warn' : 'good'),
        event.site && location(data.catalog, event.site), event.observed_at && time(event.observed_at),
        reasons[event.reason], actions,
      ];
    }), '遭遇裁决') : empty('这个范围内没有遭遇。'));
  }
  const [filterControl] = select('裁决状态', [['all', '全部'], ['held', '待复核'], ['confirmed', '已确认']], draw);
  draw('all');
  screen.append(filterControl, output);
  return screen;
}
