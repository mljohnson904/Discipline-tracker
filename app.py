#!/usr/bin/env python3
"""Channel Builder - local-first dashboard for the "Second Mission" short-form channel.

Run:  python3 app.py            (http://localhost:8000)
      python3 app.py --lan      (reachable from your phone on the same Wi-Fi)
Standard library only.
"""
import argparse
import html
import json
import mimetypes
import os
import re
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import db

ROOT = os.path.dirname(os.path.abspath(__file__))
PLATFORMS = [("tiktok", "TikTok"), ("youtube", "YouTube Shorts"), ("instagram", "Instagram Reels")]
PNAME = dict(PLATFORMS)
DROP_THRESHOLD = -50.0

METRIC_FIELDS = [("views", "Views", int), ("viewers", "Viewers", int), ("likes", "Likes", int),
                 ("comments", "Comments", int), ("shares", "Shares", int),
                 ("follows_gained", "Follows gained", int), ("stayed_pct", "Stayed to watch %", float)]
SNAP_FIELDS = [("views", "Views", int), ("viewers", "Viewers", int), ("new_viewers", "New viewers", int),
               ("profile_views", "Profile views", int), ("likes", "Likes", int), ("comments", "Comments", int),
               ("shares", "Shares", int), ("interactions", "Interactions", int),
               ("net_followers", "Net followers", int), ("prior_net_followers", "Prior-window net followers", int),
               ("total_followers", "Total followers", int), ("engaged_views", "Engaged views", int),
               ("watch_hours", "Watch time (hrs)", float), ("stayed_pct", "Stayed to watch %", float)]

NAV = [("/", "Dashboard"), ("/posts", "Posts"), ("/snapshots", "Channel stats")]


# ------------------------------------------------------------------ helpers
def esc(v):
    return html.escape("" if v is None else str(v), quote=True)


def num(v, kind=int):
    """Parse a form value; blank/garbage -> None (never invent data)."""
    if v is None:
        return None
    v = str(v).strip().replace(",", "").replace("%", "")
    if v == "":
        return None
    try:
        return kind(float(v)) if kind is int else float(v)
    except ValueError:
        return None


def txt(v):
    v = (v or "").strip()
    return v or None


def fint(v):
    return "—" if v is None else f"{v:,.0f}"


def fpct(v, digits=1):
    return "—" if v is None else f"{v:.{digits}f}%"


def ratio(n, d, scale=1.0):
    return None if n is None or not d else n / d * scale


def fdate(d, approx=False):
    if not d:
        return "no date"
    try:
        t = date.fromisoformat(d).strftime("%b %-d")
    except ValueError:
        t = d
    return ("~" if approx else "") + t


def window_label(row):
    s, e = row["window_start"], row["window_end"]
    rng = f"{fdate(s)}–{fdate(e)}" if s else f"to {fdate(e)}"
    return f"{row['window_days']}d · {rng}"


def badge(source):
    return '<span class="badge seed">seed</span>' if source == "seed" else ""


def plat_badge(p):
    return f'<span class="badge p-{esc(p)}">{esc(PNAME.get(p, p))}</span>'


def layout(title, body, path="/"):
    nav = "".join(
        f'<a href="{h}" class="{"on" if (path == h or (h != "/" and path.startswith(h))) else ""}">{l}</a>'
        for h, l in NAV)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · Channel Builder</title><link rel="stylesheet" href="/static/style.css"></head>
<body><header><div class="brand">Channel Builder <small>Second Mission</small></div><nav>{nav}</nav></header>
<main>{body}</main></body></html>"""


def field(name, label, value="", kind="text", **attrs):
    extra = " ".join(f'{k.rstrip("_")}="{esc(v)}"' for k, v in attrs.items())
    return (f'<label>{esc(label)}<input type="{kind}" name="{name}" value="{esc(value)}" {extra}></label>')


def select(name, label, options, selected=None):
    opts = "".join(f'<option value="{esc(v)}"{" selected" if str(v) == str(selected) else ""}>{esc(l)}</option>'
                   for v, l in options)
    return f"<label>{esc(label)}<select name=\"{name}\">{opts}</select></label>"


# ------------------------------------------------------------------ analytics
def prior_snapshot(conn, snap):
    if not snap["window_start"]:
        return None
    prev_end = (date.fromisoformat(snap["window_start"]) - timedelta(days=1)).isoformat()
    return conn.execute("SELECT * FROM channel_snapshots WHERE platform=? AND window_days=? AND window_end=?",
                        (snap["platform"], snap["window_days"], prev_end)).fetchone()


CHANGE_LABELS = {"views": "Views", "viewers": "Viewers", "likes": "Likes", "comments": "Comments",
                 "shares": "Shares", "profile_views": "Profile views", "net_followers": "Net followers",
                 "watch_hours": "Watch time", "engaged_views": "Engaged views"}


def changes(conn, snap):
    """Return {metric: pct change vs prior window}. Uses a stored prior snapshot when one exists,
    otherwise the percent change the platform reported (kept in extra_json)."""
    out = dict(json.loads(snap["extra_json"] or "{}").get("changes", {}))
    prior = prior_snapshot(conn, snap)
    for k in CHANGE_LABELS:
        if prior and k in snap.keys() and snap[k] is not None and prior[k]:
            out[k] = (snap[k] - prior[k]) / prior[k] * 100
    if snap["net_followers"] is not None and snap["prior_net_followers"]:
        out["net_followers"] = (snap["net_followers"] - snap["prior_net_followers"]) / snap["prior_net_followers"] * 100
    return out


def snapshot_for(conn, platform, days):
    return conn.execute("SELECT * FROM channel_snapshots WHERE platform=? AND window_days=? ORDER BY window_end DESC",
                        (platform, days)).fetchone()


def card_rows(platform, s):
    views = s["views"]
    rows = []
    if platform == "youtube":
        rows.append(("Engaged-view rate", fpct(ratio(s["engaged_views"], views, 100)),
                     "YouTube's own metric (engaged views ÷ views); not the same as like/comment rate"))
    else:
        eng = (s["interactions"] if platform == "instagram" else
               None if s["likes"] is None else (s["likes"] or 0) + (s["comments"] or 0) + (s["shares"] or 0))
        rows.append(("Engagement rate", fpct(ratio(eng, views, 100), 2),
                     "interactions ÷ views" if platform == "instagram" else "(likes + comments + shares) ÷ views"))
    rows.append(("Shares / 1K views", "—" if s["shares"] is None else f"{ratio(s['shares'], views, 1000):.2f}",
                 "" if s["shares"] is not None else "not captured on this platform"))
    ptf = ratio(s["net_followers"], s["profile_views"], 100)
    rows.append(("Profile view → follow", fpct(ptf), "net followers ÷ profile views" if ptf is not None
                 else "needs profile views + net followers"))
    return rows


def flags_html(conn, s):
    out = []
    for k, pct in sorted(changes(conn, s).items()):
        if pct <= DROP_THRESHOLD:
            out.append(f'<div class="flag">⚠ {esc(CHANGE_LABELS.get(k, k))} down {abs(pct):.1f}% vs prior window</div>')
    return "".join(out)


def platform_card(conn, platform, days):
    s = snapshot_for(conn, platform, days)
    head = f"<h3>{esc(PNAME[platform])}</h3>"
    if not s:
        alt = conn.execute("SELECT * FROM channel_snapshots WHERE platform=? ORDER BY window_end DESC",
                           (platform,)).fetchone()
        note = f'<p class="muted">No {days}d snapshot for this platform.</p>'
        if alt:
            note += (f'<p class="muted">Only <b>{alt["window_days"]}d</b> data exists, so it is left out of this '
                     f'{days}d comparison. <a href="/snapshots/{alt["id"]}/edit">See it</a>.</p>')
        return f'<section class="card dim">{head}{note}<a class="btn small" href="/snapshots/new?platform={platform}&window_days={days}">Add {days}d snapshot</a></section>'
    nf = "—" if s["net_followers"] is None else "%+d" % s["net_followers"]
    body = [f'<div class="muted">{esc(window_label(s))} {badge(s["source"])}</div>',
            '<div class="stats">'
            f'<div><b>{fint(s["views"])}</b><span>views</span></div>'
            f'<div><b>{fint(s["viewers"])}</b><span>viewers</span></div>'
            f'<div><b>{nf}</b><span>net followers</span></div></div>', '<dl>']
    for label, val, note in card_rows(platform, s):
        body.append(f'<dt>{esc(label)}</dt><dd>{val}<small>{esc(note)}</small></dd>')
    body.append("</dl>")
    body.append(flags_html(conn, s))
    if s["notes"]:
        body.append(f'<p class="note">{esc(s["notes"])}</p>')
    return f'<section class="card">{head}{"".join(body)}</section>'


def post_rows_for_window(conn, days, loose):
    allowed = {days} | ({30} if loose and days == 28 else set()) | ({28} if loose and days == 30 else set())
    q = ("SELECT p.id, p.title, p.platform, p.topic_tag, p.story_key, s.name AS series_name, m.window_days, "
         "m.window_end, m.views, m.likes, m.comments, m.shares, m.stayed_pct "
         "FROM post_metrics m JOIN posts p ON p.id = m.post_id LEFT JOIN series s ON s.id = p.series_id "
         f"WHERE m.window_days IN ({','.join('?' * len(allowed))})")
    best = {}
    for r in conn.execute(q, sorted(allowed)):
        cur = best.get(r["id"])
        if not cur or (r["window_days"] == days and cur["window_days"] != days) or \
                (r["window_days"] == cur["window_days"] and r["window_end"] > cur["window_end"]):
            best[r["id"]] = r
    return list(best.values())


def group_table(rows, keyfn, empty_label):
    groups = {}
    for r in rows:
        groups.setdefault(keyfn(r) or empty_label, []).append(r)
    out = []
    for key, rs in groups.items():
        vw = [r["views"] for r in rs if r["views"] is not None]
        eng_rs = [r for r in rs if r["likes"] is not None and r["views"]]
        eng = ratio(sum((r["likes"] or 0) + (r["comments"] or 0) + (r["shares"] or 0) for r in eng_rs),
                    sum(r["views"] for r in eng_rs), 100)
        sh_rs = [r for r in rs if r["shares"] is not None and r["views"]]
        sh = ratio(sum(r["shares"] for r in sh_rs), sum(r["views"] for r in sh_rs), 1000)
        st = [r["stayed_pct"] for r in rs if r["stayed_pct"] is not None]
        plats = sorted({r["platform"] for r in rs})
        out.append((key, len(rs), sum(vw) if vw else None, eng, sh, sum(st) / len(st) if st else None, plats, len(eng_rs)))
    out.sort(key=lambda t: (t[0] == empty_label, -(t[2] or 0)))
    if not out:
        return '<p class="muted">No posts with metrics in this window.</p>'
    h = ("<div class='scroll'><table><thead><tr><th></th><th>Posts</th><th>Views</th><th>Eng. rate</th>"
         "<th>Shares/1K</th><th>Avg stayed</th></tr></thead><tbody>")
    for key, n, v, eng, sh, st, plats, neng in out:
        pills = "".join(plat_badge(p) for p in plats)
        h += (f"<tr><td><b>{esc(key)}</b><div>{pills}</div></td><td>{n}</td><td>{fint(v)}</td>"
              f"<td>{fpct(eng, 2)}</td><td>{'—' if sh is None else f'{sh:.2f}'}</td><td>{fpct(st)}</td></tr>")
    return h + "</tbody></table></div>"


def page_dashboard(conn, q, path):
    days = 28 if q.get("w", ["7"])[0] == "28" else 7
    loose = q.get("loose", [""])[0] == "1"
    toggle = "".join(f'<a class="{"on" if d == days else ""}" href="/?w={d}{"&loose=1" if loose else ""}">{d} days</a>'
                     for d in (7, 28))
    cards = "".join(platform_card(conn, p, days) for p, _ in PLATFORMS)
    rows = post_rows_for_window(conn, days, loose)
    excluded = conn.execute("SELECT COUNT(DISTINCT post_id) FROM post_metrics").fetchone()[0] - len(rows)
    loose_link = (f'<a href="/?w={days}{"" if loose else "&loose=1"}">'
                  f'{"Use exact windows only" if loose else "Include 28d ≈ 30d (Instagram posts are 30d)"}</a>'
                  if days == 28 else "")
    top = sorted([r for r in rows if r["views"] is not None], key=lambda r: -r["views"])[:10]
    toplist = "".join(
        f'<li><a href="/posts/{r["id"]}/edit">{esc(r["title"])}</a><div>{plat_badge(r["platform"])} '
        f'<b>{fint(r["views"])}</b> views · {r["window_days"]}d</div></li>' for r in top) or \
        '<li class="muted">No post views in this window.</li>'
    body = f"""<h1>Dashboard</h1>
<div class="toggle">{toggle}</div>
<p class="muted">Platforms are compared on the <b>same {days}-day window</b>. A platform with no {days}d data is
shown greyed out rather than mixed in. Missing numbers show as —, never as zero.</p>
<div class="grid">{cards}</div>
<h2>Top posts <small>{days}d metrics{' (28d ≈ 30d)' if loose else ''}</small></h2>
<p class="muted">{excluded} post(s) have no metrics for this window. {loose_link}</p>
<ol class="toplist">{toplist}</ol>
<h2>By topic tag</h2>{group_table(rows, lambda r: r["topic_tag"], "(untagged)")}
<h2>By series</h2>{group_table(rows, lambda r: r["series_name"], "(no series)")}
<h2>By story key</h2>{group_table(rows, lambda r: r["story_key"], "(no story key)")}
<p class="muted">Tip: topic tags aren't in the seed data (I didn't invent any) — add them on the post pages and
the tag table fills in.</p>
{audience_html(conn)}"""
    return layout("Dashboard", body, path)


def audience_html(conn):
    rows = conn.execute("SELECT * FROM audience_snapshots ORDER BY id").fetchall()
    if not rows:
        return ""
    cats = {}
    for r in rows:
        cats.setdefault(r["category"], []).append(r)
    cells = ""
    for cat, rs in cats.items():
        cells += f'<div class="aud"><h4>{esc(cat.title())}</h4>' + "".join(
            f'<div class="bar"><span>{esc(r["label"])}</span><i style="width:{min(100, r["pct"] or 0)}%"></i>'
            f'<b>{fpct(r["pct"])}</b></div>' for r in rs) + "</div>"
    return (f'<h2>YouTube audience <small>28d {badge(rows[0]["source"])}</small></h2>'
            f'<div class="grid">{cells}</div>')


# ------------------------------------------------------------------ posts
def series_options(conn):
    return [("", "— none —")] + [(r["id"], r["name"]) for r in conn.execute("SELECT id, name FROM series ORDER BY name")]


def metric_summary(m):
    bits = []
    if m["views"] is not None:
        bits.append(f"<b>{fint(m['views'])}</b> views")
    for k, lab in (("likes", "likes"), ("comments", "comments"), ("shares", "shares"), ("follows_gained", "follows")):
        if m[k] is not None:
            bits.append(f"{fint(m[k])} {lab}")
    if m["stayed_pct"] is not None:
        bits.append(f"stayed {fpct(m['stayed_pct'])}")
    return f'<div class="metric"><span class="win">{m["window_days"]}d</span> {" · ".join(bits) or "no numbers"}</div>'


def page_posts(conn, q, path):
    where, args = [], []
    for key, col in (("platform", "p.platform"), ("story", "p.story_key"), ("series", "p.series_id")):
        v = q.get(key, [""])[0]
        if v:
            where.append(f"{col} = ?")
            args.append(v)
    term = q.get("q", [""])[0].strip()
    if term:
        where.append("(p.title LIKE ? OR p.hook_text LIKE ? OR p.topic_tag LIKE ? OR p.story_key LIKE ?)")
        args += [f"%{term}%"] * 4
    sql = ("SELECT p.*, s.name AS series_name FROM posts p LEFT JOIN series s ON s.id = p.series_id" +
           (" WHERE " + " AND ".join(where) if where else "") +
           " ORDER BY p.post_date IS NULL, p.post_date DESC, p.id DESC")
    posts = conn.execute(sql, args).fetchall()
    metrics = {}
    for m in conn.execute("SELECT * FROM post_metrics ORDER BY window_days"):
        metrics.setdefault(m["post_id"], []).append(m)
    cards = ""
    for p in posts:
        flag = f'<div class="flag">⚑ {esc(p["flag"])}</div>' if p["flag"] else ""
        meta = " · ".join(x for x in [
            fdate(p["post_date"], p["date_approx"]),
            f'Series: {esc(p["series_name"])}' + (f' Part {p["series_part"]}' if p["series_part"] else "")
            if p["series_name"] else "",
            f'Story: {esc(p["story_key"])}' if p["story_key"] else "",
            f'#{esc(p["topic_tag"])}' if p["topic_tag"] else ""] if x)
        hook = f'<div class="hook">Hook: “{esc(p["hook_text"])}”</div>' if p["hook_text"] else ""
        mets = "".join(metric_summary(m) for m in metrics.get(p["id"], [])) or '<div class="muted">No metrics yet</div>'
        cards += (f'<article class="card post"><div>{plat_badge(p["platform"])} {badge(p["source"])}</div>'
                  f'<h3><a href="/posts/{p["id"]}/edit">{esc(p["title"])}</a></h3>'
                  f'<div class="muted">{meta}</div>{hook}{mets}{flag}</article>')
    stories = [r[0] for r in conn.execute("SELECT DISTINCT story_key FROM posts WHERE story_key IS NOT NULL ORDER BY 1")]
    filt = (f'<form class="filters" method="get">{field("q", "Search", term, "search")}'
            f'{select("platform", "Platform", [("", "All")] + PLATFORMS, q.get("platform", [""])[0])}'
            f'{select("story", "Story", [("", "All")] + [(s, s) for s in stories], q.get("story", [""])[0])}'
            f'{select("series", "Series", [("", "All")] + series_options(conn)[1:], q.get("series", [""])[0])}'
            '<button class="btn">Filter</button></form>')
    body = (f'<div class="titlebar"><h1>Post log</h1><a class="btn" href="/posts/new">+ Add post</a></div>{filt}'
            f'<p class="muted">{len(posts)} post(s). Titles and dates are editable — open a post to fix them.</p>'
            f'<div class="grid">{cards}</div>')
    return layout("Posts", body, path)


def post_form(conn, p, path, msg=""):
    is_new = p is None
    p = p or {}
    g = lambda k, d="": p[k] if not is_new and p[k] is not None else d  # noqa: E731
    today = date.today().isoformat()
    metric_inputs = "".join(field(k, lab, kind="number", step="any") for k, lab, _ in METRIC_FIELDS)
    new_metrics = f"""<fieldset><legend>{'Metrics (optional)' if is_new else 'Add a metric record'}</legend>
<div class="row">{select("window_days", "Window", [(7, "7 days"), (28, "28 days"), (30, "30 days")], 28)}
{field("window_end", "Window ends", today, "date")}</div>
<p class="muted">Every metric record stores its date window. Leave blank what you don't know.</p>
<div class="row">{metric_inputs}</div></fieldset>"""
    form = f"""<form method="post" action="{'/posts/new' if is_new else f'/posts/{p["id"]}/edit'}" class="stack">
{field("title", "Title (as shown in the app — edit freely)", g("title"), required="")}
<div class="row">{select("platform", "Platform", PLATFORMS, g("platform", "tiktok"))}
{field("post_date", "Post date (approximate is fine)", g("post_date"), "date")}
<label class="check"><input type="checkbox" name="date_approx" value="1" {'checked' if g('date_approx', 1) else ''}> date is approximate</label></div>
{field("hook_text", "Hook text", g("hook_text"))}
<div class="row">{field("topic_tag", "Topic tag", g("topic_tag"), placeholder="e.g. observation")}
{field("story_key", "Story key (links the same story across platforms)", g("story_key"), list_="stories")}</div>
<datalist id="stories">{''.join(f'<option value="{esc(r[0])}">' for r in conn.execute("SELECT DISTINCT story_key FROM posts WHERE story_key IS NOT NULL"))}</datalist>
<div class="row">{select("series_id", "Series", series_options(conn), g("series_id"))}
{field("series_part", "Part #", g("series_part"), "number", min="1")}</div>
{field("flag", "Flag", g("flag"), placeholder="e.g. possible duplicate or failed upload")}
<label>Notes<textarea name="notes" rows="3">{esc(g("notes"))}</textarea></label>
{new_metrics if is_new else ''}
<button class="btn primary">{'Add post' if is_new else 'Save post'}</button></form>"""
    extra = ""
    if not is_new:
        rows = ""
        for m in conn.execute("SELECT * FROM post_metrics WHERE post_id=? ORDER BY window_days, window_end", (p["id"],)):
            inputs = "".join(field(k, lab, m[k], kind="number", step="any") for k, lab, _ in METRIC_FIELDS)
            rows += f"""<form method="post" action="/metrics/{m['id']}/save" class="card stack">
<div class="muted">{esc(window_label(m))} {badge(m['source'])}</div>
<div class="row">{select("window_days", "Window", [(7, "7 days"), (28, "28 days"), (30, "30 days")], m['window_days'])}
{field("window_end", "Window ends", m['window_end'], "date")}</div><div class="row">{inputs}</div>
<div class="row"><button class="btn small primary">Save</button>
<button class="btn small danger" formaction="/metrics/{m['id']}/delete">Delete</button></div></form>"""
        extra = (f'<h2>Metric records</h2>{rows or "<p class=muted>None yet.</p>"}'
                 f'<form method="post" action="/posts/{p["id"]}/metrics" class="stack">{new_metrics}'
                 f'<button class="btn">Add metric record</button></form>'
                 f'<form method="post" action="/posts/{p["id"]}/delete" onsubmit="return confirm(\'Delete this post?\')">'
                 f'<button class="btn danger">Delete post</button></form>')
    body = f'<h1>{"Add post" if is_new else "Edit post"} {"" if is_new else badge(p["source"])}</h1>{msg}{form}{extra}'
    return layout("Post", body, path)


def save_metric(conn, post_id, f):
    vals = {k: num(f.get(k, [""])[0], kind) for k, _, kind in METRIC_FIELDS}
    days = num(f.get("window_days", ["28"])[0]) or 28
    end = txt(f.get("window_end", [""])[0]) or date.today().isoformat()
    start = (date.fromisoformat(end) - timedelta(days=days - 1)).isoformat()
    cols = list(vals)
    conn.execute(f"INSERT INTO post_metrics (post_id, window_start, window_end, window_days, {','.join(cols)}) "
                 f"VALUES (?,?,?,?,{','.join('?' * len(cols))})", [post_id, start, end, days, *vals.values()])


def post_values(f):
    one = lambda k: f.get(k, [""])[0]  # noqa: E731
    plat = one("platform") if one("platform") in PNAME else "tiktok"
    return [txt(one("title")) or "Untitled", plat, txt(one("post_date")), 1 if one("date_approx") else 0,
            txt(one("hook_text")), txt(one("topic_tag")), num(one("series_id")), num(one("series_part")),
            txt(one("story_key")), txt(one("flag")), txt(one("notes"))]


# ------------------------------------------------------------------ snapshots
def page_snapshots(conn, path):
    rows = conn.execute("SELECT * FROM channel_snapshots ORDER BY platform, window_days, window_end DESC").fetchall()
    cards = ""
    for s in rows:
        vals = " · ".join(f"{lab}: <b>{fint(s[k])}</b>" for k, lab, _ in SNAP_FIELDS if s[k] is not None)
        ch = changes(conn, s)
        chs = "".join(f'<span class="{"flag-inline" if v <= DROP_THRESHOLD else ""}">{esc(CHANGE_LABELS.get(k, k))} '
                      f'{v:+.1f}%</span> ' for k, v in ch.items())
        note = '<p class="note">%s</p>' % esc(s["notes"]) if s["notes"] else ""
        cards += (f'<article class="card">{plat_badge(s["platform"])} {badge(s["source"])}'
                  f'<h3><a href="/snapshots/{s["id"]}/edit">{esc(window_label(s))}</a></h3>'
                  f'<div>{vals}</div><div class="muted">vs prior: {chs or "—"}</div>'
                  f'{note}</article>')
    body = ('<div class="titlebar"><h1>Channel stats</h1><a class="btn" href="/snapshots/new">+ Add snapshot</a></div>'
            '<p class="muted">Channel-level numbers copied from each app, one record per platform and date window.</p>'
            f'<div class="grid">{cards}</div>')
    return layout("Channel stats", body, path)


def snapshot_form(s, q, path):
    is_new = s is None
    g = lambda k, d="": s[k] if not is_new and s[k] is not None else d  # noqa: E731
    qv = lambda k, d: q.get(k, [d])[0]  # noqa: E731
    inputs = "".join(field(k, lab, g(k), kind="number", step="any") for k, lab, _ in SNAP_FIELDS)
    delete = "" if is_new else ('<form method="post" action="/snapshots/%d/delete" '
                                'onsubmit="return confirm(\'Delete?\')"><button class="btn danger">Delete</button></form>' % s["id"])
    body = f"""<h1>{'Add' if is_new else 'Edit'} channel snapshot</h1>
<form method="post" class="stack">
<div class="row">{select("platform", "Platform", PLATFORMS, g("platform", qv("platform", "tiktok")))}
{select("window_days", "Window", [(7, "7 days"), (28, "28 days"), (30, "30 days")], g("window_days", qv("window_days", "28")))}
{field("window_end", "Window ends", g("window_end", date.today().isoformat()), "date")}</div>
<div class="row">{inputs}</div>
<label>Notes (e.g. discrepancies between screens)<textarea name="notes" rows="3">{esc(g("notes"))}</textarea></label>
<button class="btn primary">Save</button></form>
{delete}"""
    return layout("Snapshot", body, path)


def save_snapshot(conn, f, sid=None):
    one = lambda k: f.get(k, [""])[0]  # noqa: E731
    days = num(one("window_days")) or 28
    end = txt(one("window_end")) or date.today().isoformat()
    start = (date.fromisoformat(end) - timedelta(days=days - 1)).isoformat()
    plat = one("platform") if one("platform") in PNAME else "tiktok"
    vals = [num(one(k), kind) for k, _, kind in SNAP_FIELDS]
    cols = [k for k, _, _ in SNAP_FIELDS]
    if sid:
        conn.execute("UPDATE channel_snapshots SET platform=?, window_start=?, window_end=?, window_days=?, notes=?, "
                     + ",".join(f"{c}=?" for c in cols) + " WHERE id=?", [plat, start, end, days, txt(one("notes")), *vals, sid])
    else:
        conn.execute("INSERT INTO channel_snapshots (platform, window_start, window_end, window_days, notes, "
                     + ",".join(cols) + ") VALUES (?,?,?,?,?," + ",".join("?" * len(cols)) + ")",
                     [plat, start, end, days, txt(one("notes")), *vals])


# ------------------------------------------------------------------ server
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send(self, body, status=200, ctype="text/html; charset=utf-8"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, to):
        self.send_response(303)
        self.send_header("Location", to)
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        if u.path.startswith("/static/"):
            fp = os.path.normpath(os.path.join(ROOT, u.path.lstrip("/")))
            if fp.startswith(os.path.join(ROOT, "static")) and os.path.isfile(fp):
                with open(fp, "rb") as fh:
                    return self.send(fh.read(), ctype=mimetypes.guess_type(fp)[0] or "application/octet-stream")
            return self.send("not found", 404, "text/plain")
        conn = db.connect()
        try:
            self.send(self.route_get(conn, u.path, parse_qs(u.query)))
        except LookupError:
            self.send(layout("Not found", "<h1>Not found</h1>"), 404)
        finally:
            conn.close()

    def route_get(self, conn, path, q):
        if path == "/":
            return page_dashboard(conn, q, path)
        if path == "/posts":
            return page_posts(conn, q, path)
        if path == "/posts/new":
            return post_form(conn, None, path)
        if path == "/snapshots":
            return page_snapshots(conn, path)
        if path == "/snapshots/new":
            return snapshot_form(None, q, path)
        m = re.fullmatch(r"/posts/(\d+)/edit", path)
        if m:
            p = conn.execute("SELECT * FROM posts WHERE id=?", (m[1],)).fetchone()
            if p:
                return post_form(conn, p, path)
        m = re.fullmatch(r"/snapshots/(\d+)/edit", path)
        if m:
            s = conn.execute("SELECT * FROM channel_snapshots WHERE id=?", (m[1],)).fetchone()
            if s:
                return snapshot_form(s, {}, path)
        raise LookupError

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        f = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
        conn = db.connect()
        try:
            self.redirect(self.route_post(conn, urlparse(self.path).path, f))
            conn.commit()
        except LookupError:
            self.send(layout("Not found", "<h1>Not found</h1>"), 404)
        finally:
            conn.close()

    def route_post(self, conn, path, f):
        if path == "/posts/new":
            vals = post_values(f)
            pid = conn.execute("INSERT INTO posts (title, platform, post_date, date_approx, hook_text, topic_tag, "
                               "series_id, series_part, story_key, flag, notes) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                               vals).lastrowid
            if any(num(f.get(k, [""])[0], kind) is not None for k, _, kind in METRIC_FIELDS):
                save_metric(conn, pid, f)
            return "/posts"
        if path == "/snapshots/new":
            save_snapshot(conn, f)
            return "/snapshots"
        m = re.fullmatch(r"/posts/(\d+)/(edit|delete|metrics)", path)
        if m:
            pid, action = int(m[1]), m[2]
            if action == "edit":
                conn.execute("UPDATE posts SET title=?, platform=?, post_date=?, date_approx=?, hook_text=?, "
                             "topic_tag=?, series_id=?, series_part=?, story_key=?, flag=?, notes=? WHERE id=?",
                             [*post_values(f), pid])
                return "/posts"
            if action == "delete":
                conn.execute("DELETE FROM posts WHERE id=?", (pid,))
                return "/posts"
            save_metric(conn, pid, f)
            return f"/posts/{pid}/edit"
        m = re.fullmatch(r"/metrics/(\d+)/(save|delete)", path)
        if m:
            row = conn.execute("SELECT post_id FROM post_metrics WHERE id=?", (m[1],)).fetchone()
            if not row:
                raise LookupError
            if m[2] == "delete":
                conn.execute("DELETE FROM post_metrics WHERE id=?", (m[1],))
            else:
                days = num(f.get("window_days", ["28"])[0]) or 28
                end = txt(f.get("window_end", [""])[0]) or date.today().isoformat()
                start = (date.fromisoformat(end) - timedelta(days=days - 1)).isoformat()
                cols = [k for k, _, _ in METRIC_FIELDS]
                conn.execute("UPDATE post_metrics SET window_start=?, window_end=?, window_days=?, source='manual', "
                             + ",".join(f"{c}=?" for c in cols) + " WHERE id=?",
                             [start, end, days, *[num(f.get(k, [""])[0], kind) for k, _, kind in METRIC_FIELDS], m[1]])
            return f"/posts/{row['post_id']}/edit"
        m = re.fullmatch(r"/snapshots/(\d+)/(edit|delete)", path)
        if m:
            if m[2] == "delete":
                conn.execute("DELETE FROM channel_snapshots WHERE id=?", (m[1],))
            else:
                save_snapshot(conn, f, int(m[1]))
            return "/snapshots"
        raise LookupError


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    ap.add_argument("--lan", action="store_true", help="listen on all interfaces (phone on same Wi-Fi)")
    a = ap.parse_args()
    conn = db.connect()
    db.init(conn)
    conn.close()
    host = "0.0.0.0" if a.lan else "127.0.0.1"
    print(f"Channel Builder running at http://localhost:{a.port}" + ("  (LAN mode: no login, trusted Wi-Fi only)" if a.lan else ""))
    ThreadingHTTPServer((host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
