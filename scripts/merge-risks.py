#!/usr/bin/env python3
"""Merge several threagile risks.json files into one, de-duplicated by synthetic id.

The default analysis is STRIDE-only, so findings from the fork's cross-cutting
rule packs (cloud-native / supply-chain / ai-ml) never reached the issue sync.
Each pack run supersets STRIDE, so we union them and drop duplicates, keeping the
first occurrence of each synthetic id (stable, deterministic order).

Usage:
  merge-risks.py <output.json> <input1.json> [<input2.json> ...]
"""
import json
import sys


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: merge-risks.py <output.json> <input...>")
    out_path, inputs = sys.argv[1], sys.argv[2:]

    seen, merged = set(), []
    for path in inputs:
        with open(path) as f:
            risks = json.load(f)
        for r in risks:
            sid = r.get("synthetic_id", "")
            if sid and sid in seen:
                continue
            seen.add(sid)
            merged.append(r)

    with open(out_path, "w") as f:
        json.dump(merged, f, indent=2)
    print(f"merged {len(merged)} unique findings from {len(inputs)} file(s) into {out_path}")


if __name__ == "__main__":
    main()
