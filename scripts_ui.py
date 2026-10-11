"""Script builder (step 4): structured 30-45 second scripts, time estimate, templates."""
import re

from ui import PNAME, badge, esc, field, layout, num, select, txt

WPS = 2.5            # spoken words per second (150 wpm)
MIN_S, MAX_S = 30, 45
WORD_RE = re.compile(r"[\w'’-]*\w[\w'’-]*")

# key, label, hint, rows, counts toward spoken time
SECTIONS = [
    ("hook_spoken", "Hook — spoken line", "The first sentence out loud. Make a viewer who's never seen you stay.", 2, True),
    ("expectation", "Expectation", "What you thought would happen (the 'expected' half of expectation-vs-reality).", 3, True),
    ("reveal", "Reveal — ONE specific detail", "A single concrete moment, quote or number. Not a summary.", 3, True),
    ("takeaway", "Takeaway — ONE lesson", "One sentence a first-year teacher can use tomorrow.", 2, True),
    ("close_ask", "Close — direct follow / share ask", "Say it plainly: follow for the next part, send this to someone.", 2, True),
    ("next_part_pointer", "Next-part pointer", "Tell them what Part N+1 covers so following has a reason.", 2, True),
]
SPOKEN_KEYS = [k for k, _, _, _, counts in SECTIONS if counts]
TEXT_KEYS = ["hook_onscreen"] + [k for k, *_ in SECTIONS]


def count_words(text):
    return len(WORD_RE.findall(text or ""))


def estimate_seconds(values):
    """Spoken time only (on-screen text is read at the same time as the hook, so it adds nothing)."""
    words = sum(count_words(values.get(k)) for k in SPOKEN_KEYS)
    return round(words / WPS)


def time_badge(sec):
    if sec is None:
        return '<span class="badge">no estimate</span>'
    cls, label = ("ok", "in range") if MIN_S <= sec <= MAX_S else (("short", "short") if sec < MIN_S else ("long", "long"))
    return f'<span class="badge t-{cls}">≈{sec}s · {label}</span>'


# ------------------------------------------------------------------ pages
def scripts_list(conn, path):
    def card(s):
        series = conn.execute("SELECT name FROM series WHERE id=?", (s["series_id"],)).fetchone() if s["series_id"] else None
        use = (f'<a class="btn small primary" href="/scripts/new?template={s["id"]}">Use this template</a> '
               if s["is_template"] else "")
        return (f'<article class="card"><h3><a href="/scripts/{s["id"]}/edit">{esc(s["title"] or "Untitled script")}</a> '
                f'{badge(s["source"])}</h3><div>{time_badge(s["est_seconds"])}'
                f'{f" <span class=muted>{esc(series[0])}</span>" if series else ""}</div>'
                f'<p class="muted">{esc((s["hook_spoken"] or s["hook_onscreen"] or "")[:140])}</p>{use}</article>')
    scripts = conn.execute("SELECT * FROM scripts WHERE is_template=0 ORDER BY id DESC").fetchall()
    templates = conn.execute("SELECT * FROM scripts WHERE is_template=1 ORDER BY id").fetchall()
    body = f"""<div class="titlebar"><h1>Scripts</h1><a class="btn primary" href="/scripts/new">+ New script</a></div>
<p class="muted">30–45 second structure: Hook → Expectation → Reveal → Takeaway → Close. The time estimate counts
spoken words at {WPS:g} words/second.</p>
<h2>Templates</h2><div class="grid">{"".join(card(s) for s in templates) or '<p class="muted">None yet. Save any script as a template.</p>'}</div>
<h2>My scripts</h2><div class="grid">{"".join(card(s) for s in scripts) or '<p class="muted">No scripts yet.</p>'}</div>"""
    return layout("Scripts", body, path)


def script_form(conn, s, q, path):
    is_new = s is None
    tpl = None
    if is_new and q.get("template", [""])[0].isdigit():
        tpl = conn.execute("SELECT * FROM scripts WHERE id=? AND is_template=1", (q["template"][0],)).fetchone()
    base = s or tpl
    g = lambda k, d="": (base[k] if base is not None and base[k] is not None else d)  # noqa: E731
    idea_id = q.get("idea", [""])[0]
    series_default = q.get("series", [""])[0] or g("series_id")
    title_default = g("title")
    if is_new and idea_id.isdigit():
        row = conn.execute("SELECT idea FROM series_ideas WHERE id=?", (idea_id,)).fetchone()
        title_default = row[0] if row else title_default
    if is_new and tpl:
        title_default = ""
    series_opts = [("", "— none —")] + [(r["id"], r["name"]) for r in conn.execute("SELECT id, name FROM series ORDER BY name")]
    post_opts = [("", "— none —")] + [(r["id"], f'{PNAME[r["platform"]].split()[0]}: {r["title"][:60]}')
                                      for r in conn.execute("SELECT id, platform, title FROM posts ORDER BY platform, title")]
    hook_opts = [("", "— insert a saved hook —")] + [(r["text"], r["text"][:70]) for r in conn.execute("SELECT text FROM hooks ORDER BY id DESC")]

    secs = ""
    for key, label, hint, rows, _ in SECTIONS:
        extra = ""
        if key == "hook_spoken":
            extra = (f'<label>Saved hooks<select id="hookpick">'
                     + "".join(f'<option value="{esc(v)}">{esc(l)}</option>' for v, l in hook_opts) + "</select></label>")
        secs += (f'<section class="card sect"><div class="sect-head"><h3>{esc(label)}</h3>'
                 f'<span class="muted cnt" data-for="{key}"></span></div><p class="muted">{esc(hint)}</p>'
                 f'{"" if key != "hook_spoken" else field("hook_onscreen", "Hook — on-screen text", g("hook_onscreen"), placeholder="Short. Readable in 1 second.")}'
                 f'<textarea name="{key}" rows="{rows}" data-spoken="1">{esc(g(key))}</textarea>{extra}</section>')

    tpl_note = f'<p class="muted">Started from template: <b>{esc(tpl["title"])}</b></p>' if tpl else ""
    action = "/scripts/new" if is_new else f'/scripts/{s["id"]}/edit'
    footer = ""
    if not is_new:
        footer = (f'<form method="post" action="/scripts/{s["id"]}/template" class="inline">'
                  f'<button class="btn">Save as template</button></form>'
                  f'<form method="post" action="/scripts/{s["id"]}/delete" onsubmit="return confirm(\'Delete this script?\')">'
                  f'<button class="btn danger">Delete</button></form>')
    body = f"""<p><a href="/scripts">← Scripts</a></p><h1>{"New script" if is_new else "Edit script"} {badge(g("source", "")) if not is_new else ""}</h1>{tpl_note}
<div id="meter" class="meter"><div class="bar2"><i id="meterfill"></i><b class="mark" style="left:{MIN_S / 60 * 100:.1f}%"></b><b class="mark" style="left:{MAX_S / 60 * 100:.1f}%"></b></div>
<div><b id="est">—</b> <span class="muted" id="estnote"></span></div></div>
<ul id="warns" class="warns"></ul>
<form method="post" action="{action}" class="stack" id="scriptform">
{field("title", "Title", title_default, placeholder="e.g. Part 4: What I changed")}
<div class="row">{select("series_id", "Series", series_opts, series_default)}{select("post_id", "Posted as (optional)", post_opts, g("post_id"))}</div>
{f'<input type="hidden" name="idea_id" value="{esc(idea_id)}">' if idea_id.isdigit() and is_new else ""}
{secs}
<label class="check"><input type="checkbox" name="is_template" value="1" {"checked" if g("is_template", 0) else ""}> this is a template</label>
<div class="row"><button class="btn primary">Save script</button><button type="button" class="btn" id="copybtn">Copy script text</button></div>
</form>
<div class="row">{footer}</div>
<script>{SCRIPT_JS.replace("__WPS__", str(WPS)).replace("__MIN__", str(MIN_S)).replace("__MAX__", str(MAX_S))}</script>"""
    return layout("Script", body, path)


SCRIPT_JS = r"""
(function () {
  var WPS = __WPS__, MIN = __MIN__, MAX = __MAX__;
  var re = /[\p{L}\p{N}_'’-]*[\p{L}\p{N}_][\p{L}\p{N}_'’-]*/gu;
  var form = document.getElementById('scriptform');
  function words(s) { var m = (s || '').match(re); return m ? m.length : 0; }
  function el(n) { return form.elements[n]; }
  function update() {
    var total = 0, w = {};
    form.querySelectorAll('textarea[data-spoken]').forEach(function (t) {
      w[t.name] = words(t.value); total += w[t.name];
      var c = document.querySelector('.cnt[data-for="' + t.name + '"]');
      if (c) c.textContent = w[t.name] + ' words · ~' + Math.round(w[t.name] / WPS) + 's';
    });
    var sec = Math.round(total / WPS);
    document.getElementById('est').textContent = '≈ ' + sec + ' seconds';
    document.getElementById('estnote').textContent = total + ' spoken words at ' + WPS + ' words/sec (target ' + MIN + '–' + MAX + 's)';
    var fill = document.getElementById('meterfill');
    fill.style.width = Math.min(100, sec / 60 * 100) + '%';
    fill.className = sec < MIN ? 'short' : (sec > MAX ? 'long' : 'ok');
    var warns = [];
    if (sec > MAX) warns.push('Over ' + MAX + 's: trim ' + (sec - MAX) + 's (about ' + Math.ceil((sec - MAX) * WPS) + ' words).');
    if (sec < MIN && total > 0) warns.push('Under ' + MIN + 's: add about ' + Math.ceil((MIN - sec) * WPS) + ' words (a detail in the Reveal usually works best).');
    if (!el('hook_onscreen').value.trim()) warns.push('Add the on-screen hook text.');
    if (w.reveal > 35) warns.push('Reveal is long. Keep it to ONE specific detail.');
    if (w.takeaway > 25) warns.push('Takeaway is long. One lesson, one sentence.');
    if (!/follow|share|send|subscribe/i.test(el('close_ask').value)) warns.push('Close needs a direct follow or share ask.');
    if (!el('next_part_pointer').value.trim()) warns.push('Add a next-part pointer so following has a reason.');
    document.getElementById('warns').innerHTML = warns.map(function (x) { return '<li>' + x.replace(/</g, '&lt;') + '</li>'; }).join('');
  }
  form.addEventListener('input', update);
  var pick = document.getElementById('hookpick');
  if (pick) pick.addEventListener('change', function () {
    if (pick.value) { el('hook_spoken').value = pick.value; update(); }
  });
  document.getElementById('copybtn').addEventListener('click', function () {
    var parts = [['HOOK (on-screen)', 'hook_onscreen'], ['HOOK (spoken)', 'hook_spoken'], ['EXPECTATION', 'expectation'],
      ['REVEAL', 'reveal'], ['TAKEAWAY', 'takeaway'], ['CLOSE', 'close_ask'], ['NEXT PART', 'next_part_pointer']];
    var out = (el('title').value ? el('title').value + '\n\n' : '') + parts.map(function (p) {
      return p[0] + ':\n' + el(p[1]).value.trim(); }).join('\n\n');
    var done = function () { document.getElementById('copybtn').textContent = 'Copied ✓'; };
    if (navigator.clipboard) navigator.clipboard.writeText(out).then(done, function () { window.prompt('Copy:', out); });
    else window.prompt('Copy:', out);
  });
  update();
})();
"""


# ------------------------------------------------------------------ routing
def handle_get(conn, path, q):
    if path == "/scripts":
        return scripts_list(conn, path)
    if path == "/scripts/new":
        return script_form(conn, None, q, path)
    m = re.fullmatch(r"/scripts/(\d+)/edit", path)
    if m:
        s = conn.execute("SELECT * FROM scripts WHERE id=?", (m[1],)).fetchone()
        if not s:
            raise LookupError
        return script_form(conn, s, q, path)
    return None


def _values(f):
    one = lambda k: f.get(k, [""])[0]  # noqa: E731
    vals = {k: txt(one(k)) for k in TEXT_KEYS}
    vals["title"] = txt(one("title"))
    vals["series_id"] = num(one("series_id"))
    vals["post_id"] = num(one("post_id"))
    vals["is_template"] = 1 if one("is_template") else 0
    vals["est_seconds"] = estimate_seconds(vals)
    return vals


def handle_post(conn, path, f):
    one = lambda k: f.get(k, [""])[0]  # noqa: E731
    cols = ["title", "series_id", "post_id", "is_template", "est_seconds"] + TEXT_KEYS
    if path == "/scripts/new":
        v = _values(f)
        sid = conn.execute(f"INSERT INTO scripts ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                           [v[c] for c in cols]).lastrowid
        if one("idea_id").isdigit():  # script written from a series idea -> mark that idea as drafted
            conn.execute("UPDATE series_ideas SET status='drafted' WHERE id=? AND status='idea'", (one("idea_id"),))
        return f"/scripts/{sid}/edit"
    m = re.fullmatch(r"/scripts/(\d+)/(edit|delete|template)", path)
    if not m:
        return None
    sid, act = int(m[1]), m[2]
    s = conn.execute("SELECT * FROM scripts WHERE id=?", (sid,)).fetchone()
    if not s:
        raise LookupError
    if act == "delete":
        conn.execute("DELETE FROM scripts WHERE id=?", (sid,))
        return "/scripts"
    if act == "edit":
        v = _values(f)
        conn.execute("UPDATE scripts SET " + ",".join(f"{c}=?" for c in cols) + " WHERE id=?", [*[v[c] for c in cols], sid])
        return f"/scripts/{sid}/edit"
    # save as template = copy, so the original script stays a normal script
    title = "Template: " + (s["title"] or "Untitled")
    tcols = [c for c in cols if c not in ("title", "is_template", "post_id")]
    new = conn.execute(f"INSERT INTO scripts (title, is_template, {','.join(tcols)}) VALUES (?,1,{','.join('?' * len(tcols))})",
                       [title, *[s[c] for c in tcols]]).lastrowid
    return f"/scripts/{new}/edit"


# ------------------------------------------------------------------ starter templates
STARTERS = [
    ("Expectation vs. Reality (starter)", dict(
        hook_onscreen="I expected [X]. What actually happened: [Y]",
        hook_spoken="I thought [what you expected]. Here's what actually happened.",
        expectation="Going in, I expected [one sentence].",
        reveal="Then [one specific detail: a quote, a number, a moment].",
        takeaway="The lesson: [one lesson, one sentence].",
        close_ask="If this helped, follow for Part [N+1], and send it to a first-year teacher.",
        next_part_pointer="Next time: [what happens next].")),
    ("Air Force to Classroom (starter)", dict(
        hook_onscreen="In the Air Force: [X]. In my classroom: [Y]",
        hook_spoken="After years as an F-16 crew chief, here's what surprised me about teaching.",
        expectation="In the Air Force, [how it worked there].",
        reveal="In my classroom, [one specific detail that was different].",
        takeaway="What carried over: [one lesson].",
        close_ask="Follow for the next part, and share this with a veteran thinking about teaching.",
        next_part_pointer="Next: [the next transition story].")),
]


def seed_templates(conn):
    for title, v in STARTERS:
        v["est_seconds"] = estimate_seconds(v)
        cols = ["title", "is_template", "source"] + list(v)
        conn.execute(f"INSERT INTO scripts ({','.join(cols)}) VALUES (?,1,'seed',{','.join('?' * len(v))})",
                     [title, *v.values()])
