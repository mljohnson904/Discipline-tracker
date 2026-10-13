/* ================= view helpers ================= */
const FORMS = {}, ACTS = {};
const UI = { dashDays: 7, loose: false, pf: { q: '', platform: '', story: '', series: '' }, hookQ: '', hookTag: '', reviewBase: 'auto', importText: '', askOut: '' };
const badge = s => s === 'seed' ? '<span class="badge seed">seed</span>' : '';
const platBadge = p => '<span class="badge p-' + esc(p) + '">' + esc(PNAME[p] || p) + '</span>';
const WIN_OPTIONS = WINDOWS.map(d => [d, d + ' days']);
function field(name, label, value, type, attrs) {
  return '<label>' + esc(label) + '<input type="' + (type || 'text') + '" name="' + name + '" value="' + esc(value) + '" ' + (attrs || '') + '></label>';
}
function select(name, label, options, selected, attrs) {
  return '<label>' + esc(label) + '<select name="' + name + '" ' + (attrs || '') + '>' + options.map(o =>
    '<option value="' + esc(o[0]) + '"' + (String(o[0]) === String(selected == null ? '' : selected) ? ' selected' : '') + '>' + esc(o[1]) + '</option>').join('') + '</select></label>';
}
function goAttrs(l) {
  return 'href="#' + l.go + '" data-go="' + l.go + '"' + (l.sub ? ' data-sub="' + l.sub + '"' : '') + (l.id != null ? ' data-id="' + l.id + '"' : '') +
    (l.series != null ? ' data-series="' + l.series + '"' : '') + (l.idea != null ? ' data-idea="' + l.idea + '"' : '') +
    (l.template != null ? ' data-template="' + l.template + '"' : '') + (l.platform ? ' data-platform="' + l.platform + '"' : '') + (l.days ? ' data-days="' + l.days + '"' : '') + (l.end ? ' data-end="' + l.end + '"' : '');
}
const seriesOptions = () => [['', '— none —']].concat(S.series.slice().sort((a, b) => a.name.localeCompare(b.name)).map(s => [s.id, s.name]));
function metricSummary(m) {
  const bits = [];
  if (m.views != null) bits.push('<b>' + fint(m.views) + '</b> views');
  [['likes', 'likes'], ['comments', 'comments'], ['shares', 'shares'], ['follows_gained', 'follows']].forEach(p => { if (m[p[0]] != null) bits.push(fint(m[p[0]]) + ' ' + p[1]); });
  if (m.stayed_pct != null) bits.push('stayed ' + fpct(m.stayed_pct));
  return '<div class="metric"><span class="win">' + m.window_days + 'd</span> ' + (bits.join(' · ') || 'no numbers') + '</div>';
}
const metricsFor = pid => S.metrics.filter(m => m.post_id === pid).sort((a, b) => a.window_days - b.window_days);
const titleBar = (h, btn) => '<div class="titlebar"><h1>' + h + '</h1>' + (btn || '') + '</div>';

/* ================= Today (dashboard) ================= */
function heroHtml() {
  const [done, total] = checklistProgress();
  const frac = total ? done / total : 0, circ = 2 * Math.PI * 44;
  const acts = suggest(PLATFORMS.map(p => platformSummary(p[0], 'auto')), today());
  const a = acts[0];
  const ring = '<div class="ring" role="img" aria-label="Profile checklist: ' + done + ' of ' + total + ' done"><svg viewBox="0 0 104 104"><circle class="ring-bg" cx="52" cy="52" r="44"/>' +
    '<circle class="ring-fg" cx="52" cy="52" r="44" stroke-dasharray="' + circ.toFixed(1) + '" stroke-dashoffset="' + (circ * (1 - frac)).toFixed(1) + '" transform="rotate(-90 52 52)"/></svg>' +
    '<div class="ring-t"><b>' + done + '</b><span>of ' + total + '</span></div></div>';
  const date = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
  return '<div class="card"><div class="hero">' + ring + '<div><div class="muted">' + esc(date) + '</div><div class="hero-big">Second Mission</div>' +
    '<div class="hero-focus">This week: ' + esc(a ? a.title : "Log this week's numbers to get a focus.") + '</div><div class="row">' +
    '<a class="btn primary small" ' + goAttrs({ go: 'review' }) + '>Weekly review</a>' +
    '<a class="btn small" ' + goAttrs(a ? a.link : { go: 'stats', sub: 'new' }) + '>Do it</a>' +
    '<a class="btn small" ' + goAttrs({ go: 'checklist' }) + '>Profile checklist</a></div></div></div></div>';
}
function flagsHtml(s) {
  return Object.keys(changes(s)).sort().filter(k => changes(s)[k] <= DROP).map(k =>
    '<div class="flag">⚠ ' + esc(CHANGE_LABELS[k] || k) + ' down ' + Math.abs(changes(s)[k]).toFixed(1) + '% vs prior window</div>').join('');
}
function platformCard(platform, days) {
  const s = snapshotFor(platform, days), head = '<h3>' + esc(PNAME[platform]) + '</h3>';
  if (!s) {
    const alt = S.snaps.filter(x => x.platform === platform).sort((a, b) => b.window_end.localeCompare(a.window_end))[0];
    let note = '<p class="muted">No ' + days + 'd snapshot for this platform.</p>';
    if (alt) note += '<p class="muted">Only <b>' + alt.window_days + 'd</b> data exists, so it is left out of this ' + days + 'd comparison. <a ' + goAttrs({ go: 'stats', sub: 'edit', id: alt.id }) + '>See it</a>.</p>';
    return '<section class="card dim">' + head + note + '<a class="btn small" ' + goAttrs({ go: 'stats', sub: 'new', platform: platform, days: days }) + '>Add ' + days + 'd snapshot</a></section>';
  }
  const nf = s.net_followers == null ? '—' : (s.net_followers >= 0 ? '+' : '') + s.net_followers;
  let body = '<div class="muted">' + esc(windowLabel(s)) + ' ' + badge(s.source) + '</div><div class="stats"><div><b>' + fint(s.views) + '</b><span>views</span></div>' +
    '<div><b>' + fint(s.viewers) + '</b><span>viewers</span></div><div><b>' + nf + '</b><span>net followers</span></div></div><dl>';
  cardRows(platform, s).forEach(r => { body += '<dt>' + esc(r[0]) + '</dt><dd>' + r[1] + '<small>' + esc(r[2]) + '</small></dd>'; });
  body += '</dl>' + flagsHtml(s) + (s.notes ? '<p class="note">' + esc(s.notes) + '</p>' : '');
  return '<section class="card">' + head + body + '</section>';
}
function groupTable(rows, keyfn, emptyLabel) {
  const g = groupRows(rows, keyfn, emptyLabel);
  if (!g.length) return '<p class="muted">No posts with metrics in this window.</p>';
  return '<div class="scroll"><table><thead><tr><th></th><th>Posts</th><th>Views</th><th>Eng. rate</th><th>Shares/1K</th><th>Avg stayed</th></tr></thead><tbody>' +
    g.map(r => '<tr><td><b>' + esc(r.key) + '</b><div>' + r.plats.map(platBadge).join('') + '</div></td><td>' + r.n + '</td><td>' + fint(r.views) + '</td><td>' + fpct(r.eng, 2) +
      '</td><td>' + (r.sh == null ? '—' : r.sh.toFixed(2)) + '</td><td>' + fpct(r.stayed) + '</td></tr>').join('') + '</tbody></table></div>';
}
function audienceHtml() {
  if (!S.audience.length) return '';
  const cats = {};
  S.audience.forEach(r => { (cats[r.category] = cats[r.category] || []).push(r); });
  const cells = Object.keys(cats).map(c => '<div class="aud"><h4>' + esc(c.charAt(0).toUpperCase() + c.slice(1)) + '</h4>' + cats[c].map(r =>
    '<div class="bar"><span>' + esc(r.label) + '</span><i style="width:' + Math.min(100, r.pct || 0) + '%"></i><b>' + fpct(r.pct) + '</b></div>').join('') + '</div>').join('');
  return '<h2>YouTube audience <small>28d ' + badge(S.audience[0].source) + '</small></h2><div class="grid">' + cells + '</div>';
}
function viewToday() {
  const days = UI.dashDays, loose = UI.loose;
  const have = new Set(S.snaps.map(s => s.window_days));
  const shown = WINDOWS.filter(d => d === 7 || d === 28 || have.has(d) || d === days);
  const toggle = shown.map(d => '<button type="button" class="' + (d === days ? 'on' : '') + '" data-act="dashWin" data-days="' + d + '">' + d + ' days</button>').join('');
  const rows = postRowsForWindow(days, loose);
  const excluded = new Set(S.metrics.map(m => m.post_id)).size - rows.length;
  const looseLink = days === 28 ? '<button type="button" class="linkbtn" data-act="toggleLoose">' + (loose ? 'Use exact windows only' : 'Include 28d ≈ 30d (Instagram posts are 30d)') + '</button>' : '';
  const top = rows.filter(r => r.views != null).sort((a, b) => b.views - a.views).slice(0, 10);
  const toplist = top.map(r => '<li><a ' + goAttrs({ go: 'posts', sub: 'edit', id: r.id }) + '>' + esc(r.title) + '</a><div>' + platBadge(r.platform) + ' <b>' + fint(r.views) + '</b> views · ' + r.window_days + 'd</div></li>').join('') ||
    '<li class="muted">No post views in this window.</li>';
  return heroHtml() + '<h1 class="sr-only">Today</h1><div class="toggle">' + toggle + '</div>' +
    '<p class="muted">Platforms are compared on the <b>same ' + days + '-day window</b>. A platform with no ' + days + 'd data is shown greyed out rather than mixed in. Missing numbers show as —, never as zero.</p>' +
    '<div class="grid">' + PLATFORMS.map(p => platformCard(p[0], days)).join('') + '</div>' +
    '<h2>Top posts <small>' + days + 'd metrics' + (loose ? ' (28d ≈ 30d)' : '') + '</small></h2><p class="muted">' + excluded + ' post(s) have no metrics for this window. ' + looseLink + '</p>' +
    '<ol class="toplist">' + toplist + '</ol><h2>By topic tag</h2>' + groupTable(rows, r => r.topic_tag, '(untagged)') +
    '<h2>By series</h2>' + groupTable(rows, r => r.series_name, '(no series)') + '<h2>By story key</h2>' + groupTable(rows, r => r.story_key, '(no story key)') +
    '<p class="muted">Tip: topic tags aren\'t in the seed data (none were invented). Add them on the post pages and the tag table fills in.</p>' + audienceHtml();
}
ACTS.dashWin = el => { UI.dashDays = +el.dataset.days; render(); };
ACTS.toggleLoose = () => { UI.loose = !UI.loose; render(); };

/* ================= Posts ================= */
function viewPosts() {
  const f = UI.pf;
  let posts = S.posts.slice();
  if (f.platform) posts = posts.filter(p => p.platform === f.platform);
  if (f.story) posts = posts.filter(p => p.story_key === f.story);
  if (f.series) posts = posts.filter(p => String(p.series_id) === String(f.series));
  if (f.q) { const q = f.q.toLowerCase(); posts = posts.filter(p => [p.title, p.hook_text, p.topic_tag, p.story_key].some(v => v && v.toLowerCase().indexOf(q) >= 0)); }
  posts.sort((a, b) => (a.post_date == null) - (b.post_date == null) || String(b.post_date).localeCompare(String(a.post_date)) || b.id - a.id);
  const cards = posts.map(p => {
    const ser = p.series_id ? byId('series', p.series_id) : null;
    const meta = [fdate(p.post_date, p.date_approx), ser ? 'Series: ' + esc(ser.name) + (p.series_part ? ' Part ' + p.series_part : '') : '', p.story_key ? 'Story: ' + esc(p.story_key) : '', p.topic_tag ? '#' + esc(p.topic_tag) : ''].filter(Boolean).join(' · ');
    const ms = metricsFor(p.id).map(metricSummary).join('') || '<div class="muted">No metrics yet</div>';
    return '<article class="card post"><div>' + platBadge(p.platform) + ' ' + badge(p.source) + '</div><h3><a ' + goAttrs({ go: 'posts', sub: 'edit', id: p.id }) + '>' + esc(p.title) + '</a></h3>' +
      '<div class="muted">' + meta + '</div>' + (p.hook_text ? '<div class="hook">Hook: “' + esc(p.hook_text) + '”</div>' : '') + ms + (p.flag ? '<div class="flag">⚑ ' + esc(p.flag) + '</div>' : '') + '</article>';
  }).join('');
  const stories = Array.from(new Set(S.posts.map(p => p.story_key).filter(Boolean))).sort();
  const filt = '<form class="filters" data-form="postFilter">' + field('q', 'Search', f.q, 'search') + select('platform', 'Platform', [['', 'All']].concat(PLATFORMS), f.platform) +
    select('story', 'Story', [['', 'All']].concat(stories.map(s => [s, s])), f.story) + select('series', 'Series', [['', 'All']].concat(seriesOptions().slice(1)), f.series) + '<button class="btn">Filter</button></form>';
  return titleBar('Post log', '<a class="btn" ' + goAttrs({ go: 'posts', sub: 'new' }) + '>+ Add post</a>') + filt +
    '<p class="muted">' + posts.length + ' post(s). Titles and dates are editable: open a post to fix them.</p><div class="grid">' + cards + '</div>';
}
FORMS.postFilter = fd => { UI.pf = { q: fd.q || '', platform: fd.platform || '', story: fd.story || '', series: fd.series || '' }; render(); };

function metricInputs(m) {
  return METRIC_FIELDS.map(f => field(f[0], f[1], m ? m[f[0]] : '', 'number', 'step="any"')).join('');
}
function viewPostForm(id) {
  const p = id ? byId('posts', id) : null;
  if (id && !p) return '<p>Post not found.</p>';
  const g = (k, d) => (p && p[k] != null ? p[k] : (d == null ? '' : d));
  const stories = Array.from(new Set(S.posts.map(x => x.story_key).filter(Boolean)));
  const newMetrics = '<fieldset><legend>' + (p ? 'Add a metric record' : 'Metrics (optional)') + '</legend><div class="row">' + select('window_days', 'Window', WIN_OPTIONS, 28) +
    field('window_end', 'Window ends', today(), 'date') + '</div><p class="muted">Every metric record stores its date window. Leave blank what you don\'t know.</p><div class="row">' + metricInputs(null) + '</div></fieldset>';
  const form = '<form data-form="postSave" data-id="' + (p ? p.id : '') + '" class="stack">' +
    field('title', 'Title (as shown in the app: edit freely)', g('title'), 'text', 'required') +
    '<div class="row">' + select('platform', 'Platform', PLATFORMS, g('platform', 'tiktok')) + field('post_date', 'Post date (approximate is fine)', g('post_date'), 'date') +
    '<label class="check"><input type="checkbox" name="date_approx" value="1" ' + (g('date_approx', 1) ? 'checked' : '') + '> date is approximate</label></div>' +
    field('hook_text', 'Hook text', g('hook_text')) +
    '<div class="row">' + field('topic_tag', 'Topic tag', g('topic_tag'), 'text', 'placeholder="e.g. observation"') + field('story_key', 'Story key (links the same story across platforms)', g('story_key'), 'text', 'list="storyList"') + '</div>' +
    '<datalist id="storyList">' + stories.map(s => '<option value="' + esc(s) + '">').join('') + '</datalist>' +
    '<div class="row">' + select('series_id', 'Series', seriesOptions(), g('series_id')) + field('series_part', 'Part #', g('series_part'), 'number', 'min="1"') + '</div>' +
    field('flag', 'Flag', g('flag'), 'text', 'placeholder="e.g. possible duplicate or failed upload"') +
    '<label>Notes<textarea name="notes" rows="3">' + esc(g('notes')) + '</textarea></label>' + (p ? '' : newMetrics) +
    '<button class="btn primary">' + (p ? 'Save post' : 'Add post') + '</button></form>';
  let extra = '';
  if (p) {
    const rows = metricsFor(p.id).map(m => '<form data-form="metricSave" data-id="' + m.id + '" class="card stack"><div class="muted">' + esc(windowLabel(m)) + ' ' + badge(m.source) + '</div>' +
      '<div class="row">' + select('window_days', 'Window', WIN_OPTIONS, m.window_days) + field('window_end', 'Window ends', m.window_end, 'date') + '</div><div class="row">' + metricInputs(m) + '</div>' +
      '<div class="row"><button class="btn small primary">Save</button><button type="button" class="btn small danger" data-act="metricDel" data-id="' + m.id + '">Delete</button></div></form>').join('');
    extra = '<h2>Metric records</h2>' + (rows || '<p class="muted">None yet.</p>') + '<form data-form="metricAdd" data-id="' + p.id + '" class="stack">' + newMetrics + '<button class="btn">Add metric record</button></form>' +
      '<button type="button" class="btn danger" data-act="postDel" data-id="' + p.id + '">Delete post</button>';
  }
  return '<p><a ' + goAttrs({ go: 'posts' }) + '>← Post log</a></p><h1>' + (p ? 'Edit post ' + badge(p.source) : 'Add post') + '</h1>' + form + extra;
}
function metricFromForm(postId, fd) {
  const vals = {};
  METRIC_FIELDS.forEach(f => { vals[f[0]] = num(fd[f[0]], f[2]); });
  const days = num(fd.window_days, 'i') || 28, end = validIso(fd.window_end) ? fd.window_end : today();
  return Object.assign({ post_id: postId, window_start: addDays(end, -(days - 1)), window_end: end, window_days: days }, vals);
}
FORMS.postSave = (fd, el) => {
  const id = el.dataset.id ? +el.dataset.id : null;
  const vals = { title: txt(fd.title) || 'Untitled', platform: PNAME[fd.platform] ? fd.platform : 'tiktok', post_date: validIso(fd.post_date) ? fd.post_date : null, date_approx: fd.date_approx ? 1 : 0,
    hook_text: txt(fd.hook_text), topic_tag: txt(fd.topic_tag), series_id: num(fd.series_id, 'i'), series_part: num(fd.series_part, 'i'), story_key: txt(fd.story_key), flag: txt(fd.flag), notes: txt(fd.notes) };
  if (id) Object.assign(byId('posts', id), vals);
  else {
    const pid = nid();
    S.posts.push(Object.assign({ id: pid, source: 'manual' }, vals));
    if (METRIC_FIELDS.some(f => num(fd[f[0]], f[2]) != null)) { S.metrics.push(Object.assign({ id: nid(), source: 'manual' }, metricFromForm(pid, fd))); }
  }
  markDirty('posts', 'metrics'); toast('Post saved'); go('posts');
};
FORMS.metricAdd = (fd, el) => {
  const pid = +el.dataset.id;
  S.metrics.push(Object.assign({ id: nid(), source: 'manual' }, metricFromForm(pid, fd)));
  markDirty('metrics'); toast('Metric record added'); render();
};
FORMS.metricSave = (fd, el) => {
  const m = byId('metrics', el.dataset.id);
  Object.assign(m, metricFromForm(m.post_id, fd), { source: 'manual' });
  markDirty('metrics'); toast('Metric record saved'); render();
};
ACTS.metricDel = el => confirmBar('Delete this metric record?', () => { S.metrics = S.metrics.filter(m => m.id !== +el.dataset.id); markDirty('metrics'); render(); });
ACTS.postDel = el => confirmBar('Delete this post and its metrics?', () => {
  const id = +el.dataset.id;
  S.posts = S.posts.filter(p => p.id !== id); S.metrics = S.metrics.filter(m => m.post_id !== id); S.hookPosts = S.hookPosts.filter(x => x.post_id !== id);
  S.scripts.forEach(s => { if (s.post_id === id) s.post_id = null; });
  markDirty('posts', 'metrics', 'hookPosts', 'scripts'); go('posts');
});

/* ================= Channel stats ================= */
function viewStats() {
  const rows = S.snaps.slice().sort((a, b) => a.platform.localeCompare(b.platform) || a.window_days - b.window_days || b.window_end.localeCompare(a.window_end));
  const cards = rows.map(s => {
    const vals = SNAP_FIELDS.filter(f => s[f[0]] != null).map(f => esc(f[1]) + ': <b>' + fnum(s[f[0]], f[2] === 'f' ? 1 : 0) + '</b>').join(' · ');
    const ch = changes(s), chs = Object.keys(ch).map(k => '<span class="' + (ch[k] <= DROP ? 'flag-inline' : '') + '">' + esc(CHANGE_LABELS[k] || k) + ' ' + (ch[k] >= 0 ? '+' : '') + ch[k].toFixed(1) + '%</span> ').join('');
    return '<article class="card">' + platBadge(s.platform) + ' ' + badge(s.source) + '<h3><a ' + goAttrs({ go: 'stats', sub: 'edit', id: s.id }) + '>' + esc(windowLabel(s)) + '</a></h3><div>' + vals +
      '</div><div class="muted">vs prior: ' + (chs || '—') + '</div>' + (s.notes ? '<p class="note">' + esc(s.notes) + '</p>' : '') + '</article>';
  }).join('');
  return titleBar('Channel stats', '<a class="btn" ' + goAttrs({ go: 'stats', sub: 'new' }) + '>+ Add snapshot</a>') +
    '<p class="muted">Channel-level numbers copied from each app, one record per platform and date window.</p><div class="grid">' + cards + '</div>';
}
function viewStatsForm(id, pre) {
  const s = id ? byId('snaps', id) : null;
  if (id && !s) return '<p>Snapshot not found.</p>';
  pre = pre || {};
  const g = (k, d) => (s && s[k] != null ? s[k] : (d == null ? '' : d));
  const inputs = SNAP_FIELDS.map(f => field(f[0], f[1], g(f[0]), 'number', 'step="any"')).join('');
  return '<p><a ' + goAttrs({ go: 'stats' }) + '>← Channel stats</a></p><h1>' + (s ? 'Edit' : 'Add') + ' channel snapshot</h1><form data-form="statsSave" data-id="' + (s ? s.id : '') + '" class="stack">' +
    '<div class="row">' + select('platform', 'Platform', PLATFORMS, g('platform', pre.platform || 'tiktok')) + select('window_days', 'Window', WIN_OPTIONS, g('window_days', pre.days || 28)) +
    field('window_end', 'Window ends', g('window_end', pre.end || today()), 'date') + '</div><div class="row">' + inputs + '</div>' +
    '<label>Notes (e.g. discrepancies between screens)<textarea name="notes" rows="3">' + esc(g('notes')) + '</textarea></label><button class="btn primary">Save</button></form>' +
    (s ? '<button type="button" class="btn danger" data-act="statsDel" data-id="' + s.id + '">Delete</button>' : '');
}
FORMS.statsSave = (fd, el) => {
  const days = num(fd.window_days, 'i') || 28, end = validIso(fd.window_end) ? fd.window_end : today();
  const vals = { platform: PNAME[fd.platform] ? fd.platform : 'tiktok', window_days: days, window_end: end, window_start: addDays(end, -(days - 1)), notes: txt(fd.notes) };
  SNAP_FIELDS.forEach(f => { vals[f[0]] = num(fd[f[0]], f[2]); });
  if (el.dataset.id) Object.assign(byId('snaps', el.dataset.id), vals);
  else S.snaps.push(Object.assign({ id: nid(), extra: {}, source: 'manual' }, vals));
  markDirty('snaps'); toast('Snapshot saved'); go('stats');
};
ACTS.statsDel = el => confirmBar('Delete this snapshot?', () => { S.snaps = S.snaps.filter(s => s.id !== +el.dataset.id); markDirty('snaps'); go('stats'); });
