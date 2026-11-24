export async function request(path, payload, { raw = false, revision } = {}) {
  const options = payload === undefined ? {} : {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: raw ? payload : JSON.stringify(payload),
  };
  if (revision !== undefined) options.headers['If-Match'] = `"${revision}"`;
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw new Error('无法连接本机服务，请确认服务仍在运行。');
  }
  const value = await response.json().catch(() => null);
  if (!response.ok || value === null) {
    throw new Error(value?.message || `服务响应异常（${response.status}）。`);
  }
  return value;
}
