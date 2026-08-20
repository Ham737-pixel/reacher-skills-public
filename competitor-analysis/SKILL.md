---
name: competitor-analysis
description: Run a TikTok Shop competitor analysis for a Reacher client using Social Intelligence - identify the brand's top 5 competitors via product mapping, break down what they're doing (top products, video formats, hooks, creator strategy), pull category-wide trends, benchmark the brand against ecosystem peers, and deliver prioritized recommendations. Use this skill whenever the user asks who a brand's competitors are, what competitors are doing, for a competitive or market analysis, category benchmarks, trending products in a niche, which hooks or formats are working in a category, or how a brand compares to similar shops, even if they don't say "competitor analysis". Requires the Reacher connector and Social Intelligence access on the shop.
---

# Competitor Analysis

Answer four questions for a Reacher client's brand, grounded entirely in Social Intelligence (SI) data: (1) who are our top ~5 competitors, (2) what are they doing that works — products, formats, hooks, creators, (3) how do we compare to them and to the wider category, (4) what should we focus on next.

The core idea: competitors are derived from products, not guessed from brand names. Map the brand's top products to similar SI products, see which sellers keep showing up, rank them, confirm with the user, then deep-dive each one and contrast against the brand's own numbers and the category baseline.

This skill is analysis-only. It never creates automations, sends outreach, or modifies anything. If the user wants the competitors' affiliates sourced as creators afterwards, that's the creator-sourcing skill (competitor mining pass) — offer the handoff, don't do it here.

## Step 0: Identify the shop and verify SI access

Resolve the client to a shop_id with `list_shops`; ask if ambiguous. All SI endpoints require a single integer shop_id (never 'all').

SI is gated per customer. On shops without access, SI endpoints return a plain `404 NOT_FOUND` — not a 403 or a permissions message. Probe cheaply with `get_seller_categories` first. A 404 means no SI: don't retry with different parameters. This skill cannot run meaningfully without SI, so say so plainly and stop; the only partial fallback worth offering is an own-shop creative review via `videos_creative` (which needs no SI).

## Step 1: Profile the brand

Before looking outward, establish the inward baseline:

- `products_list` (own shop, last 28 days): top products by GMV, price points, and the product category. This is the raw material for competitor mapping.
- `get_sellers` with `search` = the brand name: find the brand's own SI seller record and its rank in the ecosystem. The response includes a `yourBrand` rank marker for the shop — note where the brand sits in its category.
- `get_seller_detail` on the brand's own seller_id: gmv28d, creator count, video count, rating — the numbers every competitor gets compared against.
- `videos_creative` (own shop): the AI creative breakdown of the brand's own top videos — hook, sell points, shot style, videography. This is what "what competitors do differently" is measured against, so capture it before analyzing anyone else.

Consolidate any clarifications into ONE short message (per the user's known preferences — never an interrogation):
1. Time window. Default: 28 days (SI's native gmv28d window). Confirm if they want longer for trend context.
2. Known competitors. Ask if they can name direct competitors they already watch — user-named competitors go straight onto the shortlist and skip the mapping vote for their slots.
3. Deliverable. Default: analysis report in chat. Ask only if there are signals they want a client-facing document (deck, PDF).

If the user already answered any of these, restate rather than re-ask.

## Step 2: Map products to competitors

Derive competitor candidates from product overlap, in this order:

1. For each of the brand's top 3-5 products by GMV, call `get_products` with `search` = the product's core noun phrase (strip brand names and marketing adjectives: "XGlow Vitamin C Brightening Serum 30ml" → "vitamin c serum") plus the `category` filter. Note the seller of every similar product on the first 1-2 pages.
2. Run `get_sellers` filtered to the brand's category (and subcategory when it exists), sorted by gmv28d, first 1-2 pages. This catches category leaders whose flagship phrasing didn't match the product searches.
3. Score candidates: +1 for each of the brand's products that maps to one of theirs (product overlap count is the primary signal), weighted toward sellers in the same or the next GMV tier up. Same-tier competitors show what's achievable now; one-tier-up competitors show the playbook to copy. Exclude marketplace aggregators and mega-generalists (sellers whose catalog spans unrelated categories) — they surface constantly and pollute every analysis.
4. Rank the top 5 with one line of evidence each ("3 overlapping products, same GMV tier, #4 in category"). Present the shortlist, then read the room on whether to pause: if the user has signaled they just want the analysis ("run it", "just give me the report", or they push back on a pause), or this is a stated quick look, proceed straight into the deep dives and note they can swap names for a re-run. Only wait for confirmation when the shortlist is genuinely uncertain (weak overlap evidence, ambiguous niche) or the user seems invested in choosing. Don't burn call volume on sellers the user doesn't consider real competitors, but don't stall a clear run on ceremony either.
5. Before deep-diving, validate each candidate with `get_seller_detail` — see the GMV attribution warning in Practical notes. A candidate that ranked on product GMV but shows near-zero seller-level GMV has a weak creator engine; keep it in the report as a finding (one line) but pull the next-ranked candidate into the full deep-dive slot.

Product mapping beats name searching because TikTok Shop competitors are often unknown white-label sellers, not the brands the client thinks of as rivals. Present surprising entries as findings, not errors.

## Step 3: Deep-dive each confirmed competitor

For each of the 5, in a consistent order so profiles are comparable:

1. `get_seller_detail`: gmv28d, all-time GMV, creator count, video count, rating. Compute GMV-per-creator and GMV-per-video — efficiency ratios expose strategy differences that raw totals hide (e.g. "they do 3x our GMV with the same creator count" is a content-quality story; "same GMV, 5x creators" is a volume-spray story).
2. `get_seller_products` sorted by gmv28d, page 1: their trending products, price points, bundle structure. Flag products trending for them in niches the brand also covers but isn't pushing — those are the whitespace findings.
3. `get_seller_videos` sorted by gmv, 1-2 pages: their top videos WITH the AI content tags — `hookType` and `sellingPoints` are attached to top performers. Tally hook types and selling points across the top ~20-40 videos per competitor; the distribution is the finding, not any single video. Note views-to-GMV efficiency and posting recency. AI tags exist only on top performers — untagged videos still carry metrics; tally tags over the tagged subset and say what fraction was tagged rather than treating untagged as "no hook".
4. `get_seller_creators` page 1 sorted by gmv28d, plus the total count: creator strategy shape — how many creators, how concentrated (does the top page account for most GMV or is it long-tail?), typical follower sizes. Don't paginate deep; the shape is the point, not the roster. Never use `si_export_seller_creators` here — it costs one of the shop's limited daily exports and the export belongs to sourcing runs, not analysis.

Write per-competitor findings to a working file in the container as you go (one section per competitor). Five deep-dives generate more rows than conversation context reliably retains, and the synthesis step needs accurate tallies, not remembered impressions.

## Step 4: Category baseline

Two calls put the competitor set in context so "everyone does unboxing hooks" doesn't get reported as one competitor's genius move:

- `get_trending_videos` filtered to the brand's category, sorted by gmv, 1-2 pages: category-wide winning formats and hooks (same AI tags). Tally hook types here too — this is the baseline distribution.
- `get_products` for the category sorted by gmv28d and again by unitsSold, page 1 each: what's trending in the category overall, including product types nobody on the competitor list sells yet.

## Step 5: Benchmark the brand

- `get_insights_overview`: the brand vs TikTok Shop ecosystem peers in its GMV segment — funnel comparison and content-unfulfilled metrics. This is the "unlike the benchmarks" anchor: where the brand's funnel leaks relative to peers.
- Contrast the brand's own creative profile (from Step 1's `videos_creative`) against the competitor and category hook/format tallies: which winning hooks and formats is the brand not using at all? Which is it using but executing below category efficiency?
- Metric hygiene: SI reports gmv28d; own-shop endpoints like `products_list` and `creators_list` report lifetime or windowed GMV. Never mix them in one comparison — label every number with its window, and when comparing brand vs competitor GMV always use SI's own record of the brand (from `get_seller_detail`) so both sides are the same 28-day metric.

## Step 6: Synthesize and recommend

Structure the output as findings → so-what → do-this. Every recommendation must trace to a specific data point from the run; no generic TikTok advice ("post consistently") that could be written without the data.

Report skeleton:

1. **Landscape** — where the brand ranks in its category, the confirmed top 5 with one-line profiles, GMV tiers.
2. **Per-competitor breakdown** — for each: scale and efficiency ratios, top/trending products, dominant hook types and selling points, creator strategy shape, and the single biggest thing they do differently from the brand.
3. **Category trends** — winning formats/hooks category-wide, trending products, and which of these the competitor set has or hasn't caught onto yet.
4. **Benchmarks** — insights_overview funnel vs peers, brand's creative profile vs category baseline.
5. **Gaps and whitespace** — hooks/formats the brand doesn't use, product angles trending for competitors that the brand covers but doesn't push, creator-strategy deltas (e.g. brand is concentrated where competitors run long-tail).
6. **Recommendations** — 3-5, prioritized, each citing its evidence ("Competitor X's top 8 videos all use problem-solution hooks on the serum line; our top videos are 80% unboxing; test problem-solution on product Y").

Deliver the report in chat by default. If the user wants a client-facing document, offer the pitch-deck or case-study slides skills for a polished version, or a plain document — but only build one when asked.

Close by offering the natural next step: sourcing the confirmed competitors' affiliates via the creator-sourcing skill (its competitor mining pass takes the exact seller_ids from this run).

## Practical notes

- Commission rates: SI's `openCollabCommissionRate` is the PUBLIC open collab rate only. Target collab offers are private and unknowable from SI, and are often higher for the creators actually driving top videos. Never present open collab rates as "what this competitor pays," and never compare them against the brand's own blended actuals (est_commission/GMV mixes open collab and TC payouts). What open collab rates CAN support: whether a competitor tiers its public rates across SKUs (hero concentration signal), and how the brand's own public rate compares for open collab discoverability.
- GMV attribution mismatch (bit a real run): product-level `gmv28d` from `get_products` counts ALL channels — ads, product card, shop tab — while seller-level `gmv28d` from `get_seller_detail` reflects the creator/affiliate side. A seller can show £11k across product cards but £2.4k at seller level; ranking competitors on product GMV alone overweights ad-driven sellers with dead creator programs. Always pull `get_seller_detail` before treating a candidate as a real creator-commerce competitor, and label which basis every GMV number uses in the report. The mismatch itself is reportable: "ranks on product GMV, creator engine dormant" is a different strategic animal than a true competitor.
- Budget roughly: 5-8 calls for mapping, 4-6 per competitor deep-dive, 3-4 for category + benchmark — ~35 calls for a full run. If the user asks for a "quick look", collapse to: propose competitors from one mapping pass, deep-dive the top 2, skip Step 4.
- gmv28d is a rolling window; two runs weeks apart aren't comparable row-by-row. If the user references a past analysis, re-pull rather than diffing against remembered numbers.
- If a confirmed competitor returns thin data (few videos, no tagged top performers), say so and substitute the next-ranked candidate rather than padding the analysis.
- If the brand itself doesn't appear in SI (`get_sellers` search misses it), benchmarking still works via `get_insights_overview`, but note that competitor GMV comparisons will mix SI 28d numbers with the brand's own Reacher-side numbers — label accordingly.
- Repeat runs recur per client (monthly/quarterly cadence is natural). End the report with a compact ledger line: date, window, confirmed competitor seller_ids, and headline hook distribution — so the next run can diff against something concrete if the user pastes it back.
