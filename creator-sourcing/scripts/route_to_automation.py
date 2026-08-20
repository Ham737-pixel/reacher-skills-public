#!/usr/bin/env python3
"""Match a sourced batch to an EXISTING automation, or refuse and ask.

Usage:
  python3 route_to_automation.py SEGMENTS_JSON BATCH_TAGS_CSV [--min-coverage 0.30] [--min-margin 0.50]

SEGMENTS_JSON is {automation_id: {name, list_id, community: [tags...]}} built from
automation_detail -> details.targeting.filters.Creators.Community for each
candidate automation. BATCH_TAGS_CSV is the comma-separated community/topic tags
the sourcing run actually targeted.

Two conditions must BOTH hold before this proposes a target:
  COVERAGE  the top segment matches >= min-coverage of the batch's tags
  MARGIN    the top segment beats the runner-up by >= min-margin (relative)

Anything else exits 2 with ranked candidates for the user to choose from. The
margin rule is the one that matters: on one shop's real segments a
"healthy snack ideas for kids' lunchboxes" batch scores Family 62% / Food 50%,
so a naive highest-score-wins router would silently attach lunchbox creators to
whichever segment edged ahead. That is the wrong-segment-into-wrong-automation
failure this guard exists to prevent.

This script NEVER writes. Attaching is a separate, explicitly-confirmed
automation_update call, and automation creation is out of scope entirely.
"""
import json, sys, argparse

def rank(batch_tags, segments):
    bt = set(batch_tags)
    out = []
    for aid, s in segments.items():
        hits = sorted(bt & set(s.get('community', [])))
        out.append({'automation_id': aid, 'name': s.get('name', aid),
                    'list_id': s.get('list_id'),
                    'coverage': len(hits) / len(bt) if bt else 0.0,
                    'matched_tags': hits})
    out.sort(key=lambda r: r['coverage'], reverse=True)
    return out

def decide(ranked, min_coverage, min_margin):
    if not ranked:
        return 'ASK', 'no candidate automations supplied'
    top = ranked[0]
    runner = ranked[1] if len(ranked) > 1 else {'coverage': 0.0, 'name': '-'}
    if top['coverage'] < min_coverage:
        return 'ASK', f"no segment explains >={min_coverage:.0%} of the batch (best {top['coverage']:.0%})"
    if runner['coverage'] > 0:
        margin = (top['coverage'] - runner['coverage']) / top['coverage']
        if margin < min_margin:
            return 'ASK', (f"{top['name']} {top['coverage']:.0%} vs {runner['name']} "
                           f"{runner['coverage']:.0%} — margin {margin:.0%} < {min_margin:.0%}")
    return 'PROPOSE', f"{top['name']} {top['coverage']:.0%} vs next {runner['coverage']:.0%}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('segments_json')
    ap.add_argument('batch_tags')
    ap.add_argument('--min-coverage', type=float, default=0.30)
    ap.add_argument('--min-margin', type=float, default=0.50)
    a = ap.parse_args()

    segments = json.load(open(a.segments_json))
    tags = [t.strip() for t in a.batch_tags.split(',') if t.strip()]
    ranked = rank(tags, segments)
    verdict, why = decide(ranked, a.min_coverage, a.min_margin)

    print(f"batch tags ({len(tags)}): {', '.join(tags)}\n")
    for r in ranked:
        print(f"  {r['coverage']:>6.0%}  {r['name']:<22} automation {r['automation_id']:<8} "
              f"list {r['list_id']}  matched: {', '.join(r['matched_tags']) or '-'}")
    print(f"\nVERDICT: {verdict}  ({why})")
    if verdict == 'PROPOSE':
        t = ranked[0]
        print(f"NEXT   : confirm with the user, then attach via\n"
              f"         automation_update(automation_id={t['automation_id']}, "
              f"creators_to_include.lists_selected=[<new_list_id>, '{t['list_id']}'])")
        sys.exit(0)
    print("NEXT   : show these candidates and ask which automation to attach to.\n"
          "         Always offer 'hold the list unattached' as an option.")
    sys.exit(2)

if __name__ == '__main__':
    main()
