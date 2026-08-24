---
name: creator-sourcing
description: Source new TikTok Shop affiliate creators for a Reacher client using multi-mode AI search (profile, transcript, video, lookalike), Social Intelligence competitor-affiliate mining, keyword variation, top-performer lookalike seeding, exclusion of existing creators, and output as Reacher lists. Use this skill whenever the user asks to source creators, find new creators, find affiliates, build a creator list, find lookalikes of top performers, poach or mine competitor creators, or run creator discovery for a shop, even if they don't say the word "sourcing". Requires the Reacher connector.
---

# Creator Sourcing

Source as many high-quality, net-new affiliate creators as possible for a Reacher client's shop, and deliver them as a Reacher list ready for outreach.

The core idea: one search with one phrasing finds one slice of the creator universe. This skill multiplies coverage by (a) running every available AI search mode, (b) rewording each keyword 3-5 ways, (c) seeding lookalike search with the client's own top performers, and (d) mining the affiliates of the brand's direct competitors via Social Intelligence. Then it deduplicates, removes creators the brand already works with, applies quality floors, and saves the results as lists in Reacher.

Two bundled scripts carry the data handling so it isn't reinvented (buggily) each run: `scripts/process_export.py` parses an `export_creators` result, applies the floors, and appends qualifiers to a raw per-method CSV; `scripts/finalize_lists.py` does the global dedupe, exclusion filtering, and final per-method CSV output. Run them with python3; both print the counts the final summary needs.

## Step 0: Identify the shop

If the user names a client, resolve it to a shop_id with `list_shops`. If multiple shops match or none is named, ask which shop. Every search endpoint in this flow requires a single shop_id (not 'all').

Then call `ai_search_capabilities` for that shop. It returns which modes are enabled for the shop's region: profile (always), transcript, video, lookalike. Only use enabled modes; skip disabled ones silently and note it in the final summary.

Social Intelligence (SI) is a separate sourcing method alongside AI search: it browses the whole TikTok Shop ecosystem (sellers, products, creators) rather than searching by description. SI is gated per customer; on shops without SI access, SI endpoints (`get_sellers`, `get_seller_categories`, etc.) return a plain `404 NOT_FOUND`, not a 403 or a permissions message. Treat a 404 from any SI endpoint as "this shop has no SI" rather than a malformed request: don't retry with different parameters, just skip the competitor pass, note it in the summary, and continue with the other modes.

## Step 1: Understand the client and confirm parameters

Pull context before searching:

- `products_list` for the shop: note the top products by GMV and the product category (L2 category). This anchors keyword generation in what the shop actually sells.
- If the user hasn't described the target audience/demographic, infer a starting point from the product catalog and confirm it: "Looks like this shop sells X in the Y category. Am I right that the target creator profile is Z?"

Then confirm these five things with the user before running searches (one short message, not an interrogation):

0. **Precise or bulk?** Ask this first, because it decides which mechanism runs. Precise means AI search for creators who genuinely match the niche, and lands in the hundreds. Bulk means a category-and-performance filter the automation re-resolves every run, and reaches tens of thousands but cannot target a topic. Put the tradeoff in one sentence and let them choose; if they want both, run them as two separate automations so the results stay comparable. See "Precise vs bulk" below for the numbers to quote.

1. Quality floors. Default: creator GMV above $100 and post rate above 60%. State these defaults explicitly and ask if they want different filters (follower range, engagement rate, avg views, etc.). Don't silently apply defaults without telling them, since the brand may have stricter or looser standards.

   Quote the cost of these floors, because it is larger than it looks. Post rate is on a 0-100 scale, not 0-1: `60` means 60 percent. Measured on a US Food & Beverage shop with server-side filters: GMV >= $2,000 alone returns 2,907 on-category creators, and adding post rate >= 60 takes it to 1,778. On the Sports & Outdoor category the same pair returns 6,330. Floors are the first lever to discuss when a brand needs volume, not the last, so say so up front rather than delivering a small list and letting them discover it.
2. Exclusions. Ask whether to exclude creators the brand already works with, and which definition they mean: (a) active affiliate creators of the shop, (b) creators who already received a TC invite, (c) creators who already received a sample, or any combination. Different brands mean different things by "already ours", so the brand should clarify this rather than the skill assuming.
3. Anything unusual about the audience (region, language, content style) that should shape keywords.
4. Competitors. Ask whether they want competitor affiliates included (default: yes if SI is available) and whether they can name the brand's direct competitors. If they can't, propose candidates yourself: `get_sellers` filtered to the client's category, sorted by gmv28d, cross-checked against the client's products, and confirm the shortlist before mining. Don't mine sellers the user hasn't confirmed as competitors, since adjacent-category giants pollute the pool.

If the user already answered any of these in their request, don't re-ask; just restate what you're using. Fold all four into the one consolidated message.

## Step 2: Generate keyword variants

For each audience/niche descriptor, generate 3-5 distinct wordings. The variants must be grounded in the client's target demographic and product category, not generic synonyms. Vary the vocabulary the creators themselves would use, since search matches how creators describe themselves and their content.

Example: target audience "plus size women", category Womenswear:
- "plus size fashion creators"
- "curvy women outfit and try-on content"
- "midsize and plus size style creators"
- "body positive fashion creators"
- "size inclusive clothing hauls"

Example: category Beauty & Personal Care, product is a scalp serum:
- "hair growth and scalp care creators"
- "creators who talk about hair thinning"
- "haircare routine content"
- "hair loss journey creators"

Build variants for each mode's strengths:
- Profile mode: who the creator is ("plus size fashion creators in the US")
- Transcript mode: what they say ("talks about finding clothes that fit", "mentions hair thinning")
- Video mode: what their content looks like ("plus size try-on haul in a bedroom", "applying serum to scalp")

The strongest profile queries pair an audience identity with a usage occasion: name the person AND the moment they'd use the product ("moms packing school lunchboxes", "nurses who need a fast snack on shift", "renters mounting cameras without drilling"). Two query shapes reliably fail and are worth recognizing on sight: bare product keywords ("protein snacks", "security camera") pull competitor shops and resellers instead of recruitable creators, and bare lifestyle identities ("college dorm life") pull the adjacent category's creators instead of ones who'd sell this product. If a query drifts into either shape, rebuild it around identity plus occasion rather than pushing the results through.

## Step 3: Run the searches

Run every enabled mode with every relevant variant. The workhorse is bulk export, not pagination: paging search results one screen at a time blows up the context (bios, video embeds, signed avatar URLs) and caps volume far below what one export call returns.

1. Profile search: `export_creators` once per keyword variant (up to 50K rows per call, includes gmv_segment and post_rate columns).

   **Pass the floors server-side using these exact field paths.** The endpoint accepts a `filters` object in the portal search-filter shape, and it now REJECTS unrecognized fields with a 400 that names the offending path. Guessing field names is the single most expensive mistake in this skill: a wrong name used to be accepted and silently ignored, which returned an unfiltered pool that then got cut to a few hundred rows client-side.

   | Filter | Path | Value |
   | --- | --- | --- |
   | GMV | `performance.gmv` | `{"min": 2000}` numeric dollars |
   | Post rate | `performance.post_rate` | `{"min": 60}` on a 0-100 scale |
   | Category | `creators.product_categories` | `["Sports & Outdoor"]` |
   | Followers | `creators.followers` | numeric range |

   `performance.fulfillment_rate` returns a 400; the export wants `post_rate`. The automations filter endpoint calls the same metric `fulfillment_rate` (labelled "Post Rate") and the CSV returns both `post_rate` and `fulfillment_rate_segment`, so confirm which surface you are on before naming the field. Call `automation_filters` for the shop region to get valid category values.

   Server-side filters hold to roughly 0.1 percent leakage (8 rows below the floor out of 6,330 on a measured run), so `process_export.py` still re-checks every row. That is a safety net now, not the primary filter.

   For a query you haven't validated yet, pull page 1 of `search_creators` first as a cheap preview: if more than half the page is brand accounts, resellers, or off-category creators, the query is wrong (see the failure shapes in Step 2), so rebuild it before exporting, since a 50K export of junk poisons the raw CSV. Once a query previews clean, export it, save the tool result to a file, and run `scripts/process_export.py` on it to apply the floors and append qualifiers to `raw/keyword.csv`; it prints total vs qualified per query so you can report yields. Fall back to paginated `search_creators` only if the export endpoint is unavailable on the key.
2. Transcript search (if enabled): `search_transcript` with spoken-phrase variants. Consider `match_sources: ["audio", "video"]` to also match on-screen text. No export exists for this mode, so keep it to 1-2 pages per query as topical seasoning on top of the export base, and append each page's qualifiers to `raw/transcript.csv` immediately (same 9-column header as process_export.py writes) before requesting the next page; page payloads are too heavy to hold several in context and transcribe at the end.
3. Video search (if enabled): `search_video` with visual-description variants. Same 1-2 page discipline. Expect low yield: video matching surfaces many brand accounts and low-post-rate profiles, so a page with one or two qualifiers is normal, not a sign the query failed.
4. Lookalike search (if enabled). Seed with TikTok HANDLES, never internal creator IDs: an ID seed silently returns zero results with no error, which looks like an empty niche when it's actually a malformed seed. Run MULTIPLE seed passes, not one:
   - Pass A, top performers: pull the client's top creators by GMV with `creators_performance` (last 90 days, sorted by gmv desc). Take the top 30-50 handles if available; if the shop has fewer, use what exists. Fall back to `creators_list` sorted by shop_gmv for younger shops with thin recent data. If page 1 of `creators_list` (sorted by shop_gmv) is already in context from the exclusion pull, seed directly from those handles instead of making an extra `creators_performance` call.
   - Pass B, all GMV-generating creators: seed from the shop's full set of creators who have generated GMV, not just the top tier. If the shop has a CRM group or list for GMV-generating creators, seed with `seed_crm_group_id` / `seed_list_id` directly. Otherwise pull all creators with shop GMV > 0 via `creators_list` and chunk the handles into batches of up to 50 seeds, one `search_lookalike` call per batch. Mid-tier sellers surface different neighborhoods than whales.
   - Pass C, random subsets: shuffle the seed pool and run 1-2 extra passes with randomized 25-seed subsets, since different seed compositions surface different results.
   - Lookalike has no export either: 1-2 pages per pass, appending qualifiers to `raw/lookalike.csv` as you go. Seeds are automatically excluded from lookalike results, but not from the other modes' results, so still dedupe globally.
5. Competitor affiliates via SI (if SI access is enabled and the user confirmed competitors):
   - For each confirmed competitor, resolve the seller_id via `get_sellers` (search by brand name).
   - Pull their creators with `get_seller_creators`, sorted by gmv28d desc, passing the agreed floors server-side via `min_gmv` and `min_post_rate` (SI natively filters post rate, unlike AI search). Paginate all pages at page_size 100.
   - Only use `si_export_seller_creators` when a competitor's filtered creator count is too large to page through comfortably; it costs one of the shop's limited daily exports (shared with portal exports), so prefer paging. If you do export, check `truncated` before treating the result as complete.
   - These creators are proven affiliate sellers in the exact niche, so they're often the highest-intent segment of the whole run. Bonus signal: a creator appearing under 2+ competitors is a strong candidate; flag those in the summary.
   - SI returns 28-day GMV (`gmv28d`), NOT lifetime GMV like the AI search modes. Keep the metrics in separate, clearly labeled columns; never mix them in one column.
   - Saturation check: if a same-niche competitor yields very few creators past the floors and a large share are already the client's affiliates, the audiences overlap heavily; deprioritize that competitor and spend the calls on larger adjacent sellers instead.
   - Spot-check bios for region mismatches (e.g. a creator in the UK universe whose bio says NZ) before the list ships.

All AI search endpoints (profile, transcript, video, lookalike) accept the same `filters` object documented in Step 3. Pass the agreed GMV / post rate / follower floors server-side on every mode. They are honoured to roughly 0.1 percent leakage on export, but transcript / video / lookalike results still need a client-side check before hand-appended rows go into the raw CSVs. SI competitor filters (`min_gmv`, `min_post_rate` on `get_seller_creators`) use their own names and are reliable server-side.

Exports now return a numeric `gmv` column alongside `gmv_segment`. Always filter on numeric `gmv`. `gmv_segment` is a rounded display string (e.g. `$2.1K`, `$1.9M`) and is NOT a band, so never parse it for a floor: an earlier version of this skill compared floors against a band's lower bound, and a $2,000 floor silently discarded every creator between $2,000 and $5,000. `process_export.py` reads numeric `gmv` and falls back to parsing `gmv_segment` only for exports saved before the column existed.

### Volume: as many as we can find

In precise mode there is no fixed volume target; the goal is to exhaust the pool, and the pool is smaller than people expect. Do NOT promise thousands from AI search. Quote the measured shape instead: roughly 60-140 qualifying creators per keyword query at a $2,000 GMV floor, converging on several hundred net-new for a niche after all modes and competitor mining. If the user needs thousands, that is a bulk-mode conversation, not more keyword rounds. Search totals tell you the ceiling: if a query reports thousands of matches, page 1 is a skim, not the harvest. Keep going until additional pages and variants stop producing new on-topic creators: pull pages 2-5+ of the strongest queries, build out 6-10 keyword variants, then broaden to adjacent angles (e.g. for a wig brand: braids, extensions, GRWM beauty, 40+ beauty). Expect floors to cut 30-50% of raw results, so overshoot on raw volume.

In regions where only profile mode is enabled (no lookalike/transcript/video), this matters even more: profile search is carrying the entire run, so double the variant count by default. Stop a query only when results go clearly off-topic or start repeating.

### Precise vs bulk: pick the mode before you search

These are two different jobs and they use two different mechanisms. Ask which one the user wants in the Step 1 message, because the answer changes everything downstream.

**Precise** is what the rest of this skill does: AI search across profile, transcript, video and lookalike modes, plus competitor mining, producing lists of named handles that genuinely match the niche. Expect **hundreds, not thousands**. Measured on a US Food & Beverage shop targeting fitness creators at GMV >= $2,000 and post rate >= 60: a single keyword query matches 3,456 creators, of which 137 clear the GMV floor and **62** clear both. Six or seven rounds across all modes plus competitor mining lands around **700 net-new**, and that is close to exhaustive for that niche at those floors, not a failure.

**Bulk** does not use AI search at all. It hands the automation a filter and lets Reacher resolve it against the whole creator universe on every run. Use `creators_to_include.filters` on `automation_create_target_collab` or `automation_update`, with `is_evergreen: true` so it re-evaluates continuously. Verified working field set:

| Field | Shape |
| --- | --- |
| `gmv` | `{"min": 2000}` |
| `post_rate` | `{"min": 60}` |
| `engagement_rate`, `units_sold`, `average_views` | `{"min": N}` |
| `product_categories` | `["Sports & Outdoor", "Health"]` |
| `follower_count`, `gender` | range / list |

The API translates these into the portal's filter shape (`Performance.GMV: ["custom:2000-"]`) and stamps `creator_source_type: "filters"`.

**The honest tradeoff, and do not hide it from the user.** Bulk filters have no topical targeting. There is no community, hashtag, topic or interest field on the API's filter set, so the only relevance lever is product category, and category is a weak proxy for a niche. Measured: of 6,330 creators matching `Sports & Outdoor` + GMV >= $2,000 + post rate >= 60, only **10%** had anything fitness-related in their bio. 87% were fashion, shoes, home and general-shopping accounts carrying a sports tag. So bulk buys volume by accepting that most recipients are adjacent rather than on-niche.

Say that plainly rather than reporting a filter's reach as if it were a targeted list. A run that returns 700 precise creators is not worse than one that reaches 20,000 loose ones; they are answers to different questions.

**Previewing a bulk filter's reach.** The dry run does NOT report a projected count. To size a filter before committing, create the automation with `dry_run: false` (it is created stopped, so nothing sends), then read `creators_remaining` from `automation_detail`. Report that number, then ask whether to start it. Never start it yourself.

**Combining them.** The strongest pattern is bulk for reach plus precise for quality, as two separate automations with different messages, so the results stay comparable. Do not pour a precise list into a bulk automation; you lose the ability to tell which one worked.

When the pool runs thin, escalate the cheapest lever first: (1) relax the floors with the user's OK, since dropping a GMV floor one tier often multiplies the addressable pool many times over; (2) broaden to adjacent niches and identities; (3) reseed lookalike from different creator subsets; (4) as a deliberate last resort, omit the query entirely on `search_creators`/`export_creators`, which switches to browse mode and returns the region's top creators unfiltered by topic. Browse mode trades targeting for raw volume, so only use it knowingly and label those rows' source query as "browse" so the client can treat them differently in outreach.

## Step 4: Mix, dedupe, and filter

- Run `scripts/finalize_lists.py` against the raw per-method CSVs: it dedupes by handle across methods (by the overlap precedence from Step 5), drops handles in the exclusion file, and writes the final per-method CSVs with removal counts for the summary. Don't hand-roll this step; a fresh script rewritten each run is where transcription bugs creep in.
- Interleave results round-robin across modes (profile, transcript, video, lookalike, repeat) rather than concatenating one mode's full output first. This keeps the final list diverse instead of front-loaded with one mode's bias.
- Verify the agreed quality floors on every candidate using the fields returned (gmv, post_rate, follower_count, engagement); server-side filters should have done most of this, so this is a safety net. If post rate is missing on a candidate's record and can't be verified, keep the creator but note in the summary that the post rate floor should also be enforced at outreach/automation time via performance criteria.
- Remove excluded creators per the brand's Step 1 choice. FIRST check `total_count` on page 1 of each exclusion source before committing to paginate:
  - Small sets (under ~500 rows): pull all pages. Active creators via `creators_list`, campaign-linked via `list_managed_creators`, sampled via `samples_list`.
  - Invited creators are the hard case: `automations_list` reports per-automation reach COUNTS, not handles. Enumerating handles requires `automation_creators` per automation, which is only feasible for a handful of automations; a shop with dozens of automations and thousands of reached creators has no enumerable invited set. When invited counts dwarf what you can pull, state that plainly, exclude what you have, and rely on Reacher's server-side skip of previously-contacted creators at send time.
  - Large sets (mature shops can have 5,000-10,000 affiliates and thousands of sample rows): full pagination is not feasible in a chat session. Do best-effort exclusion against the top pages sorted by GMV plus any handles already seen in context, state the coverage gap explicitly in the summary, and rely on Reacher's server-side skip of previously-invited/connected creators at automation send time (visible as `skipped` counts on TC runs). Never silently claim full exclusion.

## Step 5: Deliver as separate lists per method

`list_create` exists in the API but is permission-gated: some keys are read-only and won't expose or allow it, while keys with write scope will. Attempt `list_create` first; if the tool is absent from the registry or the call fails with a permission error, you're on a read-only key. Then fall back to one import-ready CSV per sourcing method (saved to outputs and presented to the user) formatted for the portal's list import, or offer to create the lists in the portal via Claude in Chrome. Either way, keep one list/file per sourcing method so the methods can be tracked and compared in outreach:

1. Keyword list: creators found via keyword-driven searches (profile, transcript, video). Name it e.g. "Sourced 2026-08-19 - keywords - plus size fashion".
2. Lookalike list: creators found via lookalike seeding. Name it e.g. "Sourced 2026-08-19 - lookalikes - plus size fashion".
3. Competitor list: creators mined from confirmed competitors via SI. Name it e.g. "Sourced 2026-08-19 - competitors - plus size fashion".

A creator found by multiple methods goes into exactly one list, by precedence keyword > lookalike > competitor, so no creator gets targeted twice if all lists feed automations. (This is the default; the user can ask for overlap handled differently.) If a method wasn't run (region not enabled, no SI access, user declined competitors), skip its list and say so in the summary.

Then give the user a short summary in chat:
- Total unique creators found, split per list (keyword vs lookalike vs competitor) and per mode/keyword variant/competitor
- How many were removed by dedupe, floors, and exclusions
- Creators found under 2+ competitors, called out as high-intent
- All list names/IDs in Reacher
- 10-15 sample handles with follower count and GMV so they can sanity-check quality
- Any modes skipped (region not enabled) or floors that couldn't be applied at search time
- A compact ledger block for repeat runs: one line per query with the date, exact query text, floors, total pool, and qualified yield. Sourcing for the same shop tends to recur, and a fresh session has no memory of past runs, so this block is what lets the next run avoid re-searching the same phrasings before the pool has had time to refresh. If the user pastes a ledger from a previous run (or one exists in project files), respect it: skip queries run within the last 2-3 months and treat queries whose yield was near zero as exhausted rather than retrying them.

## Step 6: Route the list into an EXISTING automation

Only run this when the user asks for the list to feed outreach. The hard rule: **this skill never calls `automation_create_*`.** Sourcing attaches to automations that already exist, or it hands back an unattached list. Creating automations is `automation-creation`'s job, and doing it here is how a shop ends up with 87 automations nobody can reason about.

1. Enumerate candidates with `automations_list` (filter to the relevant `automation_type`, `exclude_created_via: ["api_direct"]` to hide single-creator direct invites).
2. For each plausible candidate, call `automation_detail` and read `details.targeting.filters.Creators.Community` — that hashtag set IS the segment definition. Also record `include_lists`, since attaching means adding to that array, not replacing it.
3. Score the sourced batch's tags against each segment and apply BOTH gates, via `scripts/route_to_automation.py`:
   - **Coverage** — the top segment must match >= 30% of the batch's tags.
   - **Margin** — the top segment must beat the runner-up by >= 50% relative.
4. On a confident match, propose it and **wait for an explicit yes**. On ambiguity, present the ranked candidates and ask, always offering "hold the list unattached" as a third option.
5. Attach with `automation_update(automation_id, creators_to_include.lists_selected=[<new_list>, ...existing])`. Never drop the existing list ids.

Why the margin gate exists, measured on two real segments from one shop: a batch tagged for "healthy snack ideas for kids' lunchboxes" scores **Family Segment 62% / Food Segment 50%**. Family wins outright, so a naive highest-score router attaches silently — and that is precisely the wrong-segment-into-wrong-automation failure. A 12-point gap is not a decision; it is a question. By contrast a mukbang/ASMR taste-test batch scores Food 100% / Family 0% and routes cleanly.

## Step 7: Re-engagement — the three recipient settings

"Only creators never contacted" is the single biggest reason a sourced list looks too small. Three settings control this, and they are already in the API — do not rebuild this logic out of per-creator outcome pulls.

| # | Setting | Where | What it does |
| --- | --- | --- | --- |
| 1 | `exclude_previously_messaged` | `creators_to_exclude`, bool, default `false` | `true` skips everyone this shop has ever DM'd. Leave `false` to let non-responders back in. This is the on/off switch for the whole problem. |
| 2 | `auto_resolve_conflicts` | top level, default `MOVE_NOT_ACCEPTED` | Governs creators holding a pending TC invite from another automation. `SKIP_ALL` leaves them alone, `MOVE_NOT_ACCEPTED` re-targets those who never accepted, `MOVE_ALL` re-targets regardless. |
| 3 | TC Cleanup automation | `automation_create_tc_cleanup` | Purpose-built re-targeting of creators who got a TC invite and did not accept, scoped by `invite_start_before_days` (invite sent at least N days ago) and `invite_expire_after_days` (expiring within N days). |

Recommended default for a re-engagement pass: `exclude_previously_messaged: false`, `auto_resolve_conflicts: MOVE_NOT_ACCEPTED`, and a TC Cleanup automation with `invite_start_before_days: 14` for the never-accepted tail. Setting 3 is an existing automation type, so routing into it still goes through Step 6 rather than creating one here.

State which of the three is in play in the run summary. A list built with `exclude_previously_messaged: false` is not comparable to one built with it `true`, and quietly switching it makes week-over-week volume look like a sourcing win when it is a settings change.

## Step 8: Report the runway

Every run ends with a runway block, per segment, so nobody has to do this arithmetic by hand:

- **Never-contacted remaining** — `creators_remaining` from `automations_list` for the automation covering that segment.
- **Burn rate** — the segment's daily cap from `details.schedule.daily_caps`, or observed `creators_reached` per day if that is lower.
- **Days to exhaustion** — remaining / burn rate.
- **Warn at <= 3 days.** Name the segment, the number, and the date it runs dry, then propose the cheapest refill: relax the floors, add keyword variants, run the browse recipe above, or flip to a re-engagement pass via Step 7.

Report this even when the runway is healthy. A number that only appears when it is bad reads as an alarm; a number that appears every week is a plan.

Do not send any invites, DMs, or samples from this skill. Sourcing ends at the saved list, or at an explicitly-confirmed attach to an existing automation. If the user wants a NEW automation built, that's `automation-creation`.

## Practical notes

- Write results to container files incrementally after each search (the bundled scripts do this for exports; append transcript/video/lookalike qualifiers by hand as you go). Never compile the final lists from conversation context at the end: context is lossy at this volume and transcription errors creep in. The exclusion handle set should also live in a file, one handle per line.
- Do not treat a few hundred net-new as a failed run. At a $2,000 GMV floor with a 60% post-rate floor, the floors remove about 98% of every AI-search result set, so several hundred qualified creators for a niche is the expected shape. Report each search's `total` ceiling alongside the qualified count so the user can see where the cut happened, and name the floors as the lever rather than running more rounds against an exhausted pool.
- Volume goal is "as many as possible", so err on the side of more keyword variants, not fewer. Stop a query when results go clearly off-topic or repeat.
- If two clarifying answers conflict (e.g. "no floors" but also "only proven sellers"), surface the conflict instead of guessing.
- If list creation is unavailable (read-only key) or fails, fall back to per-method CSVs (works for all modes) or `export_creators` (profile-mode only), and tell the user which path was used.
- Keep the user's time cheap: one consolidated clarifying message up front, then run the whole pipeline without further questions.
