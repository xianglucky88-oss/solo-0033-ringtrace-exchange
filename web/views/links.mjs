import { request } from '../client.mjs';
import { openDetail } from '../dialog.mjs';
import { differences } from '../differences.mjs';
import { time } from '../display.mjs';
import { button, empty, heading, node } from '../dom.mjs';
import { field, submit } from '../forms.mjs';
import { table } from '../table.mjs';

export function links({ data, change, run }) {
  const screen = node('div', null, 'stack');
  screen.append(heading('换环凭据', '凭据生效时由新环接续，同一环号只有一个前任和一个后继。'));
  const form = node('form', null, 'paper entry');
  field(form, 'proof', '凭据编号', 'LINK-APR04');
  field(form, 'old_band', '旧环号', 'RING-A');
  field(form, 'new_band', '新环号', 'RING-B');
  field(form, 'effective_at', '生效时刻（含时区）', '2026-04-04T06:00:00+08:00');
  submit(form, '登记凭据', () => change(async () => {
    const row = await request('/api/links', Object.fromEntries(new FormData(form)));
    return `已登记 ${row.proof}。`;
  }));
  const preview = proof => run(async () => {
    const diff = await request(`/api/links/${proof}/impact`);
    openDetail(`去除凭据试算 · ${proof}`, differences(diff, data.catalog));
  });
  screen.append(form, data.links.length ? table(['凭据编号', '旧环', '新环', '生效时刻', '影响'], data.links.map(row => [
    row.proof, row.old_band, row.new_band, time(row.effective_at), button('试算移除', () => preview(row.proof), 'plain'),
  ]), '换环凭据') : empty('尚未登记换环凭据。'));
  return screen;
}
