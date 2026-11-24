export function node(tag, text = null, classes = '') {
  const element = document.createElement(tag);
  if (text !== null) element.textContent = text;
  if (classes) element.className = classes;
  return element;
}

export function heading(title, intro) {
  const group = node('div', null, 'section-heading');
  group.append(node('h1', title), node('p', intro, 'muted'));
  return group;
}

export function button(label, action, classes = '') {
  const control = node('button', label, classes);
  control.type = 'button';
  control.addEventListener('click', action);
  return control;
}

export function badge(text, type = '') {
  return node('span', text, `badge ${type}`);
}

export function empty(message) {
  return node('p', message, 'empty');
}

export function select(label, options, change) {
  const wrap = node('label', label, 'inline-label');
  const input = node('select');
  for (const [value, text] of options) {
    const option = node('option', text);
    option.value = value;
    input.append(option);
  }
  if (change) input.addEventListener('change', () => change(input.value));
  wrap.append(input);
  return [wrap, input];
}
