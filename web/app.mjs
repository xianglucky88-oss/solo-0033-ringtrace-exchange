import { request } from './client.mjs';
import { openDetail } from './dialog.mjs';
import { button, empty } from './dom.mjs';
import { showEvidence } from './evidence.mjs';
import { tracks } from './views/tracks.mjs';
import { encounters } from './views/encounters.mjs';
import { batches } from './views/batches.mjs';
import { links } from './views/links.mjs';
import { provenance } from './views/provenance.mjs';
import { releases } from './views/releases.mjs';

const screen = document.getElementById('screen');
const notice = document.getElementById('notice');
const refreshButton = document.getElementById('refresh');
const views = { tracks, encounters, batches, provenance, links, releases };
const ctx = { refresh, run, change, openEvent };
let busy = false;

function render() {
  if (!ctx.data) return;
  const hash = window.location.hash.slice(1);
  const page = Object.hasOwn(views, hash) ? hash : 'tracks';
  for (const link of document.querySelectorAll('.tabs a')) {
    if (link.hash === `#${page}`) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }
  document.getElementById('revision').textContent = `修订 ${ctx.data.revision}`;
  screen.replaceChildren(views[page](ctx));
}

function openEvent(event) {
  const row = typeof event === 'string' ? ctx.data.encounters.find(item => item.event === event) : event;
  if (row) openDetail(`遭遇 · ${row.event}`, showEvidence(row, ctx.data.catalog));
}

function announce(message = '', failed = false) {
  notice.textContent = message;
  notice.className = failed ? 'error' : '';
}

async function run(task) {
  announce();
  try {
    await task();
  } catch (error) {
    announce(error.message, true);
  }
}

async function readWorkspace() {
  const [data, versions] = await Promise.all([request('/api/workspace'), request('/api/releases')]);
  Object.assign(ctx, { data, versions });
  render();
}

async function change(task) {
  if (busy) return;
  busy = true;
  refreshButton.disabled = true;
  await run(async () => {
    const message = await task();
    try {
      await readWorkspace();
    } catch (error) {
      throw new Error(`${message ? `${message} ` : ''}界面刷新失败：${error.message}`);
    }
    announce(message);
  });
  refreshButton.disabled = false;
  busy = false;
}

async function refresh() {
  await change(async () => '');
  if (!ctx.data) screen.replaceChildren(empty('工作资料暂不可用。'), button('重试', refresh, 'primary'));
}

window.addEventListener('hashchange', render);
refreshButton.addEventListener('click', refresh);
refresh();
