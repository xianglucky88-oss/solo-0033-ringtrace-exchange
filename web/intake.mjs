import { request } from './client.mjs';
import { differences } from './differences.mjs';
import { badge, button, empty, node } from './dom.mjs';
import { openDetail } from './dialog.mjs';
import { table } from './table.mjs';

export const intakeReasons = {
  invalid_row: '同组有报文未通过校验',
  duplicate_report: '同组报文编号重复',
  cross_group_report: '报文编号在包内跨组重用',
  report_conflict: '同组报文编号已被该来源接收',
  invalid_reference: '遭遇引用缺失或无效',
  package_rejected: '包内遭遇引用缺失或无效',
  group_rejected: '同组拒收',
  unknown_site: '遭遇样地未登记',
  unknown_kind: '遭遇类别无效',
  invalid_token: '编号格式无效',
  invalid_time: '时刻格式无效',
  invalid_fields: '字段不完整',
  misreceived: '封存记为已收但复算应拒收',
  missed: '封存记为拒收但复算应接收',
};

function groupRows(result) {
  return result.groups.map(group => [
    group.event,
    badge(group.state === 'accepted' ? '可收' : '拒收', group.state === 'accepted' ? 'good' : 'warn'),
    group.rejected_lines.length ? group.rejected_lines.join('、') : '—',
    group.reason ? intakeReasons[group.reason] || group.reason : '—',
  ]);
}

function lineRows(result) {
  return result.lines.filter(line => line.disposition === 'rejected').map(line => [
    line.position, line.event, line.report || '—', intakeReasons[line.reason] || line.reason,
    line.message || '—',
  ]);
}

export async function previewIntake(file, { data, change }) {
  if (!file || file.size > 2 * 1024 * 1024) {
    throw new Error('请选择不超过 2 MiB 的 JSON 文件。');
  }
  let payload;
  try {
    // Preserve the original JSON text so the server can detect duplicate keys.
    payload = new TextDecoder('utf-8', { fatal: true }).decode(await file.arrayBuffer());
  } catch {
    throw new Error('文件须采用 UTF-8 编码。');
  }
  const result = await request('/api/batch-previews', payload, { raw: true });
  const { base_revision: revision, receipt } = result;
  const detail = node('div', null, 'stack');
  const accepted = result.groups.filter(group => group.state === 'accepted').length;
  const summary = receipt?.replayed
    ? `该包已在修订 ${receipt.revision} 接收。`
    : result.acceptable
      ? `共 ${result.lines.length} 行，${accepted} 个遭遇组可收。以下变化以修订 ${revision} 为起点。`
      : `共 ${result.lines.length} 行，没有可接收的遭遇组。整包拒收，不产生回执或修订。`;
  detail.append(node('p', summary),
    table(['遭遇组', '结论', '拒收行号', '原因'], groupRows(result), '各组结论'));
  const rejected = lineRows(result);
  if (rejected.length) {
    detail.append(node('h3', `拒收明细 · ${rejected.length} 行`),
      table(['原包行号', '遭遇引用', '报文', '原因', '说明'], rejected, '拒收明细'));
  }
  if (result.acceptable) detail.append(differences(result.diff, data.catalog));
  else detail.append(empty('没有可收组，因此没有裁决或移动段预报。'));
  if (receipt && !receipt.replayed) {
    const commit = button('确认接收此包', async () => {
      commit.disabled = true;
      document.getElementById('details').close();
      await change(async () => {
        const row = await request('/api/batches', payload, { raw: true, revision });
        return row.replayed ? `已返回原回执 ${row.batch}。`
          : `已接收 ${row.batch} 的 ${row.count} 行，拒收 ${row.line_count - row.count} 行。`;
      });
      commit.disabled = false;
    }, 'primary');
    detail.append(commit);
  }
  openDetail(`试算采集包 · ${receipt?.batch || result.batch}`, detail);
}
