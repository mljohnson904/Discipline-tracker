# Channel Builder

Local-first web app for growing the **Second Mission** short-form channel (TikTok, YouTube Shorts, Instagram Reels).
No platform APIs, no accounts, no dependencies beyond Python 3 (standard library only). Data lives in one SQLite file.

## Run it (Mac or Chromebook)

1. Check Python: `python3 --version` (3.8+; Mac: `xcode-select --install` or python.org; Chromebook: Linux/Crostini terminal, `sudo apt install python3`).
2. From this folder: `python3 app.py`
3. Open <http://localhost:8000>.

First run creates `data/channel.db` and loads the seed data (labeled **seed**). Delete `data/channel.db` to start over.

**On your phone:** run `python3 app.py --lan`, find the computer's Wi-Fi IP (Mac: `ipconfig getifaddr en0`), and open `http://<that-ip>:8000` on the phone. There is no login, so only use `--lan` on a trusted network.

Options: `--port 9000` (or `PORT=9000`), `CHANNEL_DB=/path/to/file.db`.

## Status (building in steps)

- [x] Step 1: Post log, channel stats, dashboard (7/28 day toggle), seed data
- [x] Step 2: CSV import / export (Data page)
- [x] Step 3: Series planner, hook library
- [x] Step 4: Script builder + templates
- [x] Step 5: Conversion checklist
- [x] Step 6: Weekly review
- [x] Step 7 (optional): "Ask Claude" via `ANTHROPIC_API_KEY` env var

## How the numbers work

- Every metric record stores its **date window** (7, 14, 28, 30, 60 or 90 days + end date).
- The dashboard only compares platforms on the **same window**. A platform with no data for the chosen window is greyed out, not mixed in. (Instagram reports 30 days, so it appears only when you add a 7d/28d snapshot; the post tables have an opt-in "28d ≈ 30d" switch.)
- Missing data is shown as `—`, never as 0.
- Engagement rate: TikTok = (likes+comments+shares)/views; Instagram = interactions/views; YouTube shows engaged-view rate (its own metric, labeled separately).
- Profile-view-to-follow = net followers / profile views.
- Any metric down more than 50% vs the prior window is flagged. The prior window comes from a stored earlier snapshot, or the percent change the app reported.
- Seed post dates are approximate (e.g. "~2w old" → relative to Oct 11, 2026). Edit them; titles are truncated as shown in the apps, so edit those too. No topic tags were in the source data, so none were invented.

## CSV import / export (Data page)

- **Export:** `Data` → "Download everything" gives a zip with one CSV per table plus `post_log.csv`. All files open in Excel/Sheets.
- **Import:** `Data` → choose a file (or paste text) → **Preview** → confirm. Nothing is written until you confirm; bad rows are listed and skipped.
- Import format = `post_log.csv` columns: `title, platform, post_date, date_approx, hook_text, topic_tag, series_name, series_part, story_key, flag, notes, window_days, window_end, views, viewers, likes, comments, shares, follows_gained, stayed_pct`. Only `title` and `platform` are required. Common header variants (`date`, `tag`, `series`, `stayed to watch`, …) and `;`/tab separators are accepted.
- A row whose platform + title match an existing post updates it (blank cells never erase data). Re-importing the same window updates that metric record instead of duplicating it.

## Series planner and hook library

- **Series** tab: create a series, add existing posts with a Part number (a post can be set to a different part or removed inline). Missing part numbers are flagged, and the "next-part ideas" list tracks Idea → Drafted → Posted.
- **Hooks** tab: save hooks with comma-separated tags, search by text/tag/notes, and click a tag chip to filter. A hook's performance is shown **per date window** (7d/28d/30d are never added together). A post counts as using a hook if you linked it on the hook's edit page, or if the post's *hook text* matches the hook exactly (case-insensitive). Hooks typed on posts but not yet in the library are offered under "Hooks from your posts not yet saved".

## Script builder

- **Scripts** tab → New script. Sections: Hook (on-screen text + spoken line), Expectation, Reveal (one specific detail), Takeaway (one lesson), Close (direct follow/share ask), Next-part pointer.
- A live meter estimates run time from **spoken** words at 2.5 words/second (150 wpm) and flags anything outside **30–45 s**, a long Reveal/Takeaway, a Close with no follow/share ask, or a missing next-part pointer. On-screen text isn't counted (it appears while you speak the hook).
- **Save as template** copies a script into the Templates list; "Use this template" starts a new script from it. Two starter templates are included (labeled seed).
- From a series' next-part idea, **Write script** starts a script and marks the idea "Drafted".
- "Insert a saved hook" pulls from the Hook library. "Copy script text" copies the whole script for your notes app or teleprompter.

## Conversion checklist

- **Checklist** tab: for each platform, five items (bio line, pinned post, link, profile photo, featured content). Ticking an item stamps today's date (editable). Pressing Save with a date marks it done on that date; unticking clears the date. Each item has a note for what you set it to.
- The dashboard shows overall progress (x/15).

## Weekly review

- **Weekly review** tab: for each platform with a 7-day snapshot, this week vs a baseline, per-7-day, with ⚠ on anything down 50% or more.
- **Baseline** (picked per platform, or force one with the Auto/28d/60d/90d chips):
  1. *Exact*: a stored snapshot (28d preferred) that ends the day before the 7-day window starts.
  2. *Derived*: a longer snapshot (28/60/90d) that contains the week. This week is subtracted and the remainder is averaged per 7 days. This is why a 28d snapshot works even though its dates overlap the 7d one.
  3. Neither: the page says so and links to the form for the missing snapshot. Nothing is guessed.
- As the accounts age you can log 60 or 90 day snapshots; they become usable baselines automatically. Longer windows are also available in the forms, CSV import and the dashboard toggle.
- **3 suggested actions** are rule-based, not AI, and each shows the numbers behind it: views down 50%+, low follows per 1K viewers, low shares per 1K views, a strong story missing on a platform, fewer than 3 posts this week, a low stayed-to-watch hook, unfinished checklist.

## Optional: Ask Claude (hook variations + script feedback)

Off by default. The core app needs nothing but Python; this feature adds one optional package and one environment variable.

```
pip install anthropic
export ANTHROPIC_API_KEY=your-key-here      # Mac/Linux; the app never stores or prints it
python3 app.py
```

With the key set, the script builder shows an **Ask Claude** panel. Pick a target platform and click the button; after a confirmation, it sends your **draft script** plus a text summary of your **post log** (titles, dates, hooks, series, story keys, metrics), **channel snapshots** and **hook library** to the Anthropic API and shows 5 hook variations, feedback against the script structure, and one conversion tweak. Without the key the panel doesn't appear and the endpoint answers 404.

- The key is read from the environment by the Anthropic SDK. It is never hardcoded, saved in the database, rendered in a page, or included in what is sent.
- Model: `claude-opus-5-5` (override with `ASK_CLAUDE_MODEL`, e.g. `claude-sonnet-5-5` for lower cost). Each click costs roughly a few cents. A server-side refusal fallback is enabled for supported models.
- Safety rails: a cap of 20 requests per hour (`ASK_CLAUDE_MAX_PER_HOUR`), and the endpoint rejects requests that don't come from the app's own page (so another website can't trigger paid calls). In `--lan` mode anyone on your Wi-Fi can use the app, including this button, so only use `--lan` on a network you trust.
- To keep data local, simply don't set the variable.
