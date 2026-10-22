#!/usr/bin/env python3
"""Maintenance tool for the Event Calendar repo.

  python3 scripts/calendar_tool.py validate
  python3 scripts/calendar_tool.py learn            # feedback -> data/profile.json "learned"
  python3 scripts/calendar_tool.py prune            # drop old, unflagged events
  python3 scripts/calendar_tool.py ics              # interested.ics from flagged events
  python3 scripts/calendar_tool.py digest --from 2026-10-23 --to 2026-10-25 [--area home]
  python3 scripts/calendar_tool.py weekly           # validate + prune + learn + ics

The scoring formula matches index.html so the email and the page rank events the same way.
"""
import argparse, datetime as dt, html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
def _config():
    try:
        return json.loads((DATA / "config.json").read_text())
    except Exception:
        return {}


CONFIG = _config()
SITE = CONFIG.get("site") or "./"
CATS = {
    "music": ("Concerts", "#c4701f"), "film": ("Film", "#3b6fc0"), "museum": ("Museums & art", "#157f78"),
    "theater": ("Theater & dance", "#b8432c"), "comedy": ("Comedy", "#a88a12"), "festival": ("Festivals", "#b0447f"),
    "talk": ("Talks & books", "#6f7e22"), "nightlife": ("Nightlife", "#7a4fa3"), "food": ("Food & markets", "#94683a"),
    "community": ("Tours & community", "#3f7d3c"),
}
RUN_DAYS = 7
REQUIRED = ["id", "area", "title", "category", "start", "venue", "url", "base"]


def load(name):
    return json.loads((DATA / name).read_text())


def save(name, obj):
    (DATA / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")


def d(s):
    return dt.date.fromisoformat(s[:10])


# ---------------------------------------------------------------- scoring
def map_url(e, venues=None, areas=None):
    """Google Maps link for an event's venue, or "" for citywide / multi-venue events."""
    from urllib.parse import quote
    venues = venues if venues is not None else load("venues.json").get("venues", {})
    areas = areas if areas is not None else load("areas.json")["areas"]
    v = venues.get(e.get("venue"), {})
    if e.get("map") is False or v.get("map") is False or not e.get("venue"):
        return ""
    addr = e.get("address") or v.get("address")
    city = next((a["name"] for a in areas if a["id"] == e.get("area")), "")
    q = f"{e['venue']}, {addr}" if addr else f"{e['venue']}, {city}"
    return "https://www.google.com/maps/search/?api=1&query=" + quote(q)


def people():
    try:
        return load("people.json")["people"]
    except Exception:
        return [{"id": "person1", "name": "Person 1"}]


def fb_items():
    """Feedback v2: items[id] = {meta..., by: {person: {status, ts}}}. An old single-person item ({status, ts}) belongs to the first person."""
    out = {}
    for k, f in load("feedback.json").get("items", {}).items():
        if "by" not in f:
            f = dict({x: y for x, y in f.items() if x not in ("status", "ts")},
                     by={people()[0]["id"]: {"status": f.get("status"), "ts": f.get("ts")}} if f.get("status") else {})
        out[k] = f
    return out


def status(items, eid, person):
    return (items.get(eid, {}).get("by", {}).get(person) or {}).get("status") or ""


def fans(items, eid):
    return [p for p in people() if status(items, eid, p["id"]) == "interested"]


def learned(items, person):
    L = {"category": {}, "venue": {}, "tag": {}}

    def bump(kind, k, st):
        if not k:
            return
        a = L[kind].setdefault(k, {"i": 0, "n": 0})
        a["i" if st == "interested" else "n"] += 1

    for f in items.values():
        st = (f.get("by", {}).get(person) or {}).get("status")
        if not st:
            continue
        bump("category", f.get("category"), st)
        bump("venue", f.get("venue"), st)
        for t in f.get("tags", []):
            bump("tag", t, st)
    return L


def aff(m, k):
    a = m.get(k)
    return (a["i"] - a["n"]) / (a["i"] + a["n"] + 2) if a else 0.0


def score(e, L):
    tags = e.get("tags") or []
    t = sum(aff(L["tag"], x) for x in tags) / len(tags) if tags else 0
    s = e.get("base", 50) + 14 * aff(L["category"], e["category"]) + 8 * aff(L["venue"], e.get("venue")) + 6 * t
    return max(0, min(100, s))


# ---------------------------------------------------------------- commands
def cmd_validate(_):
    ev = load("events.json")["events"]
    areas = {a["id"] for a in load("areas.json")["areas"]}
    errs, seen = [], set()
    for e in ev:
        for k in REQUIRED:
            if k not in e or e[k] in (None, ""):
                errs.append(f"{e.get('id')}: missing {k}")
        if e.get("id") in seen:
            errs.append(f"duplicate id {e['id']}")
        seen.add(e.get("id"))
        if e.get("category") not in CATS:
            errs.append(f"{e.get('id')}: bad category {e.get('category')}")
        if e.get("area") not in areas:
            errs.append(f"{e.get('id')}: unknown area {e.get('area')}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(T\d{2}:\d{2})?", e.get("start", "")):
            errs.append(f"{e.get('id')}: bad start {e.get('start')}")
        if e.get("until") and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["until"]):
            errs.append(f"{e.get('id')}: bad until {e.get('until')}")
        if e.get("free") not in (True, False, None):
            errs.append(f"{e.get('id')}: free must be true/false/null")
    for x in errs:
        print("ERROR", x)
    print(f"{len(ev)} events, {len(errs)} problems")
    return 1 if errs else 0


def cmd_learn(_):
    items = fb_items()
    prof = load("profile.json")
    prof["learned"] = {"updated": dt.datetime.now().isoformat(timespec="minutes")}
    for p in people():
        L = learned(items, p["id"])
        prof["learned"][p["id"]] = {k: {n: round(aff(v, n), 3) for n in v} for k, v in L.items()}
        sts = [status(items, k, p["id"]) for k in items]
        print(f"{p['name']}: {sts.count('interested')} interested, {sts.count('not_interested')} not interested")
        for kind in ("category", "venue", "tag"):
            ranked = sorted(prof["learned"][p["id"]][kind].items(), key=lambda kv: kv[1])
            if ranked:
                print(f"  {kind}: less {ranked[:3]}  more {ranked[-3:]}")
    both = [k for k in items if len(fans(items, k)) == len(people()) > 1]
    print(f"both interested: {len(both)}")
    save("profile.json", prof)
    return 0


def cmd_prune(a):
    obj = load("events.json")
    items = fb_items()
    flagged = {k for k in items if fans(items, k)}
    cutoff = dt.date.today() - dt.timedelta(days=a.keep_days)
    keep = [e for e in obj["events"] if e["id"] in flagged or d(e.get("until") or e.get("end") or e["start"]) >= cutoff]
    print(f"pruned {len(obj['events']) - len(keep)} events older than {cutoff}")
    obj["events"] = keep
    save("events.json", obj)
    return 0


def ics_text(events, areas, label="Interested"):
    tz = {x["id"]: x.get("timezone", CONFIG.get("timezone", "UTC")) for x in areas}
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    esc = lambda s: re.sub(r"([,;\\])", r"\\\1", str(s or "")).replace("\n", "\\n")
    out = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//event-calendar//EN",
           f"X-WR-CALNAME:Event Calendar — {label}", "X-PUBLISHED-TTL:PT12H"]
    for e in events:
        out += ["BEGIN:VEVENT", f"UID:{e['id']}@event-calendar", f"DTSTAMP:{now}"]
        s = e["start"]
        if e.get("allDay") or len(s) < 16:
            out.append(f"DTSTART;VALUE=DATE:{s[:10].replace('-', '')}")
        else:
            z = tz.get(e["area"], CONFIG.get("timezone", "UTC"))
            out.append(f"DTSTART;TZID={z}:{s.replace('-', '').replace(':', '')}00")
            end = e.get("end") if e.get("end") and len(e["end"]) >= 16 else \
                (dt.datetime.fromisoformat(s) + dt.timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M")
            out.append(f"DTEND;TZID={z}:{end.replace('-', '').replace(':', '')}00")
        out += [f"SUMMARY:{esc(e['title'])}", f"LOCATION:{esc(e.get('venue'))}",
                f"DESCRIPTION:{esc(' — '.join(x for x in [e.get('cost'), e.get('description') or e.get('summary'), e.get('url')] if x))}"]
        if e.get("url"):
            out.append(f"URL:{e['url']}")
        out.append("END:VEVENT")
    out.append("END:VCALENDAR")
    return "\r\n".join(out) + "\r\n"


def cmd_ics(_):
    items, evs, areas = fb_items(), load("events.json")["events"], load("areas.json")["areas"]
    ppl = people()
    files = {"interested.ics": ("Anyone interested", lambda e: fans(items, e["id"]))}
    for p in ppl:
        files[f"interested-{p['id']}.ics"] = (f"{p['name']} interested", lambda e, pid=p["id"]: status(items, e["id"], pid) == "interested")
    if len(ppl) > 1:
        files["interested-both.ics"] = ("Both interested", lambda e: len(fans(items, e["id"])) == len(ppl))
    for name, (label, keep) in files.items():
        ev = [e for e in evs if keep(e)]
        (ROOT / name).write_text(ics_text(ev, areas, label))
        print(f"{name}: {len(ev)} events")
    return 0


def fmt_time(s):
    if len(s) < 16:
        return ""
    t = dt.datetime.fromisoformat(s)
    h = t.hour % 12 or 12
    return f"{h}{':%02d' % t.minute if t.minute else ''} {'pm' if t.hour >= 12 else 'am'}"


def fmt_day(day):
    return day.strftime("%a %b ") + str(day.day)


def occurs(e, a, b):
    s = d(e["start"])
    u = d(e["until"]) if e.get("until") else s
    return s <= b and u >= a


def cmd_digest(a):
    start, end = dt.date.fromisoformat(a.frm), dt.date.fromisoformat(a.to)
    items, ppl = fb_items(), people()
    Ls = {p["id"]: learned(items, p["id"]) for p in ppl}
    venues, areas_all = load("venues.json").get("venues", {}), load("areas.json")["areas"]
    evs = []
    for e in load("events.json")["events"]:
        if a.area != "all" and e["area"] != a.area:
            continue
        f = fans(items, e["id"])
        nos = [p for p in ppl if status(items, e["id"], p["id"]) == "not_interested"]
        if (nos and not f) or not occurs(e, start, end):
            continue
        is_run = bool(e.get("until")) and (d(e["until"]) - d(e["start"])).days >= RUN_DAYS
        opening = is_run and start <= d(e["start"]) <= end
        base = sum(score(e, Ls[p["id"]]) for p in ppl) / len(ppl)
        mark = ("♥ " + " & ".join(p["name"] for p in f) if len(f) == len(ppl) > 1 else
                " ".join("★ " + p["name"] for p in f))
        e = dict(e, _map=map_url(e, venues, areas_all), _score=base + 60 * len(f), _star=bool(f), _mark=mark, _run=is_run and not opening,
                 _opening=opening)
        evs.append(e)
    dated = sorted([e for e in evs if not e["_run"]], key=lambda e: -e["_score"])
    runs = sorted([e for e in evs if e["_run"]], key=lambda e: -e["_score"])
    picks = [e for e in dated if e["_score"] >= a.min_score or e["_star"]][: a.max]
    top3 = picks[:3]
    groups = {}
    for e in picks:
        groups.setdefault(e["category"], []).append(e)
    order = sorted(groups, key=lambda c: -max(x["_score"] for x in groups[c]))
    for c in groups:
        groups[c].sort(key=lambda e: e["start"])
    runs = [e for e in runs if e["_score"] >= a.min_score][:5]

    title = f"Weekend Events Digest · {fmt_day(start)} – {fmt_day(end)}"
    when = lambda e: (fmt_day(d(e["start"])) + (f", {fmt_time(e['start'])}" if not e.get("allDay") and len(e["start"]) >= 16 else "")
                      + (f" → {fmt_day(d(e['until']))}" if e.get("until") else ""))
    cost = lambda e: "Free" if e.get("free") is True else (e.get("cost") or "Cost not listed")
    day_link = lambda e: f"{SITE}#day/{max(d(e['start']), start).isoformat()}"

    # ---- plain text
    t = [title, "=" * len(title), ""]
    if top3:
        t.append("DON'T MISS")
        for e in top3:
            t.append(f"  {e['_mark'] + ' · ' if e['_star'] else ''}{e['title']} — {when(e)}, {e['venue']} ({cost(e)})")
        t.append("")
    for c in order:
        t.append(CATS[c][0].upper())
        for e in groups[c]:
            t.append(f"  • {e['_mark'] + ' · ' if e['_star'] else ''}{e['title']}\n    {when(e)} · {e['venue']} · {cost(e)}")
            if e.get("description") or e.get("summary"):
                t.append(f"    {e.get('description') or e['summary']}")
            t.append(f"    {e['url']}")
            if e["_map"]:
                t.append(f"    Map: {e['_map']}")
        t.append("")
    if runs:
        t.append("ALSO ON VIEW")
        for e in runs:
            t.append(f"  • {e['title']} — {e['venue']}, through {fmt_day(d(e['until']))} ({cost(e)})  {e['url']}")
        t.append("")
    t.append(f"Full calendar (flag Interested / Not interested to tune these picks): {SITE}#week/{start.isoformat()}")
    text = "\n".join(t)

    # ---- html (light, table-based, inline styles for mail clients)
    h = html.escape
    def card(e, big=False, show_cat=False):
        name, col = CATS[e["category"]]
        stripe = "background-image:repeating-linear-gradient(135deg,transparent 0 8px,rgba(31,39,51,.06) 8px 12px);" if e.get("free") is True else ""
        badge = ('<span style="display:inline-block;border:1px solid #157f78;color:#157f78;border-radius:9px;padding:0 7px;'
                 'font-size:11px;letter-spacing:.06em;text-transform:uppercase;margin-left:6px">Free</span>') if e.get("free") is True else ""
        star = f'<span style="color:#3b76b3;font-size:13px">{h(e["_mark"])} · </span>' if e["_star"] else ""
        opens = "Opens: " if e.get("_opening") and "(opens)" not in e["title"] else ""
        return (f'<tr><td style="padding:0 0 10px 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
                f'style="border:1px solid #c4ccd6;border-left:4px solid {col};border-radius:4px;background:#ffffff;{stripe}">'
                f'<tr><td style="padding:10px 12px;font-family:Helvetica,Arial,sans-serif;color:#1f2733">'
                + (f'<div style="font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:{col};font-weight:bold">{h(name)}</div>' if show_cat else "")
                + f'<div style="font-size:{18 if big else 16}px;font-weight:bold;margin:2px 0 3px">{star}{opens}'
                f'<a href="{h(e["url"])}" style="color:#1f2733;text-decoration:none">{h(e["title"])}</a>{badge}</div>'
                f'<div style="font-size:13px;color:#64707f">{h(when(e))} · '
                + (f'<a href="{h(e["_map"])}" style="color:#64707f">📍 {h(e["venue"])}</a>' if e["_map"] else h(e["venue"]))
                + f' · <span style="color:#1f2733">{h(cost(e))}</span></div>'
                + (f'<div style="font-size:14px;margin-top:5px">{h(e.get("description") or e["summary"])}</div>' if e.get("description") or e.get("summary") else "")
                + f'<div style="font-size:13px;margin-top:6px"><a href="{h(e["url"])}" style="color:#3b76b3">Event page</a>'
                + (f' &nbsp;·&nbsp; <a href="{h(e["_map"])}" style="color:#3b76b3">Map</a>' if e["_map"] else "")
                + f' &nbsp;·&nbsp; <a href="{h(day_link(e))}" style="color:#3b76b3">On the calendar</a></div>'
                f'</td></tr></table></td></tr>')

    def section(label, col, rows):
        return (f'<tr><td style="padding:18px 0 8px;font-family:Helvetica,Arial,sans-serif;font-size:13px;font-weight:bold;'
                f'letter-spacing:.14em;text-transform:uppercase;color:{col};border-bottom:2px solid {col}">{h(label)}</td></tr>'
                f'<tr><td style="height:8px"></td></tr>' + "".join(rows))

    body = []
    if top3:
        rows = "".join(
            f'<tr><td style="padding:4px 0;font-family:Helvetica,Arial,sans-serif;font-size:15px;color:#1f2733">'
            f'<span style="display:inline-block;width:9px;height:9px;background:{CATS[e["category"]][1]};border-radius:2px;margin-right:7px"></span>'
            f'<a href="{h(e["url"])}" style="color:#1f2733;font-weight:bold;text-decoration:none">{h(e["title"])}</a>'
            f' <span style="color:#64707f;font-size:13px">— {h(when(e))} · {h(cost(e))}</span></td></tr>' for e in top3)
        body.append(f'<tr><td style="padding:14px 0 0"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
                    f'style="background:#ffffff;border:1px solid #c4ccd6;border-radius:6px"><tr><td style="padding:10px 14px">'
                    f'<div style="font-family:Helvetica,Arial,sans-serif;font-size:12px;font-weight:bold;letter-spacing:.14em;color:#3b76b3;margin-bottom:4px">DON\'T MISS</div>'
                    f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0">{rows}</table></td></tr></table></td></tr>')
    for c in order:
        body.append(section(CATS[c][0], CATS[c][1], [card(e) for e in groups[c]]))
    if runs:
        body.append(section("Also on view", "#64707f", [card(e) for e in runs]))
    legend = " ".join(f'<span style="display:inline-block;margin:0 8px 4px 0;font-size:12px;color:#64707f">'
                      f'<span style="display:inline-block;width:9px;height:9px;background:{col};border-radius:2px;margin-right:4px"></span>{h(n)}</span>'
                      for k, (n, col) in CATS.items() if k in groups)
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{h(title)}</title></head><body style="margin:0;background:#eef2f6">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#eef2f6"><tr><td align="center" style="padding:20px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:640px">
<tr><td style="background:#161814;border-radius:6px;padding:16px 18px;font-family:Helvetica,Arial,sans-serif">
<div style="color:#f2b648;font-family:Menlo,Consolas,monospace;font-size:12px;letter-spacing:.12em">{h(fmt_day(start).upper())} – {h(fmt_day(end).upper())}</div>
<div style="color:#ece5d3;font-size:26px;font-weight:bold;letter-spacing:.04em;text-transform:uppercase">Weekend Events Digest</div>
<div style="color:#9c9d89;font-size:13px;margin-top:4px">{len(picks)} picks for {h(a.area_name)}, ranked by fit and your flags. Striped cards are free.</div>
</td></tr>
<tr><td style="padding:10px 2px 0;font-family:Helvetica,Arial,sans-serif">{legend}</td></tr>
{''.join(body)}
<tr><td style="padding:18px 4px;font-family:Helvetica,Arial,sans-serif;font-size:13px;color:#64707f">
<a href="{SITE}#week/{start.isoformat()}" style="color:#3b76b3;font-weight:bold">Open the full calendar</a> — flag events Interested or Not interested and future digests adjust.
Costs and times come from venue listings; confirm before you go.</td></tr>
</table></td></tr></table></body></html>"""
    out = ROOT / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".html").write_text(doc)
    out.with_suffix(".txt").write_text(text + "\n")
    print(f"digest: {len(picks)} picks in {len(order)} categories, {len(runs)} on view -> {out}.html/.txt")
    return 0


def cmd_weekly(a):
    a.keep_days = 45
    return cmd_validate(a) or cmd_prune(a) or cmd_learn(a) or cmd_ics(a)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("validate")
    sub.add_parser("learn")
    pr = sub.add_parser("prune"); pr.add_argument("--keep-days", type=int, default=45)
    sub.add_parser("ics")
    sub.add_parser("weekly")
    dg = sub.add_parser("digest")
    dg.add_argument("--from", dest="frm", required=True)
    dg.add_argument("--to", required=True)
    home = next((x for x in load("areas.json")["areas"] if x.get("home")), {"id": "all", "name": "your area"})
    dg.add_argument("--area", default=home["id"])
    dg.add_argument("--area-name", default=home["name"].split(",")[0])
    dg.add_argument("--max", type=int, default=22)
    dg.add_argument("--min-score", type=int, default=45)
    dg.add_argument("--out", default=None)
    a = p.parse_args()
    if a.cmd == "digest" and not a.out:
        a.out = f"digests/{a.frm}"
    return {"validate": cmd_validate, "learn": cmd_learn, "prune": cmd_prune, "ics": cmd_ics,
            "digest": cmd_digest, "weekly": cmd_weekly}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
