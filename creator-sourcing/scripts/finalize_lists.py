#!/usr/bin/env python3
"""Global dedupe + exclusion filter across all raw per-method CSVs, then write final per-method CSVs.

Usage:
  python3 finalize_lists.py --raw-dir raw --exclude exclude_dedup.txt --out-dir out \
      [--precedence keyword,transcript,lookalike,video,competitor]

Reads every <raw-dir>/<method>.csv (written by process_export.py or appended by hand
for transcript/video/lookalike/competitor rows using the same 9-column header).
Drops handles in the exclusion file (one handle per line, case-insensitive),
dedupes across methods by the precedence order (earlier method keeps the creator),
and writes <out-dir>/<method>.csv for each method that has survivors.
Prints per-method counts plus how many rows were removed as excluded vs cross-method dupes.
"""
import csv, os, sys, argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--raw-dir', default='raw')
    ap.add_argument('--exclude', default=None)
    ap.add_argument('--out-dir', default='out')
    ap.add_argument('--precedence', default='keyword,transcript,lookalike,video,competitor')
    a = ap.parse_args()

    excl = set()
    if a.exclude and os.path.exists(a.exclude):
        excl = {l.strip().lower() for l in open(a.exclude) if l.strip()}

    order = [m.strip() for m in a.precedence.split(',') if m.strip()]
    # any raw files not named in precedence go last, alphabetically
    present = [f[:-4] for f in os.listdir(a.raw_dir) if f.endswith('.csv')]
    methods = [m for m in order if m in present] + sorted(m for m in present if m not in order)

    seen, stats = set(), {'excluded': 0, 'dup': 0}
    os.makedirs(a.out_dir, exist_ok=True)
    for m in methods:
        path = os.path.join(a.raw_dir, f'{m}.csv')
        with open(path) as f:
            reader = csv.reader(f)
            header = next(reader)
            kept = []
            for row in reader:
                h = (row[0] or '').strip().lower()
                if not h:
                    continue
                if h in excl:
                    stats['excluded'] += 1
                    continue
                if h in seen:
                    stats['dup'] += 1
                    continue
                seen.add(h)
                kept.append(row)
        if kept:
            with open(os.path.join(a.out_dir, f'{m}.csv'), 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(header)
                w.writerows(kept)
        print(f'{m}: {len(kept)}')
    print(f"removed as excluded: {stats['excluded']}, cross-method dupes: {stats['dup']}")

if __name__ == '__main__':
    main()
