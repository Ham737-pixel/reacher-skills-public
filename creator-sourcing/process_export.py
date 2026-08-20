#!/usr/bin/env python3
"""Parse one export_creators tool result, apply quality floors, append qualifiers to a raw per-method CSV.

Usage:
  python3 process_export.py RESULT_JSON METHOD "QUERY LABEL" [--min-gmv 100] [--min-post-rate 60] [--raw-dir DIR]

RESULT_JSON is the saved tool-result file for one Reacher export_creators call.
Accepts either the tool-result array (first element has a 'text' field holding
{'raw': <csv>}) or a bare {'raw': <csv>} object.
Appends to <raw-dir>/<METHOD>.csv, creating it with a header on first write.
Prints "label: total=N qualified=M" so you can report per-query yields.

GMV: exports now return a numeric `gmv` column. The floor is applied against it
directly. `gmv_segment` is a rounded DISPLAY string ("$2.1K", "$1.9M"), not a
band, and is used only as a fallback for exports saved before `gmv` existed.
Parsing it as a band is what made a $2,000 floor behave like a $5,000 floor and
silently discard every creator between the two.

POST RATE IS ON A 0-100 SCALE, not 0-1. --min-post-rate 60 means 60%. Prefer
passing both floors server-side (performance.gmv.min / performance.post_rate.min);
this script is the client-side safety net for the ~0.1% that leaks through.

Column fallbacks: browse-mode exports used to return post_rate / engagement_rate
/ average_views EMPTY, carrying the signals under *_segment columns instead. That
is fixed server-side, but the fallbacks are kept so previously-saved exports
still parse. The per-row source is recorded in the post_rate_source column.
"""
import json, csv, io, sys, os, re, argparse

def seg_lower_bound(seg):
    """Lower bound in dollars of a gmv_segment string. '$100-$1K' -> 100, '$50K+' -> 50000, '<$100'/'$0' -> 0."""
    if not seg:
        return 0
    m = re.match(r'^\$?([\d.]+)(K|M)?', seg.replace('<', '0-').lstrip('$<'))
    if not m:
        return 0
    v = float(m.group(1))
    if m.group(2) == 'K':
        v *= 1000
    elif m.group(2) == 'M':
        v *= 1000000
    return v

def _num(val):
    """Parse a numeric cell; return None when absent or unparseable."""
    if val is None:
        return None
    s = str(val).strip().replace('%', '').replace(',', '')
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None

# primary column -> legacy fallback column
FALLBACKS = {
    'post_rate': 'fulfillment_rate_segment',
    'engagement_rate': 'engagement_rate_segment',
    'average_views': 'video_views_segment',
}

def resolve(row, col):
    """(value, source) for col, falling back to its browse-mode twin."""
    v = _num(row.get(col))
    if v is not None:
        return v, col
    alt = FALLBACKS.get(col)
    if alt:
        v = _num(row.get(alt))
        if v is not None:
            return v, alt
    return None, None

def load_rows(path):
    d = json.load(open(path))
    if isinstance(d, list):
        d = json.loads(d[0]['text'])
    return list(csv.DictReader(io.StringIO(d['raw'])))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('result_json')
    ap.add_argument('method')
    ap.add_argument('label')
    ap.add_argument('--min-gmv', type=float, default=100)
    ap.add_argument('--min-post-rate', type=float, default=60)
    ap.add_argument('--raw-dir', default='raw')
    a = ap.parse_args()

    rows = load_rows(a.result_json)

    qual, sources, no_rate = [], {}, 0
    for r in rows:
        gmv = _num(r.get('gmv'))
        if gmv is None:                       # pre-`gmv` export: parse the display string
            gmv = seg_lower_bound(r.get('gmv_segment', ''))
        pr, src = resolve(r, 'post_rate')
        if pr is None:
            no_rate += 1
            pr = 0.0
            src = 'missing'
        sources[src] = sources.get(src, 0) + 1
        if gmv >= a.min_gmv and pr >= a.min_post_rate:
            qual.append((r, pr, src, gmv))

    # A browse export with no usable post rate anywhere is the silent-zero trap.
    if no_rate == len(rows) and rows and a.min_post_rate > 0:
        print(f'WARNING [{a.label}]: no post_rate or fulfillment_rate_segment on any of '
              f'{len(rows)} rows, so --min-post-rate {a.min_post_rate:g} drops every one of them. '
              f'Re-run with --min-post-rate 0 and filter at outreach time instead.', file=sys.stderr)

    os.makedirs(a.raw_dir, exist_ok=True)
    out = os.path.join(a.raw_dir, f'{a.method}.csv')
    exists = os.path.exists(out)
    with open(out, 'a', newline='') as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(['handle', 'method', 'query', 'follower_segment', 'gmv',
                        'post_rate', 'post_rate_source', 'engagement_rate', 'avg_views', 'categories'])
        for r, pr, src, gmv in qual:
            eng, _ = resolve(r, 'engagement_rate')
            views, _ = resolve(r, 'average_views')
            w.writerow([r.get('creator_name') or r.get('handle'), a.method, a.label,
                        r.get('follower_segment', ''), f'{gmv:.0f}',
                        f'{pr:g}', src,
                        '' if eng is None else f'{eng:g}',
                        '' if views is None else f'{views:g}',
                        r.get('categories', '')])

    src_note = ' '.join(f'{k}={v}' for k, v in sorted(sources.items()))
    print(f'{a.label}: total={len(rows)} qualified={len(qual)} [post_rate source: {src_note}]')

if __name__ == '__main__':
    main()
