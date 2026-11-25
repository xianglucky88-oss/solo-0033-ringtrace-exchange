export const reasons = {
  inactive_band: '报文环号未在该时刻生效',
  peer_conflict: '同级来源不一致',
  lower_disagreement: '低优先来源有分歧',
  no_common_second: '同级报文无共同有效观测秒',
  same_time: '同刻遭遇无法排序',
  overlapping_window: '观测区间相交无法排序',
  held_between: '途经待复核遭遇',
  intervening_event: '中间还夹着确认遭遇',
};

export function location(catalog, code) {
  return catalog.sites[code] || code;
}

export function time(value) {
  return value ? value.replace('T', ' ').replace('Z', ' UTC') : '—';
}

export function timeRange(from, until) {
  if (!from) return '—';
  return until && until !== from ? `${time(from)} 至 ${time(until)}` : time(from);
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

export function durationRange(min, max) {
  return min === max ? duration(min) : `${duration(min)} 至 ${duration(max)}`;
}
