"""Conversion checklist (step 5): profile items per platform, checked off with dates."""
import re
from datetime import date

from ui import PLATFORMS, esc, layout, txt

ITEMS = [
    ("bio_line", "Bio line"),
    ("pinned_post", "Pinned post"),
    ("link", "Link"),
    ("profile_photo", "Profile photo"),
    ("featured_content", "Featured content"),
]
ITEM_KEYS = [k for k, _ in ITEMS]
HINTS = {
    "bio_line": "Say who it's for and why to follow: what a first-time viewer gets from you every week.",
    "pinned_post": "Pin your best story post so a first-time viewer lands on it, ideally a post that points to the next part.",
    "link": "One link with one purpose. Decide where you want a viewer to go next.",
    "profile_photo": "Same clear, recognizable photo on all three platforms so people know it's you.",
}
FEATURED_HINTS = {
    "tiktok": "Playlists or series so a viewer can binge a story arc.",
    "youtube": "Featured video or a Shorts playlist for the series.",
    "instagram": "Highlights or pinned Reels for your best stories.",
}


def ensure_rows(conn):
    for p, _ in PLATFORMS:
        for k in ITEM_KEYS:
            conn.execute("INSERT OR IGNORE INTO checklist_items (platform, item_key) VALUES (?, ?)", (p, k))
    conn.commit()


def progress(conn):
    """(done, total) across all platforms, for the dashboard."""
    ensure_rows(conn)
    r = conn.execute("SELECT COALESCE(SUM(done), 0), COUNT(*) FROM checklist_items").fetchone()
    return r[0], r[1]


def page(conn, path):
    ensure_rows(conn)
    rows = {(r["platform"], r["item_key"]): r for r in conn.execute("SELECT * FROM checklist_items")}
    cards = ""
    for p, pname in PLATFORMS:
        n_done = sum(1 for k in ITEM_KEYS if rows[(p, k)]["done"])
        items = ""
        for k, label in ITEMS:
            r = rows[(p, k)]
            hint = FEATURED_HINTS[p] if k == "featured_content" else HINTS[k]
            items += (f'<form method="post" action="/checklist/save" class="citem{" done" if r["done"] else ""}">'
                      f'<input type="hidden" name="platform" value="{p}"><input type="hidden" name="item_key" value="{k}">'
                      f'<label class="check big"><input type="checkbox" name="done" value="1" '
                      f'{"checked" if r["done"] else ""} onchange="this.form.submit()"> <b>{esc(label)}</b></label>'
                      f'<div class="muted">{esc(hint)}</div>'
                      f'<div class="row"><label>Date done<input type="date" name="done_date" value="{esc(r["done_date"])}"></label>'
                      f'<label>Note (what you set it to)<input type="text" name="note" value="{esc(r["note"])}"></label></div>'
                      f'<button class="btn small" name="save" value="1">Save</button></form>')
        cards += (f'<section class="card"><h3>{esc(pname)} <span class="badge{" t-ok" if n_done == len(ITEMS) else ""}">'
                  f'{n_done}/{len(ITEMS)} done</span></h3>{items}</section>')
    body = ("<h1>Conversion checklist</h1><p class=\"muted\">Most viewers are first-timers, so your profile has to do the "
            "convincing: check items off with the date you finished them.</p>"
            f'<div class="grid">{cards}</div>')
    return layout("Checklist", body, path)


def handle_get(conn, path, q):
    return page(conn, path) if path == "/checklist" else None


def handle_post(conn, path, f):
    if path != "/checklist/save":
        return None
    one = lambda k: f.get(k, [""])[0]  # noqa: E731
    p, k = one("platform"), one("item_key")
    if p not in dict(PLATFORMS) or k not in ITEM_KEYS:
        raise LookupError
    ensure_rows(conn)
    done = 1 if one("done") else 0
    d = txt(one("done_date"))
    if d and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
        d = None
    if one("save") and d:
        done = 1  # pressing Save with a date means "done on that date"
    if done and not d:
        d = date.today().isoformat()
    if not done:
        d = None  # unchecking clears the date
    conn.execute("UPDATE checklist_items SET done=?, done_date=?, note=? WHERE platform=? AND item_key=?",
                 (done, d, txt(one("note")), p, k))
    return "/checklist"
