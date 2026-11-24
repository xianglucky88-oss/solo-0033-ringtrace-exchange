import { node } from './dom.mjs';

export function table(headers, rows, label) {
  const wrapper = node('div', null, 'table-scroll');
  const grid = node('table');
  grid.setAttribute('aria-label', label);
  const header = grid.createTHead().insertRow();
  for (const title of headers) {
    const cell = node('th', title);
    cell.scope = 'col';
    header.append(cell);
  }
  const body = grid.createTBody();
  for (const values of rows) {
    const row = body.insertRow();
    for (const value of values) {
      const cell = row.insertCell();
      if (value instanceof Node) cell.append(value);
      else cell.textContent = value ?? '—';
    }
  }
  wrapper.append(grid);
  return wrapper;
}
