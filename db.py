"""SQLite schema and seed data for Channel Builder."""
import json
import os
import sqlite3

DB_PATH = os.environ.get("CHANNEL_DB", os.path.join(os.path.dirname(__file__), "data", "channel.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS series (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT, source TEXT DEFAULT 'manual'
);
CREATE TABLE IF NOT EXISTS series_ideas (
  id INTEGER PRIMARY KEY, series_id INTEGER NOT NULL REFERENCES series(id) ON DELETE CASCADE,
  idea TEXT NOT NULL, status TEXT DEFAULT 'idea', sort INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY,
  title TEXT NOT NULL,
  platform TEXT NOT NULL CHECK (platform IN ('tiktok','youtube','instagram')),
  post_date TEXT, date_approx INTEGER DEFAULT 0,
  hook_text TEXT, topic_tag TEXT,
  series_id INTEGER REFERENCES series(id) ON DELETE SET NULL, series_part INTEGER,
  story_key TEXT, flag TEXT, notes TEXT,
  source TEXT DEFAULT 'manual', created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS post_metrics (
  id INTEGER PRIMARY KEY,
  post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  window_start TEXT, window_end TEXT NOT NULL, window_days INTEGER NOT NULL,
  views INTEGER, viewers INTEGER, likes INTEGER, comments INTEGER, shares INTEGER,
  follows_gained INTEGER, stayed_pct REAL, note TEXT, source TEXT DEFAULT 'manual'
);

CREATE TABLE IF NOT EXISTS channel_snapshots (
  id INTEGER PRIMARY KEY,
  platform TEXT NOT NULL CHECK (platform IN ('tiktok','youtube','instagram')),
  window_start TEXT, window_end TEXT NOT NULL, window_days INTEGER NOT NULL,
  views INTEGER, viewers INTEGER, new_viewers INTEGER, profile_views INTEGER,
  likes INTEGER, comments INTEGER, shares INTEGER, interactions INTEGER,
  net_followers INTEGER, prior_net_followers INTEGER, total_followers INTEGER,
  engaged_views INTEGER, watch_hours REAL, stayed_pct REAL,
  notes TEXT, extra_json TEXT, source TEXT DEFAULT 'manual'
);

CREATE TABLE IF NOT EXISTS audience_snapshots (
  id INTEGER PRIMARY KEY, platform TEXT NOT NULL, window_days INTEGER, window_end TEXT,
  category TEXT NOT NULL, label TEXT NOT NULL, pct REAL, source TEXT DEFAULT 'manual'
);

CREATE TABLE IF NOT EXISTS hooks (
  id INTEGER PRIMARY KEY, text TEXT NOT NULL, tags TEXT, notes TEXT, source TEXT DEFAULT 'manual'
);
CREATE TABLE IF NOT EXISTS hook_posts (
  hook_id INTEGER NOT NULL REFERENCES hooks(id) ON DELETE CASCADE,
  post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
  PRIMARY KEY (hook_id, post_id)
);

CREATE TABLE IF NOT EXISTS scripts (
  id INTEGER PRIMARY KEY, title TEXT, post_id INTEGER REFERENCES posts(id) ON DELETE SET NULL,
  series_id INTEGER REFERENCES series(id) ON DELETE SET NULL,
  hook_onscreen TEXT, hook_spoken TEXT, expectation TEXT, reveal TEXT, takeaway TEXT,
  close_ask TEXT, next_part_pointer TEXT, est_seconds INTEGER, is_template INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS checklist_items (
  id INTEGER PRIMARY KEY, platform TEXT NOT NULL, item_key TEXT NOT NULL,
  done INTEGER DEFAULT 0, done_date TEXT, note TEXT, UNIQUE (platform, item_key)
);
"""


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init(conn):
    conn.executescript(SCHEMA)
    if not conn.execute("SELECT 1 FROM meta WHERE key='seeded'").fetchone():
        load_seed(conn)
        conn.execute("INSERT INTO meta VALUES ('seeded', '1')")
    conn.commit()


# ---------------------------------------------------------------- seed data
# Real numbers captured Oct 10-11, 2026. Anything not listed is None (never invented).
# Post dates are approximate: "~2w old" etc. are converted relative to Oct 11, 2026.
D_19H, D_4D, D_1W, D_2W, D_1MO = "2026-10-10", "2026-10-07", "2026-10-04", "2026-09-27", "2026-09-11"

W = {  # window label -> (start, end, days)
    "tt7": ("2026-10-03", "2026-10-09", 7),
    "tt28": ("2026-09-13", "2026-10-10", 28),
    "yt28": ("2026-09-13", "2026-10-10", 28),
    "ig30": ("2026-09-11", "2026-10-10", 30),
}

STORY_NERVOUS = "first observation (nervous)"
STORY_OVER = "first observation (over)"
STORY_CONF = "post-observation conference"
STORY_F16 = "F-16 / Air Force"

# (platform, title, date, story, hook_text, flag, [(window, views, likes, comments, stayed_pct)])
POSTS = [
    ("tiktok", "I thought pacing might come up in my post-observation conference...", D_2W, STORY_CONF, None, None,
     [("tt28", 4629, None, None, None), ("tt7", 262, None, None, None)]),
    ("tiktok", "My first formal classroom observation is today, and someh...", D_1MO, STORY_NERVOUS,
     "More nervous than an Air Force evaluation", None, [("tt28", 2247, None, None, None), ("tt7", 235, None, None, None)]),
    ("tiktok", "My first formal classroom observation is officially over. Ad...", D_1MO, STORY_OVER, None, None,
     [("tt28", 2223, None, None, None)]),
    ("tiktok", "First-year teacher milestone today: my first post-observation confer...", D_2W, STORY_CONF, None, None,
     [("tt28", 1174, None, None, None), ("tt7", 233, None, None, None)]),
    ("tiktok", "A half-day for students does not mean a half-day for teachers. To...", None, None, None, None,
     [("tt28", 1110, None, None, None)]),
    ("tiktok", "One thing I'm learning in my first year teaching: being prepared do...", D_1W, None, None, None,
     [("tt7", 347, None, None, None)]),
    ("tiktok", "15 years as an F-16 crew chief. This isn't the part I thought I'd miss.", D_4D, STORY_F16, None, None,
     [("tt7", 316, None, None, None)]),

    ("youtube", "15 years as an F-16 crew chief -> fir...", None, STORY_F16, None, None, [("yt28", 1100, None, None, 52.9)]),
    ("youtube", "Students Leave Early - Teachers Stil...", None, None, None, None, [("yt28", 1000, None, None, 51.3)]),
    ("youtube", "My First Teacher Observation Is Ove...", None, STORY_OVER, None, None, [("yt28", 1000, None, None, 57.2)]),
    ("youtube", "I Gave Clear Instructions - My Stu...", None, None, None, None, [("yt28", None, None, None, 59.0)]),
    ("youtube", "15 Years in the Air Force Didn't Pre...", None, STORY_F16, None, None, [("yt28", None, None, None, 56.3)]),
    ("youtube", "I Did Not Student Teach Before Get...", None, None, None, None, [("yt28", None, None, None, 53.5)]),
    ("youtube", "What My Evaluator Told Me After M...", None, STORY_CONF, "What my evaluator actually told me...", None,
     [("yt28", None, None, None, 51.1)]),
    ("youtube", "My Best Lesson Wasn't in the Less...", None, None, None, None, [("yt28", None, None, None, 45.5)]),

    ("instagram", "Everyone asks what I miss....", D_19H, STORY_F16, "Everyone asks what I miss...", None,
     [("ig30", 157, 0, 0, None)]),
    ("instagram", "15 years as an F-16 crew ch...", D_4D, STORY_F16, None, None, [("ig30", 270, 3, 0, None)]),
    ("instagram", "I came into teaching with a...", D_1W, None, None, None, [("ig30", 142, 0, 0, None)]),
    ("instagram", "The best lesson I've had thi...", D_1W, None, None, None, [("ig30", 163, 2, 0, None)]),
    ("instagram", "My best lesson wasn't planned", D_1W, None, None, "possible duplicate or failed upload",
     [("ig30", 0, None, None, None)]),
    ("instagram", "I took both of my teacher c...", D_2W, None, None, None, [("ig30", 145, 0, 1, None)]),
    ("instagram", "Teacher certification tests", D_2W, None, None, "possible duplicate or failed upload",
     [("ig30", 0, None, None, None)]),
    ("instagram", "The results from my first po...", D_2W, STORY_CONF, None, None, [("ig30", 395, 2, 0, None)]),
]

SNAPSHOTS = [
    dict(platform="tiktok", w="tt7", views=1700, viewers=1300, new_viewers=967, profile_views=63, likes=57,
         comments=5, shares=0, net_followers=1, prior_net_followers=6, total_followers=114,
         extra=dict(changes={"views": -74.5})),
    dict(platform="tiktok", w="tt28", views=16800, viewers=11800, new_viewers=11300, profile_views=535, likes=503,
         comments=61, shares=4, net_followers=27, total_followers=114, extra=dict(changes={"views": 140.7})),
    dict(platform="youtube", w="yt28", views=8600, engaged_views=4400, watch_hours=21.8, net_followers=6,
         stayed_pct=51.3,
         notes="Discrepancy: YouTube showed +6 subscribers on one screen and +7 on another. Stored 6.",
         extra=dict(changes={"engaged_views": 9, "watch_hours": -7}, swiped_away_pct=48.7,
                    monthly_audience=4100, monthly_new_pct=99.2, monthly_casual=34, monthly_regular=0,
                    monthly_audience_peak=7200, monthly_audience_peak_note="peaked near 7,200 around Sep 26")),
    dict(platform="instagram", w="ig30", views=2021, viewers=1615, interactions=9,
         extra=dict(follower_views_pct=0, non_follower_views_pct=100, reels_views_approx=2000, feed_post_views=0),
         notes="Net followers unavailable from Instagram."),
]

AUDIENCE = {
    "gender": [("Male", 75.3), ("Female", 24.7)],
    "country": [("United States", 78.7), ("United Kingdom", 1.1), ("Canada", 0.8)],
    "age": [("13-17", 3.0), ("18-24", 1.8), ("25-34", 26.7), ("35-44", 27.8), ("45-54", 17.6), ("55-64", 13.3),
            ("65+", 9.7)],
    "device": [("Mobile", 79.7), ("Computer", 11.0), ("Tablet", 7.5), ("TV", 1.8)],
    "subtitles": [("No subtitles", 87.9)],
}

HOOKS = [
    ("What my evaluator actually told me...", "observation,evaluator", "What My Evaluator Told Me After M..."),
    ("More nervous than an Air Force evaluation", "observation,air-force,nervous",
     "My first formal classroom observation is today, and someh..."),
    ("Everyone asks what I miss...", "air-force,veteran", "Everyone asks what I miss...."),
]


def load_seed(conn):
    sid = conn.execute("INSERT INTO series (name, description, source) VALUES (?,?,'seed')",
                       ("Observation Arc", "First observation through the post-observation conference.")).lastrowid
    part_of = {STORY_NERVOUS: 1, STORY_OVER: 2, STORY_CONF: 3}

    post_ids = {}
    for platform, title, date, story, hook, flag, rows in POSTS:
        part = part_of.get(story)
        pid = conn.execute(
            "INSERT INTO posts (title, platform, post_date, date_approx, hook_text, story_key, series_id,"
            " series_part, flag, source) VALUES (?,?,?,?,?,?,?,?,?,'seed')",
            (title, platform, date, 1 if date else 0, hook, story, sid if part else None, part, flag)).lastrowid
        post_ids[(platform, title)] = pid
        for wk, views, likes, comments, stayed in rows:
            s, e, d = W[wk]
            conn.execute(
                "INSERT INTO post_metrics (post_id, window_start, window_end, window_days, views, likes, comments,"
                " stayed_pct, source) VALUES (?,?,?,?,?,?,?,?,'seed')", (pid, s, e, d, views, likes, comments, stayed))

    cols = ["views", "viewers", "new_viewers", "profile_views", "likes", "comments", "shares", "interactions",
            "net_followers", "prior_net_followers", "total_followers", "engaged_views", "watch_hours", "stayed_pct",
            "notes"]
    for s in SNAPSHOTS:
        ws, we, wd = W[s["w"]]
        vals = [s.get(c) for c in cols]
        conn.execute(
            f"INSERT INTO channel_snapshots (platform, window_start, window_end, window_days, {','.join(cols)},"
            " extra_json, source) VALUES (?,?,?,?," + ",".join("?" * len(cols)) + ",?, 'seed')",
            [s["platform"], ws, we, wd, *vals, json.dumps(s.get("extra") or {})])

    for cat, items in AUDIENCE.items():
        for label, pct in items:
            conn.execute("INSERT INTO audience_snapshots (platform, window_days, window_end, category, label, pct,"
                         " source) VALUES ('youtube', 28, '2026-10-10', ?, ?, ?, 'seed')", (cat, label, pct))

    for text, tags, title in HOOKS:
        hid = conn.execute("INSERT INTO hooks (text, tags, source) VALUES (?,?,'seed')", (text, tags)).lastrowid
        for (plat, t), pid in post_ids.items():
            if t == title:
                conn.execute("INSERT OR IGNORE INTO hook_posts VALUES (?,?)", (hid, pid))
