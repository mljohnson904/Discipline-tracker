"""Shared constants and HTML helpers for Channel Builder."""
import html
from datetime import date

PLATFORMS = [("tiktok", "TikTok"), ("youtube", "YouTube Shorts"), ("instagram", "Instagram Reels")]
PNAME = dict(PLATFORMS)
DROP_THRESHOLD = -50.0
WINDOW_CHOICES = [7, 14, 28, 30, 60, 90]  # days; longer windows become useful as the accounts age
WINDOW_OPTIONS = [(d, f"{d} days") for d in WINDOW_CHOICES]

METRIC_FIELDS = [("views", "Views", int), ("viewers", "Viewers", int), ("likes", "Likes", int),
                 ("comments", "Comments", int), ("shares", "Shares", int),
                 ("follows_gained", "Follows gained", int), ("stayed_pct", "Stayed to watch %", float)]
SNAP_FIELDS = [("views", "Views", int), ("viewers", "Viewers", int), ("new_viewers", "New viewers", int),
               ("profile_views", "Profile views", int), ("likes", "Likes", int), ("comments", "Comments", int),
               ("shares", "Shares", int), ("interactions", "Interactions", int),
               ("net_followers", "Net followers", int), ("prior_net_followers", "Prior-window net followers", int),
               ("total_followers", "Total followers", int), ("engaged_views", "Engaged views", int),
               ("watch_hours", "Watch time (hrs)", float), ("stayed_pct", "Stayed to watch %", float)]

# Grouped navigation: bottom tab bar on phones, sidebar on desktop.
# (color group, label, icon, [(href, tab label, icon)], solo?)
NAV_GROUPS = [
    ("plan", "Today", "home", [("/", "Today", "home")], True),
    ("plan", "Plan", "calendar", [("/series", "Series", "layers"), ("/scripts", "Scripts", "file"),
                                  ("/hooks", "Hooks", "bookmark")], False),
    ("grade", "Track", "chart", [("/posts", "Posts", "list"), ("/snapshots", "Channel stats", "activity"),
                                 ("/review", "Weekly review", "target")], False),
    ("manage", "Checklist", "check", [("/checklist", "Checklist", "check")], True),
    ("support", "Data", "database", [("/data", "Data", "database")], True),
]
ICONS = {
    "brand": '<rect x="2" y="6" width="14" height="12" rx="2"/><path d="M22 8l-6 4 6 4z"/>',
    "home": '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/>',
    "calendar": '<rect x="3" y="4" width="18" height="17" rx="2"/><path d="M3 9h18M8 2v4M16 2v4"/>',
    "chart": '<path d="M4 20V10M10 20V4M16 20v-8M22 20H2"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
    "database": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5 9-5z"/><path d="M3 13l9 5 9-5"/>',
    "file": '<path d="M6 3h9l4 4v14H6z"/><path d="M14 3v5h5M9 13h7M9 17h7"/>',
    "bookmark": '<path d="M6 3h12v18l-6-4-6 4z"/>',
    "list": '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
    "activity": '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "moon": '<path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/>',
}


def icon(name, extra=""):
    return f'<svg class="ic {extra}" viewBox="0 0 24 24" aria-hidden="true" focusable="false">{ICONS[name]}</svg>'


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


def _active(path):
    """(group index, tab href) for the current page, longest matching prefix wins."""
    best = (None, None, -1)
    for gi, (_, _, _, tabs, _) in enumerate(NAV_GROUPS):
        for href, _, _ in tabs:
            if path == href or (href != "/" and path.startswith(href + "/")):
                if len(href) > best[2]:
                    best = (gi, href, len(href))
    return best[0], best[1]


def layout(title, body, path="/"):
    active_g, active_href = _active(path)
    grp_key = NAV_GROUPS[active_g][0] if active_g is not None else "plan"
    groups = ""
    for gi, (grp, label, ic, tabs, solo) in enumerate(NAV_GROUPS):
        tabs_html = "".join(
            f'<a class="tab" href="{h}"{" aria-current=\"page\"" if h == active_href else ""}>{icon(i)}'
            f'<span class="tl">{esc(l)}</span></a>' for h, l, i in tabs)
        if solo:
            groups += (f'<div class="grp solo{" has-active" if gi == active_g else ""}" data-grp="{grp}">'
                       f'<div class="grp-tabs">{tabs_html}</div></div>')
        else:
            groups += (f'<div class="grp{" has-active" if gi == active_g else ""}" data-grp="{grp}">'
                       f'<span class="grp-label" aria-hidden="true">{esc(label)}</span>'
                       f'<button class="grp-toggle" type="button" aria-expanded="false" aria-controls="gt-{gi}">'
                       f'{icon(ic)}<span>{esc(label)}</span></button>'
                       f'<div class="grp-tabs" id="gt-{gi}">{tabs_html}</div></div>')
    today = date.today()
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)} · Channel Builder</title>
<script>try{{var t=localStorage.getItem('cb-theme');if(t)document.documentElement.setAttribute('data-theme',t)}}catch(e){{}}</script>
<link rel="stylesheet" href="/static/style.css"><script src="/static/shell.js" defer></script></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="appbar no-print">
<button class="ab-brand" id="aboutBtn" type="button" aria-expanded="false" aria-controls="aboutPop">{icon("brand")}<span><span class="ab-long">Channel </span>Builder</span></button>
<div class="ab-search"><label class="sr-only" for="gsearch">Search posts, hooks, scripts and series</label>{icon("search")}
<input type="text" id="gsearch" placeholder="Search: hook, observation, F-16" autocomplete="off" role="combobox" aria-expanded="false" aria-controls="gresults" aria-autocomplete="list">
<ul id="gresults" role="listbox" aria-label="Search results" hidden></ul></div>
<span class="ab-spacer"></span>
<button class="ico" id="searchBtn" type="button" aria-label="Search">{icon("search")}</button>
<a class="tchip" href="/review">{today.strftime("%b %-d")}<span class="chip-d">Weekly review</span></a>
<button class="ico" id="themeBtn" type="button" aria-label="Switch light or dark mode">{icon("moon", "ic-moon")}{icon("sun", "ic-sun")}</button>
<div id="aboutPop" hidden><p><strong>Channel Builder</strong></p>
<p>For the Second Mission channel on TikTok, YouTube Shorts and Instagram Reels. Everything you enter is saved in a database file on this computer.</p>
<p class="small"><a href="/data">Open Data</a> to export a backup of everything.</p></div>
</header>
<div class="shell"><nav id="nav" aria-label="Sections"><div class="inner">{groups}</div></nav>
<div class="content"><main id="main"><section class="panel active" data-grp="{grp_key}">{body}</section></main></div></div>
</body></html>"""


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
