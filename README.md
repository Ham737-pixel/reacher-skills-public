# Reacher Skills

Claude Agent Skills for running a TikTok Shop affiliate program on
[Reacher](https://reacher.com).

Each skill is a folder with a `SKILL.md` inside it. Claude reads the skill's
description, decides on its own when it applies, then follows the instructions
in the file: which Reacher API calls to make, in what order, how to handle the
edge cases, and what the finished deliverable should look like.

The result is that "find me 5,000 new creators in this niche" or "turn this
list into an outreach automation" becomes one sentence instead of an afternoon.

## The skills

| Skill | What it does |
| --- | --- |
| **creator-sourcing** | Sources net-new affiliate creators using multi-mode AI search (profile, transcript, video, lookalike), competitor-affiliate mining, keyword variation, and lookalike seeding off your own top performers. Excludes creators you already work with, applies quality floors, reports remaining runway per segment, and writes the result out as Reacher lists. |
| **competitor-analysis** | Identifies a brand's top 5 competitors via product mapping, then breaks down what they are doing — top products, video formats, hooks, creator strategy — pulls category-wide trends, benchmarks the brand against ecosystem peers, and ends in prioritized recommendations. |
| **brief-creation** | Builds the creator brief that tells creators what to film, as an image poster or a video-derived document. Groups the catalogue into pack families, grounds the copy in the hooks and structure that actually earned on your own videos, renders a preview you can look at before anything ships, and attaches it to the automation that reaches creators at the Sample Approved stage. |
| **automation-creation** | Turns a sourced batch of creators into one Target Collab outreach automation. Fills a known-good template, runs a preflight check and a dry run, creates the automation **stopped**, returns the ID, and then asks whether to start it. It never starts an automation on its own. |

They are designed to run in sequence — source, then analyze the competitive
picture, then launch — but each works on its own.

## Install

### Claude Code

Copy the skill folders you want into your skills directory. The folder name
must match the `name:` in the skill's frontmatter.

```bash
git clone https://github.com/ReacherApp/reacher-skills-public.git

# available in every project
cp -R reacher-skills-public/creator-sourcing ~/.claude/skills/

# or scoped to one project
mkdir -p .claude/skills
cp -R reacher-skills-public/automation-creation .claude/skills/
```

Then ask for the work in plain language — "source creators for my shop" — and
Claude loads the matching skill on its own. `/skills` lists what is available.

### Claude.ai

Settings → Capabilities → Skills → **Upload skill**, and upload the skill
folder as a `.zip`. Zip the folder itself, so `SKILL.md` sits one level down.

```bash
cd reacher-skills-public && zip -r creator-sourcing.zip creator-sourcing
```

## What you need

- A **Reacher account** and an API key scoped to your shop.
- The **Reacher connector** enabled in Claude, with tools set to *Always
  allow* — an unanswered permission prompt will kill a long sourcing run
  halfway through.
- **Social Intelligence** access on the shop, for `competitor-analysis` and
  the competitor-mining half of `creator-sourcing`. Without it those steps
  skip cleanly and the rest still runs.
- **Python 3** for the bundled scripts under `creator-sourcing/scripts/`.

Put your API key in the connector's own authentication screen. Never paste it
into a chat, a doc, or a skill file, and rotate any key that has been.

## How these skills behave

**Every number comes off the API.** Nothing is estimated. When a field is
missing, the output says it is missing rather than filling in a plausible
number, and each run ends with the caveats that actually applied.

**The shop is always confirmed first.** Skills call `list_shops` and resolve
the `shop_id` before pulling anything. They do not infer which brand you meant
when more than one is connected.

**Nothing sends without a human.** `automation-creation` creates outreach in a
stopped state and hands back the ID for a person to start. No skill here
messages a creator or changes ad spend on its own. `creator-sourcing` will
attach a list to an existing automation only after you explicitly confirm the
target, and will never create an automation itself.

**They degrade gracefully.** A skill that loses a capability says so and
continues on what it can still reach.

## Notes on the bundled scripts

`creator-sourcing/scripts/` carries three helpers so the data handling isn't
reinvented (buggily) on each run:

- `process_export.py` — parses an export result, re-checks the quality
  floors, and appends qualifiers to a per-method CSV. Floors should be
  passed server-side on the export call; this is the client-side safety
  net for the small fraction that leaks through. Still parses older
  exports saved before the numeric `gmv` column existed.
- `finalize_lists.py` — global dedupe, exclusion filtering, final per-method
  CSV output.
- `route_to_automation.py` — scores a sourced batch against existing
  automations' segment definitions and only proposes a target when one wins
  clearly. Read-only; it never attaches anything itself.

## Contributing

Open a pull request. Keep one skill per folder, keep `name:` in the
frontmatter identical to the folder name, and write the `description:` so it
covers the phrasings a real person would actually use — that description is
the only thing Claude sees when deciding whether to load the skill.
