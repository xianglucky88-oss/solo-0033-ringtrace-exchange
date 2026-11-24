export const reasons = {
  inactive_band: '报文环号未在该时刻生效',
  peer_conflict: '同级来源不一致',
  lower_disagreement: '低优先来源有分歧',
  same_time: '同刻遭遇无法排序',
  held_between: '途经待复核遭遇',
  explanation_divergence: '可行解释之间结论不一致',
  held_endpoint: '端点遭遇未在该解释下确认',
  root_divergence: '环根在不同解释下不一致',
  not_adjacent: '该解释下不构成相邻遭遇',
};

export function explanationLabel(code) {
  return `解释 ${code.replace(/^X/, '')}`;
}

export function location(catalog, code) {
  return catalog.sites[code] || code;
}

export function time(value) {
  return value ? value.replace('T', ' ').replace('Z', ' UTC') : '—';
}

export function duration(seconds) {
  const units = [[86400, '天'], [3600, '小时'], [60, '分'], [1, '秒']];
  const parts = [];
  for (const [size, unit] of units) {
    const count = Math.floor(seconds / size);
    if (count) parts.push(`${count}${unit}`);
    seconds %= size;
  }
  return parts.join(' ') || '0 秒';
}
