"""Shared constants and HTML helpers for Channel Builder."""
import html
from datetime import date

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

NAV = [("/", "Dashboard"), ("/posts", "Posts"), ("/series", "Series"), ("/hooks", "Hooks"),
       ("/snapshots", "Channel stats"), ("/data", "Data")]


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
