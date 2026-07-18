# Oakland GoodLife · NARCH 40 & Over tracker

A live results tracker for the **40 & Over** division of the NARCH finals, built around
**Oakland GoodLife**. It reads straight from the official NARCH scoreboard, so the numbers
always match the source.

**Live site:** https://playorbbeplayd.github.io/narch-goodlife-tracker/

## What it does

- **GoodLife spotlight** — record, points, goals for/against, division rank, and the next game.
- **Full standings** for all six teams, with GoodLife highlighted.
- **Schedule & results** grouped by day: completed games show final scores with the winner
  highlighted, upcoming games show start time and rink.
- **Live refresh** — the page pulls current scores the moment it opens, again every
  60 seconds, whenever you return to the tab, and instantly when you tap **Refresh**.
- **🎉 Confetti on a GoodLife win** — fires once per win, in team colors.
- **GoodLife branding** — team colors throughout, mascot in the header and as the tab icon.

## How it works

There is no server and no database. The whole app is one self-contained `docs/index.html`
served by GitHub Pages.

The NARCH scoreboard is powered by a third-party stats backend (DigitalShift). The page
reproduces the same calls the official site makes, directly from the visitor's browser:

1. `POST /login` with a public `client_service_id` → returns a short-lived visitor ticket.
2. `GET /partials/stats/schedule/table?division_id=50812&all=1` → schedule + results.
3. `GET /partials/stats/standings/table?division_id=50812` → standings.
4. The responses embed the real data as HTML-encoded JSON and an HTML table; the page
   unpacks them, keeps the 40+ division, and flags every GoodLife row and game.

Because this runs client-side, viewers get true real-time scores on demand — no waiting on
a scheduled job.

### ⚠️ The `all=1` gotcha

`schedule/table` returns **only upcoming games** by default. Once a game finishes it
disappears from the feed entirely. **`&all=1` is required** to get the full schedule
including `"Final"` games. Without it the results section renders empty and win detection
never fires. Known status values: `"Not Started"`, `"Final"`.

### Backstop

`.github/workflows/scrape.yml` runs `scraper/scrape.py` every 2 hours (pure Python
standard library, no dependencies), writing `docs/data/latest.json`. The page falls back to
that file only if the live call fails, so it never renders empty.

## Layout

```
docs/index.html        the entire app (logo embedded as a data URI)
docs/data/latest.json  fallback data, refreshed by the Action
scraper/scrape.py      the same scrape, server-side, for the backstop
.github/workflows/     the 2-hour cron
```

## Maintenance

- **Refresh the backup now:** Actions → *Update NARCH 40+ scores* → **Run workflow**.
- **After the tournament:** Actions → *Update NARCH 40+ scores* → **⋯ → Disable workflow**.
- **Different team or division:** edit the constants at the top of the `<script>` in
  `docs/index.html` (`DIV`, `GL_ID`) and the matching ones in `scraper/scrape.py`.
- **Change the auto-refresh interval:** the `setInterval(..., 60000)` at the bottom of
  `docs/index.html`.
