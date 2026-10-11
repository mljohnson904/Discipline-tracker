"""CSV import / export for Channel Builder (standard library only)."""
import csv
import io
import zipfile
from datetime import date, datetime, timedelta

PLATFORM_ALIASES = {
    "tiktok": "tiktok", "tik tok": "tiktok", "tt": "tiktok",
    "youtube": "youtube", "youtube shorts": "youtube", "yt": "youtube", "shorts": "youtube",
    "instagram": "instagram", "instagram reels": "instagram", "ig": "instagram", "reels": "instagram",
}
HEADER_ALIASES = {
    "date": "post_date", "posted": "post_date", "posted_date": "post_date", "hook": "hook_text",
    "tag": "topic_tag", "topic": "topic_tag", "series": "series_name", "part": "series_part",
    "story": "story_key", "window": "window_days", "days": "window_days", "window_end_date": "window_end",
    "end_date": "window_end", "follows": "follows_gained", "followers_gained": "follows_gained",
    "stayed": "stayed_pct", "stayed_to_watch": "stayed_pct", "stayed_to_watch_pct": "stayed_pct",
    "stayed_to_watch_%": "stayed_pct", "platform_name": "platform",
}
INT_COLS = ["views", "viewers", "likes", "comments", "shares", "follows_gained"]
POST_COLS = ["title", "platform", "post_date", "date_approx", "hook_text", "topic_tag", "series_name",
             "series_part", "story_key", "flag", "notes"]
METRIC_COLS = ["window_days", "window_end", *INT_COLS, "stayed_pct"]
FLAT_COLS = POST_COLS + METRIC_COLS
EXPORT_TABLES = ["posts", "post_metrics", "channel_snapshots", "audience_snapshots", "series", "series_ideas",
                 "hooks", "hook_posts", "scripts", "checklist_items"]


def _num(v, as_int=False):
    v = (v or "").strip().replace(",", "").replace("%", "")
    if not v or v.lower() in ("n/a", "na", "null", "none", "-", "—"):
        return None
    try:
        f = float(v)
    except ValueError:
        raise ValueError(f"not a number: {v!r}")
    return int(round(f)) if as_int else f


def _date(v):
    v = (v or "").strip()
    if not v:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%b %d %Y", "%B %d %Y"):
        try:
            return datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"unrecognized date: {v!r} (use YYYY-MM-DD)")


def _norm_header(h):
    h = (h or "").strip().lstrip("﻿").lower().replace(" ", "_").replace("-", "_")
    return HEADER_ALIASES.get(h, h)


def parse(text):
    """Parse CSV text into (rows, unknown_headers). Each row is a dict with either clean values or an 'error'."""
    text = text.lstrip("﻿")
    if not text.strip():
        return [], []
    try:
        dialect = csv.Sniffer().sniff(text[:2000], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    header = [_norm_header(h) for h in next(reader, [])]
    unknown = [h for h in header if h and h not in FLAT_COLS]
    rows = []
    for i, cells in enumerate(reader, start=2):
        if not any(c.strip() for c in cells):
            continue
        raw = {h: (cells[j] if j < len(cells) else "") for j, h in enumerate(header) if h in FLAT_COLS}
        out = {"line": i}
        try:
            out["title"] = raw.get("title", "").strip()
            if not out["title"]:
                raise ValueError("title is required")
            p = raw.get("platform", "").strip().lower()
            if p not in PLATFORM_ALIASES:
                raise ValueError(f"platform must be TikTok, YouTube or Instagram (got {p!r})")
            out["platform"] = PLATFORM_ALIASES[p]
            out["post_date"] = _date(raw.get("post_date"))
            da = raw.get("date_approx", "").strip().lower()
            out["date_approx"] = None if not da else int(da in ("1", "true", "yes", "y"))
            for k in ("hook_text", "topic_tag", "series_name", "story_key", "flag", "notes"):
                out[k] = (raw.get(k) or "").strip() or None
            out["series_part"] = _num(raw.get("series_part"), True)
            for k in INT_COLS:
                out[k] = _num(raw.get(k), True)
            out["stayed_pct"] = _num(raw.get("stayed_pct"))
            wd = _num(raw.get("window_days"), True)
            out["has_metrics"] = any(out[k] is not None for k in INT_COLS + ["stayed_pct"])
            if out["has_metrics"] and wd not in (None, 7, 14, 28, 30, 60, 90):
                raise ValueError("window_days must be 7, 14, 28, 30, 60 or 90")
            out["window_days"] = wd or 28
            out["window_end"] = _date(raw.get("window_end")) or date.today().isoformat()
        except ValueError as e:
            out["error"] = str(e)
        rows.append(out)
    return rows, unknown


def _find_post(conn, platform, title):
    return conn.execute("SELECT id FROM posts WHERE platform=? AND lower(title)=lower(?)", (platform, title)).fetchone()


def plan(conn, rows):
    """Label each row: new / update / error, without writing anything. Rows sharing a title count once as 'new'."""
    seen = set()
    for r in rows:
        if "error" in r:
            r["status"] = "error"
            continue
        key = (r["platform"], r["title"].lower())
        if _find_post(conn, *key) or key in seen:
            r["status"] = "update"
        else:
            r["status"] = "new"
            seen.add(key)
    return rows


def apply(conn, rows):
    """Write valid rows. Existing posts (same platform + title) are updated; blank cells never erase data."""
    stats = {"posts_new": 0, "posts_updated": 0, "metrics": 0, "skipped": 0}
    for r in rows:
        if "error" in r:
            stats["skipped"] += 1
            continue
        series_id = None
        if r["series_name"]:
            row = conn.execute("SELECT id FROM series WHERE lower(name)=lower(?)", (r["series_name"],)).fetchone()
            series_id = row[0] if row else conn.execute("INSERT INTO series (name, source) VALUES (?, 'csv')",
                                                       (r["series_name"],)).lastrowid
        found = _find_post(conn, r["platform"], r["title"])
        fields = {"post_date": r["post_date"], "hook_text": r["hook_text"], "topic_tag": r["topic_tag"],
                  "series_id": series_id, "series_part": r["series_part"], "story_key": r["story_key"],
                  "flag": r["flag"], "notes": r["notes"]}
        if r["date_approx"] is not None:
            fields["date_approx"] = r["date_approx"]
        elif r["post_date"]:
            fields["date_approx"] = 0
        if found:
            pid = found[0]
            sets = {k: v for k, v in fields.items() if v is not None}
            if sets:
                conn.execute("UPDATE posts SET " + ",".join(f"{k}=?" for k in sets) + " WHERE id=?",
                             [*sets.values(), pid])
            stats["posts_updated"] += 1
        else:
            cols = ["title", "platform", "source"] + [k for k, v in fields.items() if v is not None]
            vals = [r["title"], r["platform"], "csv"] + [v for v in fields.values() if v is not None]
            pid = conn.execute(f"INSERT INTO posts ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                               vals).lastrowid
            stats["posts_new"] += 1
        if r["has_metrics"]:
            days, end = r["window_days"], r["window_end"]
            start = (date.fromisoformat(end) - timedelta(days=days - 1)).isoformat()
            vals = {k: r[k] for k in INT_COLS + ["stayed_pct"]}
            ex = conn.execute("SELECT id FROM post_metrics WHERE post_id=? AND window_days=? AND window_end=?",
                              (pid, days, end)).fetchone()
            if ex:
                sets = {k: v for k, v in vals.items() if v is not None}
                conn.execute("UPDATE post_metrics SET source='csv'," + ",".join(f"{k}=?" for k in sets) +
                             " WHERE id=?", [*sets.values(), ex[0]])
            else:
                conn.execute("INSERT INTO post_metrics (post_id, window_start, window_end, window_days, source, "
                             + ",".join(vals) + ") VALUES (?,?,?,?,'csv'," + ",".join("?" * len(vals)) + ")",
                             [pid, start, end, days, *vals.values()])
            stats["metrics"] += 1
    return stats


# ------------------------------------------------------------------ export
def _csv_bytes(header, rows):
    buf = io.StringIO(newline="")
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")  # BOM so Excel/Sheets read UTF-8 correctly


def table_csv(conn, table):
    if table not in EXPORT_TABLES:
        raise LookupError(table)
    cur = conn.execute(f"SELECT * FROM {table}")
    return _csv_bytes([d[0] for d in cur.description], cur.fetchall())


def post_log_csv(conn):
    """Flat, re-importable post log: one row per post per metric window (posts with no metrics get one row)."""
    cur = conn.execute(
        "SELECT p.title, p.platform, p.post_date, p.date_approx, p.hook_text, p.topic_tag, s.name, p.series_part, "
        "p.story_key, p.flag, p.notes, m.window_days, m.window_end, m.views, m.viewers, m.likes, m.comments, "
        "m.shares, m.follows_gained, m.stayed_pct FROM posts p LEFT JOIN series s ON s.id = p.series_id "
        "LEFT JOIN post_metrics m ON m.post_id = p.id ORDER BY p.platform, p.post_date, p.id, m.window_days")
    return _csv_bytes(FLAT_COLS, cur.fetchall())


def export_zip(conn):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("post_log.csv", post_log_csv(conn))
        for t in EXPORT_TABLES:
            z.writestr(f"{t}.csv", table_csv(conn, t))
    return buf.getvalue()
