'use strict';
/* ================= constants ================= */
const PLATFORMS = [['tiktok', 'TikTok'], ['youtube', 'YouTube Shorts'], ['instagram', 'Instagram Reels']];
const PNAME = Object.fromEntries(PLATFORMS);
const WINDOWS = [7, 14, 28, 30, 60, 90];
const DROP = -50;
const METRIC_FIELDS = [['views', 'Views', 'i'], ['viewers', 'Viewers', 'i'], ['likes', 'Likes', 'i'], ['comments', 'Comments', 'i'],
  ['shares', 'Shares', 'i'], ['follows_gained', 'Follows gained', 'i'], ['stayed_pct', 'Stayed to watch %', 'f']];
const SNAP_FIELDS = [['views', 'Views', 'i'], ['viewers', 'Viewers', 'i'], ['new_viewers', 'New viewers', 'i'], ['profile_views', 'Profile views', 'i'],
  ['likes', 'Likes', 'i'], ['comments', 'Comments', 'i'], ['shares', 'Shares', 'i'], ['interactions', 'Interactions', 'i'],
  ['net_followers', 'Net followers', 'i'], ['prior_net_followers', 'Prior-window net followers', 'i'], ['total_followers', 'Total followers', 'i'],
  ['engaged_views', 'Engaged views', 'i'], ['watch_hours', 'Watch time (hrs)', 'f'], ['stayed_pct', 'Stayed to watch %', 'f']];
const TABLES = ['posts', 'metrics', 'snaps', 'audience', 'series', 'ideas', 'hooks', 'hookPosts', 'scripts', 'checklist'];
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/* ================= small helpers ================= */
const $ = (s, c) => (c || document).querySelector(s);
const $$ = (s, c) => Array.from((c || document).querySelectorAll(s));
const esc = v => String(v == null ? '' : v).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
function num(v, kind) {
  if (v == null) return null;
  v = String(v).trim().replace(/,/g, '').replace(/%/g, '');
  if (v === '') return null;
  const f = Number(v);
  if (!isFinite(f)) return null;
  return kind === 'i' ? Math.round(f) : f;
}
const txt = v => { v = (v == null ? '' : String(v)).trim(); return v === '' ? null : v; };
const fint = v => v == null ? '—' : Math.round(v).toLocaleString('en-US');
const fnum = (v, d) => v == null ? '—' : v.toLocaleString('en-US', { minimumFractionDigits: d == null ? 1 : d, maximumFractionDigits: d == null ? 1 : d });
const fpct = (v, d) => v == null ? '—' : v.toFixed(d == null ? 1 : d) + '%';
const ratio = (n, d, s) => (n == null || !d) ? null : n / d * (s || 1);
const pd = s => { const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d, 12); };
const iso = dt => dt.getFullYear() + '-' + String(dt.getMonth() + 1).padStart(2, '0') + '-' + String(dt.getDate()).padStart(2, '0');
const addDays = (s, n) => { const d = pd(s); d.setDate(d.getDate() + n); return iso(d); };
const today = () => iso(new Date());
const validIso = s => /^\d{4}-\d{2}-\d{2}$/.test(s || '') && !isNaN(pd(s));
const fdate = (s, approx) => {
  if (!s) return 'no date';
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (!m) return s;
  return (approx ? '~' : '') + MON[+m[2] - 1] + ' ' + (+m[3]);
};
const windowLabel = r => r.window_days + 'd · ' + (r.window_start ? fdate(r.window_start) + '–' + fdate(r.window_end) : 'to ' + fdate(r.window_end));
const byId = (t, id) => S[t].find(x => x.id === +id) || null;

/* ================= state + persistence ================= */
let S = emptyState();
function emptyState() {
  const s = { meta: { seq: 1000, seeded: false } };
  TABLES.forEach(t => { s[t] = []; });
  return s;
}
const Store = { db: null, mode: 'loading', dirty: new Set(), timer: null, busy: false, error: '' };

function nid() { S.meta.seq += 1; markDirty('meta'); return S.meta.seq; }

function markDirty() {
  for (const t of arguments) Store.dirty.add(t);
  try { localStorage.setItem('cb-v1', JSON.stringify(S)); } catch (e) { /* storage may be blocked */ }
  clearTimeout(Store.timer);
  Store.timer = setTimeout(flush, 500);
  setStatus('saving');
}

async function flush() {
  if (Store.busy) { Store.timer = setTimeout(flush, 300); return; }
  if (!Store.db) { Store.dirty.clear(); setStatus(Store.mode === 'local' ? 'local' : 'ok'); return; }
  Store.busy = true;
  try {
    for (const t of Array.from(Store.dirty)) {
      Store.dirty.delete(t);
      const body = t === 'meta' ? { v: S.meta } : { items: S[t] };
      await Store.db.doc('cb/' + t).set(body);
    }
    Store.error = '';
    setStatus('ok');
  } catch (e) {
    Store.error = (e && e.message) || 'Could not save';
    if (e && e.code === 'quota_exceeded') Store.error = 'The database is full. Export a backup and delete old posts.';
    setStatus('error');
  }
  Store.busy = false;
  if (Store.dirty.size && !Store.error) Store.timer = setTimeout(flush, 100);
}

async function initStore() {
  let db = null;
  try {
    if (window.claude && window.claude.use) db = await window.claude.use('db');
  } catch (e) { db = null; }
  Store.db = db;
  let loaded = false;
  if (db) {
    try {
      const snap = await db.collection('cb').get();
      if (!snap.empty) {
        const next = emptyState();
        snap.docs.forEach(d => {
          const data = d.data() || {};
          if (d.id === 'meta') next.meta = Object.assign(next.meta, data.v || {});
          else if (TABLES.indexOf(d.id) >= 0) next[d.id] = data.items || [];
        });
        S = next; loaded = true; Store.mode = 'db';
      }
    } catch (e) { Store.error = (e && e.message) || 'Could not read saved data'; }
  }
  if (!loaded) {
    // no db (or empty): fall back to this device's copy, else seed
    let local = null;
    try { local = JSON.parse(localStorage.getItem('cb-v1') || 'null'); } catch (e) { local = null; }
    if (local && local.meta && local.meta.seeded) {
      S = Object.assign(emptyState(), local);
      Store.mode = db ? 'db' : 'local';
      if (db) TABLES.concat(['meta']).forEach(t => Store.dirty.add(t));
    } else {
      S = emptyState();
      applySeed();
      Store.mode = db ? 'db' : 'local';
      TABLES.concat(['meta']).forEach(t => Store.dirty.add(t));
    }
    if (db) { Store.timer = setTimeout(flush, 50); }
  }
  ensureTemplates();
  ensureChecklist();
  setStatus(db ? (Store.error ? 'error' : 'ok') : 'local');
}

function applySeed() {
  const seed = makeSeed();
  TABLES.forEach(t => { S[t] = seed[t] || []; });
  S.meta = { seq: seed.seq, seeded: true, tpl: false };
  try { localStorage.setItem('cb-v1', JSON.stringify(S)); } catch (e) { /* ignore */ }
}

/* ================= seed data (real numbers captured Oct 10-11, 2026) =================
   Anything not listed is null. Post dates are approximate and editable. */
function makeSeed() {
  let id = 0;
  const nx = () => ++id;
  const out = {};
  TABLES.forEach(t => { out[t] = []; });
  const D = { h19: '2026-10-10', d4: '2026-10-07', w1: '2026-10-04', w2: '2026-09-27', mo1: '2026-09-11' };
  const W = { tt7: ['2026-10-03', '2026-10-09', 7], tt28: ['2026-09-13', '2026-10-10', 28], yt28: ['2026-09-13', '2026-10-10', 28], ig30: ['2026-09-11', '2026-10-10', 30] };
  const NERV = 'first observation (nervous)', OVER = 'first observation (over)', CONF = 'post-observation conference', F16 = 'F-16 / Air Force';
  const sid = nx();
  out.series.push({ id: sid, name: 'Observation Arc', description: 'First observation through the post-observation conference.', source: 'seed' });
  const part = {}; part[NERV] = 1; part[OVER] = 2; part[CONF] = 3;
  const P = [
    ['tiktok', 'I thought pacing might come up in my post-observation conference...', D.w2, CONF, null, null, [['tt28', 4629], ['tt7', 262]]],
    ['tiktok', 'My first formal classroom observation is today, and someh...', D.mo1, NERV, 'More nervous than an Air Force evaluation', null, [['tt28', 2247], ['tt7', 235]]],
    ['tiktok', 'My first formal classroom observation is officially over. Ad...', D.mo1, OVER, null, null, [['tt28', 2223]]],
    ['tiktok', 'First-year teacher milestone today: my first post-observation confer...', D.w2, CONF, null, null, [['tt28', 1174], ['tt7', 233]]],
    ['tiktok', 'A half-day for students does not mean a half-day for teachers. To...', null, null, null, null, [['tt28', 1110]]],
    ['tiktok', "One thing I'm learning in my first year teaching: being prepared do...", D.w1, null, null, null, [['tt7', 347]]],
    ['tiktok', "15 years as an F-16 crew chief. This isn't the part I thought I'd miss.", D.d4, F16, null, null, [['tt7', 316]]],
    ['youtube', '15 years as an F-16 crew chief -> fir...', null, F16, null, null, [['yt28', 1100, null, null, 52.9]]],
    ['youtube', 'Students Leave Early - Teachers Stil...', null, null, null, null, [['yt28', 1000, null, null, 51.3]]],
    ['youtube', 'My First Teacher Observation Is Ove...', null, OVER, null, null, [['yt28', 1000, null, null, 57.2]]],
    ['youtube', 'I Gave Clear Instructions - My Stu...', null, null, null, null, [['yt28', null, null, null, 59.0]]],
    ['youtube', "15 Years in the Air Force Didn't Pre...", null, F16, null, null, [['yt28', null, null, null, 56.3]]],
    ['youtube', 'I Did Not Student Teach Before Get...', null, null, null, null, [['yt28', null, null, null, 53.5]]],
    ['youtube', 'What My Evaluator Told Me After M...', null, CONF, 'What my evaluator actually told me...', null, [['yt28', null, null, null, 51.1]]],
    ['youtube', "My Best Lesson Wasn't in the Less...", null, null, null, null, [['yt28', null, null, null, 45.5]]],
    ['instagram', 'Everyone asks what I miss....', D.h19, F16, 'Everyone asks what I miss...', null, [['ig30', 157, 0, 0]]],
    ['instagram', '15 years as an F-16 crew ch...', D.d4, F16, null, null, [['ig30', 270, 3, 0]]],
    ['instagram', 'I came into teaching with a...', D.w1, null, null, null, [['ig30', 142, 0, 0]]],
    ['instagram', "The best lesson I've had thi...", D.w1, null, null, null, [['ig30', 163, 2, 0]]],
    ['instagram', "My best lesson wasn't planned", D.w1, null, null, 'possible duplicate or failed upload', [['ig30', 0]]],
    ['instagram', 'I took both of my teacher c...', D.w2, null, null, null, [['ig30', 145, 0, 1]]],
    ['instagram', 'Teacher certification tests', D.w2, null, null, 'possible duplicate or failed upload', [['ig30', 0]]],
    ['instagram', 'The results from my first po...', D.w2, CONF, null, null, [['ig30', 395, 2, 0]]]
  ];
  const postIds = [];
  P.forEach(p => {
    const pn = part[p[3]] || null;
    const pid = nx();
    postIds.push(pid);
    out.posts.push({ id: pid, title: p[1], platform: p[0], post_date: p[2], date_approx: p[2] ? 1 : 0, hook_text: p[4], topic_tag: null,
      series_id: pn ? sid : null, series_part: pn, story_key: p[3], flag: p[5], notes: null, source: 'seed' });
    p[6].forEach(m => {
      const w = W[m[0]];
      out.metrics.push({ id: nx(), post_id: pid, window_start: w[0], window_end: w[1], window_days: w[2], views: m[1] == null ? null : m[1],
        viewers: null, likes: m[2] == null ? null : m[2], comments: m[3] == null ? null : m[3], shares: null, follows_gained: null,
        stayed_pct: m[4] == null ? null : m[4], source: 'seed' });
    });
  });
  const snap = (platform, w, vals, extra, notes) => {
    const x = { id: nx(), platform: platform, window_start: W[w][0], window_end: W[w][1], window_days: W[w][2], notes: notes || null, extra: extra || {}, source: 'seed' };
    SNAP_FIELDS.forEach(f => { x[f[0]] = vals[f[0]] == null ? null : vals[f[0]]; });
    out.snaps.push(x);
  };
  snap('tiktok', 'tt7', { views: 1700, viewers: 1300, new_viewers: 967, profile_views: 63, likes: 57, comments: 5, shares: 0, net_followers: 1, prior_net_followers: 6, total_followers: 114 }, { changes: { views: -74.5 } });
  snap('tiktok', 'tt28', { views: 16800, viewers: 11800, new_viewers: 11300, profile_views: 535, likes: 503, comments: 61, shares: 4, net_followers: 27, total_followers: 114 }, { changes: { views: 140.7 } });
  snap('youtube', 'yt28', { views: 8600, engaged_views: 4400, watch_hours: 21.8, net_followers: 6, stayed_pct: 51.3 },
    { changes: { engaged_views: 9, watch_hours: -7 }, swiped_away_pct: 48.7, monthly_audience: 4100, monthly_new_pct: 99.2, monthly_casual: 34, monthly_regular: 0, monthly_audience_peak: 7200, monthly_audience_peak_note: 'peaked near 7,200 around Sep 26' },
    'Discrepancy: YouTube showed +6 subscribers on one screen and +7 on another. Stored 6.');
  snap('instagram', 'ig30', { views: 2021, viewers: 1615, interactions: 9 }, { follower_views_pct: 0, non_follower_views_pct: 100, reels_views_approx: 2000, feed_post_views: 0 }, 'Net followers unavailable from Instagram.');
  const AUD = { gender: [['Male', 75.3], ['Female', 24.7]], country: [['United States', 78.7], ['United Kingdom', 1.1], ['Canada', 0.8]],
    age: [['13-17', 3.0], ['18-24', 1.8], ['25-34', 26.7], ['35-44', 27.8], ['45-54', 17.6], ['55-64', 13.3], ['65+', 9.7]],
    device: [['Mobile', 79.7], ['Computer', 11.0], ['Tablet', 7.5], ['TV', 1.8]], subtitles: [['No subtitles', 87.9]] };
  Object.keys(AUD).forEach(cat => AUD[cat].forEach(r => out.audience.push({ id: nx(), platform: 'youtube', window_days: 28, window_end: '2026-10-10', category: cat, label: r[0], pct: r[1], source: 'seed' })));
  const H = [['What my evaluator actually told me...', 'observation,evaluator', 'What My Evaluator Told Me After M...'],
    ['More nervous than an Air Force evaluation', 'observation,air-force,nervous', 'My first formal classroom observation is today, and someh...'],
    ['Everyone asks what I miss...', 'air-force,veteran', 'Everyone asks what I miss....']];
  H.forEach(h => {
    const hid = nx();
    out.hooks.push({ id: hid, text: h[0], tags: h[1], notes: null, source: 'seed' });
    out.posts.forEach(p => { if (p.title === h[2]) out.hookPosts.push({ hook_id: hid, post_id: p.id }); });
  });
  out.seq = id + 1000;
  return out;
}

const STARTERS = [
  ['Expectation vs. Reality (starter)', { hook_onscreen: 'I expected [X]. What actually happened: [Y]', hook_spoken: "I thought [what you expected]. Here's what actually happened.",
    expectation: 'Going in, I expected [one sentence].', reveal: 'Then [one specific detail: a quote, a number, a moment].', takeaway: 'The lesson: [one lesson, one sentence].',
    close_ask: 'If this helped, follow for Part [N+1], and send it to a first-year teacher.', next_part_pointer: 'Next time: [what happens next].' }],
  ['Air Force to Classroom (starter)', { hook_onscreen: 'In the Air Force: [X]. In my classroom: [Y]', hook_spoken: "After years as an F-16 crew chief, here's what surprised me about teaching.",
    expectation: 'In the Air Force, [how it worked there].', reveal: 'In my classroom, [one specific detail that was different].', takeaway: 'What carried over: [one lesson].',
    close_ask: 'Follow for the next part, and share this with a veteran thinking about teaching.', next_part_pointer: 'Next: [the next transition story].' }]
];

function ensureTemplates() {
  if (S.meta.tpl) return;
  STARTERS.forEach(t => {
    const v = Object.assign({}, t[1]);
    S.scripts.push(Object.assign({ id: nid(), title: t[0], post_id: null, series_id: null, is_template: 1, source: 'seed', est_seconds: estimateSeconds(v) }, v));
  });
  S.meta.tpl = true;
  markDirty('scripts', 'meta');
}

const CHECK_ITEMS = [['bio_line', 'Bio line'], ['pinned_post', 'Pinned post'], ['link', 'Link'], ['profile_photo', 'Profile photo'], ['featured_content', 'Featured content']];
function ensureChecklist() {
  let added = false;
  PLATFORMS.forEach(p => CHECK_ITEMS.forEach(i => {
    if (!S.checklist.find(c => c.platform === p[0] && c.item_key === i[0])) {
      S.checklist.push({ platform: p[0], item_key: i[0], done: 0, done_date: null, note: null });
      added = true;
    }
  }));
  if (added) markDirty('checklist');
}
