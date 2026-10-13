/* ================= Weekly review ================= */
function rnum(v, dec) {
  if (v == null) return '—';
  if (v === Math.trunc(v) && !dec) return v.toLocaleString('en-US', { maximumFractionDigits: 0 });
  const d = Math.abs(v) >= 10 ? dec : Math.max(dec, 1);
  return v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
}
function reviewTable(s) {
  const b = s.baseline;
  let body = s.rows.map(r => {
    const c = r.chg, flag = c != null && c <= DROP;
    return '<tr><td>' + esc(r.label) + '</td><td>' + rnum(r.week, r.dec) + '</td><td>' + (b ? rnum(r.base, r.dec) : '—') + '</td><td' + (flag ? ' class="flag-inline"' : '') + '>' +
      (c == null ? '—' : (c >= 0 ? '+' : '') + c.toFixed(0) + '%') + (flag ? ' ⚠' : '') + '</td></tr>';
  }).join('');
  const wr = s.weekRates, br = s.baseRates;
  [['Engagement rate', 'eng', x => fpct(x, 2)], ['Shares / 1K views', 'shares1k', x => x == null ? '—' : x.toFixed(2)], ['Profile view → follow', 'ptf', x => fpct(x)], ['Net follows / 1K viewers', 'fol1k', x => x == null ? '—' : x.toFixed(1)]].forEach(x => {
    if (wr[x[1]] == null && (!br || br[x[1]] == null)) return;
    body += '<tr class="rate"><td>' + x[0] + '</td><td>' + x[2](wr[x[1]]) + '</td><td>' + (br ? x[2](br[x[1]]) : '—') + '</td><td></td></tr>';
  });
  return '<div class="scroll"><table><thead><tr><th></th><th>This week</th><th>Baseline / 7d</th><th>Change</th></tr></thead><tbody>' + body + '</tbody></table></div>';
}
function viewReview() {
  const base = UI.reviewBase === 'auto' ? 'auto' : +UI.reviewBase, t = today();
  const sums = PLATFORMS.map(p => platformSummary(p[0], base));
  const avail = Array.from(new Set(S.snaps.filter(s => s.window_days >= 14).map(s => s.window_days))).sort((a, b) => a - b);
  const chips = '<button type="button" class="chip' + (base === 'auto' ? ' on' : '') + '" data-act="reviewBase" data-base="auto">Auto</button>' +
    avail.map(d => '<button type="button" class="chip' + (base === d ? ' on' : '') + '" data-act="reviewBase" data-base="' + d + '">' + d + 'd</button>').join('');
  const acts = suggest(sums, t);
  const actHtml = acts.slice(0, 3).map(a => '<li class="act"><b>' + esc(a.title) + '</b><p>' + esc(a.why) + '</p><a class="btn small" ' + goAttrs(a.link) + '>' + esc(a.linkText) + '</a></li>').join('');
  const more = acts.slice(3).map(a => '<li>' + esc(a.title) + '</li>').join('');
  let cards = '';
  const needs = [];
  sums.forEach(s => {
    const name = PNAME[s.platform];
    if (!s.s7) { needs.push('<li>No 7-day snapshot for ' + esc(name) + '. <a ' + goAttrs({ go: 'stats', sub: 'new', platform: s.platform, days: 7 }) + '>Add one</a> to include it.</li>'); return; }
    const s7 = s.s7, age = Math.round((pd(t) - pd(s7.window_end)) / 864e5);
    const stale = age > 8 ? '<p class="note">This snapshot ended ' + age + ' days ago (' + fdate(s7.window_end) + '). Log a newer one for a current read.</p>' : '';
    let note;
    if (s.baseline) note = '<p class="muted">Baseline = ' + esc(baselineLabel(s.baseline)) + '.</p>';
    else {
      note = '<p class="muted">No baseline yet, so there are no comparisons.</p>';
      const end = s7.window_start ? addDays(s7.window_start, -1) : '';
      needs.push('<li>' + esc(name) + ' needs a baseline: add a 28d snapshot ending ' + fdate(end) + ' (exact), or any 28/60/90d snapshot that includes this week (I subtract this week). <a ' +
        goAttrs({ go: 'stats', sub: 'new', platform: s.platform, days: 28, end: end }) + '>Add it</a>.</li>');
    }
    cards += '<section class="card"><h3>' + esc(name) + ' <span class="muted">' + esc(windowLabel(s7)) + '</span></h3>' + stale + note + reviewTable(s) + '</section>';
  });
  const posts = S.metrics.filter(m => m.window_days === 7 && m.views != null).sort((a, b) => b.views - a.views).slice(0, 5);
  const plist = posts.map(m => { const p = byId('posts', m.post_id); return p ? '<li><a ' + goAttrs({ go: 'posts', sub: 'edit', id: p.id }) + '>' + esc(p.title) + '</a> <span class="muted">' + esc(PNAME[p.platform]) + ' · <b>' + fint(m.views) + '</b> views (7d)</span></li>' : ''; }).join('');
  return '<h1>Weekly review</h1><p class="muted">Last 7 days vs a baseline. Baselines come from the snapshots you\'ve logged. If you log a 60 or 90 day snapshot later, it can serve as the baseline too.</p><p>Baseline: ' + chips + '</p>' +
    '<h2>3 suggested next actions</h2><ol class="acts">' + actHtml + '</ol>' + (more ? '<details><summary>Also noticed (' + (acts.length - 3) + ')</summary><ul>' + more + '</ul></details>' : '') +
    '<h2>This week vs baseline</h2><div class="grid">' + (cards || '<p class="muted">No 7-day snapshots yet.</p>') + '</div>' + (needs.length ? '<h2>Data that would sharpen this</h2><ul>' + needs.join('') + '</ul>' : '') +
    '<h2>This week\'s posts <small>7d records</small></h2><ul>' + (plist || '<li class="muted">No 7-day post records.</li>') + '</ul>' +
    '<p class="muted">Suggestions are rule-based (not AI) and show the numbers behind them. Changes of ' + Math.abs(DROP) + '% or more down are flagged ⚠.</p>';
}
ACTS.reviewBase = el => { UI.reviewBase = el.dataset.base; render(); };

/* ================= CSV: parse, import, export ================= */
const PLATFORM_ALIASES = { tiktok: 'tiktok', 'tik tok': 'tiktok', tt: 'tiktok', youtube: 'youtube', 'youtube shorts': 'youtube', yt: 'youtube', shorts: 'youtube', instagram: 'instagram', 'instagram reels': 'instagram', ig: 'instagram', reels: 'instagram' };
const HEADER_ALIASES = { date: 'post_date', posted: 'post_date', posted_date: 'post_date', hook: 'hook_text', tag: 'topic_tag', topic: 'topic_tag', series: 'series_name', part: 'series_part', story: 'story_key',
  window: 'window_days', days: 'window_days', end_date: 'window_end', window_end_date: 'window_end', follows: 'follows_gained', followers_gained: 'follows_gained', stayed: 'stayed_pct', stayed_to_watch: 'stayed_pct',
  stayed_to_watch_pct: 'stayed_pct', 'stayed_to_watch_%': 'stayed_pct' };
const POST_COLS = ['title', 'platform', 'post_date', 'date_approx', 'hook_text', 'topic_tag', 'series_name', 'series_part', 'story_key', 'flag', 'notes'];
const INT_COLS = ['views', 'viewers', 'likes', 'comments', 'shares', 'follows_gained'];
const FLAT_COLS = POST_COLS.concat(['window_days', 'window_end'], INT_COLS, ['stayed_pct']);

function parseCsvText(text) {
  text = String(text || '').replace(/^﻿/, '');
  const first = text.split(/\r?\n/)[0] || '';
  const delim = [',', ';', '\t'].map(d => [d, first.split(d).length]).sort((a, b) => b[1] - a[1])[0][0];
  const rows = []; let row = [], cell = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) { if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += c; }
    else if (c === '"') q = true;
    else if (c === delim) { row.push(cell); cell = ''; }
    else if (c === '\n' || c === '\r') { if (c === '\r' && text[i + 1] === '\n') i++; row.push(cell); rows.push(row); row = []; cell = ''; }
    else cell += c;
  }
  if (cell !== '' || row.length) { row.push(cell); rows.push(row); }
  return rows;
}
function csvNum(v, int) {
  v = String(v == null ? '' : v).trim().replace(/,/g, '').replace(/%/g, '');
  if (!v || /^(n\/a|na|null|none|-|—)$/i.test(v)) return null;
  const f = Number(v);
  if (!isFinite(f)) throw new Error('not a number: "' + v + '"');
  return int ? Math.round(f) : f;
}
function csvDate(v) {
  v = String(v || '').trim();
  if (!v) return null;
  let m = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(v);
  if (m) return m[1] + '-' + m[2].padStart(2, '0') + '-' + m[3].padStart(2, '0');
  m = /^(\d{1,2})\/(\d{1,2})\/(\d{2}|\d{4})$/.exec(v);
  if (m) return (m[3].length === 2 ? '20' + m[3] : m[3]) + '-' + m[1].padStart(2, '0') + '-' + m[2].padStart(2, '0');
  const d = new Date(v + ' 12:00');
  if (!isNaN(d) && /[a-z]/i.test(v)) return iso(d);
  throw new Error('unrecognized date: "' + v + '" (use YYYY-MM-DD)');
}
function parseImport(text) {
  const grid = parseCsvText(text);
  if (!grid.length) return { rows: [], unknown: [] };
  const header = grid[0].map(h => { h = h.trim().toLowerCase().replace(/[ -]/g, '_'); return HEADER_ALIASES[h] || h; });
  const unknown = header.filter(h => h && FLAT_COLS.indexOf(h) < 0);
  const rows = [];
  grid.slice(1).forEach((cells, idx) => {
    if (!cells.some(c => c.trim())) return;
    const raw = {}; header.forEach((h, j) => { if (FLAT_COLS.indexOf(h) >= 0) raw[h] = cells[j] == null ? '' : cells[j]; });
    const out = { line: idx + 2 };
    try {
      out.title = (raw.title || '').trim();
      if (!out.title) throw new Error('title is required');
      const p = (raw.platform || '').trim().toLowerCase();
      if (!PLATFORM_ALIASES[p]) throw new Error('platform must be TikTok, YouTube or Instagram (got "' + p + '")');
      out.platform = PLATFORM_ALIASES[p];
      out.post_date = csvDate(raw.post_date);
      const da = (raw.date_approx || '').trim().toLowerCase();
      out.date_approx = da ? (['1', 'true', 'yes', 'y'].indexOf(da) >= 0 ? 1 : 0) : null;
      ['hook_text', 'topic_tag', 'series_name', 'story_key', 'flag', 'notes'].forEach(k => { out[k] = (raw[k] || '').trim() || null; });
      out.series_part = csvNum(raw.series_part, true);
      INT_COLS.forEach(k => { out[k] = csvNum(raw[k], true); });
      out.stayed_pct = csvNum(raw.stayed_pct);
      const wd = csvNum(raw.window_days, true);
      out.has_metrics = INT_COLS.concat(['stayed_pct']).some(k => out[k] != null);
      if (out.has_metrics && wd != null && WINDOWS.indexOf(wd) < 0) throw new Error('window_days must be ' + WINDOWS.join(', '));
      out.window_days = wd || 28;
      out.window_end = csvDate(raw.window_end) || today();
    } catch (e) { out.error = e.message; }
    rows.push(out);
  });
  return { rows, unknown };
}
const findPost = (platform, title) => S.posts.find(p => p.platform === platform && p.title.toLowerCase() === title.toLowerCase());
function planImport(rows) {
  const seen = new Set();
  rows.forEach(r => {
    if (r.error) { r.status = 'error'; return; }
    const key = r.platform + '|' + r.title.toLowerCase();
    if (findPost(r.platform, r.title) || seen.has(key)) r.status = 'update'; else { r.status = 'new'; seen.add(key); }
  });
  return rows;
}
function applyImport(rows) {
  const st = { added: 0, updated: 0, metrics: 0, skipped: 0 };
  rows.forEach(r => {
    if (r.error) { st.skipped++; return; }
    let seriesId = null;
    if (r.series_name) {
      let s = S.series.find(x => x.name.toLowerCase() === r.series_name.toLowerCase());
      if (!s) { s = { id: nid(), name: r.series_name, description: null, source: 'csv' }; S.series.push(s); }
      seriesId = s.id;
    }
    const f = { post_date: r.post_date, hook_text: r.hook_text, topic_tag: r.topic_tag, series_id: seriesId, series_part: r.series_part, story_key: r.story_key, flag: r.flag, notes: r.notes };
    if (r.date_approx != null) f.date_approx = r.date_approx; else if (r.post_date) f.date_approx = 0;
    let p = findPost(r.platform, r.title);
    if (p) { Object.keys(f).forEach(k => { if (f[k] != null) p[k] = f[k]; }); st.updated++; }
    else {
      p = Object.assign({ id: nid(), title: r.title, platform: r.platform, post_date: null, date_approx: 0, hook_text: null, topic_tag: null, series_id: null, series_part: null, story_key: null, flag: null, notes: null, source: 'csv' },
        Object.fromEntries(Object.keys(f).filter(k => f[k] != null).map(k => [k, f[k]])));
      S.posts.push(p); st.added++;
    }
    if (r.has_metrics) {
      const days = r.window_days, end = r.window_end, vals = {};
      INT_COLS.concat(['stayed_pct']).forEach(k => { vals[k] = r[k]; });
      let m = S.metrics.find(x => x.post_id === p.id && x.window_days === days && x.window_end === end);
      if (m) { Object.keys(vals).forEach(k => { if (vals[k] != null) m[k] = vals[k]; }); m.source = 'csv'; }
      else S.metrics.push(Object.assign({ id: nid(), post_id: p.id, window_start: addDays(end, -(days - 1)), window_end: end, window_days: days, source: 'csv' }, vals));
      st.metrics++;
    }
  });
  markDirty('posts', 'metrics', 'series');
  return st;
}

/* ---- export ---- */
function csvCell(v) {
  if (v == null) return '';
  if (typeof v === 'object') v = JSON.stringify(v);
  v = String(v);
  return /[",\n\r]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v;
}
const toCsv = (header, rows) => '﻿' + [header.join(',')].concat(rows.map(r => r.map(csvCell).join(','))).join('\r\n') + '\r\n';
function tableCsv(t) {
  const items = S[t], header = [];
  items.forEach(it => Object.keys(it).forEach(k => { if (header.indexOf(k) < 0) header.push(k); }));
  return toCsv(header, items.map(it => header.map(k => it[k])));
}
function postLogCsv() {
  const rows = [];
  S.posts.slice().sort((a, b) => a.platform.localeCompare(b.platform) || String(a.post_date).localeCompare(String(b.post_date)) || a.id - b.id).forEach(p => {
    const ser = p.series_id ? byId('series', p.series_id) : null, ms = metricsFor(p.id);
    const base = [p.title, p.platform, p.post_date, p.date_approx, p.hook_text, p.topic_tag, ser ? ser.name : null, p.series_part, p.story_key, p.flag, p.notes];
    if (!ms.length) rows.push(base.concat([null, null, null, null, null, null, null, null, null]));
    ms.forEach(m => rows.push(base.concat([m.window_days, m.window_end, m.views, m.viewers, m.likes, m.comments, m.shares, m.follows_gained, m.stayed_pct])));
  });
  return toCsv(FLAT_COLS, rows);
}
const CRC_T = (() => { const t = []; for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
function crc32(b) { let c = 0xFFFFFFFF; for (let i = 0; i < b.length; i++) c = CRC_T[(c ^ b[i]) & 255] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; }
function makeZip(files) {
  const enc = new TextEncoder(), now = new Date();
  const dt = ((now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1)) & 0xFFFF, dd = (((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate()) & 0xFFFF;
  const parts = [], central = []; let offset = 0;
  files.forEach(f => {
    const name = enc.encode(f.name), data = enc.encode(f.text), crc = crc32(data);
    const lh = new DataView(new ArrayBuffer(30));
    lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0x0800, true); lh.setUint16(8, 0, true); lh.setUint16(10, dt, true); lh.setUint16(12, dd, true);
    lh.setUint32(14, crc, true); lh.setUint32(18, data.length, true); lh.setUint32(22, data.length, true); lh.setUint16(26, name.length, true); lh.setUint16(28, 0, true);
    parts.push(new Uint8Array(lh.buffer), name, data);
    const ch = new DataView(new ArrayBuffer(46));
    ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true); ch.setUint16(8, 0x0800, true); ch.setUint16(10, 0, true); ch.setUint16(12, dt, true); ch.setUint16(14, dd, true);
    ch.setUint32(16, crc, true); ch.setUint32(20, data.length, true); ch.setUint32(24, data.length, true); ch.setUint16(28, name.length, true); ch.setUint32(42, offset, true);
    central.push(new Uint8Array(ch.buffer), name);
    offset += 30 + name.length + data.length;
  });
  const cdSize = central.reduce((n, p) => n + p.length, 0), end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true); end.setUint32(12, cdSize, true); end.setUint32(16, offset, true);
  return new Blob(parts.concat(central, [new Uint8Array(end.buffer)]), { type: 'application/zip' });
}
async function saveFile(filename, data, fallbackText) {
  let dl = null;
  try { if (window.claude && window.claude.use) dl = await window.claude.use('downloads'); } catch (e) { dl = null; }
  if (dl) {
    try { const r = await dl.save({ filename, data }); toast(r === 'saved' || (r && r.status === 'saved') ? 'Saved ' + filename : 'Download started'); return; }
    catch (e) { if (e && e.code === 'declined') { toast('Download cancelled'); return; } }
  }
  if (typeof data === 'string') showText(filename, data);
  else if (fallbackText) showText('Backup (JSON)', fallbackText);
  else toast('Downloads are not available in this view');
}
const backupJson = () => JSON.stringify(S, null, 1);
ACTS.exportZip = () => {
  const files = [{ name: 'post_log.csv', text: postLogCsv() }].concat(TABLES.map(t => ({ name: t + '.csv', text: tableCsv(t) })));
  saveFile('channel-builder-' + today() + '.zip', makeZip(files), backupJson());
};
ACTS.exportPostLog = () => saveFile('post_log.csv', postLogCsv());
ACTS.exportTable = el => saveFile(el.dataset.table + '.csv', tableCsv(el.dataset.table));
ACTS.exportJson = () => saveFile('channel-builder-backup-' + today() + '.json', backupJson());
ACTS.copyJson = () => copyText(backupJson(), 'Backup copied');

/* ---- Data page ---- */
function viewData() {
  const counts = TABLES.map(t => '<li><button type="button" class="linkbtn" data-act="exportTable" data-table="' + t + '">' + t + '.csv</button> <span class="muted">(' + S[t].length + ' rows)</span></li>').join('');
  const where = Store.mode === 'db' ? 'Your data is saved in this page\'s database and follows you between devices.' : 'Your data is saved in this browser only. Export a backup now and then.';
  return '<h1>Data</h1><p class="muted">' + esc(where) + '</p><h2>Export</h2><div class="row"><button type="button" class="btn primary" data-act="exportZip">Download everything (.zip of CSVs)</button>' +
    '<button type="button" class="btn" data-act="exportJson">Backup (.json)</button><button type="button" class="btn" data-act="copyJson">Copy backup text</button></div>' +
    '<p class="muted"><b>post_log.csv</b> is the flat post log (one row per post per metric window) and can be re-imported below. The rest are raw tables.</p>' +
    '<ul><li><button type="button" class="linkbtn" data-act="exportPostLog">post_log.csv</button> <span class="muted">(re-importable)</span></li>' + counts + '</ul>' +
    '<h2>Import post log (CSV)</h2><form data-form="importPreview" class="stack"><label>Choose a .csv file<input type="file" id="csvfile" accept=".csv,text/csv,text/plain"></label>' +
    '<label>…or paste CSV text<textarea id="csvtext" name="csv" rows="7" placeholder="title,platform,post_date,views,...">' + esc(UI.importText) + '</textarea></label><button class="btn primary">Preview import</button></form>' +
    '<details><summary>CSV format</summary><p class="muted">First row = headers. Required: <b>title</b>, <b>platform</b> (TikTok / YouTube / Instagram). Optional: ' + esc(FLAT_COLS.join(', ')) + '.</p>' +
    '<ul class="muted"><li>A row whose platform + title match an existing post <b>updates</b> it; otherwise a new post is created. Blank cells never erase existing data.</li>' +
    '<li>Metrics need a window: <b>window_days</b> (' + WINDOWS.join(', ') + '; default 28) and <b>window_end</b> (YYYY-MM-DD; default today). Re-importing the same window updates that record.</li>' +
    '<li>Put the same post on two rows to give it two windows. Dates: YYYY-MM-DD or M/D/YYYY. Leave unknowns blank, not 0.</li></ul></details>' +
    '<h2>Restore from a backup</h2><p class="muted">Paste backup text (from "Backup (.json)" or "Copy backup text") or choose the file. Restoring replaces everything currently in the app.</p>' +
    '<form data-form="restore" class="stack"><label>Choose a backup .json file<input type="file" id="jsonfile" accept=".json,application/json,text/plain"></label><label>…or paste backup text<textarea id="jsontext" name="json" rows="5"></textarea></label>' +
    '<button class="btn">Restore backup</button></form>';
}
function viewImportPreview() {
  const { rows, unknown } = parseImport(UI.importText);
  planImport(rows);
  if (!rows.length) return '<h1>Import preview</h1><p>No data rows found. <a ' + goAttrs({ go: 'data' }) + '>Back</a></p>';
  const n = { new: 0, update: 0, error: 0 };
  rows.forEach(r => { n[r.status]++; });
  const trs = rows.slice(0, 300).map(r => {
    let detail;
    if (r.status === 'error') detail = '<span class="flag-inline">' + esc(r.error) + '</span>';
    else {
      const bits = INT_COLS.filter(k => r[k] != null).map(k => k + ': ' + r[k]);
      if (r.stayed_pct != null) bits.push('stayed: ' + r.stayed_pct + '%');
      detail = bits.length ? r.window_days + 'd to ' + esc(r.window_end) + ': ' + bits.join(', ') : 'no metrics';
    }
    return '<tr><td>' + r.line + '</td><td><b>' + r.status + '</b></td><td>' + esc(PNAME[r.platform] || '') + '</td><td>' + esc(r.title) + '</td><td>' + detail + '</td></tr>';
  }).join('');
  const act = n.new + n.update;
  return '<h1>Import preview</h1><p><b>' + n.new + '</b> new post(s) · <b>' + n.update + '</b> update(s) · <b>' + n.error + '</b> error(s) <span class="muted">(errors are skipped)</span></p>' +
    (unknown.length ? '<p class="muted">Ignored unknown column(s): ' + esc(unknown.join(', ')) + '</p>' : '') +
    (act ? '<div class="row"><button type="button" class="btn primary" data-act="importCommit">Import ' + act + ' row(s)</button><a class="btn" ' + goAttrs({ go: 'data' }) + '>Cancel</a></div>' : '<p><a class="btn" ' + goAttrs({ go: 'data' }) + '>Back</a></p>') +
    '<div class="scroll"><table><thead><tr><th>Line</th><th>Action</th><th>Platform</th><th>Title</th><th>Details</th></tr></thead><tbody>' + trs + '</tbody></table></div>' +
    (rows.length > 300 ? '<p class="muted">Showing first 300 of ' + rows.length + ' rows.</p>' : '');
}
FORMS.importPreview = fd => { UI.importText = fd.csv || ''; go('data', 'preview'); };
ACTS.importCommit = () => {
  const { rows } = parseImport(UI.importText);
  const st = applyImport(planImport(rows));
  UI.importText = '';
  toast('Imported: ' + st.added + ' new, ' + st.updated + ' updated, ' + st.metrics + ' metric record(s), ' + st.skipped + ' skipped'); go('data');
};
FORMS.restore = fd => {
  let data;
  try { data = JSON.parse(fd.json || ''); } catch (e) { toast('That is not valid backup text'); return; }
  if (!data || !data.meta || !Array.isArray(data.posts)) { toast('That does not look like a Channel Builder backup'); return; }
  confirmBar('Replace everything in the app with this backup?', () => {
    const next = emptyState(); next.meta = Object.assign(next.meta, data.meta);
    TABLES.forEach(t => { next[t] = Array.isArray(data[t]) ? data[t] : []; });
    S = next; ensureTemplates(); ensureChecklist();
    TABLES.concat(['meta']).forEach(t => Store.dirty.add(t)); markDirty('meta'); toast('Backup restored'); go('today');
  });
};

/* ================= global search ================= */
function searchAll(term) {
  term = term.trim().toLowerCase();
  if (term.length < 2) return [];
  const out = [], has = v => v && String(v).toLowerCase().indexOf(term) >= 0;
  const snip = vals => { for (const v of vals) { if (has(v)) { const i = v.toLowerCase().indexOf(term), a = Math.max(0, i - 40); return (a ? '…' : '') + v.slice(a, i + term.length + 60); } } return ''; };
  S.posts.forEach(p => { const f = [p.hook_text, p.topic_tag, p.story_key, p.notes, p.flag]; if (has(p.title) || f.some(has)) out.push({ title: p.title.slice(0, 90), tab: 'Post · ' + PNAME[p.platform].split(' ')[0], snip: snip(f), go: { go: 'posts', sub: 'edit', id: p.id } }); });
  S.hooks.forEach(h => { const f = [h.tags, h.notes]; if (has(h.text) || f.some(has)) out.push({ title: h.text.slice(0, 90), tab: 'Hook', snip: snip(f), go: { go: 'hooks', sub: 'edit', id: h.id } }); });
  S.scripts.forEach(s => { const f = TEXT_KEYS.map(k => s[k]); if (has(s.title) || f.some(has)) out.push({ title: (s.title || 'Untitled script').slice(0, 90), tab: s.is_template ? 'Template' : 'Script', snip: snip(f), go: { go: 'scripts', sub: 'edit', id: s.id } }); });
  S.series.forEach(s => { if (has(s.name) || has(s.description)) out.push({ title: s.name, tab: 'Series', snip: snip([s.description]), go: { go: 'series', id: s.id } }); });
  S.ideas.forEach(i => { if (has(i.idea)) { const s = byId('series', i.series_id); out.push({ title: i.idea.slice(0, 90), tab: 'Idea · ' + (s ? s.name : ''), snip: '', go: { go: 'series', id: i.series_id } }); } });
  out.sort((a, b) => (a.title.toLowerCase().indexOf(term) < 0) - (b.title.toLowerCase().indexOf(term) < 0));
  return out.slice(0, 14);
}
