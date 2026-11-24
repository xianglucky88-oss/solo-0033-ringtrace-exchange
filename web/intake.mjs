import { request } from './client.mjs';
import { differences } from './differences.mjs';
import { button, node } from './dom.mjs';
import { openDetail } from './dialog.mjs';

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
  const { receipt, base_revision: revision } = result;
  const detail = node('div', null, 'stack');
  const summary = receipt.replayed
    ? `该包已在修订 ${receipt.revision} 接收。`
    : `${receipt.count} 条报文。以下变化以修订 ${revision} 为起点。`;
  detail.append(node('p', summary), differences(result.diff, data.catalog));
  if (!receipt.replayed) {
    const commit = button('确认接收此包', async () => {
      commit.disabled = true;
      document.getElementById('details').close();
      await change(async () => {
        const row = await request('/api/batches', payload, { raw: true, revision });
        return row.replayed ? `已返回原回执 ${row.batch}。` : `已接收 ${row.batch} 的 ${row.count} 条报文。`;
      });
      commit.disabled = false;
    }, 'primary');
    detail.append(commit);
  }
  openDetail(`试算采集包 · ${receipt.batch}`, detail);
}
