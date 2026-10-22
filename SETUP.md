# Setting up your own Event Calendar

About 20 minutes. You need a free GitHub account and a paid Claude plan (Pro, Max, Team or Enterprise), since the weekly research runs as a Claude scheduled task.

## 1. Copy the template
On this repo's GitHub page, click **Use this template → Create a new repository**. Name it anything (e.g. `Event-Calendar`) and keep it **Public** (free GitHub Pages hosting needs a public repo, so don't put anything private in it).

## 2. Turn on the website
In your new repo: **Settings → Pages → Build and deployment → Deploy from a branch → `main` / `(root)` → Save.** In a minute or two the calendar is live at `https://YOUR-USERNAME.github.io/YOUR-REPO/`.

## 3. Make it yours
Edit these files on GitHub (open the file → pencil icon → Commit changes):

| File | What to change |
|---|---|
| `data/config.json` | `repo` → `YOUR-USERNAME/YOUR-REPO`; `site` → your Pages address; `timezone` → your IANA zone (e.g. `America/Chicago`, `Europe/London`); `title` if you like |
| `data/areas.json` | `name` → your city (e.g. `Portland, OR`) and its `timezone` |
| `data/people.json` | Your name. Add a second person (e.g. `{"id": "sam", "name": "Sam"}`) for a shared household calendar |
| `data/profile.json` | Replace the example `likes` / `lessLikely` with real ones. The more specific, the better the first run |
| `data/taste.json` | Use the same person ids as `people.json` (one entry each) |

## 4. Let the page save your flags (optional but recommended)
Flags work on one device without this. To sync them across devices and let the agent learn from them:

1. Open https://github.com/settings/personal-access-tokens/new in a web browser.
2. Name it, choose an expiration.
3. **Repository access → Only select repositories →** your calendar repo. (Not "Public repositories" — that is read-only.)
4. **Permissions → Contents → Read and write.** (Newer layout: **+ Add permissions → Contents**, then change Read-only to Read and write.) Metadata: Read-only is added automatically.
5. **Generate token**, copy it, and paste it on your calendar under **⚙ Settings → Sync flags to GitHub → Save**. Let your browser save it as a password and it will follow you to your other devices.

Each person can make their own token the same way.

## 5. Schedule the agent
In Claude, connect **GitHub** and **Gmail** (Settings → Connectors). Then either ask Claude in a chat:

> Set up the scheduled tasks for my event calendar repo YOUR-USERNAME/YOUR-REPO using its SETUP.md. Email the digest to you@example.com.

…or create them yourself at claude.ai/code/routines with these two prompts (replace the capitalized parts):

**Full run — weekly, e.g. Thursday 11:40 a.m.**
```
Weekly Event Calendar run.
1. Attach the GitHub repo YOUR-USERNAME/YOUR-REPO with push access, clone it, and read AGENT.md in the repo root. Follow AGENT.md exactly, including step 4.
2. Email the Weekend Events Digest with the connected Gmail send_message tool (HTML body from digests/<friday>.html, plain-text body from digests/<friday>.txt, subject "Weekend Events Digest · <Fri date> – <Sun date>").
   Recipients — send ONLY to: YOU@EXAMPLE.COM
   Send every week, even if the weekend is thin. The repo is public: never write any email address into a file in it.
3. Finish with a short summary of what changed and who the email went to.
```

**Mid-week refresh — weekly, e.g. Monday 8:30 a.m.**
```
Mid-week Event Calendar refresh. NO EMAIL on this run.
Attach the GitHub repo YOUR-USERNAME/YOUR-REPO with push access, clone it, read AGENT.md, and follow it as the mid-week refresh: every step except 4. Focus on the next 10 days and newly announced events. Commit and push to main. Finish with a short summary.
```

Click **Run now** on the full-run task once to fill the calendar right away — the first run takes longer because it starts from scratch.

## 6. Use it
Open your calendar, pick yourself in the 👤 menu, and start flagging events ★ Interested or ✕ Not interested. Check **⚙ Settings → What the agent has learned** now and then, and edit anything it gets wrong.

## What it costs
- **GitHub:** free (public repo + Pages).
- **Claude:** no per-run fee. Each run uses your plan's usage like a long chat would — a full run does dozens of searches and page reads, so on Pro it can use a noticeable share of a usage window. If that's a problem, run the full task with a lighter model, drop the mid-week refresh, or shorten the research window in AGENT.md.
- **Gmail:** free.
