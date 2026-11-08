# GIMS Results content system: handover

Everything George's automated content machine does, where it lives, and how to change it.
Start any new Claude chat about this system with: **"Read SYSTEM.md in gimsresults/blog-images first."**

Owner: George Spiroski, GIMS Results (Perth, works Australia-wide). Time zone: Australia/Perth.

---

## 1. What runs, and when (all times Perth)

| What | When | Where it runs | Scheduled task ID |
|---|---|---|---|
| Blog: Local SEO | Mon 8:50am | Claude scheduled task → GHL blog | `trig_016kvqDdL3gAxpPjzw2yV2s3` |
| Blog: Google Ads | Wed 2:10pm | Claude scheduled task → GHL blog | `trig_018U7dqNg7dCW6YVeLSfk9nj` |
| Blog: Meta Ads | Sat 8:50am | Claude scheduled task → GHL blog | `trig_01MMTFghpU2zPnkJEwTLk3hL` |
| X posts (3/day: 9:40am, 2:20pm, 6:00pm) + Threads & Bluesky (3/day: 8:15am, 1:15pm, 7:15pm) | writer runs daily 5:41am | Claude task writes; GitHub Action posts X; GHL posts Threads/Bluesky | `trig_01ESCCcKBnk1zC9tdXoGRhaz` |
| Instagram + Facebook carousel | every 3 days, posts 12:00pm (check runs 8:23pm daily) | Claude task → GitHub render → GHL | `trig_01RJBw2zR1LVNXdERKMbTWZn` |
| Google Business Profile weekly post | weekly | Claude scheduled task (separate, untouched by this system) | `trig_01VgeHAsqrCUkau3LkaDHAfX` |

Not part of this system (own chats): Morning plan briefing, Weekly review (1% Diary dashboard).

**The scheduled task prompts are the source of truth for the rules.** To change a rule, read the task's current prompt (`list_triggers` / `update_trigger` with the ID above) and edit it. Never paste an old copy over it: George edits them from other chats too.

## 2. Accounts and IDs

GHL (GoHighLevel connector `mcp__GHL__*`)
- locationId `xAQ56Sa4ugduqz5GZJRY`, userId `973dB04KyzuRREfMUvQT`
- Blog: blogId `M9EVQ0GeyWXVoJ0dxMj7`, author `68a2e3d0123c6b2132d57dde`
- Categories: Local SEO `693c1ca1c7d81c3b87fdd72c`, Marketing `68a2e3c9c64751586e4916f9`
- Social accounts:
  - Threads `6ade09827502021b9014a362_xAQ56Sa4ugduqz5GZJRY_29573981282194392_profile`
  - Bluesky `6add8e183001992f37dab2e1_xAQ56Sa4ugduqz5GZJRY_did:plc:ar3imzngtdz23p4tufolql4v_profile`
  - Instagram `6923ea2ee1ea9fc915166830_xAQ56Sa4ugduqz5GZJRY_17841476230202860`
  - Facebook page `6898b8d29ba76f48735157f8_xAQ56Sa4ugduqz5GZJRY_740331392497977_page`
  - Also connected in GHL: Google, LinkedIn, TikTok, Pinterest, YouTube
- GHL API quirks: `get-blog-post` with status SCHEDULED returns nothing, so list without a status filter; `get-blog-post-by-id` only works on published posts; `check-url-slug-exists` takes `urlSlug` only; `create-post` needs `"media": []` even with no media; `update-blog-post` must resend the whole body.

Website service pages (blog P.S. links): `/services/local-seo`, `/services/google-ads`, `/services/meta-ads` on gimsresults.com.au.

GitHub: public repo `gimsresults/blog-images` (this repo), served by jsDelivr (`https://cdn.jsdelivr.net/gh/gimsresults/blog-images@<commit or main>/...`).
Secrets live in GitHub repo secrets only (X API keys, `TELEGRAM_BOT_TOKEN`). Never paste keys in chat.

Telegram: bot @gims_ideas_bot in George's group "GIMS Results", topic "Blog_ideas" (group -1002534213146, topic 7). One idea per line.

Higgsfield (videos, voice): Starter plan, low credits. Saved voice clones are blocked on Starter. George's voice is made per line with `seed_audio` + his clean VSL recording as `audio_references` (media id `6972fa3e-f3f1-4713-8b27-168631c3c851`).

## 3. Repo map

| Path | What |
|---|---|
| `.github/workflows/build-covers.yml` + `scripts/scan_blog.py`, `make_cover.py` | Every ~5 min: finds blog posts using `assets/placeholder.jpg?cover=...`, renders `images/<slug>.jpg` from George's template |
| `.github/workflows/post-tweets.yml` + `scripts/post_tweet.py` | Every 15 min: posts due items from `tweets/queue/YYYY-MM-DD.json` to X (OAuth1 secrets) |
| `.github/workflows/collect-ideas.yml` + `scripts/collect_ideas.py` | Pulls Telegram ideas from the Blog_ideas topic into `ideas/ideas.json` |
| `.github/workflows/build-carousels.yml` + `scripts/make_carousel.py` | On push of `carousels/<slug>.json`, renders `carousels/<slug>/01-09.jpg` |
| `carousels/log.json` | Carousel history (date, pillar, place, topic, GHL post id) |
| `tweets/queue/`, `tweets/social/` | X queue per day; Threads/Bluesky log per day |
| `covers/` | Cover headline specs |
| `scripts/make_short.py` | Faceless short: AI clips + voiceover + captions + CTA card |
| `scripts/edit_reel.py`, `scripts/music_bed.py` | Talking-head reel editor (zooms, info cards, red keyword captions) and an original royalty-free music bed |
| `assets/template.png` | George's cover/brand template (logo, red underline, background) |

Animated reels (Remotion, no AI credits): project template from the `/animated-reels` skill, branded version built for "Does your business need SEO?" (Barlow Condensed, red #EC1212, black, white, GIMS logo). Rebuild from the skill template when needed.

## 4. Content rules (summary; the full wording is in each task prompt)

- **Voice:** George's writing-style guide (skill `gims-writing-style`). Direct, story-first, anti-hype. No em/en dashes, no "it's not X, it's Y", no hedging words, no AI/corporate words, no reflex lists of three.
- **Clarity check (top rule):** clear beats clever. One point per piece, metaphors explained on the spot, no puzzles, every pronoun obvious.
- **Fit check:** George's asides ("(famous last words)", "(solid headline right there)") only where they fit the line before them.
- **Views:** never suggest monthly task reports, client references, or judging an agency by its reviews; no prices; no promised rankings or quick fixes; no lock-in.
- **Places:** Perth first (real Perth suburbs). Blogs: every 5th post goes to Sydney/Melbourne (now and then Brisbane/Adelaide). Social and carousels: about 1 in 5 Sydney/Melbourne, never any other city.
- **Blog openings:** rotate formats A-F (conversation story at most 1 in 4; tips; something noticed; hot take; news reaction; George's own story). Banned openers like "Had a call..." unless it's format A.
- **Links:** X: one link a week (Wed 6pm). Threads/Bluesky: link only in the 7:15pm post on Mon/Wed/Sat. Carousels: no links. Blog P.S. links to the matching service page.
- **Ideas first:** George's Telegram ideas are used before anything else (tag `idea-<id>` on blogs, `source: idea-<id>` in queues/logs).
- **CTA (carousels, reels):** "Send us a DM and I'll check your Google profile for free." (Google Ads / Facebook & Instagram ads variants for those pillars). Button "DM US".

## 5. Video status (as of 8 Nov 2026)

- Tested: faceless AI shorts (OK), AI talking-head from George's photos (rejected: teeth and lip-sync not good enough), re-edit with info cards + music (OK), animated Remotion reel in George's cloned voice (latest).
- Voice: the "flowing" read style (normal speed, long pauses trimmed, natural joined sentences) is the one George liked best. Spell SEO as "S.E.O." and DM as "D.M." for the voice.
- Not yet scheduled: no weekly video task exists. Needs a bigger Higgsfield plan for AI clips; Remotion reels cost nothing. Recommended: George films himself and the system edits.

## 6. How to work on this in a new chat

1. Say what you want changed, e.g. "Change the X posting times" or "Make this week's reel".
2. Claude reads this file, then the live task prompt (by ID) or the repo file it needs.
3. Claude changes only what was asked and reports back.

Update this file whenever something structural changes (new task, new ID, new rule).
