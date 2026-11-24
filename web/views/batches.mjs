import { request } from '../client.mjs';
import { openDetail } from '../dialog.mjs';
import { button, empty, heading, node } from '../dom.mjs';
import { time } from '../display.mjs';
import { previewIntake } from '../intake.mjs';
import { submit } from '../forms.mjs';
import { table } from '../table.mjs';

export function batches(ctx) {
  const { data, run } = ctx;
  const screen = node('div', null, 'stack');
  screen.append(heading('报文接收', '接收带有来源编号与遭遇引用的 UTF-8 JSON 采集包。每包最多 500 条报文。'));
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
    details.append(node('p', `摘要 ${row.sha256}`, 'digest'), archive, table(['原包行号', '报文', '当前遭遇', '原遭遇号', '环号', '录入时刻', '标准时刻'],
      row.reports.map(report => [report.position, report.report, report.event,
        report.original_event && report.original_event !== report.event ? report.original_event : '—',
        report.band, report.recorded_at, time(report.observed_at)]), '原始报文'));
    openDetail(`采集包 · ${batch}`, details);
  });
  const rows = [...data.batches].reverse().map(row => [row.batch, data.catalog.sources[row.source].label,
    row.count, row.revision, button('查看回执', () => inspect(row.batch), 'plain')]);
  screen.append(rows.length ? table(['采集包', '来源', '报文数', '接收修订', '回执'], rows, '采集包回执') : empty('尚未接收采集包。'));
  return screen;
}
