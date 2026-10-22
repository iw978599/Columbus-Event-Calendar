# Scheduled run — Event Calendar

This is the runbook Claude follows on two scheduled runs (times in `data/config.json → timezone`):
- **Full run (e.g. Thursday around lunch):** every step below, including the digest email.
- **Mid-week refresh (e.g. Monday morning):** every step except 4 — no digest, no email. Focus research on the next 10 days and newly announced events.

Goal: keep `data/events.json` full of events the people in `data/people.json` are likely to enjoy, learn from their flags, publish the site, and email the Weekend Events Digest.

## 0. Setup
- Work in a clone of the repo named in `data/config.json → repo` (push access). Pull first: `git pull --rebase origin main`.
- Get today's date from the clock tool, in the configured timezone.
- **First run?** If `data/events.json` has no events, this is a fresh calendar: do a broader first pass (aim for 100+ events across the next six weeks) and build up `data/sources.json` as you go.

## 1. Read the state
- `data/config.json` — title, repo, site address, timezone.
- `data/people.json` — who flags on the calendar.
- `data/profile.json` — the first person's tastes (`likes`, `lessLikely`), others' under `people.<id>`, plus `learned` weights per person.
- `data/taste.json` — a plain-language summary per person of what's been learned. Shown and editable in the calendar's Settings.
- `data/feedback.json` — flags set on the calendar: `items[id].by[person] = {status, ts}` (`interested`, `not_interested`, or empty = cleared), plus a snapshot of the event's category, venue and tags.
- `data/areas.json` — the home area plus any trips (`from`/`to` dates).
- `data/sources.json` — local sources that have worked before, per area.
- `data/digest.json` — who is on the email list, by name. **Email addresses are never stored in this repo** (it is public); they are in the scheduled task's own instructions. Never write an email address into any file here.
- Run `python3 scripts/calendar_tool.py learn` and read its per-person summary. Search harder for categories, venues and tags people flag Interested, especially things everyone flagged (♥). Something one person rejects is fine to keep if another might like it; things everyone rejects get less coverage.

### Taste summaries (`data/taste.json`)
- If a person's entry has `updatedBy` other than `"agent"`, a person edited it: **every statement in it is authoritative.** Keep those statements, follow them when scoring and researching, and never contradict or quietly drop them. Fold new likes/dislikes from the edit into `profile.json`.
- At the end of every run, rewrite each person's `summary` in plain language (short bullet lines, no jargon, no scores): what they clearly like, what they pass on, any shift since last time, and how many flags it's based on. Keep user-written statements verbatim or nearly so, under a line such as "You told me:". Set `updated` to now and `updatedBy` to `"agent"`.

## 2. Research
Windows:
- **Home area**: today through today + 42 days. Fill thin days first, then refresh the coming two weeks.
- **Trips**: every area in `areas.json` whose `to` is today or later and whose `from` is within 120 days. Cover its whole date range. If a trip has no `timezone`, add the IANA zone (e.g. `America/Lima`).

Search widely, then fetch pages for real dates, times and prices (search snippets are too thin). Kinds of sources that work well in most cities:
- **Listings:** the city magazine's events calendar, alt-weekly and local news "things to do" roundups, the tourism board's calendar, neighborhood blogs.
- **Film:** independent and repertory cinemas (revival series, one-night screenings), film festivals, museum screenings.
- **Music:** club and venue calendars, jazz rooms, concert halls, Songkick/Bandsintown for the city, Resident Advisor for club nights.
- **Museums and galleries:** exhibition schedules (many museums publish an iCal feed, often `…/events/?ical=1`), gallery openings, free-admission days.
- **Talks, tours, community:** bookstores, libraries, lecture series, historic-building open days, gardens and nature centers, maker fairs.
- **Food:** markets, pop-ups and special dinners from local food coverage.
- **Instagram:** follow Instagram links that listings cite; search `site:instagram.com <venue> <month>` for venues that only post flyers.

Each time a source proves useful, add it to `data/sources.json` under its area (name, URL, what it's good for), and start with those sources on later runs.

Rules:
- Never invent a date, time or price. If cost is unknown, write `"See site"` and `free: null`.
- Skip civic meetings, support groups, job fairs, kids-only programming and generic bar crawls unless the profile says otherwise.
- Prefer the venue's own page for `url`.
- Respect site blocks: if a fetch is refused, use another source; never route around a block, paywall or login.

## 3. Write events
Each event in `data/events.json` → `events[]`:

```json
{
  "id": "2026-10-24-doors-open-weekend",           // YYYY-MM-DD + slug of title, unique
  "area": "home",                                   // id from areas.json
  "title": "Doors Open Weekend",
  "category": "community",                          // music | film | museum | theater | comedy | festival | talk | nightlife | food | community
  "start": "2026-10-24T10:00",                      // local time at the event; date only + "allDay": true if no time
  "end": "2026-10-24T17:00",                        // optional
  "until": "2027-02-21",                            // optional, for multi-day runs (exhibitions, theater runs, festivals)
  "venue": "Citywide",
  "address": "123 Main St, Your City, ST",          // optional; or add the venue to data/venues.json once
  "map": false,                                     // optional; only for citywide / multi-venue events
  "cost": "Free",                                   // as listed: "$15–55", "Pay what you can", "See site"
  "free": true,                                     // true | false | null (unknown)
  "url": "https://…",
  "base": 80,                                       // 0–100 fit for the household (see below)
  "description": "1–3 plain sentences on what the event is.",
  "summary": "Optional short practical note: extra dates, set times, sold out.",
  "tags": ["architecture", "history"],              // lower-case; reuse existing tags so learning carries over
  "source": "City Magazine"
}
```

`base` is a household score — fit for everyone in `people.json` together, from `profile.json`, `taste.json` and learned weights. Guidance: 75–90 strong fit; 55–74 good; 35–54 maybe; below 35 only if the day is thin. Apply what `learn` showed: nudge whole categories, venues and tags up or down.

- **Descriptions:** every event gets a `description` written from its page or listing (open it — don't stop at the title): the artist's style, the film's director/year/premise, what the exhibition shows, what you do at a workshop. Well-established public facts are fine; never invent details about an unfamiliar act or show.
- **Map links:** use the same `venue` spelling each time; when you find a new venue's street address on its site or a listing, add it to `data/venues.json` (`"Venue name": {"address": "…"}`). Without one the link searches "venue, city". Set `"map": false` for citywide or multi-venue events. Never guess an address.
- Update an existing event in place (same `id`) if details changed; don't duplicate.
- Leave events anyone flagged `interested` alone even if they are past.
- Set the top-level `"updated"` to now (ISO with offset).
- Run `python3 scripts/calendar_tool.py weekly` (validates, prunes events older than 45 days, refreshes learned weights, writes the `.ics` feeds). Fix any validation errors.

The page shows at most 10 events per day (best fit first, each viewer's Interested flags on top) and flags busier days, so it's fine to list more than 10 on a busy day.

## 4. Digest email (full run only)
- Weekend = the Friday–Sunday after today: `python3 scripts/calendar_tool.py digest --from <FRI> --to <SUN>` (defaults to the home area). If a trip overlaps that weekend, also build one for it (`--area <id> --area-name "<Name>" --out digests/<FRI>-<id>`) and send it as its own email.
- Read `digests/<FRI>.txt` and sanity-check it: dates right, nothing everyone rejected, links present.
- Send with the connected Gmail (`send_message`) **only to the addresses listed in your scheduled task's instructions**, every time, even if it's thin:
  - Subject: `Weekend Events Digest · <Fri Mon D> – <Sun Mon D>`
  - HTML body: `digests/<FRI>.html`; plain-text body: `digests/<FRI>.txt`.

## 5. Publish
- `git add -A && git commit -m "Scheduled update <date>"`.
- `git pull --rebase origin main` before pushing — the calendar page commits `data/feedback.json`, `data/areas.json` and `data/taste.json` on its own. On a conflict in one of those, keep the remote version and re-run `weekly`.
- `git push origin main`. The site is GitHub Pages from `main` (address in `data/config.json → site`).

## 6. Finish
On the mid-week refresh, skip step 4 and say so. Reply with a short summary: events added/updated per area, flags per person, what the learning shifted, and (full run) who the email went to.
