import { request } from '../client.mjs';
import { openDetail } from '../dialog.mjs';
import { badge, button, empty, heading, node } from '../dom.mjs';
import { time } from '../display.mjs';
import { intakeReasons, previewIntake } from '../intake.mjs';
import { submit } from '../forms.mjs';
import { table } from '../table.mjs';

export function batches(ctx) {
  const { data, run } = ctx;
  const screen = node('div', null, 'stack');
  screen.append(heading('报文接收', '接收带有来源编号与遭遇引用的 UTF-8 JSON 采集包。按遭遇引用分组受理，一行不合格只拒收同组。'));
  const form = node('form', null, 'paper entry');
  const label = node('label', '采集包文件');
  const input = node('input');
  input.type = 'file';
  input.accept = '.json,application/json';
  input.required = true;
  label.append(input);
  form.append(label);
  submit(form, '先试算影响', () => run(() => previewIntake(input.files[0], ctx)));
  screen.append(form);
  const inspect = batch => run(async () => {
    const row = await request(`/api/batches/${batch}`);
    const details = node('div', null, 'stack');
    const archive = node('a', '下载原包 JSON');
    archive.href = `/api/batches/${batch}/source.json`;
    details.append(node('p', `摘要 ${row.sha256}`, 'digest'), archive,
      node('h3', `各组结论 · ${row.groups.length}`),
      table(['遭遇组', '结论', '拒收行号', '原因'], row.groups.map(group => [
        group.event,
        badge(group.state === 'accepted' ? '入账' : '拒收', group.state === 'accepted' ? 'good' : 'warn'),
        row.lines.filter(line => line.event === group.event && line.disposition === 'rejected')
          .map(line => line.position).join('、') || '—',
        group.reason ? intakeReasons[group.reason] || group.reason : '—',
      ]), '各组结论'),
      node('h3', `逐行去向 · ${row.line_count} 行`),
      table(['原包行号', '报文', '遭遇引用', '环号', '录入时刻', '标准时刻', '去向'],
        row.lines.map(line => {
          const report = row.reports.find(item => item.position === line.position);
          const source = report || line.original;
          return [line.position, line.report || '—', line.event, source?.band || '—',
            source?.observed_at || '—', report ? time(report.observed_at) : '—',
            line.disposition === 'accepted' ? badge('入账', 'good') : badge(`拒收 · ${intakeReasons[line.reason] || line.reason}`, 'warn')];
        }), '逐行去向'));
    openDetail(`采集包 · ${batch}`, details);
  });
  const rows = [...data.batches].reverse().map(row => [row.batch, data.catalog.sources[row.source].label,
    `${row.count} / ${row.line_count}`, row.revision, button('查看回执', () => inspect(row.batch), 'plain')]);
  screen.append(rows.length ? table(['采集包', '来源', '入账 / 总行数', '接收修订', '回执'], rows, '采集包回执') : empty('尚未接收采集包。'));
  return screen;
}
