import { request } from '../client.mjs';
import { openDetail } from '../dialog.mjs';
import { differences } from '../differences.mjs';
import { time } from '../display.mjs';
import { button, empty, heading, node, select } from '../dom.mjs';
import { submit } from '../forms.mjs';
import { table } from '../table.mjs';

function download(revision, filename, label) {
  const link = node('a', label);
  link.href = `/api/releases/${revision}/${filename}`;
  return link;
}

export function releases({ data, versions, change, run }) {
  const screen = node('div', null, 'stack');
  const header = node('div', null, 'headline');
  header.append(heading('封存对账', '封存当前证据、待复核遭遇与移动断点，可下载成果或用随版输入重新计算。'));
  const freeze = button(`封存修订 ${data.revision}`, () => change(async () => {
    const row = await request('/api/releases', { revision: data.revision });
    return row.replayed ? `修订 ${row.revision} 已封存。` : `已生成封存版本 ${row.revision}。`;
  }), 'primary');
  const pendingGroups = (data.groups || []).filter(group => group.state === 'pending');
  freeze.disabled = !data.encounters.length || pendingGroups.length > 0;
  header.append(freeze);
  if (pendingGroups.length) {
    header.append(node('p', `互斥组 ${pendingGroups.map(group => group.group_id).join('、')} 尚未定案，定案后才能封存。`, 'muted'));
  }
  screen.append(header);
  if (!versions.length) {
    screen.append(empty('尚无封存版本。'));
    return screen;
  }
  if (versions.length > 1) {
    const form = node('form', null, 'paper entry');
    const choices = versions.map(row => [row.revision, `修订 ${row.revision}`]);
    const [leftLabel, left] = select('基准版本', choices);
    const [rightLabel, right] = select('对照版本', choices);
    left.value = versions[1].revision;
    form.append(leftLabel, rightLabel);
    submit(form, '对账', () => run(async () => {
      const diff = await request(`/api/releases/${left.value}/compare/${right.value}`);
      openDetail(`修订 ${diff.from_revision} 对比 ${diff.to_revision}`, differences(diff, data.catalog));
    }));
    screen.append(form);
  }
  function verify(number) {
    return run(async () => {
      const result = await request(`/api/releases/${number}/verify`);
      openDetail(`复算修订 ${number}`, node('p', result.matches ? `已核对 ${result.verified_batches} 个采集包。复算摘要与封存摘要一致。` : '复算摘要与封存摘要不一致。'));
    });
  }
  screen.append(table(['修订', '封存时刻', '摘要', '复核与下载'], versions.map(row => {
    const actions = node('div', null, 'actions');
    actions.append(button('复算', () => verify(row.revision), 'plain'), download(row.revision, 'evidence.json', '证据 JSON'),
      download(row.revision, 'routes.csv', '移动段 CSV'));
    const checksum = node('code', row.sha256.slice(0, 16));
    checksum.title = row.sha256;
    return [row.revision, time(row.created_at), checksum, actions];
  }), '历史封存'));
  return screen;
}
