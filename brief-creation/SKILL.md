---
name: brief-creation
description: >
  Generate a creator brief for a product and wire it into the automation that reaches
  creators. Covers both mechanisms Reacher offers — the image brief (a poster built from
  the product catalogue, the default) and the creative brief (a document derived from the
  product's own analyzed winning videos) — renders a preview the user can actually look at
  before anything ships, and attaches it at the Sample Approved stage. Use when the user
  asks to "make a brief", "create an image brief", "build a creator brief", "replace the
  content guide", "send creators a brief", "brief per product", or wants creators to get
  guidance on what to film. Do NOT use for sourcing (creator-sourcing), for building the
  automation itself from scratch (automation-creation), or for formatting an analysis as a
  document (html-report). Distinct from `creative-angle-brief`, which works from a
  manually supplied UVI CSV to produce an internal angle summary plus an outreach
  message; this skill is API-driven and ends with a brief attached to an automation.
---

# Brief Creation

Creators do not click links off TikTok. A brief only works if it arrives as something they
can look at inside the DM. That is the whole reason this skill exists, and it is why the
image brief is the default.

## Step 0: pick the mechanism

Two different things are both called a "brief". Ask which one, and lead with the image brief.

| | **Image brief** (default) | **Creative brief** |
|---|---|---|
| Tools | `image_brief_generate` then `image_brief_create` | `creative_brief_generate` |
| Input | up to 3 `product_ids`, index 0 is the hero | one `product_id` |
| Built from | catalogue copy, the product's top hooks, brand voice | the product's already-analyzed videos |
| Returns | kicker, `winningHooks`, `socialProof`, `benefits`, `contentIdeas`, `shopTagline` | content angles, USPs, filming recommendations, dos and don'ts, inspiration videos |
| Saving | generate does NOT save — you must call create | saves a `drafted` brief on generation |
| Fails when | — | **422** if the product has no analyzed videos |
| Shareable link | none | `creative_brief_published_url`, once published |

Default to the **image brief**. Reach for the creative brief when the user wants depth —
angles, dos and don'ts, real inspiration videos — and the product has analyzed videos. If
`creative_brief_generate` returns 422, say plainly that the product has no analyzed videos
yet and offer the image brief instead rather than retrying.

Both accept `dry_run`. Both require an `idempotency_key`, and generation **spends model
tokens** — a retry with the same key replays the first result instead of regenerating, so
always pass your own UUID rather than letting one be auto-generated.

Generation is non-deterministic. The same products give different copy each run. Never
promise the user they can reproduce a brief by re-running it; save the one they liked.

## Step 1: group the catalogue into pack families first

**Do not default to one brief per SKU.** Most catalogues are the same product in several
sizes and flavours, and a creator films the pack in their hand, not the SKU id. One brief
per SKU produces near-duplicates nobody maintains.

Pull `products_list` for the last 30 days and group by **what a creator would film**:
bulk multipack, mid-size multipack, single-flavour pack, a different product line
entirely. Five or six families usually covers a twenty-product catalogue. Measured on one
food shop: 20 products, 14 with any GMV, 4 driving 91% — five families covered all of it.

Within a family, put the best-selling SKU at index 0 (it renders the poster header) and
use the remaining two slots for its closest variants. Do not mix families in one brief —
a mismatched supporting product reads as spam.

Show the user the proposed grouping and get agreement before generating, since every
generation spends tokens.

## Step 2: gather before generating

1. **Which product.** If they have not said, pull `products_list` for the last 30 days
   sorted by GMV and propose the top seller. One shop had a single SKU driving 71% of
   affiliate GMV — brief that one first.
2. **Hero and supporting products.** The image brief takes up to 3. Index 0 is the hero and
   its identity fills the poster header. Supporting products should be variants of the same
   thing, not unrelated SKUs.
3. **Check what already exists.** `image_briefs_list` / `creative_briefs_list`. Shops
   accumulate abandoned drafts — one had three, two of which were untouched template
   defaults about a garment, on a snack-food shop. Offer to reuse or replace rather than
   adding a fourth.
4. **Preview the header.** `image_brief_product_context` returns the exact name, brand,
   price, image and `topHooks` the poster will render, before you spend a generation.
5. **Brand voice.** `image_brief_get_brand_voice` feeds every generation. If it is empty,
   say so — the copy will be more generic — and offer to set it with
   `image_brief_set_brand_voice`.

## Step 3: ground the brief in the shop's own winning videos

A brief written from the catalogue alone produces plausible copy that nobody has tested.
A brief carrying lines that already earned money on this exact product is a different
object. Do both: prescribe the **structure** the data supports, and show **verbatim hooks**
from that family's own top earners.

### Pull the evidence

For each family: `videos_list` filtered to the family's `product_ids`, sorted by
`video_gmv` desc, then `video_intel_analysis_batch` with `include_experimental: true`.
Take the hook from `hook_text`, falling back to the opening sentence of `transcript`.

**Check the analyzer is healthy over your window before trusting any hook label.** One
shop's analyzer degenerated partway through the year and returned `hook_classification:
"none"` on ~98% of later videos, plus constant values for tone, pace and production
quality. Transcripts were unaffected. Test it: compute the share of videos with a
populated hook per month; a step change to near-zero means the labels are junk from that
point and you must restrict hook extraction to the healthy window. Say which window you
used in the run summary.

### What the structure guidance should say

Derive it from the shop's own data, but the shape that has held up on a measured
catalogue is: **surprising statement → review → say the price out loud → ask for the sale.**
On one shop that combination earned $147.72 per video across 164 videos, against $8.93
across the 503 videos that opened with a rhetorical question. Adding the closing ask alone
roughly tripled GMV per video within the same opening style.

Two corrections worth carrying into most food and CPG briefs, both measured:
- **Demote the spec sheet.** Nutrition claims appeared at the same rate or higher in
  zero-GMV videos. Keep the headline number as a supporting beat, never the opener.
- **Promote price and occasion.** Saying the price out loud was the single biggest verbal
  differentiator; naming a concrete use occasion was second.

### Screen the hooks before they go in a brand-issued brief

The best-performing hooks are often not brief-safe. Real examples from one shop's top
earners: a $2,333 video opening with a crude bathroom joke, a $1,742 video opening with
profanity about the platform. They work; they cannot go out under the brand's name
unedited.

**Surface every flagged hook to the user rather than silently dropping it** — the decision
is theirs. Flag: profanity or crude humour, medical or health claims, competitor names,
and **expired discounts**. Price-specific hooks like "75% OFF" or "ENDS TODAY" convert well
but date badly in a standing brief; render them as a pattern rather than a fixed number
unless the brief is paired with a live promo.

### Brand voice

`image_brief_get_brand_voice` feeds every generation and is very often empty, which is the
usual reason generated copy reads generic. Do not invent descriptors. Derive them from how
the shop's top creators actually talk — read the transcripts of the highest earners and
characterise register, energy and sentence length — then **show the user the proposed
descriptors and get approval before calling `image_brief_set_brand_voice`.** It affects
every future generation, so it is not yours to set quietly.

### Segments

Default to **one brief per family, segment-neutral**. Brands often run separate audience
segments, but the stage automation that delivers the brief usually does not split by
segment, so segment variants multiply the build for no delivery benefit. Offer them only
where a single product carries several genuinely different audiences and the delivery
path can actually target them.

## Step 4: show the user the brief before it goes anywhere

The API returns brief content as **structured JSON, not as a picture**. There is no render,
preview, export or screenshot endpoint on either brief type. So the user cannot see what
their brief looks like without opening the portal.

**Close that gap yourself: rebuild the poster as an HTML artifact and publish it.** This is
the single most useful thing this skill does. Read the saved brief back with
`image_brief_detail`, then lay out its fields with the brief's own `accent_color`, and label
the page clearly as a Claude reconstruction rather than a copy of the portal's renderer —
the portal templates are `zine` and `editorial-dark` and yours will not match them exactly.

Two mechanics that will bite:
- Product image URLs are **signed and expire**. Download and inline them as data URIs
  before publishing, or the artifact renders with broken images a day later.
- The artifact viewer's CSP blocks external images entirely, so inlining is required, not
  optional.

Show the preview and get an explicit yes before Step 3.

## Step 5: attach it at Sample Approved

The default placement is the **Sample Approved** stage. A creator who has just been approved
can read the brief while waiting for the box to arrive, which is the moment they are most
receptive and have the most time to plan. Content Pending is too late — they already have
the sample and many have already filmed.

Route into an **existing** automation on that stage rather than creating one. Follow
`automation-creation`'s Step 6 routing rules; do not call `automation_create_*` from this
skill.

Hard constraint, verified: setting `creators_to_include.filters` on a list-based automation
**silently discards every attached list**. If the target automation is list-backed, do not
touch its targeting at all — only its message content.

Report which automation you attached to, how many creators sit in that stage today, and what
the previous message was, so the user can see exactly what they are replacing.

## Step 6: measure it

The user will ask whether the brief worked. Set expectations honestly up front:

- Creative briefs carry `views` and `last_opened_at` — that is a real open metric, and it is
  the only one either brief type has. One shop had three briefs, all with `views: 0` and
  `last_opened_at: null`: written, never delivered.
- **Image briefs carry no open or view tracking at all.** An image in a DM has nothing to
  instrument. If the user wants open rates, tell them the image brief cannot provide them
  and the creative brief's published URL can.
- Downstream, judge by the stage the brief is meant to move: post rate out of Sample
  Approved, and time from approval to first video. Compare the cohort that got the brief
  against the cohort before it, and say plainly that this is a before-and-after, not a
  controlled test.

## Practical notes

- Never edit a brief's numbers or claims to make them stronger. The copy is generated from
  the shop's own catalogue and videos; inventing a statistic in a creator brief puts a false
  claim in front of thousands of creators.
- Keep `signatureHooks` and `winningHooks` in the creator's voice. They are lines a creator
  will read aloud, not marketing copy.
- `contentIdeas` should be filmable in one take on a phone. If a generated idea needs a set,
  a second person, or editing software, replace it.
- One brief per product. Do not build a single brief covering an unrelated catalogue — the
  hero product's identity is what renders, and a mismatched supporting product reads as spam.
