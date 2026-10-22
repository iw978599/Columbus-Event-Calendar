# Event Calendar

A personal events calendar that researches itself. Once or twice a week, a Claude scheduled task searches local listings, venues, museums, cinemas and Instagram for events you're likely to enjoy, adds them to a calendar website hosted free on GitHub Pages, learns from what you flag, and emails you a Weekend Events Digest.

**To make your own, see [SETUP.md](SETUP.md).**

## What you get
- **Month / Week / Day views**, weeks running Monday–Sunday. Tap a day to open it. Keyboard: ← → to move, `m` `w` `d` to switch views.
- **Color = event type** (Concert, Film, Museum & art, Theater & dance, Comedy, Festival, Talks & books, Nightlife, Food & markets, Tours & community). Tap a legend chip to hide a type. **Diagonal stripe = free.**
- **Ten per day.** Each day lists its ten best-fit events; busier days get an orange count badge and a "Show N more" button. Long runs (exhibitions, theater runs) sit in an "Also on view" drawer.
- **Details** for every event: a short description, cost, a link to the event page, and a 📍 Google Maps link to the venue.
- **Flags, per person.** Pick who you are in the 👤 menu. ★ Interested adds an event to your calendar; ✕ Not interested hides it for you only. Calendars: All events · each person's · ♥ Both interested · Either. Markers: ★ you, ☆ the other person, ♥ everyone.
- **Learning.** Each run turns everyone's flags into their own preferences and searches harder for what you like. **Settings → What the agent has learned** shows a plain-language summary you can edit; your edits are treated as fact.
- **Trips.** Add a city and dates in Settings; the next run researches events there.
- **Calendar feeds.** `interested.ics` (anyone), `interested-<person>.ics` and `interested-both.ics` can be subscribed to in Google or Apple Calendar.
- **Weekend Events Digest** email: picks for Friday–Sunday grouped by type, with cost, links and map links.
- **Light / Dark** toggle.

## Files
- `index.html` — the whole site (no build step).
- `data/config.json` — title, repo, site address, timezone.
- `data/events.json` — events. `data/areas.json` — home + trips. `data/people.json` — who flags.
- `data/feedback.json` — flags per person (written by the page). `data/profile.json` — taste notes + learned weights. `data/taste.json` — plain-language summaries shown in Settings.
- `data/venues.json` — venue addresses for map links. `data/sources.json` — local sources the agent has found useful. `data/digest.json` — who's on the email list, by name (addresses live in your scheduled task, never in the repo).
- `scripts/calendar_tool.py` — validate, prune, learn, build the `.ics` feeds and the digest.
- `AGENT.md` — the runbook the scheduled task follows.

## Privacy
The repo is public, so everything in it is too: your flags, taste notes, city and trips. Email addresses and your GitHub token are deliberately kept out — the token stays in your browser, and addresses live only in your Claude scheduled task.
