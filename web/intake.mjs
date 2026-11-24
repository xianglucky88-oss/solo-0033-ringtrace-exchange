import { request } from './client.mjs';
import { differences } from './differences.mjs';
import { button, node } from './dom.mjs';
import { openDetail } from './dialog.mjs';

function readFile(file) {
  if (!file || file.size > 2 * 1024 * 1024) {
    throw new Error('请选择不超过 2 MiB 的 JSON 文件。');
  }
  // Preserve the original JSON text so the server can detect duplicate keys.
  return new TextDecoder('utf-8', { fatal: true }).decode(file.arrayBuffer());
}

function chooseRouting(packageData, aliases) {
  const stale = packageData.reports
    .map((report, index) => ({ report, position: index + 1, targets: aliases[report.event] }))
    .filter(row => row.targets);
  if (!stale.length) return null;
  const form = node('div', null, 'stack');
  form.append(node('p', '检测到仍写旧遭遇号的报文，请逐行确认归入哪个新号；漏选或错选整包不入账。'));
  const selections = new Map();
  const rows = stale.map(row => {
    const select = node('select');
    for (const target of row.targets) {
      const option = node('option', target);
      option.value = target;
      select.append(option);
    }
    selections.set(row.position, select);
    return [row.position, row.report.report, row.report.event, select];
  });
  const table = node('table');
  const head = table.createTHead().insertRow();
  for (const title of ['原包行号', '报文', '旧遭遇号', '归入新号']) {
    const cell = node('th', title);
    cell.scope = 'col';
    head.append(cell);
  }
  const body = table.createTBody();
  for (const values of rows) {
    const tr = body.insertRow();
    values.forEach((value, index) => {
      const cell = tr.insertCell();
      if (value instanceof Node) cell.append(value);
      else cell.textContent = value;
    });
  }
  form.append(table);
  return { form, routing: () => [...selections].map(([position, select]) => ({
    position, event: select.value,
  })) };
}

export async function previewIntake(file, ctx) {
  const payload = readFile(file);
  const packageData = JSON.parse(payload);
  const routingStep = chooseRouting(packageData, ctx.data.aliases || {});
  const submitBody = () => (routingStep
    ? JSON.stringify({ package: packageData, routing: routingStep.routing() })
    : payload);
  const result = await request('/api/batch-previews', submitBody(), { raw: true });
  const { receipt, base_revision: revision } = result;
  const detail = node('div', null, 'stack');
  const summary = receipt.replayed
    ? `该包已在修订 ${receipt.revision} 接收。`
    : `${receipt.count} 条报文。以下变化以修订 ${revision} 为起点。`;
  if (routingStep) detail.append(routingStep.form);
  detail.append(node('p', summary), differences(result.diff, ctx.data.catalog));
  if (!receipt.replayed) {
    const commit = button('确认接收此包', async () => {
      commit.disabled = true;
      document.getElementById('details').close();
      await ctx.change(async () => {
        const row = await request('/api/batches', submitBody(), { raw: true, revision });
        return row.replayed ? `已返回原回执 ${row.batch}。` : `已接收 ${row.batch} 的 ${row.count} 条报文。`;
      });
      commit.disabled = false;
    }, 'primary');
    detail.append(commit);
  }
  openDetail(`试算采集包 · ${receipt.batch}`, detail);
}
