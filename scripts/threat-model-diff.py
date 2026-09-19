#!/usr/bin/env python3
"""
scripts/threat-model-diff.py

Compares two Threagile risks.json outputs and surfaces new/removed risks.
Optionally reads threagile.yaml to check whether new critical/elevated risks
already have a risk_tracking entry (used to drive the pipeline gate).

Sets GitHub Actions step outputs:
  new_risks_count        — number of new risks introduced
  has_critical           — 'true' if any new risk is critical or elevated
  has_untracked_critical — 'true' if any critical/elevated new risk lacks tracking
"""
import json
import argparse
import os
import re
import sys


# ── Risk loading ──────────────────────────────────────────────────────────────

def load_risks(filepath):
    """Load a Threagile risks.json. Handles both list and dict formats."""
    with open(filepath) as f:
        data = json.load(f)
    if isinstance(data, dict):
        risks = []
        for risk_id, risk_data in data.items():
            risk_data['synthetic_id'] = risk_id
            risks.append(risk_data)
        return risks
    return data


# ── YAML risk_tracking loader ─────────────────────────────────────────────────

def load_tracked_ids(model_path):
    """
    Return the set of risk IDs that already have a risk_tracking entry in the
    Threagile model YAML. The model is split across files via `includes:` (one
    per feature), and the risk_tracking blocks live in those included files, so
    includes are resolved recursively. Returns an empty set if the file is
    unavailable or PyYAML is not installed.
    """
    if not model_path or not os.path.exists(model_path):
        return set()
    try:
        import yaml
    except ImportError:
        print("Warning: PyYAML not installed — skipping risk_tracking check.", file=sys.stderr)
        return set()

    tracked = set()
    seen = set()

    def collect(path):
        real = os.path.realpath(path)
        if real in seen:
            return
        seen.add(real)
        with open(path) as handle:
            model = yaml.safe_load(handle) or {}
        tracked.update((model.get('risk_tracking') or {}).keys())
        for include in model.get('includes') or []:
            collect(os.path.join(os.path.dirname(path), include))

    collect(model_path)
    return tracked


# ── Diff ──────────────────────────────────────────────────────────────────────

def diff_risks(previous, current):
    prev_ids = {r.get('synthetic_id', r.get('id', '')) for r in previous}
    curr_ids = {r.get('synthetic_id', r.get('id', '')) for r in current}

    new_ids     = curr_ids - prev_ids
    removed_ids = prev_ids - curr_ids

    curr_map = {r.get('synthetic_id', r.get('id', '')): r for r in current}
    prev_map = {r.get('synthetic_id', r.get('id', '')): r for r in previous}

    return {
        'new_risks':      [curr_map[rid] for rid in sorted(new_ids)],
        'removed_risks':  [prev_map[rid] for rid in sorted(removed_ids)],
        'total_current':  len(current),
        'total_previous': len(previous),
        'delta':          len(current) - len(previous),
    }


# ── GitHub Actions output ─────────────────────────────────────────────────────

def set_output(name, value):
    github_output = os.environ.get('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a') as f:
            f.write(f"{name}={value}\n")
    else:
        print(f"[output] {name}={value}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Diff two Threagile risk outputs')
    parser.add_argument('--previous', required=True, help='Path to previous risks.json')
    parser.add_argument('--current',  required=True, help='Path to current risks.json')
    parser.add_argument('--output',   required=True, help='Path for diff-report.json')
    parser.add_argument('--model',    default=None,  help='Path to threagile.yaml (for risk_tracking check)')
    args = parser.parse_args()

    previous = load_risks(args.previous)
    current  = load_risks(args.current)
    result   = diff_risks(previous, current)

    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)

    # ── Severity flags ────────────────────────────────────────────────────────
    critical_severities = {'critical', 'elevated'}
    new_critical = [
        r for r in result['new_risks']
        if r.get('severity', '').lower() in critical_severities
    ]
    has_critical = len(new_critical) > 0

    # ── Tracking check ────────────────────────────────────────────────────────
    # A new critical risk is "untracked" when no risk_tracking entry covers it.
    # Matching mirrors the analyzer: a `*` in a tracking key matches one
    # @-delimited part (at least one character) and the match is unanchored.
    # The previous category-prefix heuristic marked every new risk in an already
    # tracked category as tracked, so the gate only ever fired for categories
    # with no entry at all.
    tracked_ids = load_tracked_ids(args.model)
    untracked = []
    for risk in new_critical:
        rid = risk.get('synthetic_id', risk.get('id', ''))
        is_tracked = any(
            re.search(re.sub(r'\\\*', '[^@]+', re.escape(tid)), rid) is not None
            for tid in tracked_ids
        )
        if not is_tracked:
            untracked.append(risk)

    has_untracked_critical = len(untracked) > 0

    # ── Set outputs ───────────────────────────────────────────────────────────
    set_output('new_risks_count',        str(len(result['new_risks'])))
    set_output('has_critical',           'true' if has_critical else 'false')
    set_output('has_untracked_critical', 'true' if has_untracked_critical else 'false')

    # ── Human-readable summary ────────────────────────────────────────────────
    print(f"\nDiff summary")
    print(f"  New risks:      {len(result['new_risks'])}")
    print(f"  Removed risks:  {len(result['removed_risks'])}")
    print(f"  Total current:  {result['total_current']}")
    print(f"  Has critical:   {has_critical}")
    print(f"  Untracked crit: {has_untracked_critical}")

    if result['new_risks']:
        print("\nNew risks:")
        for r in result['new_risks']:
            sev = r.get('severity', '?').upper()
            rid = r.get('synthetic_id', r.get('id', 'unknown'))
            tracked_marker = '' if rid not in [u.get('synthetic_id','') for u in untracked] else ' ⚠ UNTRACKED'
            print(f"  [{sev}] {rid}{tracked_marker}")

    if result['removed_risks']:
        print("\nRemoved risks:")
        for r in result['removed_risks']:
            print(f"  {r.get('synthetic_id', r.get('id', 'unknown'))}")


if __name__ == '__main__':
    main()
