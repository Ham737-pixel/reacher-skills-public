---
name: automation-creation
description: >
  Create one Target Collab outreach automation on a Reacher shop from a creator-sourcing
  manifest, reliably and without failing quietly. Use this skill WHENEVER the user asks to
  "create the automation", "launch outreach from this list", "make the Target Collab
  automation", "turn this list into an automation", "set up the outreach", or hands over a
  sourced batch of creators to be turned into a running automation. It fills a frozen
  known-good template, validates with a preflight check and a dry run, creates the
  automation in a stopped state, returns the automation ID, and then always asks whether
  to start it. It NEVER starts an automation itself. Do NOT use this to source creators
  (that is creator-sourcing) or to build reports.
---

# Reacher Automation Creation

This skill turns a sourced list into one Target Collab automation. It is the only skill
that touches the create endpoint, so it is built to be impossible to break quietly. The
create payload is large and several of its validators hard-fail with a 422, so the design
shrinks the decision surface to almost nothing, validates before calling, and never
persists without a dry run first.

The output is one automation, created **stopped**, with its ID returned. The skill then
asks whether to start it now or leave it for the operator to start in the portal. It does
not start automations. Starting is a human decision, every time.

## The one-automation model

Do not spawn a new automation per list. One outreach automation holds the whole pool,
capped at 10,000 a day. It dispatches 10,000, self-pauses when it hits the daily limit,
and resumes when the window resets at 00:00 UTC. When its runway (`creators_remaining`)
drops below 20,000 (two days), the sourcing skill produces a fresh batch and those
creators are appended to this same automation's list. `exclude_previously_messaged` keeps
it from ever re-hitting anyone. So this skill usually creates the one automation once, and
after that the work is feeding it, not rebuilding it.

## Before creating anything

1. **Confirm the shop** with `list_shops`.
2. **Load the tools first.** Reacher MCP tools are deferred. Call `tool_search` before the
   first Reacher call.
3. **Ensure a support contact exists.** Target Collab creates require a support email, or
   they reject with 422 `SUPPORT_CONTACT_REQUIRED`. Default the support contact to the
   shop's account email on file. Better still, set it once as the shop default with
   `target_collab_set_support_contact_default`, after which every create can omit the
   field. Do not invent a client-facing email for a shop whose account email you do not
   know; ask for it or set the default first.

## The frozen template

Bake this known-good payload in and fill only the four variable slots. Everything else is
pre-decided so the model cannot get it wrong. The copy skeleton that has held up best:
audience hook, one product fact, the commission ladder, a low-pressure close, no income
claims.

```
automation_name           <- segment_name from the manifest
creators_to_include        { "list_upload": <handles> }  OR  { "lists_selected": [<list_id>] }
schedule                   10,000 on every one of the seven days, timezone America/Los_Angeles
is_evergreen               true
exclude_previously_messaged true  (under creators_to_exclude)
idempotency_key            deterministic UUID from shop + segment + week + floor
target_collab.invitation_name   <- the brand name           (<= 30 chars)
target_collab.message           <- copy_variant template  (<= 500 chars, no "amazon")
target_collab.content_type      "no_preference"
target_collab.products          [{ "product_id": <hero product>, "commission_rate": <rate, 0-1> }]
target_collab.sample_policy     { "offer_free_samples": true, "auto_approve": false }
target_collab.support_contact   { "email": <shop account email> }   (omit if shop default set)
```

The four variable slots are `segment_name`, the creator selection (`list_id` or
`handles`), `copy_variant`, and `gmv_floor` (which is already applied at search time and is
carried only as a label, never sent to the create). Nothing else varies run to run.

**The daily cap is always 10,000 on every day, never lower.** Set
`Monday_maxCreators` through `Sunday_maxCreators` to 10000 each. A cap below 10,000 is the
exact bug that has throttled outreach in practice: a 30-per-day cap against a 30,000
creator pool would take 2.8 years to clear. The whole point of the one-automation
model is that one automation carries the full daily allowance, which only works if its cap
is the full 10,000. If a lower cap is ever wanted for a deliberate test, say so explicitly;
the default is never anything but 10,000.

## Creator selection: lists mode only

Populate exactly one of `list_upload` or `lists_selected`, and never `filters` or
`crm_group_id`. Mixing selection modes is the easiest way to trip a 422. Pushing all the
targeting (niche, floor, lookalike) into the sourcing skill keeps this skill in lists mode
always, which is what makes it reliable.

## Preflight validator

Before any create, assert these yourself and stop with the exact failing field if any
fails. Do not call the API on a bad payload.

- `invitation_name` is 1 to 30 characters.
- `message` is 1 to 500 characters and does not contain the word "amazon" (the portal
  rejects it).
- every `commission_rate` is between 0 and 1 (0.15 for 15 percent, not 15).
- the schedule sets every day's cap to 10,000 (never a smaller throttle like 30; that was
  the throttle bug above). Reject any day above 10,000, and flag any day below it.
- exactly one creator-selection mode is populated.
- the list or handle set is non-empty (a create that reaches nobody is the worst silent
  failure).
- `idempotency_key` is a fresh UUID v4, derived deterministically so a retry is safe.

## The create sequence

1. **Dry run.** Call `automation_create_target_collab` with `dry_run: true`. Read back that
   it validated and the projected `creators_remaining`. If it rejects, surface the exact
   field it names (the API forbids unknown fields and returns descriptive errors) and fix
   it. Do not proceed on a failed dry run.
2. **Create stopped.** Call again with `dry_run: false`. The automation is created in a
   stopped state. Capture the returned automation ID.
3. **Verify it is not running.** Read it back with
   `automations_list_automations_list_post` and confirm the status is not Running.
4. **Return the ID and prompt.** Tell the user the automation is created and stopped, give
   the ID and the projected reach, and ask whether to start it now or start it themselves
   in the portal. Never start it in this skill.

If a write is blocked by an approval gate, report that plainly and hand over the exact
validated payload so the user can run it where writes clear. It is not a payload problem.

## Idempotency

Derive the key deterministically from shop, segment, and week (and floor for the week-1
test), so a retry after a transient error returns the cached result instead of creating a
duplicate. A fresh, different payload needs a fresh key, or the API returns 409.

## Refilling the one automation

When runway drops below 20,000, do not create a second automation. Take the next batch
from the sourcing skill and append those creators to this automation's existing list, then
let the evergreen re-scan pick them up. If appending to a running automation's pool is not
supported on the current API, the fallback is one evergreen automation pointed at a saved
list, where the refill adds to the list. Either way it stays one automation.

## Gotchas

- **`SUPPORT_CONTACT_REQUIRED`** if no support email and no shop default. Set the default
  once to remove this failure class for good.
- **`commission_rate` is 0 to 1**, not a percentage. 0.15, not 15.
- **The message rejects "amazon".** Keep it out of the copy.
- **`extra="forbid"`** means a typo'd field returns a 422 rather than being ignored. Use
  exact field names, which is why the frozen template matters.
- **Write approval gate.** Creates may be held for approval in some environments. That is
  not a payload error; the reads still work. Hand over the payload if a write cannot clear.
- **No em dashes** in the automation name or message copy.
