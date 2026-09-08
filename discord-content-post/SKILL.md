---
name: discord-content-post
description: >
  Post creator content into a brand's Discord community — either a product brief or a
  breakdown of one real top-performing video — and schedule it to recur. Picks the video,
  writes the post in Discord markdown, asks which channel, and posts or schedules it via
  the Discord API. Use when the user asks to "post to Discord", "send a brief to Discord",
  "weekly Discord content", "share a video breakdown with the community", "schedule a
  Discord post", or wants recurring creator education in an inactive server. Do NOT use to
  build the brief itself (that is brief-creation), to analyse video performance for internal
  reporting, or to message individual creators (that is per-creator outreach, not community
  posting).
---

# Discord Content Post

Posts one thing at a time into a brand's Discord: **a product brief**, or **a breakdown of a
single real video**. The user picks which. It is community content, not per-creator
outreach — one post, whole server.

## Step 0: work out how you can actually deliver

The Discord endpoints exist on the REST API but are **not currently exposed as MCP tools**.
Establish the delivery path before doing any work, and tell the user which one you are on.

| Endpoint | Purpose |
| --- | --- |
| `GET /discord/channels` | List the shop's channels |
| `POST /discord/messages` | Post now or schedule. Body: `channel_id`, `message`, optional `scheduled_at` (ISO 8601, **UTC**), `recurrence`, `images[]` |
| `GET /discord/messages` | List scheduled, sent and failed messages, with engagement |
| `GET /discord/messages/{id}` | One message and its engagement |
| `DELETE /discord/messages/{id}` | Cancel a scheduled message |

In order:

1. **Check for MCP tools first** — search the tool surface for Discord message tools. If
   they have been added since this was written, use them.
2. **Otherwise call the REST API directly**, if the user has an API key available in the
   environment. Never ask the user to paste a key into the chat; if it is not already
   available, do not request it.
3. **Otherwise produce the post for the user to paste**, and say plainly that nothing is
   scheduled. Do not imply a cadence has been set when nothing will fire.

Also check `integrations_status` — if `discord` is not `connected`, stop and say so.

## Step 1: brief or breakdown?

Ask, unless the user already said. They are different jobs:

- **Product brief** — the poster from `brief-creation`. Good when a new product launches, or
  when a brief exists that creators have not seen. Post the image via `images[]`.
- **Video breakdown** — one real video, its hook, its structure, its numbers, and the one
  thing to copy. Good as recurring weekly content because there is a fresh one every week
  and it teaches craft rather than advertising.

Default to the **breakdown** for a recurring slot, and the **brief** for a one-off tied to a
product.

## Step 2: pick the video

Default: **the top-earning video posted in the last 7 days.** Always offer the alternatives,
because the default is not always the best teaching example:

| Pick | When it is right |
| --- | --- |
| Top GMV, last 7 days | Default. Current and clearly "this worked right now". |
| Best structural example | The video that best shows hook → talk → price → ask. Teaches the pattern rather than celebrating an outlier. |
| Highest GMV per 1,000 views | Surfaces small accounts that convert hard — the most motivating pick for a server full of newer creators. |
| A specific video the user names | They saw something worth featuring. |

Pull with `videos_list` (last 7 days, sorted by `video_gmv`), then `video_intel_analysis_batch`
for the creative detail.

**Sanity-check the week before you commit.** A quiet week may have no video worth featuring.
If the top video earned almost nothing or has very few views, say so and offer to widen to 14
or 30 days rather than featuring a weak example.

## Step 3: write the post

**Breakdown** — five short blocks, in this order:

1. **The hook, quoted verbatim.** Never paraphrase; a paraphrased hook is useless as a model.
2. **The numbers.** Views, GMV, and how many videos that creator posted. Concrete.
3. **The structure.** How it opens, what it demonstrates, how it closes.
4. **The one thing to copy.** A single instruction, not a list.
5. **A link to the video** so people can watch it.

**Brief** — post the image with two or three lines of context saying which product it is for
and what changed. The image carries the content; do not restate it.

### Attribution

**Name the creator, do not tag them.** Naming credits the work and gives others someone to
learn from. Tagging pushes a notification and singles the person out in a community that may
already be fragile — one brand's server had 4,000+ members and low engagement precisely
because people felt over-messaged. Names come from the video record; `campaign_creators_discord`
maps TikTok handles to Discord handles if the user ever asks to tag, but do not do it by
default.

Never post a hook that is not brand-safe. Screen for profanity, crude humour, appearance or
weight claims, medical claims, and **expired discounts** — a "75% OFF" hook converts well and
dates badly the moment the promo ends. If the top video's hook fails the screen, say so and
feature the next one rather than sanitising a quote.

### Formatting

Discord markdown only: `**bold**`, `> quote`, `-` bullets, `##` at most. No tables, no HTML.
Keep it under ~2,000 characters and split at a natural break if longer.

## Step 4: pick the channel

**Always ask.** Call `GET /discord/channels`, show the list, and let the user choose — do not
guess from a channel name. If the user has told you the channel before in this conversation,
reuse it and say which one you are using.

## Step 5: post or schedule

Confirm the exact text and the channel with the user **before** posting. This goes to a whole
community and cannot be unsent.

- **Post now**: `POST /discord/messages` with `channel_id` and `message`.
- **Schedule**: add `scheduled_at` as ISO 8601 **in UTC**. Convert from the brand's local time
  and state both in your confirmation, because an off-by-timezone post lands in the middle of
  the night.
- **Recurring**: set `recurrence`. Say clearly that it will keep firing until cancelled, and
  note that `DELETE /discord/messages/{id}` is how it stops.

A recurring breakdown must re-select the video each run. If the recurrence just re-posts fixed
text, it will repeat the same video forever — check the semantics before relying on it, and if
it is a static repeat, schedule single posts instead and say why.

## Step 6: report and measure

Return the message id, the channel, and when it fires. Then set expectations: `GET /discord/messages`
carries engagement, so a follow-up run can report how the last post did.

The deeper question — whether posting lifts creator output — is answerable by cross-referencing
`campaign_creators_discord` handles against `videos_list` for the following period. Offer it as
a proxy and be clear it is a proxy.

## Voice

Write to creators, not about them. Concrete and specific, no hype. Never imply anyone's content
is bad; frame everything as what the winning video did. These are people who already work with
the brand, and the post should read like a colleague sharing something useful.
