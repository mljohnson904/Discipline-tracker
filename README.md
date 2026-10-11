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
- [ ] Step 2: CSV import / export
- [ ] Step 3: Series planner, hook library
- [ ] Step 4: Script builder + templates
- [ ] Step 5: Conversion checklist
- [ ] Step 6: Weekly review
- [ ] Step 7 (optional): "Ask Claude" via `ANTHROPIC_API_KEY` env var

## How the numbers work

- Every metric record stores its **date window** (7, 28 or 30 days + end date).
- The dashboard only compares platforms on the **same window**. A platform with no data for the chosen window is greyed out, not mixed in. (Instagram reports 30 days, so it appears only when you add a 7d/28d snapshot; the post tables have an opt-in "28d ≈ 30d" switch.)
- Missing data is shown as `—`, never as 0.
- Engagement rate: TikTok = (likes+comments+shares)/views; Instagram = interactions/views; YouTube shows engaged-view rate (its own metric, labeled separately).
- Profile-view-to-follow = net followers / profile views.
- Any metric down more than 50% vs the prior window is flagged. The prior window comes from a stored earlier snapshot, or the percent change the app reported.
- Seed post dates are approximate (e.g. "~2w old" → relative to Oct 11, 2026). Edit them; titles are truncated as shown in the apps, so edit those too. No topic tags were in the source data, so none were invented.
