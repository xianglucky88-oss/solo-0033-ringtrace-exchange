import { badge, button, empty, heading, node, select } from '../dom.mjs';
import { location, reasons, time } from '../display.mjs';
import { table } from '../table.mjs';

export function encounters({ data, openEvent }) {
  const screen = node('div', null, 'stack');
  screen.append(heading('遭遇裁决', '按事件引用比较来源。同级来源的时刻、样地或身份不一致时，留待复核。'));
  const output = node('div', null, 'paper');
  function draw(filter) {
    const rows = data.encounters.filter(event => filter === 'all' || event.state === filter);
    output.replaceChildren(rows.length ? table(['遭遇引用', '状态', '已确认样地', '已确认时刻', '分歧说明', '证据'], rows.map(event => [
      event.event, badge(event.state === 'held' ? '待复核' : '已确认', event.state === 'held' ? 'warn' : 'good'),
      event.site && location(data.catalog, event.site), event.observed_at && time(event.observed_at),
      reasons[event.reason], button(`报文 ${event.candidates.length} 条`, () => openEvent(event), 'plain'),
    ]), '遭遇裁决') : empty('这个范围内没有遭遇。'));
  }
  const [filter] = select('裁决状态', [['all', '全部'], ['held', '待复核'], ['confirmed', '已确认']], draw);
  draw('all');
  screen.append(filter, output);
  return screen;
}
