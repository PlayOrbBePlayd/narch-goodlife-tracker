# NARCH Finals · 40 & Over — GoodLife Tracker

Live tracker for the **40 & Over** division of the NARCH finals, spotlighting
**Oakland Goodlife**. It reads directly from the official NARCH scoreboard (the
DigitalShift API behind narch.com/stats), so the numbers always match the source.

**Live site:** https://playorbbeplayd.github.io/narch-goodlife-tracker/

## How it works

- **`scraper/scrape.py`** — logs into the NARCH stats API for an anonymous
  ticket, pulls the schedule and standings for division `50812` (40 & Over),
  parses them, flags every GoodLife game/row, and writes `docs/data/latest.json`.
  Pure Python standard library — no dependencies.
- **`.github/workflows/scrape.yml`** — a GitHub Action runs the scraper every
  2 hours (and on demand) and commits refreshed data. GitHub Pages redeploys
  automatically on each commit.
- **`docs/index.html`** — a single self-contained page that reads that JSON and
  renders the GoodLife spotlight, standings, and schedule. It also re-fetches
  every 90 seconds while open, so scores update live during games.

Once games start, each matchup flips **Upcoming → Live → Final** on its own, the
standings fill in, and GoodLife's spotlight updates automatically.

## Maintenance

- **Run a refresh now:** Actions tab → *Update NARCH 40+ scores* → **Run workflow**.
- **After the tournament:** Actions tab → *Update NARCH 40+ scores* → **⋯ → Disable workflow**.
- **Spotlight a different team / division:** edit the constants at the top of
  `scraper/scrape.py` (`DIVISION_ID`, `GOODLIFE_TEAM_ID`, `GOODLIFE_NAME_HINT`).
- **Change refresh frequency:** edit the `cron` line in `.github/workflows/scrape.yml`.
