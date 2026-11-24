import { node } from './dom.mjs';

export function field(form, name, caption, placeholder) {
  const label = node('label', caption);
  const input = node('input');
  input.name = name;
  input.required = true;
  input.placeholder = placeholder;
  label.append(input);
  form.append(label);
  return input;
}

export function submit(form, label, action) {
  const control = node('button', label, 'primary');
  control.type = 'submit';
  form.append(control);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    control.disabled = true;
    try {
      await action();
    } finally {
      control.disabled = false;
    }
  });
}
