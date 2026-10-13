/* ================= script helpers (also used by seed) ================= */
const WPS = 2.5, MIN_S = 30, MAX_S = 45;
const WORD_RE = /[\p{L}\p{N}_'’-]*[\p{L}\p{N}_][\p{L}\p{N}_'’-]*/gu;
const SECTIONS = [
  ['hook_spoken', 'Hook — spoken line', "The first sentence out loud. Make a viewer who's never seen you stay.", 2],
  ['expectation', 'Expectation', "What you thought would happen (the 'expected' half of expectation-vs-reality).", 3],
  ['reveal', 'Reveal — ONE specific detail', 'A single concrete moment, quote or number. Not a summary.', 3],
  ['takeaway', 'Takeaway — ONE lesson', 'One sentence a first-year teacher can use tomorrow.', 2],
  ['close_ask', 'Close — direct follow / share ask', 'Say it plainly: follow for the next part, send this to someone.', 2],
  ['next_part_pointer', 'Next-part pointer', 'Tell them what Part N+1 covers so following has a reason.', 2]
];
const SPOKEN_KEYS = SECTIONS.map(s => s[0]);
const TEXT_KEYS = ['hook_onscreen'].concat(SPOKEN_KEYS);
const countWords = t => ((t || '').match(WORD_RE) || []).length;
const estimateSeconds = v => Math.round(SPOKEN_KEYS.reduce((n, k) => n + countWords(v[k]), 0) / WPS);

/* ================= dashboard math ================= */
const CHANGE_LABELS = { views: 'Views', viewers: 'Viewers', likes: 'Likes', comments: 'Comments', shares: 'Shares', profile_views: 'Profile views',
  net_followers: 'Net followers', watch_hours: 'Watch time', engaged_views: 'Engaged views' };

function snapshotFor(platform, days) {
  const rows = S.snaps.filter(s => s.platform === platform && s.window_days === days).sort((a, b) => b.window_end.localeCompare(a.window_end));
  return rows[0] || null;
}
function priorSnapshot(s) {
  if (!s.window_start) return null;
  const pe = addDays(s.window_start, -1);
  return S.snaps.find(x => x.platform === s.platform && x.window_days === s.window_days && x.window_end === pe) || null;
}
/* % change vs the prior window: from a stored prior snapshot if there is one, else the % the app reported */
function changes(s) {
  const out = Object.assign({}, (s.extra && s.extra.changes) || {});
  const prior = priorSnapshot(s);
  Object.keys(CHANGE_LABELS).forEach(k => { if (prior && s[k] != null && prior[k]) out[k] = (s[k] - prior[k]) / prior[k] * 100; });
  if (s.net_followers != null && s.prior_net_followers) out.net_followers = (s.net_followers - s.prior_net_followers) / s.prior_net_followers * 100;
  return out;
}
function cardRows(platform, s) {
  const views = s.views, rows = [];
  if (platform === 'youtube') {
    rows.push(['Engaged-view rate', fpct(ratio(s.engaged_views, views, 100)), "YouTube's own metric (engaged views ÷ views); not the same as like/comment rate"]);
  } else {
    const eng = platform === 'instagram' ? s.interactions : (s.likes == null ? null : (s.likes || 0) + (s.comments || 0) + (s.shares || 0));
    rows.push(['Engagement rate', fpct(ratio(eng, views, 100), 2), platform === 'instagram' ? 'interactions ÷ views' : '(likes + comments + shares) ÷ views']);
  }
  const sh = s.shares == null ? null : ratio(s.shares, views, 1000);
  rows.push(['Shares / 1K views', sh == null ? '—' : sh.toFixed(2), s.shares != null ? '' : 'not captured on this platform']);
  const ptf = ratio(s.net_followers, s.profile_views, 100);
  rows.push(['Profile view → follow', fpct(ptf), ptf != null ? 'net followers ÷ profile views' : 'needs profile views + net followers']);
  return rows;
}
function postRowsForWindow(days, loose) {
  const allowed = new Set([days]);
  if (loose && days === 28) allowed.add(30);
  if (loose && days === 30) allowed.add(28);
  const best = {};
  S.metrics.forEach(m => {
    if (!allowed.has(m.window_days)) return;
    const p = byId('posts', m.post_id);
    if (!p) return;
    const row = Object.assign({}, m, { id: p.id, title: p.title, platform: p.platform, topic_tag: p.topic_tag, story_key: p.story_key,
      series_name: p.series_id ? ((byId('series', p.series_id) || {}).name || null) : null });
    const cur = best[p.id];
    if (!cur || (row.window_days === days && cur.window_days !== days) || (row.window_days === cur.window_days && row.window_end > cur.window_end)) best[p.id] = row;
  });
  return Object.values(best);
}
function groupRows(rows, keyfn, emptyLabel) {
  const groups = {};
  rows.forEach(r => { (groups[keyfn(r) || emptyLabel] = groups[keyfn(r) || emptyLabel] || []).push(r); });
  const out = Object.keys(groups).map(key => {
    const rs = groups[key];
    const vw = rs.filter(r => r.views != null).map(r => r.views);
    const engRs = rs.filter(r => r.likes != null && r.views);
    const eng = ratio(engRs.reduce((a, r) => a + (r.likes || 0) + (r.comments || 0) + (r.shares || 0), 0), engRs.reduce((a, r) => a + r.views, 0), 100);
    const shRs = rs.filter(r => r.shares != null && r.views);
    const sh = ratio(shRs.reduce((a, r) => a + r.shares, 0), shRs.reduce((a, r) => a + r.views, 0), 1000);
    const st = rs.filter(r => r.stayed_pct != null).map(r => r.stayed_pct);
    return { key, n: rs.length, views: vw.length ? vw.reduce((a, b) => a + b, 0) : null, eng, sh, stayed: st.length ? st.reduce((a, b) => a + b, 0) / st.length : null,
      plats: Array.from(new Set(rs.map(r => r.platform))).sort() };
  });
  out.sort((a, b) => (a.key === emptyLabel) - (b.key === emptyLabel) || (b.views || 0) - (a.views || 0));
  return out;
}

/* ================= weekly review ================= */
const REVIEW_METRICS = [['views', 'Views', 0], ['viewers', 'Viewers', 0], ['engaged_views', 'Engaged views', 0], ['profile_views', 'Profile views', 0],
  ['likes', 'Likes', 0], ['comments', 'Comments', 0], ['shares', 'Shares', 0], ['interactions', 'Interactions', 0], ['net_followers', 'Net followers', 0], ['watch_hours', 'Watch time (hrs)', 1]];
const AUTO_PREF = [28, 60, 90, 30, 14];
const pctChange = (now, base) => (now == null || base == null || base <= 0) ? null : (now - base) / base * 100;

function derivedRates(platform, v) {
  const views = v.views;
  let eng;
  if (platform === 'instagram') eng = v.interactions;
  else if (platform === 'youtube') eng = v.engaged_views;
  else eng = v.likes == null ? null : (v.likes || 0) + (v.comments || 0) + (v.shares || 0);
  const ok = (a, b) => a != null && b;
  return {
    eng: ok(eng, views) ? eng / views * 100 : null,
    shares1k: ok(v.shares, views) ? v.shares / views * 1000 : null,
    ptf: ok(v.net_followers, v.profile_views) ? v.net_followers / v.profile_views * 100 : null,
    fol1k: ok(v.net_followers, v.viewers) ? v.net_followers / v.viewers * 1000 : null
  };
}
function findBaseline(s7, base) {
  let rows = S.snaps.filter(r => r.platform === s7.platform && r.id !== s7.id && r.window_days >= 14);
  if (base !== 'auto') rows = rows.filter(r => r.window_days === base);
  const order = r => { const i = AUTO_PREF.indexOf(r.window_days); return i < 0 ? 99 : i; };
  const prevEnd = s7.window_start ? addDays(s7.window_start, -1) : null;
  const exact = rows.filter(r => prevEnd && r.window_end === prevEnd).sort((a, b) => order(a) - order(b));
  if (exact.length) {
    const w = exact[0], per7 = {};
    REVIEW_METRICS.forEach(m => { per7[m[0]] = w[m[0]] != null ? w[m[0]] / w.window_days * 7 : null; });
    return { kind: 'exact', snap: w, days: w.window_days, per7 };
  }
  const inside = rows.filter(r => s7.window_start && r.window_start && r.window_start <= s7.window_start && r.window_end >= s7.window_end && r.window_days - 7 >= 7)
    .sort((a, b) => order(a) - order(b));
  if (inside.length) {
    const w = inside[0], rest = w.window_days - 7, per7 = {};
    REVIEW_METRICS.forEach(m => { const a = w[m[0]], b = s7[m[0]]; per7[m[0]] = (a != null && b != null && a >= b) ? (a - b) / rest * 7 : null; });
    return { kind: 'derived', snap: w, days: rest, per7 };
  }
  return null;
}
function baselineLabel(b) {
  const w = b.snap;
  if (b.kind === 'exact') return 'the prior ' + w.window_days + ' days (' + windowLabel(w) + '), averaged per 7 days';
  return 'the earlier ' + b.days + ' days: your ' + w.window_days + 'd snapshot (' + windowLabel(w) + ') minus this week, averaged per 7 days';
}
function platformSummary(platform, base) {
  const s7 = S.snaps.filter(s => s.platform === platform && s.window_days === 7).sort((a, b) => b.window_end.localeCompare(a.window_end))[0];
  if (!s7) return { platform, s7: null };
  const b = findBaseline(s7, base);
  const week = {};
  REVIEW_METRICS.forEach(m => { week[m[0]] = s7[m[0]]; });
  const rows = [];
  REVIEW_METRICS.forEach(m => {
    if (week[m[0]] == null) return;
    const bv = b ? b.per7[m[0]] : null;
    rows.push({ key: m[0], label: m[1], dec: m[2], week: week[m[0]], base: bv, chg: pctChange(week[m[0]], bv) });
  });
  const chg = {};
  rows.forEach(r => { chg[r.key] = r.chg; });
  return { platform, s7, baseline: b, rows, week, weekRates: derivedRates(platform, week), baseRates: b ? derivedRates(platform, b.per7) : null, chg };
}
function bestStories() {
  const best = {};
  S.metrics.forEach(m => { if (m.views != null && (!best[m.post_id] || m.window_days > best[m.post_id].window_days)) best[m.post_id] = m; });
  const stories = {};
  S.posts.forEach(p => {
    if (!p.story_key) return;
    const s = stories[p.story_key] = stories[p.story_key] || { views: 0, platforms: new Set() };
    s.platforms.add(p.platform);
    if (best[p.id]) s.views += best[p.id].views;
  });
  return Object.keys(stories).filter(k => stories[k].views > 0).map(k => [k, stories[k]]).sort((a, b) => b[1].views - a[1].views);
}
function scriptLink(story) {
  let idea = null;
  if (story) {
    const sids = new Set(S.posts.filter(p => p.story_key === story && p.series_id).map(p => p.series_id));
    idea = S.ideas.filter(i => i.status === 'idea' && sids.has(i.series_id)).sort((a, b) => a.id - b.id)[0] || null;
  }
  if (!idea) idea = S.ideas.filter(i => i.status === 'idea').sort((a, b) => a.id - b.id)[0] || null;
  if (idea) return [{ go: 'scripts', sub: 'new', series: idea.series_id, idea: idea.id }, 'Write a script: "' + idea.idea + '"'];
  return [{ go: 'scripts', sub: 'new' }, 'Start a new script'];
}
function checklistProgress() {
  return [S.checklist.filter(c => c.done).length, S.checklist.length];
}
function suggest(sums, todayIso) {
  const acts = [];
  const stories = bestStories();
  const top = stories.length ? stories[0][0] : null;
  sums.forEach(s => {
    if (!s.s7) return;
    const name = PNAME[s.platform], w = s.week, chg = s.chg.views;
    if (chg != null && chg <= DROP) {
      const [link, lt] = scriptLink(top);
      let why = name + ' views were ' + fint(w.views) + ' this week vs about ' + fint(s.baseline.per7.views) + ' per week in the baseline (' + (chg >= 0 ? '+' : '') + chg.toFixed(0) + '%).';
      if (top) why += ' Your strongest story so far is "' + top + '" (' + fint(stories[0][1].views) + ' views).';
      acts.push({ pri: 100, title: 'Rebuild momentum on ' + name + ': post the next part of your best story', why, link, linkText: lt });
    }
    const r = s.weekRates;
    if (r.fol1k != null && r.fol1k < 5 && w.viewers) {
      const nv = s.s7.new_viewers != null ? ' About ' + (s.s7.new_viewers / w.viewers * 100).toFixed(0) + '% of viewers were new.' : '';
      acts.push({ pri: 90, title: 'Fix follow conversion on ' + name + ': add a direct follow ask and a next-part pointer to every Close',
        why: (w.net_followers >= 0 ? '+' : '') + w.net_followers + ' net followers from ' + fint(w.viewers) + ' viewers this week (' + r.fol1k.toFixed(1) + ' per 1K viewers).' + nv + ' Give first-time viewers a reason to follow.',
        link: { go: 'scripts' }, linkText: 'Open the script builder' });
    }
    if (r.shares1k != null && r.shares1k < 1) {
      acts.push({ pri: 80, title: 'Make your next ' + name + ' post shareable: end the Takeaway with "send this to a first-year teacher"',
        why: fint(w.shares) + ' shares on ' + fint(w.views) + ' views this week (' + r.shares1k.toFixed(2) + ' per 1K views).', link: { go: 'scripts' }, linkText: 'Open the script builder' });
    }
  });
  for (const [story, info] of stories) {
    const missing = PLATFORMS.filter(p => !info.platforms.has(p[0])).map(p => p[1]);
    if (missing.length) {
      const have = PLATFORMS.filter(p => info.platforms.has(p[0])).map(p => p[1]).join(', ');
      acts.push({ pri: 70, title: 'Repurpose "' + story + '" to ' + missing.join(' and '),
        why: 'It has ' + fint(info.views) + ' views on ' + have + ' only. Same story, new platform audience (story keys link them).', link: { go: 'posts', sub: 'new' }, linkText: 'Add the post' });
      break;
    }
  }
  const weekAgo = addDays(todayIso, -6);
  const dated = S.posts.filter(p => p.post_date && p.post_date >= weekAgo && p.post_date <= todayIso).length;
  if (S.posts.some(p => p.post_date) && dated < 3) {
    acts.push({ pri: 60, title: 'Post at least 3 times this week', why: 'Only ' + dated + ' post(s) are dated in the last 7 days (dates may be approximate).', link: { go: 'posts', sub: 'new' }, linkText: 'Log a post' });
  }
  const low = S.metrics.filter(m => m.stayed_pct != null).sort((a, b) => a.stayed_pct - b.stayed_pct)[0];
  if (low && low.stayed_pct < 50) {
    const p = byId('posts', low.post_id);
    if (p) acts.push({ pri: 50, title: 'Rewrite the hook on "' + p.title + '"', why: 'Only ' + low.stayed_pct.toFixed(1) + '% stayed to watch, your lowest. Try a hook from your library that held viewers better.', link: { go: 'hooks' }, linkText: 'Open the hook library' });
  }
  const [done, total] = checklistProgress();
  if (done < total) {
    const item = S.checklist.find(c => !c.done);
    acts.push({ pri: 40, title: 'Finish the conversion checklist', why: 'Nearly every viewer is a first-timer, so your profile has to convert them.' +
      (item ? ' Next up: ' + PNAME[item.platform] + ' ' + item.item_key.replace(/_/g, ' ') + '.' : ''), link: { go: 'checklist' }, linkText: 'Open the checklist' });
  }
  const [lk, lt] = scriptLink(top);
  acts.push({ pri: 30, title: 'Write the next part of a series', why: 'Keeps viewers coming back for the next part.', link: lk, linkText: lt });
  acts.sort((a, b) => b.pri - a.pri);
  return acts;
}

/* ================= hooks helpers ================= */
const splitTags = t => String(t || '').replace(/;/g, ',').split(',').map(x => x.trim().toLowerCase()).filter(Boolean);
const normTags = v => { const u = Array.from(new Set(splitTags(v))); return u.length ? u.join(',') : null; };
function hookPostsFor(h) {
  const explicit = new Set(S.hookPosts.filter(x => x.hook_id === h.id).map(x => x.post_id));
  const key = h.text.trim().toLowerCase();
  const rows = S.posts.filter(p => explicit.has(p.id) || (p.hook_text && p.hook_text.trim().toLowerCase() === key));
  rows.sort((a, b) => (a.post_date == null) - (b.post_date == null) || String(a.post_date).localeCompare(String(b.post_date)) || a.id - b.id);
  return rows.map(p => [p, explicit.has(p.id)]);
}
