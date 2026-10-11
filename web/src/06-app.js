/* ================= shell, router, events ================= */
const NAV_GROUPS = [
  ['plan', 'Today', 'home', [['today', 'Today', 'home']], true],
  ['plan', 'Plan', 'calendar', [['series', 'Series', 'layers'], ['scripts', 'Scripts', 'file'], ['hooks', 'Hooks', 'bookmark']], false],
  ['grade', 'Track', 'chart', [['posts', 'Posts', 'list'], ['stats', 'Channel stats', 'activity'], ['review', 'Weekly review', 'target']], false],
  ['manage', 'Checklist', 'check', [['checklist', 'Checklist', 'check']], true],
  ['support', 'Data', 'database', [['data', 'Data', 'database']], true]
];
const ICONS = {
  brand: '<rect x="2" y="6" width="14" height="12" rx="2"/><path d="M22 8l-6 4 6 4z"/>', home: '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/>',
  calendar: '<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M3 9h18M8 2v4M16 2v4"/>', chart: '<path d="M4 20V10M10 20V4M16 20v-8M22 20H2"/>',
  check: '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>', database: '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
  layers: '<path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/>', file: '<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 13h7M9 17h7"/>', bookmark: '<path d="M6 3h12v18l-6-4-6 4z"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>', activity: '<path d="M3 12h4l3-8 4 16 3-8h4"/>', target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  search: '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>', sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/>'
};
const icon = (n, x) => '<svg class="ic ' + (x || '') + '" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' + ICONS[n] + '</svg>';
const TABS = ['today', 'posts', 'stats', 'series', 'hooks', 'scripts', 'checklist', 'review', 'data'];
let R = { tab: 'today', sub: null, id: null, params: {} }, loaded = false;

function go(tab, sub, id, params) {
  R = { tab, sub: sub || null, id: id || null, params: params || {} };
  closeMenus(); render(); window.scrollTo(0, 0);
  try { history.replaceState(null, '', '#' + tab); } catch (e) { /* frame may refuse */ }
}
function groupOfTab(tab) { for (let i = 0; i < NAV_GROUPS.length; i++) if (NAV_GROUPS[i][3].some(t => t[0] === tab)) return i; return 0; }

function buildShell() {
  $('#app').innerHTML = '<a class="skip" href="#main">Skip to content</a>' +
    '<header class="appbar"><button class="ab-brand" id="aboutBtn" type="button" aria-expanded="false" aria-controls="aboutPop">' + icon('brand') + '<span><span class="ab-long">Channel </span>Builder</span></button>' +
    '<div class="ab-search"><label class="sr-only" for="gsearch">Search posts, hooks, scripts and series</label>' + icon('search') +
    '<input type="text" id="gsearch" placeholder="Search: hook, observation, F-16" autocomplete="off" role="combobox" aria-expanded="false" aria-controls="gresults" aria-autocomplete="list">' +
    '<ul id="gresults" role="listbox" aria-label="Search results" hidden></ul></div><span class="ab-spacer"></span>' +
    '<span class="schip" id="schip" role="status">Loading…</span>' +
    '<button class="ico" id="searchBtn" type="button" aria-label="Search">' + icon('search') + '</button>' +
    '<button class="ico" id="themeBtn" type="button" aria-label="Switch light or dark mode">' + icon('moon', 'ic-moon') + icon('sun', 'ic-sun') + '</button>' +
    '<div id="aboutPop" hidden><p><strong>Channel Builder</strong></p><p>For the Second Mission channel on TikTok, YouTube Shorts and Instagram Reels. ' +
    'Your data is kept in this page\'s own database, so it follows you between your phone and computer.</p><p class="small">Use Data to export a backup of everything.</p></div></header>' +
    '<div class="shell"><nav id="nav" aria-label="Sections"><div class="inner"></div></nav><div class="content"><main id="main"></main></div></div>' +
    '<div id="cfmBar" role="alertdialog" aria-live="assertive" hidden></div><div id="toast" role="status" aria-live="polite"></div><div id="txtBox" hidden></div>';
}
function renderNav() {
  const gi = groupOfTab(R.tab);
  $('#nav .inner').innerHTML = NAV_GROUPS.map((g, i) => {
    const tabs = g[3].map(t => '<a class="tab" href="#' + t[0] + '" data-go="' + t[0] + '"' + (t[0] === R.tab ? ' aria-current="page"' : '') + '>' + icon(t[2]) + '<span class="tl">' + esc(t[1]) + '</span></a>').join('');
    if (g[4]) return '<div class="grp solo' + (i === gi ? ' has-active' : '') + '" data-grp="' + g[0] + '"><div class="grp-tabs">' + tabs + '</div></div>';
    return '<div class="grp' + (i === gi ? ' has-active' : '') + '" data-grp="' + g[0] + '"><span class="grp-label" aria-hidden="true">' + esc(g[1]) + '</span>' +
      '<button class="grp-toggle" type="button" aria-expanded="false" aria-controls="gt-' + i + '">' + icon(g[2]) + '<span>' + esc(g[1]) + '</span></button><div class="grp-tabs" id="gt-' + i + '">' + tabs + '</div></div>';
  }).join('');
}
function viewFor() {
  const sub = R.sub, id = R.id, p = R.params;
  switch (R.tab) {
    case 'posts': return sub === 'new' ? viewPostForm(null) : sub === 'edit' ? viewPostForm(id) : viewPosts();
    case 'stats': return sub === 'new' ? viewStatsForm(null, p) : sub === 'edit' ? viewStatsForm(id) : viewStats();
    case 'series': return id ? viewSeriesDetail(id) : viewSeriesList();
    case 'hooks': return sub === 'edit' ? viewHookEdit(id) : viewHooks();
    case 'scripts': return sub === 'new' ? viewScriptForm(null, p) : sub === 'edit' ? viewScriptForm(id) : viewScripts();
    case 'checklist': return viewChecklist();
    case 'review': return viewReview();
    case 'data': return sub === 'preview' ? viewImportPreview() : viewData();
    default: return viewToday();
  }
}
function render() {
  const main = $('#main');
  if (!loaded) { main.innerHTML = '<section class="panel active"><p class="muted">Loading your data…</p></section>'; return; }
  renderNav();
  const grp = NAV_GROUPS[groupOfTab(R.tab)][0];
  let html;
  try { html = viewFor(); } catch (e) { html = '<h1>Something went wrong</h1><p class="muted">' + esc(e && e.message) + '</p><p><a ' + goAttrs({ go: 'today' }) + '>Back to Today</a></p>'; if (window.console) console.error(e); }
  main.innerHTML = '<section class="panel active" data-grp="' + grp + '">' + html + '</section>';
  if (R.tab === 'scripts' && (R.sub === 'new' || R.sub === 'edit')) bindScriptForm();
}

/* ---- status, toast, confirm, copy ---- */
function setStatus(st) {
  const chip = $('#schip');
  if (!chip) return;
  const map = { saving: ['Saving…', ''], ok: ['Saved', 'ok'], local: ['Saved on this device', 'local'], error: ['Not saved', 'err'] };
  const m = map[st] || map.ok;
  chip.textContent = m[0]; chip.className = 'schip ' + m[1];
  chip.title = st === 'error' ? Store.error : st === 'local' ? 'This view has no database, so your data is kept in this browser only.' : '';
  if (st === 'error') toast(Store.error || 'Could not save');
}
let toastTimer = null;
function toast(msg) {
  const t = $('#toast');
  if (!t) return;
  t.textContent = msg; t.classList.add('show');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove('show'), 2600);
}
let cfmYes = null;
function confirmBar(msg, onYes) {
  const b = $('#cfmBar');
  cfmYes = onYes;
  b.innerHTML = '<p>' + esc(msg) + '</p><div class="row"><button type="button" class="btn primary small" data-act="cfmYes">Yes</button><button type="button" class="btn small" data-act="cfmNo">Cancel</button></div>';
  b.hidden = false; $('[data-act=cfmYes]', b).focus();
}
ACTS.cfmYes = () => { const f = cfmYes; cfmYes = null; $('#cfmBar').hidden = true; if (f) f(); };
ACTS.cfmNo = () => { cfmYes = null; $('#cfmBar').hidden = true; };
function showText(title, text) {
  const b = $('#txtBox');
  b.innerHTML = '<div class="txt-card"><h3>' + esc(title) + '</h3><p class="muted">Select all and copy this text.</p><textarea readonly id="txtArea" rows="12">' + esc(text) + '</textarea>' +
    '<div class="row"><button type="button" class="btn primary small" data-act="txtCopy">Copy</button><button type="button" class="btn small" data-act="txtClose">Close</button></div></div>';
  b.hidden = false; const a = $('#txtArea'); a.focus(); a.select();
}
ACTS.txtClose = () => { $('#txtBox').hidden = true; };
ACTS.txtCopy = () => copyText($('#txtArea').value, 'Copied');
function copyText(text, msg) {
  const fallback = () => showText('Copy this text', text);
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(() => toast(msg || 'Copied'), fallback);
    else fallback();
  } catch (e) { fallback(); }
}

/* ---- menus, search, theme, events ---- */
function closeMenus() {
  $$('#nav .grp.open').forEach(g => { g.classList.remove('open'); const t = $('.grp-toggle', g); if (t) t.setAttribute('aria-expanded', 'false'); });
  const pop = $('#aboutPop'); if (pop) { pop.hidden = true; $('#aboutBtn').setAttribute('aria-expanded', 'false'); }
  closeSearch();
}
let sel = -1, results = [];
function closeSearch() {
  const list = $('#gresults'), input = $('#gsearch'), bar = $('.appbar');
  if (!list) return;
  list.hidden = true; input.setAttribute('aria-expanded', 'false'); sel = -1; bar.classList.remove('searching');
}
function hl(text, q) {
  const i = text.toLowerCase().indexOf(q.toLowerCase());
  return i < 0 ? esc(text) : esc(text.slice(0, i)) + '<mark>' + esc(text.slice(i, i + q.length)) + '</mark>' + esc(text.slice(i + q.length));
}
function runSearch() {
  const input = $('#gsearch'), list = $('#gresults'), q = input.value.trim();
  if (q.length < 2) { list.hidden = true; return; }
  results = searchAll(q);
  list.innerHTML = results.length ? results.map((r, i) => '<li role="option" id="gr' + i + '" data-i="' + i + '" aria-selected="false"><div class="r-top"><b>' + hl(r.title, q) + '</b><span class="r-tab">' + esc(r.tab) + '</span></div>' +
    (r.snip ? '<div class="r-snip">' + hl(r.snip, q) + '</div>' : '') + '</li>').join('') : '<li class="r-none" role="presentation">No matches for “' + esc(q) + '”.</li>';
  list.hidden = false; input.setAttribute('aria-expanded', 'true'); sel = -1;
}
function chooseResult(i) { const r = results[i]; if (r) { closeSearch(); $('#gsearch').value = ''; go(r.go.go, r.go.sub, r.go.id); } }
function setSel(i) {
  const items = $$('#gresults li[role=option]');
  if (!items.length) return;
  sel = (i + items.length) % items.length;
  items.forEach((li, k) => li.setAttribute('aria-selected', k === sel ? 'true' : 'false'));
  $('#gsearch').setAttribute('aria-activedescendant', items[sel].id); items[sel].scrollIntoView({ block: 'nearest' });
}
function wireEvents() {
  document.addEventListener('click', e => {
    const t = e.target;
    const nav = t.closest('[data-go]');
    if (nav) {
      e.preventDefault();
      const d = nav.dataset, params = {};
      ['platform', 'days', 'end', 'template', 'series', 'idea'].forEach(k => { if (d[k] != null) params[k] = d[k]; });
      go(d.go, d.sub, d.id, params); return;
    }
    const tog = t.closest('.grp-toggle');
    if (tog) {
      e.stopPropagation();
      const g = tog.parentNode, open = !g.classList.contains('open');
      $$('#nav .grp.open').forEach(x => { if (x !== g) x.classList.remove('open'); });
      g.classList.toggle('open', open); tog.setAttribute('aria-expanded', open ? 'true' : 'false'); return;
    }
    if (t.closest('#aboutBtn')) { e.stopPropagation(); const pop = $('#aboutPop'); pop.hidden = !pop.hidden; $('#aboutBtn').setAttribute('aria-expanded', pop.hidden ? 'false' : 'true'); return; }
    if (t.closest('#aboutPop')) return;
    if (t.closest('#themeBtn')) {
      const cur = document.documentElement.getAttribute('data-theme') || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'), next = cur === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try { localStorage.setItem('cb-theme', next); } catch (err) { /* ignore */ }
      return;
    }
    if (t.closest('#searchBtn')) { e.stopPropagation(); $('.appbar').classList.add('searching'); $('#gsearch').focus(); return; }
    const li = t.closest('#gresults li[data-i]');
    if (li) { chooseResult(+li.dataset.i); return; }
    const act = t.closest('[data-act]');
    if (act && ACTS[act.dataset.act]) { e.preventDefault(); ACTS[act.dataset.act](act, e); return; }
    if (!t.closest('#gsearch')) closeMenus();
  });
  document.addEventListener('submit', e => {
    const form = e.target.closest('[data-form]');
    if (!form) return;
    e.preventDefault();
    let fd;
    try { fd = Object.fromEntries(new FormData(form, e.submitter)); } catch (err) { fd = Object.fromEntries(new FormData(form)); }
    if (FORMS[form.dataset.form]) FORMS[form.dataset.form](fd, form);
  });
  document.addEventListener('change', e => {
    const t = e.target;
    if (t.matches && t.matches('[data-autosubmit]')) { t.form.requestSubmit(); return; }
    if (t.id === 'csvfile' || t.id === 'jsonfile') {
      const f = t.files && t.files[0];
      if (!f) return;
      const rd = new FileReader();
      rd.onload = () => { const box = $(t.id === 'csvfile' ? '#csvtext' : '#jsontext'); if (box) box.value = rd.result; };
      rd.readAsText(f);
    }
  });
  const input = $('#gsearch');
  input.addEventListener('input', runSearch);
  input.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSel(sel + 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setSel(sel - 1); }
    else if (e.key === 'Enter') { e.preventDefault(); chooseResult(sel >= 0 ? sel : 0); }
    else if (e.key === 'Escape') { closeSearch(); input.blur(); }
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') { if (!$('#cfmBar').hidden) ACTS.cfmNo(); else if (!$('#txtBox').hidden) ACTS.txtClose(); else closeMenus(); }
    if (e.key === '/' && !/^(INPUT|TEXTAREA|SELECT)$/.test((document.activeElement || {}).tagName || '')) { e.preventDefault(); $('.appbar').classList.add('searching'); input.focus(); }
  });
}

/* ================= boot ================= */
(async function boot() {
  buildShell();
  const h = (location.hash || '').replace('#', '');
  if (TABS.indexOf(h) >= 0) R.tab = h;
  wireEvents();
  render();
  await initStore();
  loaded = true;
  render();
})();
