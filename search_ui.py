"""Global search across posts, hooks, scripts, series and series ideas (feeds the app bar search box)."""
import json

from ui import PNAME

LIMIT = 14
SCRIPT_FIELDS = ["title", "hook_onscreen", "hook_spoken", "expectation", "reveal", "takeaway", "close_ask",
                 "next_part_pointer"]


def _like(term):
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _snippet(values, term):
    """First field containing the term, trimmed to a readable window around the match."""
    low = term.lower()
    for v in values:
        if v and low in v.lower():
            i = v.lower().index(low)
            a = max(0, i - 40)
            return ("…" if a else "") + v[a:i + len(term) + 60] + ("…" if i + len(term) + 60 < len(v) else "")
    return ""


def search(conn, term):
    term = term.strip()
    if len(term) < 2:
        return []
    p, out = _like(term), []

    def run(sql, fields, tab, title_key, href, extra=""):
        n = len(fields)
        cond = " OR ".join(f"{f} LIKE ? ESCAPE '\\'" for f in fields)
        for r in conn.execute(f"SELECT * FROM {sql} WHERE {cond} ORDER BY id DESC LIMIT {LIMIT}", [p] * n):
            title = (r[title_key] or "Untitled")[:90]
            snip = _snippet([r[f] for f in fields if f != title_key], term)
            out.append({"title": title, "tab": tab + (f" · {PNAME[r['platform']].split()[0]}" if "platform" in r.keys() else ""),
                        "snip": snip, "href": href(r)})

    run("posts", ["title", "hook_text", "topic_tag", "story_key", "notes", "flag"], "Post", "title",
        lambda r: f"/posts/{r['id']}/edit")
    run("hooks", ["text", "tags", "notes"], "Hook", "text", lambda r: f"/hooks/{r['id']}/edit")
    run("scripts", SCRIPT_FIELDS, "Script", "title", lambda r: f"/scripts/{r['id']}/edit")
    run("series", ["name", "description"], "Series", "name", lambda r: f"/series/{r['id']}")
    for r in conn.execute("SELECT i.id, i.series_id, i.idea, s.name FROM series_ideas i JOIN series s ON s.id = i.series_id "
                          "WHERE i.idea LIKE ? ESCAPE '\\' LIMIT ?", (p, LIMIT)):
        out.append({"title": r["idea"][:90], "tab": "Idea · " + r["name"], "snip": "", "href": f"/series/{r['series_id']}"})
    # exact-ish title matches first
    low = term.lower()
    out.sort(key=lambda x: (low not in x["title"].lower()))
    return out[:LIMIT]


def handle(conn, q):
    return json.dumps({"results": search(conn, q.get("q", [""])[0])}).encode("utf-8")
