"""Weekly review (step 6): last 7 days vs a baseline, plus 3 rule-based next actions.

Baseline logic (per platform, from the 7-day snapshot):
  * exact   - a stored snapshot (28d by default) that ends the day before the 7-day window starts
  * derived - a longer snapshot (28/60/90d...) that CONTAINS the 7-day window; this week is subtracted
              and the remainder is scaled to a per-7-day rate
Nothing is guessed: with no usable baseline the page says so and links to the form for the missing snapshot.
"""
from datetime import date, timedelta
from urllib.parse import quote

from ui import DROP_THRESHOLD, PLATFORMS, PNAME, esc, fdate, fint, fpct, layout, window_label

METRICS = [("views", "Views", 0), ("viewers", "Viewers", 0), ("engaged_views", "Engaged views", 0),
           ("profile_views", "Profile views", 0), ("likes", "Likes", 0), ("comments", "Comments", 0),
           ("shares", "Shares", 0), ("interactions", "Interactions", 0), ("net_followers", "Net followers", 0),
           ("watch_hours", "Watch time (hrs)", 1)]
AUTO_PREFERENCE = [28, 60, 90, 30, 14]   # closest to the "prior 28 days" idea first, then longer = steadier


def pct_change(now, base):
    if now is None or base is None or base <= 0:
        return None
    return (now - base) / base * 100


def derived(platform, v):
    """Rates that make platforms comparable. v maps metric name -> value (totals or per-7-day rates)."""
    g = lambda k: v.get(k)  # noqa: E731
    views = g("views")
    if platform == "instagram":
        eng = g("interactions")
    elif platform == "youtube":
        eng = g("engaged_views")
    else:
        eng = None if g("likes") is None else (g("likes") or 0) + (g("comments") or 0) + (g("shares") or 0)
    ok = lambda a, b: a is not None and b  # noqa: E731
    return {
        "eng": eng / views * 100 if ok(eng, views) else None,
        "shares1k": g("shares") / views * 1000 if ok(g("shares"), views) else None,
        "ptf": g("net_followers") / g("profile_views") * 100 if ok(g("net_followers"), g("profile_views")) else None,
        "fol1k": g("net_followers") / g("viewers") * 1000 if ok(g("net_followers"), g("viewers")) else None,
    }


def find_baseline(conn, s7, base="auto"):
    """Return dict(kind, snap, days, per7) or None."""
    rows = conn.execute("SELECT * FROM channel_snapshots WHERE platform=? AND id!=? AND window_days>=14",
                        (s7["platform"], s7["id"])).fetchall()
    if base != "auto":
        rows = [r for r in rows if r["window_days"] == base]
    order = lambda r: AUTO_PREFERENCE.index(r["window_days"]) if r["window_days"] in AUTO_PREFERENCE else 99  # noqa: E731
    prev_end = (date.fromisoformat(s7["window_start"]) - timedelta(days=1)).isoformat() if s7["window_start"] else None
    exact = sorted([r for r in rows if prev_end and r["window_end"] == prev_end], key=order)
    if exact:
        w = exact[0]
        return {"kind": "exact", "snap": w, "days": w["window_days"],
                "per7": {k: (w[k] / w["window_days"] * 7 if w[k] is not None else None) for k, _, _ in METRICS}}
    inside = sorted([r for r in rows if s7["window_start"] and r["window_start"] and r["window_start"] <= s7["window_start"]
                     and r["window_end"] >= s7["window_end"] and r["window_days"] - 7 >= 7], key=order)
    if inside:
        w = inside[0]
        rest = w["window_days"] - 7
        per7 = {}
        for k, _, _ in METRICS:
            a, b = w[k], s7[k]
            per7[k] = (a - b) / rest * 7 if a is not None and b is not None and a >= b else None
        return {"kind": "derived", "snap": w, "days": rest, "per7": per7}
    return None


def baseline_label(b):
    w = b["snap"]
    if b["kind"] == "exact":
        return f"the prior {w['window_days']} days ({window_label(w)}), averaged per 7 days"
    return (f"the earlier {b['days']} days: your {w['window_days']}d snapshot ({window_label(w)}) minus this week, "
            f"averaged per 7 days")


# ------------------------------------------------------------------ analysis
def platform_summary(conn, platform, base):
    s7 = conn.execute("SELECT * FROM channel_snapshots WHERE platform=? AND window_days=7 ORDER BY window_end DESC",
                      (platform,)).fetchone()
    if not s7:
        return {"platform": platform, "s7": None}
    b = find_baseline(conn, s7, base)
    week = {k: s7[k] for k, _, _ in METRICS}
    rows = []
    for k, label, dec in METRICS:
        if week[k] is None:
            continue
        bv = b["per7"].get(k) if b else None
        rows.append({"key": k, "label": label, "dec": dec, "week": week[k], "base": bv, "chg": pct_change(week[k], bv)})
    return {"platform": platform, "s7": s7, "baseline": b, "rows": rows, "week": week,
            "week_rates": derived(platform, week), "base_rates": derived(platform, b["per7"]) if b else None,
            "chg": {r["key"]: r["chg"] for r in rows}}


def best_story(conn):
    """Stories ranked by views (each post counted once, using its longest-window record). Platforms come from ALL
    posts with that story key, including posts that have no view count yet."""
    best = {}
    for r in conn.execute("SELECT p.id, m.views, m.window_days FROM posts p JOIN post_metrics m ON m.post_id = p.id "
                          "WHERE m.views IS NOT NULL"):
        cur = best.get(r["id"])
        if not cur or r["window_days"] > cur["window_days"]:
            best[r["id"]] = r
    stories = {}
    for r in conn.execute("SELECT id, story_key, platform FROM posts WHERE story_key IS NOT NULL"):
        s = stories.setdefault(r["story_key"], {"views": 0, "platforms": set()})
        s["platforms"].add(r["platform"])
        if r["id"] in best:
            s["views"] += best[r["id"]]["views"]
    return sorted(((k, v) for k, v in stories.items() if v["views"] > 0), key=lambda kv: -kv[1]["views"])


def script_link(conn, story=None):
    """Link to start a script, preferring an open next-part idea from the story's series."""
    row = None
    if story:
        row = conn.execute("SELECT i.id, i.series_id, i.idea FROM series_ideas i JOIN posts p ON p.series_id = i.series_id "
                           "WHERE p.story_key = ? AND i.status = 'idea' ORDER BY i.id LIMIT 1", (story,)).fetchone()
    if not row:
        row = conn.execute("SELECT id, series_id, idea FROM series_ideas WHERE status='idea' ORDER BY id LIMIT 1").fetchone()
    if row:
        return f"/scripts/new?series={row['series_id']}&idea={row['id']}", f'Write a script: "{row["idea"]}"'
    return "/scripts/new", "Start a new script"


def suggest(conn, sums, today):
    """Rule-based actions, each with the evidence behind it. Returns list of (priority, title, why, href, link_text)."""
    acts = []
    stories = best_story(conn)
    top_story = stories[0][0] if stories else None
    for s in sums:
        if not s["s7"]:
            continue
        p, name, w = s["platform"], PNAME[s["platform"]], s["week"]
        chg = s["chg"].get("views")
        if chg is not None and chg <= DROP_THRESHOLD:
            href, text = script_link(conn, top_story)
            why = (f"{name} views were {fint(w['views'])} this week vs about {fint(s['baseline']['per7']['views'])} per week "
                   f"in the baseline ({chg:+.0f}%).")
            if top_story:
                why += f" Your strongest story so far is \"{top_story}\" ({fint(stories[0][1]['views'])} views)."
            acts.append((100, f"Rebuild momentum on {name}: post the next part of your best story", why, href, text))
        r = s["week_rates"]
        if r["fol1k"] is not None and r["fol1k"] < 5 and w.get("viewers"):
            new = f" About {s['s7']['new_viewers'] / w['viewers'] * 100:.0f}% of viewers were new." \
                if s["s7"]["new_viewers"] is not None else ""
            acts.append((90, f"Fix follow conversion on {name}: add a direct follow ask and a next-part pointer to every Close",
                         f"{w['net_followers']:+d} net followers from {fint(w['viewers'])} viewers this week "
                         f"({r['fol1k']:.1f} per 1K viewers).{new} Give first-time viewers a reason to follow.",
                         "/scripts", "Open the script builder"))
        if r["shares1k"] is not None and r["shares1k"] < 1:
            acts.append((80, f"Make your next {name} post shareable: end the Takeaway with \"send this to a first-year teacher\"",
                         f"{fint(w['shares'])} shares on {fint(w['views'])} views this week "
                         f"({r['shares1k']:.2f} per 1K views).", "/scripts", "Open the script builder"))
    for story, info in stories:
        missing = [PNAME[p] for p, _ in PLATFORMS if p not in info["platforms"]]
        if missing:
            have = ", ".join(PNAME[p] for p in sorted(info["platforms"]))
            acts.append((70, f"Repurpose \"{story}\" to {' and '.join(missing)}",
                         f"It has {fint(info['views'])} views on {have} only. Same story, new platform audience "
                         f"(story keys link them).", "/posts/new", "Add the post"))
            break
    week_ago = (today - timedelta(days=6)).isoformat()
    dated = conn.execute("SELECT COUNT(*) FROM posts WHERE post_date >= ? AND post_date <= ?",
                         (week_ago, today.isoformat())).fetchone()[0]
    any_dated = conn.execute("SELECT COUNT(*) FROM posts WHERE post_date IS NOT NULL").fetchone()[0]
    if any_dated and dated < 3:
        acts.append((60, "Post at least 3 times this week", f"Only {dated} post(s) are dated in the last 7 days "
                     "(dates may be approximate).", "/posts/new", "Log a post"))
    low = conn.execute("SELECT p.id, p.title, p.hook_text, m.stayed_pct FROM post_metrics m JOIN posts p ON p.id = m.post_id "
                       "WHERE m.stayed_pct IS NOT NULL ORDER BY m.stayed_pct LIMIT 1").fetchone()
    if low and low["stayed_pct"] < 50:
        acts.append((50, f'Rewrite the hook on "{low["title"]}"', f"Only {low['stayed_pct']:.1f}% stayed to watch, "
                     "your lowest. Try a hook from your library that held viewers better.",
                     "/hooks", "Open the hook library"))
    item = conn.execute("SELECT platform, item_key FROM checklist_items WHERE done=0 ORDER BY id LIMIT 1").fetchone()
    done = conn.execute("SELECT COALESCE(SUM(done),0), COUNT(*) FROM checklist_items").fetchone()
    if done[1] == 0 or done[0] < done[1]:
        acts.append((40, "Finish the conversion checklist",
                     "Nearly every viewer is a first-timer, so your profile has to convert them."
                     + (f" Next up: {PNAME[item['platform']]} {item['item_key'].replace('_', ' ')}." if item else ""),
                     "/checklist", "Open the checklist"))
    href, text = script_link(conn, top_story)
    acts.append((30, "Write the next part of a series", "Keeps viewers coming back for the next part.", href, text))
    acts.sort(key=lambda a: -a[0])
    return acts


# ------------------------------------------------------------------ page
def _num(v, dec):
    if v is None:
        return "—"
    return f"{v:,.{dec if abs(v) >= 10 else max(dec, 1)}f}" if v != int(v) or dec else f"{v:,.0f}"


def _table(s):
    b = s["baseline"]
    head = ("<div class='scroll'><table><thead><tr><th></th><th>This week</th><th>Baseline / 7d</th><th>Change</th>"
            "</tr></thead><tbody>")
    body = ""
    for r in s["rows"]:
        c = r["chg"]
        cls = ' class="flag-inline"' if c is not None and c <= DROP_THRESHOLD else ""
        body += (f'<tr><td>{esc(r["label"])}</td><td>{_num(r["week"], r["dec"])}</td>'
                 f'<td>{_num(r["base"], max(r["dec"], 0)) if b else "—"}</td><td{cls}>'
                 f'{"—" if c is None else f"{c:+.0f}%"}{" ⚠" if cls else ""}</td></tr>')
    wr, br = s["week_rates"], s["base_rates"]
    for label, key, fmt in (("Engagement rate", "eng", lambda x: fpct(x, 2)), ("Shares / 1K views", "shares1k",
                            lambda x: "—" if x is None else f"{x:.2f}"), ("Profile view → follow", "ptf", fpct),
                            ("Net follows / 1K viewers", "fol1k", lambda x: "—" if x is None else f"{x:.1f}")):
        if wr[key] is None and (not br or br[key] is None):
            continue
        body += (f'<tr class="rate"><td>{label}</td><td>{fmt(wr[key])}</td><td>{fmt(br[key]) if br else "—"}</td><td></td></tr>')
    return head + body + "</tbody></table></div>"


def page(conn, q, path):
    today = date.today()
    base_q = q.get("base", ["auto"])[0]
    base = int(base_q) if base_q.isdigit() else "auto"
    sums = [platform_summary(conn, p, base) for p, _ in PLATFORMS]
    avail = sorted({r[0] for r in conn.execute("SELECT DISTINCT window_days FROM channel_snapshots WHERE window_days>=14")})
    chips = '<a class="chip%s" href="/review">Auto</a>' % (" on" if base == "auto" else "") + "".join(
        f'<a class="chip{" on" if base == d else ""}" href="/review?base={d}">{d}d</a>' for d in avail)

    acts = suggest(conn, sums, today)
    top = acts[:3]
    act_html = "".join(f'<li class="act"><b>{esc(t)}</b><p>{esc(why)}</p><a class="btn small" href="{esc(h)}">{esc(lt)}</a></li>'
                       for _, t, why, h, lt in top)
    more = "".join(f"<li>{esc(t)}</li>" for _, t, *_ in acts[3:])

    cards, needs = "", []
    for s in sums:
        name = PNAME[s["platform"]]
        if not s["s7"]:
            needs.append(f'<li>No 7-day snapshot for {esc(name)}. <a href="/snapshots/new?platform={s["platform"]}&window_days=7">'
                         f'Add one</a> to include it.</li>')
            continue
        s7 = s["s7"]
        age = (today - date.fromisoformat(s7["window_end"])).days
        stale = f'<p class="note">This snapshot ended {age} days ago ({fdate(s7["window_end"])}). Log a newer one for a current read.</p>' if age > 8 else ""
        if s["baseline"]:
            note = f'<p class="muted">Baseline = {esc(baseline_label(s["baseline"]))}.</p>'
        else:
            note = '<p class="muted">No baseline yet, so there are no comparisons.</p>'
            end = (date.fromisoformat(s7["window_start"]) - timedelta(days=1)).isoformat() if s7["window_start"] else ""
            needs.append(f'<li>{esc(name)} needs a baseline: add a 28d snapshot ending {fdate(end)} (exact), or any 28/60/90d '
                         f'snapshot that includes this week (I subtract this week). '
                         f'<a href="/snapshots/new?platform={s["platform"]}&window_days=28&window_end={quote(end)}">Add it</a>.</li>')
        cards += (f'<section class="card"><h3>{esc(name)} <span class="muted">{esc(window_label(s7))}</span></h3>{stale}{note}'
                  f'{_table(s)}</section>')

    posts = conn.execute("SELECT p.id, p.title, p.platform, m.views, m.likes, m.stayed_pct FROM post_metrics m "
                         "JOIN posts p ON p.id = m.post_id WHERE m.window_days = 7 AND m.views IS NOT NULL "
                         "ORDER BY m.views DESC LIMIT 5").fetchall()
    plist = "".join(f'<li><a href="/posts/{p["id"]}/edit">{esc(p["title"])}</a> <span class="muted">'
                    f'{esc(PNAME[p["platform"]])} · <b>{fint(p["views"])}</b> views (7d)</span></li>' for p in posts)

    body = f"""<h1>Weekly review</h1>
<p class="muted">Last 7 days vs a baseline. Baselines come from the snapshots you've logged. If you log a 60 or 90 day
snapshot later, it can serve as the baseline too.</p>
<p>Baseline: {chips}</p>
<h2>3 suggested next actions</h2><ol class="acts">{act_html}</ol>
{f'<details><summary>Also noticed ({len(acts) - 3})</summary><ul>{more}</ul></details>' if more else ''}
<h2>This week vs baseline</h2>
<div class="grid">{cards or '<p class="muted">No 7-day snapshots yet.</p>'}</div>
{f'<h2>Data that would sharpen this</h2><ul>{"".join(needs)}</ul>' if needs else ''}
<h2>This week's posts <small>7d records</small></h2><ul>{plist or '<li class="muted">No 7-day post records.</li>'}</ul>
<p class="muted">Suggestions are rule-based (not AI) and show the numbers behind them. Changes of {abs(DROP_THRESHOLD):.0f}% or more
down are flagged ⚠.</p>"""
    return layout("Weekly review", body, path)


def handle_get(conn, path, q):
    return page(conn, q, path) if path == "/review" else None
