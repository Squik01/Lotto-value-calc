# Lottery Value Check — live-updating app

This folder is a complete GitHub repo. Once pushed, a scheduled job fetches
current jackpots twice a day and the app reads them automatically — no
manual typing, no server you have to maintain yourself (GitHub runs it for
free).

## One-time setup (~10 minutes)

1. **Create a new repo on GitHub** (public or private, either works — if
   private, GitHub Pages needs a paid plan, so public is simplest).
2. **Upload everything in this folder** to that repo (drag-and-drop on
   github.com works, or `git init && git add . && git commit -m "init" && git push`
   if you're comfortable with git).
3. **Turn on GitHub Pages**: repo → Settings → Pages → Source: "Deploy from
   a branch" → Branch: `main`, folder `/ (root)` → Save. GitHub gives you a
   URL like `https://yourname.github.io/lottery-app/`.
4. **Run the fetcher once manually** to populate real data immediately
   instead of waiting for the schedule: repo → Actions tab → "Update
   lottery jackpots" → Run workflow. Check the log — it prints what it
   found for each game.
5. **Install the app on your phone** using that GitHub Pages URL (Safari:
   Share → Add to Home Screen. Chrome: menu → Install app).

That's it. From here:
- The Action re-runs automatically at 06:00 and 22:00 UTC every day and
  commits any updated jackpot figures.
- The app fetches `jackpots.json` fresh every time you open it — same
  origin as the app itself, so there's no CORS wall this time.
- If a game's figure couldn't be confirmed on a given run, the app tells
  you which one and shows its last known value rather than guessing.

## If the scraper stops finding figures

Check Actions → the failed run → the log output — it prints exactly what
it did and didn't find. Send me that log in chat and I'll patch
`scripts/fetch_jackpots.py`; the parsing logic is isolated there, so a fix
won't touch the app itself.

## Sharpening the Powerball estimate over time

Use the "+ Log real ticket sales" box in the app whenever a real sales
figure gets reported somewhere (news coverage occasionally mentions this).
That's stored in your phone's local browser storage, not in this repo, so
it stays private to your device.

## Changing the schedule

Edit the `cron` line in `.github/workflows/update-jackpots.yml`. It's UTC,
and cron fields are `minute hour day month weekday`.
