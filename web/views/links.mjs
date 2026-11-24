import { request } from '../client.mjs';
import { openDetail } from '../dialog.mjs';
import { differences } from '../differences.mjs';
import { badge, button, empty, heading, node } from '../dom.mjs';
import { time } from '../display.mjs';
import { field, submit } from '../forms.mjs';
import { table } from '../table.mjs';

function ordinaryForm(change) {
  const form = node('form', null, 'paper entry');
  form.append(node('h2', '登记普通凭据'));
  field(form, 'proof', '凭据编号', 'LINK-APR04');
  field(form, 'old_band', '旧环号', 'RING-A');
  field(form, 'new_band', '新环号', 'RING-B');
  field(form, 'effective_at', '生效时刻（含时区）', '2026-04-04T06:00:00+08:00');
  submit(form, '登记凭据', () => change(async () => {
    const row = await request('/api/links', Object.fromEntries(new FormData(form)));
    return `已登记 ${row.proof}。`;
  }));
  return form;
}

function parseProofs(text) {
  const rows = [];
  for (const line of text.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const [proof, old_band, effective_at] = trimmed.split(/\s*,\s*/);
    if (!proof || !old_band || !effective_at) {
      throw new Error('每行格式：凭据编号, 旧环号, 生效时刻');
    }
    rows.push({ proof, old_band, effective_at });
  }
  if (rows.length < 2) throw new Error('互斥组至少需要两张凭据。');
  return rows;
}

function groupForm(change) {
  const form = node('form', null, 'paper entry');
  form.append(node('h2', '登记互斥凭据组'),
    node('p', '同一新环收到多张凭据、填写了不同旧环时登记为一组。每行一张：凭据编号, 旧环号, 生效时刻。', 'muted'));
  field(form, 'new_band', '共同新环号', 'RING-NEW');
  const label = node('label', '互斥凭据（每行一张）');
  const textarea = node('textarea');
  textarea.name = 'proofs_text';
  textarea.rows = 4;
  textarea.placeholder = 'PRF-1, RING-A, 2026-05-02T00:00:00Z\nPRF-2, RING-B, 2026-05-02T00:00:00Z';
  textarea.required = true;
  label.append(textarea);
  form.append(label);
  submit(form, '登记互斥组', () => change(async () => {
    const data = Object.fromEntries(new FormData(form));
    const payload = { new_band: data.new_band, proofs: parseProofs(data.proofs_text) };
    const row = await request('/api/link-groups', payload);
    return `已登记互斥组 ${row.group}，含 ${row.proofs.length} 张凭据。`;
  }));
  return form;
}

function alternativeForm(change, groups) {
  const pending = groups.filter(group => group.state === 'pending');
  if (!pending.length) return null;
  const form = node('form', null, 'paper entry');
  form.append(node('h2', '向待裁定组补记凭据'));
  const label = node('label', '目标互斥组');
  const select = node('select');
  select.name = 'group';
  for (const group of pending) {
    const option = node('option', `${group.group_id}（新环 ${group.new_band}）`);
    option.value = group.group_id;
    select.append(option);
  }
  label.append(select);
  form.append(label);
  field(form, 'proof', '凭据编号', 'PRF-3');
  field(form, 'old_band', '旧环号', 'RING-C');
  field(form, 'effective_at', '生效时刻（含时区）', '2026-05-02T00:00:00Z');
  submit(form, '补记备选凭据', () => change(async () => {
    const data = Object.fromEntries(new FormData(form));
    const row = await request('/api/link-group-alternatives', data);
    return `已补记 ${row.proof}。`;
  }));
  return form;
}

function decisionForm(change, groups, revision) {
  const pending = groups.filter(group => group.state === 'pending');
  if (!pending.length) return null;
  const form = node('form', null, 'paper entry');
  form.append(node('h2', '原件核实后正式裁定'),
    node('p', '成功只推进一次修订；其余备选更新为可选项或留存排除记录。所有组定案后才能封存。', 'muted'));
  const groupLabel = node('label', '互斥组');
  const groupSelect = node('select');
  groupSelect.name = 'group';
  for (const group of pending) {
    const option = node('option', `${group.group_id}（新环 ${group.new_band}）`);
    option.value = group.group_id;
    groupSelect.append(option);
  }
  groupLabel.append(groupSelect);
  const proofLabel = node('label', '正式选定凭据编号');
  const proofInput = node('input');
  proofInput.name = 'proof';
  proofInput.required = true;
  proofInput.placeholder = 'PRF-1';
  proofLabel.append(proofInput);
  form.append(groupLabel, proofLabel);
  submit(form, '提交裁定', () => change(async () => {
    const row = await request('/api/link-decisions', {
      group: groupSelect.value, proof: proofInput.value, revision,
    });
    return `组 ${row.group} 已选定 ${row.proof}，修订推进至 ${row.revision}。`;
  }));
  return form;
}

function groupCard(group, catalog, run) {
  const state = group.state === 'decided'
    ? badge(`已定案 · ${group.chosen_proof}`, 'good')
    : badge('待裁定', 'warn');
  const memberRows = group.members.map(member => [
    member.proof, member.old_band, time(member.effective_at),
    member.state === 'excluded'
      ? badge(`已排除${member.excluded_note ? ` · ${member.excluded_note}` : ''}`, 'warn')
      : badge('可选', 'good'),
    button('试算移除', () => run(async () => {
      const diff = await request(`/api/links/${member.proof}/impact`);
      openDetail(`去除凭据试算 · ${member.proof}`, differences(diff, catalog));
    }), 'plain'),
  ]);
  const card = node('div', null, 'paper stack');
  card.append(node('h3', `${group.group_id} · 新环 ${group.new_band}`), state,
    table(['凭据编号', '旧环', '生效时刻', '状态', '影响'], memberRows, '组成员'));
  return card;
}

export function links({ data, change, run }) {
  const screen = node('div', null, 'stack');
  screen.append(heading('换环凭据', '普通凭据构成单链；互斥组为同一新环登记不同旧环，按可行解释核对，原件核实后逐组裁定。'));
  screen.append(ordinaryForm(change), groupForm(change));
  const extra = alternativeForm(change, data.groups);
  if (extra) screen.append(extra);
  const decision = decisionForm(change, data.groups, data.revision);
  if (decision) screen.append(decision);

  const standalone = data.links.filter(link => !link.group_id);
  if (standalone.length) {
    screen.append(node('h2', '普通凭据'), table(['凭据编号', '旧环', '新环', '生效时刻', '状态', '影响'],
      standalone.map(row => [
        row.proof, row.old_band, row.new_band, time(row.effective_at),
        row.state === 'excluded' ? badge('已排除', 'warn') : badge('生效', 'good'),
        button('试算移除', () => run(async () => {
          const diff = await request(`/api/links/${row.proof}/impact`);
          openDetail(`去除凭据试算 · ${row.proof}`, differences(diff, data.catalog));
        }), 'plain'),
      ]), '普通凭据'));
  }
  if (data.groups.length) {
    const groupStack = node('div', null, 'stack');
    groupStack.append(...data.groups.map(group => groupCard(group, data.catalog, run)));
    screen.append(node('h2', '互斥凭据组'), groupStack);
  }
  if (!standalone.length && !data.groups.length) screen.append(empty('尚未登记换环凭据。'));
  return screen;
}
