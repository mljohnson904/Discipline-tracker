"""Series planner and hook library pages (step 3)."""
import re
from urllib.parse import quote

from ui import (PLATFORMS, PNAME, badge, esc, fint, fpct, field, fdate, layout, metric_summary, num, plat_badge,
                select, txt)

IDEA_STATUSES = [("idea", "Idea"), ("drafted", "Drafted"), ("posted", "Posted")]


def _posts_with_metrics(conn, where="", args=()):
    posts = conn.execute("SELECT p.*, s.name AS series_name FROM posts p LEFT JOIN series s ON s.id = p.series_id "
                         + where + " ORDER BY p.post_date IS NULL, p.post_date, p.id", args).fetchall()
    mets = {}
    for m in conn.execute("SELECT * FROM post_metrics ORDER BY window_days"):
        mets.setdefault(m["post_id"], []).append(m)
    return posts, mets


def _post_line(p, mets, extra=""):
    ms = "".join(metric_summary(m) for m in mets.get(p["id"], [])) or '<div class="muted">No metrics yet</div>'
    when = fdate(p["post_date"], p["date_approx"])
    return (f'<div class="partpost"><div>{plat_badge(p["platform"])} {badge(p["source"])} '
            f'<span class="muted">{esc(when)}</span></div>'
            f'<a href="/posts/{p["id"]}/edit">{esc(p["title"])}</a>{ms}{extra}</div>')


# ================================================================== series
def series_list(conn, path):
    rows = conn.execute(
        "SELECT s.*, (SELECT COUNT(*) FROM posts WHERE series_id = s.id) AS n_posts, "
        "(SELECT COUNT(DISTINCT series_part) FROM posts WHERE series_id = s.id AND series_part IS NOT NULL) AS n_parts, "
        "(SELECT COUNT(*) FROM series_ideas WHERE series_id = s.id AND status != 'posted') AS n_ideas "
        "FROM series s ORDER BY s.name").fetchall()
    cards = ""
    for s in rows:
        plats = [r[0] for r in conn.execute("SELECT DISTINCT platform FROM posts WHERE series_id=?", (s["id"],))]
        cards += (f'<article class="card"><h3><a href="/series/{s["id"]}">{esc(s["name"])}</a> {badge(s["source"])}</h3>'
                  f'<div class="muted">{esc(s["description"] or "")}</div>'
                  f'<p>{s["n_parts"]} part(s) · {s["n_posts"]} post(s) · {s["n_ideas"]} open idea(s)</p>'
                  f'{"".join(plat_badge(p) for p in plats)}</article>')
    body = f"""<h1>Series planner</h1>
<p class="muted">Group posts into a series, order them Part 1/2/3, and keep a list of next-part ideas.</p>
<div class="grid">{cards or '<p class="muted">No series yet.</p>'}</div>
<h2>New series</h2>
<form method="post" action="/series/new" class="stack">{field("name", "Name", required="", placeholder="e.g. Observation Arc")}
<label>Description<textarea name="description" rows="2"></textarea></label>
<button class="btn primary">Create series</button></form>"""
    return layout("Series", body, path)


def series_detail(conn, sid, path):
    s = conn.execute("SELECT * FROM series WHERE id=?", (sid,)).fetchone()
    if not s:
        raise LookupError
    posts, mets = _posts_with_metrics(conn, "WHERE p.series_id = ?", (sid,))
    parts = {}
    for p in posts:
        parts.setdefault(p["series_part"], []).append(p)
    numbered = sorted(k for k in parts if k is not None)
    next_part = (numbered[-1] + 1) if numbered else 1
    out = ""
    prev = 0
    for k in numbered:
        if k > prev + 1:
            out += f'<p class="flag">Missing: Part {prev + 1}{"" if k == prev + 2 else f"–{k - 1}"}</p>'
        prev = k
        stories = sorted({p["story_key"] for p in parts[k] if p["story_key"]})
        lines = "".join(_post_line(p, mets, _part_form(sid, p)) for p in parts[k])
        out += (f'<section class="card part"><h3>Part {k} <span class="muted">{esc(" · ".join(stories))}</span></h3>'
                f'{lines}</section>')
    if None in parts:
        lines = "".join(_post_line(p, mets, _part_form(sid, p)) for p in parts[None])
        out += f'<section class="card part"><h3>No part number yet</h3>{lines}</section>'
    if not posts:
        out = '<p class="muted">No posts in this series yet. Add some below.</p>'

    others = conn.execute("SELECT id, platform, title FROM posts WHERE series_id IS NOT ? ORDER BY platform, title",
                          (sid,)).fetchall()
    opts = [(p["id"], f'{PNAME[p["platform"]].split()[0]}: {p["title"][:70]}') for p in others]
    add = (f'<form method="post" action="/series/{sid}/assign" class="stack"><div class="row">'
           f'{select("post_id", "Post", opts)}{field("part", "Part #", next_part, "number", min="1")}</div>'
           f'<button class="btn">Add to series</button></form>') if others else ""

    ideas = conn.execute("SELECT * FROM series_ideas WHERE series_id=? ORDER BY "
                         "CASE status WHEN 'idea' THEN 0 WHEN 'drafted' THEN 1 ELSE 2 END, sort, id", (sid,)).fetchall()
    idea_html = ""
    for i in ideas:
        idea_html += (f'<li class="idea {esc(i["status"])}"><span>{esc(i["idea"])}</span>'
                      f'<form method="post" action="/ideas/{i["id"]}/status">'
                      f'{_status_select(i["status"])}<button class="btn small">Save</button>'
                      f'<button class="btn small danger" formaction="/ideas/{i["id"]}/delete">✕</button></form></li>')
    body = f"""<p><a href="/series">← All series</a></p>
<div class="titlebar"><h1>{esc(s["name"])} {badge(s["source"])}</h1></div>
<p class="muted">{esc(s["description"] or "")}</p>
<h2>Parts</h2>{out}
<h2>Add an existing post</h2>{add or '<p class="muted">All posts are already in this series.</p>'}
<h2>Next-part ideas <small>next up: Part {next_part}</small></h2>
<ul class="ideas">{idea_html or '<li class="muted">No ideas yet.</li>'}</ul>
<form method="post" action="/series/{sid}/ideas/add" class="stack">
{field("idea", f"Idea for Part {next_part}", required="", placeholder="e.g. What I changed after the conference")}
<button class="btn">Add idea</button></form>
<details><summary>Edit or delete series</summary>
<form method="post" action="/series/{sid}/edit" class="stack">{field("name", "Name", s["name"], required="")}
<label>Description<textarea name="description" rows="2">{esc(s["description"])}</textarea></label>
<button class="btn primary">Save</button></form>
<form method="post" action="/series/{sid}/delete" onsubmit="return confirm('Delete this series? Posts are kept.')">
<button class="btn danger">Delete series</button></form></details>"""
    return layout(s["name"], body, path)


def _status_select(current):
    opts = "".join(f'<option value="{v}"{" selected" if v == current else ""}>{l}</option>' for v, l in IDEA_STATUSES)
    return f'<select name="status">{opts}</select>'


def _part_form(sid, p):
    return (f'<form method="post" action="/series/{sid}/assign" class="inline">'
            f'<input type="hidden" name="post_id" value="{p["id"]}">'
            f'<input type="number" name="part" min="1" value="{p["series_part"] or ""}" placeholder="Part #" '
            f'aria-label="Part number"><button class="btn small">Set part</button>'
            f'<button class="btn small danger" formaction="/series/{sid}/unassign">Remove</button></form>')


# ================================================================== hooks
def _split_tags(tags):
    return [t.strip().lower() for t in (tags or "").replace(";", ",").split(",") if t.strip()]


def _norm_tags(v):
    return ",".join(dict.fromkeys(_split_tags(v))) or None


def hook_posts(conn, hook):
    """Posts linked explicitly, plus posts whose hook_text equals the hook text (case-insensitive)."""
    explicit = {r[0] for r in conn.execute("SELECT post_id FROM hook_posts WHERE hook_id=?", (hook["id"],))}
    auto = {r[0] for r in conn.execute("SELECT id FROM posts WHERE lower(trim(hook_text)) = lower(trim(?))",
                                       (hook["text"],))}
    posts, mets = _posts_with_metrics(conn)
    return [(p, p["id"] in explicit) for p in posts if p["id"] in explicit | auto], mets


def _performance(linked, mets):
    """Summaries are grouped by window so a 7d number is never added to a 28d one."""
    by_win = {}
    for p, _ in linked:
        for m in mets.get(p["id"], []):
            w = by_win.setdefault(m["window_days"], {"posts": set(), "views": 0, "has_views": False, "stayed": []})
            w["posts"].add(p["id"])
            if m["views"] is not None:
                w["views"] += m["views"]
                w["has_views"] = True
            if m["stayed_pct"] is not None:
                w["stayed"].append(m["stayed_pct"])
    if not by_win:
        return '<p class="muted">No performance data yet (link posts that used this hook, with metrics).</p>'
    rows = ""
    for days in sorted(by_win):
        w = by_win[days]
        st = sum(w["stayed"]) / len(w["stayed"]) if w["stayed"] else None
        rows += (f'<tr><td>{days}d</td><td>{len(w["posts"])}</td><td>{fint(w["views"]) if w["has_views"] else "—"}</td>'
                 f'<td>{fpct(st)}</td></tr>')
    return ('<div class="scroll"><table><thead><tr><th>Window</th><th>Posts</th><th>Views</th><th>Avg stayed</th></tr>'
            f'</thead><tbody>{rows}</tbody></table></div>')


def hooks_page(conn, q, path):
    term = q.get("q", [""])[0].strip()
    tag = q.get("tag", [""])[0].strip().lower()
    hooks = conn.execute("SELECT * FROM hooks ORDER BY id DESC").fetchall()
    all_tags = {}
    for h in hooks:
        for t in _split_tags(h["tags"]):
            all_tags[t] = all_tags.get(t, 0) + 1
    shown = []
    for h in hooks:
        blob = f'{h["text"]} {h["tags"] or ""} {h["notes"] or ""}'.lower()
        if term and term.lower() not in blob:
            continue
        if tag and tag not in _split_tags(h["tags"]):
            continue
        shown.append(h)
    chips = "".join(f'<a class="chip{" on" if t == tag else ""}" href="/hooks?tag={quote(t)}">#{esc(t)} '
                    f'<small>{n}</small></a>' for t, n in sorted(all_tags.items()))
    if tag:
        chips = '<a class="chip" href="/hooks">clear filter ✕</a> ' + chips

    cards = ""
    for h in shown:
        linked, mets = hook_posts(conn, h)
        plist = "".join(_post_line(p, mets) for p, _ in linked)
        notes = '<p class="note">%s</p>' % esc(h["notes"]) if h["notes"] else ""
        tags = "".join(f'<a class="chip" href="/hooks?tag={quote(t)}">#{esc(t)}</a>' for t in _split_tags(h["tags"]))
        cards += (f'<article class="card"><h3>“{esc(h["text"])}” {badge(h["source"])}</h3><div>{tags}</div>'
                  f'{notes}'
                  f'<h4>Performance <small class="muted">by window — compare like with like</small></h4>'
                  f'{_performance(linked, mets)}<h4>Posts that used it ({len(linked)})</h4>'
                  f'{plist or "<p class=muted>None linked yet.</p>"}'
                  f'<a class="btn small" href="/hooks/{h["id"]}/edit">Edit / link posts</a></article>')

    saved = {h["text"].strip().lower() for h in hooks}
    cands = conn.execute("SELECT id, platform, title, hook_text FROM posts WHERE hook_text IS NOT NULL "
                         "AND trim(hook_text) != '' ORDER BY id").fetchall()
    cand_html, seen = "", set()
    for p in cands:
        k = p["hook_text"].strip().lower()
        if k in saved or k in seen:
            continue
        seen.add(k)
        cand_html += (f'<li><form method="post" action="/hooks/from-post" class="inline">'
                      f'<input type="hidden" name="post_id" value="{p["id"]}"><span>“{esc(p["hook_text"])}” '
                      f'<span class="muted">({esc(PNAME[p["platform"]])})</span></span>'
                      f'<button class="btn small">Save to library</button></form></li>')
    cand_block = (f'<h2>Hooks from your posts not yet saved</h2><ul class="ideas">{cand_html}</ul>'
                  if cand_html else "")
    body = f"""<h1>Hook library</h1>
<form class="filters" method="get">{field("q", "Search hooks", term, "search")}<button class="btn">Search</button></form>
<div>{chips}</div>
<p class="muted">{len(shown)} hook(s). A post counts as using a hook if you linked it, or if its hook text matches
the hook exactly.</p>
<div class="grid">{cards or '<p class="muted">No hooks match.</p>'}</div>
{cand_block}
<h2>Add a hook</h2>
<form method="post" action="/hooks/new" class="stack">{field("text", "Hook text", required="")}
{field("tags", "Tags (comma-separated)", placeholder="e.g. observation, air-force, nervous")}
<label>Notes<textarea name="notes" rows="2"></textarea></label>
<button class="btn primary">Save hook</button></form>"""
    return layout("Hooks", body, path)


def hook_edit(conn, hid, path):
    h = conn.execute("SELECT * FROM hooks WHERE id=?", (hid,)).fetchone()
    if not h:
        raise LookupError
    linked, mets = hook_posts(conn, h)
    rows = ""
    for p, explicit in linked:
        act = (f'<form method="post" action="/hooks/{hid}/unlink" class="inline">'
               f'<input type="hidden" name="post_id" value="{p["id"]}"><button class="btn small danger">Unlink</button></form>'
               if explicit else '<span class="muted">linked automatically (post hook text matches)</span>')
        rows += _post_line(p, mets, act)
    linked_ids = {p["id"] for p, _ in linked}
    opts = [(p["id"], f'{PNAME[p["platform"]].split()[0]}: {p["title"][:70]}')
            for p in conn.execute("SELECT id, platform, title FROM posts ORDER BY platform, title") if p["id"] not in linked_ids]
    link = (f'<form method="post" action="/hooks/{hid}/link" class="stack">{select("post_id", "Link a post", opts)}'
            f'<button class="btn">Link post</button></form>') if opts else ""
    body = f"""<p><a href="/hooks">← Hook library</a></p><h1>Edit hook {badge(h["source"])}</h1>
<form method="post" action="/hooks/{hid}/edit" class="stack">{field("text", "Hook text", h["text"], required="")}
{field("tags", "Tags (comma-separated)", h["tags"] or "")}
<label>Notes<textarea name="notes" rows="2">{esc(h["notes"])}</textarea></label>
<button class="btn primary">Save</button></form>
<h2>Posts that used it</h2>{rows or '<p class="muted">None yet.</p>'}{link}
<form method="post" action="/hooks/{hid}/delete" onsubmit="return confirm('Delete this hook?')">
<button class="btn danger">Delete hook</button></form>"""
    return layout("Edit hook", body, path)


# ================================================================== routing
def handle_get(conn, path, q):
    if path == "/series":
        return series_list(conn, path)
    if path == "/hooks":
        return hooks_page(conn, q, path)
    m = re.fullmatch(r"/series/(\d+)", path)
    if m:
        return series_detail(conn, int(m[1]), path)
    m = re.fullmatch(r"/hooks/(\d+)/edit", path)
    if m:
        return hook_edit(conn, int(m[1]), path)
    return None


def handle_post(conn, path, f):
    one = lambda k: f.get(k, [""])[0]  # noqa: E731
    if path == "/series/new":
        name = txt(one("name"))
        if not name:
            return "/series"
        row = conn.execute("SELECT id FROM series WHERE lower(name)=lower(?)", (name,)).fetchone()
        sid = row[0] if row else conn.execute("INSERT INTO series (name, description) VALUES (?,?)",
                                              (name, txt(one("description")))).lastrowid
        return f"/series/{sid}"
    m = re.fullmatch(r"/series/(\d+)/(edit|delete|assign|unassign|ideas/add)", path)
    if m:
        sid, act = int(m[1]), m[2]
        if not conn.execute("SELECT 1 FROM series WHERE id=?", (sid,)).fetchone():
            raise LookupError
        if act == "edit":
            name = txt(one("name"))
            if name:
                try:
                    conn.execute("UPDATE series SET name=?, description=? WHERE id=?", (name, txt(one("description")), sid))
                except Exception:  # duplicate name
                    pass
        elif act == "delete":
            conn.execute("UPDATE posts SET series_part=NULL WHERE series_id=?", (sid,))
            conn.execute("DELETE FROM series WHERE id=?", (sid,))
            return "/series"
        elif act == "assign":
            conn.execute("UPDATE posts SET series_id=?, series_part=? WHERE id=?",
                         (sid, num(one("part")), num(one("post_id"))))
        elif act == "unassign":
            conn.execute("UPDATE posts SET series_id=NULL, series_part=NULL WHERE id=? AND series_id=?",
                         (num(one("post_id")), sid))
        else:
            idea = txt(one("idea"))
            if idea:
                conn.execute("INSERT INTO series_ideas (series_id, idea) VALUES (?,?)", (sid, idea))
        return f"/series/{sid}"
    m = re.fullmatch(r"/ideas/(\d+)/(status|delete)", path)
    if m:
        row = conn.execute("SELECT series_id FROM series_ideas WHERE id=?", (m[1],)).fetchone()
        if not row:
            raise LookupError
        if m[2] == "delete":
            conn.execute("DELETE FROM series_ideas WHERE id=?", (m[1],))
        elif one("status") in dict(IDEA_STATUSES):
            conn.execute("UPDATE series_ideas SET status=? WHERE id=?", (one("status"), m[1]))
        return f"/series/{row[0]}"

    if path == "/hooks/new":
        text = txt(one("text"))
        if text:
            conn.execute("INSERT INTO hooks (text, tags, notes) VALUES (?,?,?)",
                         (text, _norm_tags(one("tags")), txt(one("notes"))))
        return "/hooks"
    if path == "/hooks/from-post":
        p = conn.execute("SELECT id, hook_text FROM posts WHERE id=?", (num(one("post_id")),)).fetchone()
        if p and p["hook_text"]:
            hid = conn.execute("INSERT INTO hooks (text) VALUES (?)", (p["hook_text"].strip(),)).lastrowid
            conn.execute("INSERT OR IGNORE INTO hook_posts VALUES (?,?)", (hid, p["id"]))
        return "/hooks"
    m = re.fullmatch(r"/hooks/(\d+)/(edit|delete|link|unlink)", path)
    if m:
        hid, act = int(m[1]), m[2]
        if not conn.execute("SELECT 1 FROM hooks WHERE id=?", (hid,)).fetchone():
            raise LookupError
        if act == "delete":
            conn.execute("DELETE FROM hooks WHERE id=?", (hid,))
            return "/hooks"
        if act == "edit":
            text = txt(one("text"))
            if text:
                conn.execute("UPDATE hooks SET text=?, tags=?, notes=? WHERE id=?",
                             (text, _norm_tags(one("tags")), txt(one("notes")), hid))
            return "/hooks"
        pid = num(one("post_id"))
        if act == "link" and pid:
            conn.execute("INSERT OR IGNORE INTO hook_posts VALUES (?,?)", (hid, pid))
        elif act == "unlink":
            conn.execute("DELETE FROM hook_posts WHERE hook_id=? AND post_id=?", (hid, pid))
        return f"/hooks/{hid}/edit"
    return None
