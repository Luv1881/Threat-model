#!/usr/bin/env python3
"""
scripts/threat-model-diff.py
Compares two Threagile risks.json outputs and surfaces new/removed risks.
Sets GitHub Actions outputs for downstream step conditions.
"""
import json
import argparse
import os
import sys


def load_risks(filepath):
    """Load a Threagile risks.json file. Handles both dict and list formats."""
    with open(filepath) as f:
        data = json.load(f)
    if isinstance(data, dict):
        risks = []
        for risk_id, risk_data in data.items():
            risk_data['synthetic_id'] = risk_id
            risks.append(risk_data)
        return risks
    return data


def diff_risks(previous, current):
    prev_ids = {r.get('synthetic_id', r.get('id', '')) for r in previous}
    curr_ids = {r.get('synthetic_id', r.get('id', '')) for r in current}

    new_ids     = curr_ids - prev_ids
    removed_ids = prev_ids - curr_ids

    curr_map = {r.get('synthetic_id', r.get('id', '')): r for r in current}
    prev_map = {r.get('synthetic_id', r.get('id', '')): r for r in previous}

    return {
        'new_risks':     [curr_map[rid] for rid in new_ids],
        'removed_risks': [prev_map[rid] for rid in removed_ids],
        'total_current':  len(current),
        'total_previous': len(previous),
        'delta':          len(current) - len(previous),
    }


def set_output(name, value):
    """Write a GitHub Actions step output."""
    github_output = os.environ.get('GITHUB_OUTPUT')
    if github_output:
        with open(github_output, 'a') as f:
            f.write(f"{name}={value}\n")
    else:
        # Fallback for local testing
        print(f"::set-output name={name}::{value}")


def main():
    parser = argparse.ArgumentParser(description='Diff two Threagile risk outputs')
    parser.add_argument('--previous', required=True, help='Path to previous risks.json')
    parser.add_argument('--current',  required=True, help='Path to current risks.json')
    parser.add_argument('--output',   required=True, help='Path for diff-report.json')
    args = parser.parse_args()

    previous = load_risks(args.previous)
    current  = load_risks(args.current)
    result   = diff_risks(previous, current)

    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)

    has_critical = any(
        r.get('severity', '') in ('critical', 'elevated')
        for r in result['new_risks']
    )

    # Determine untracked: new critical risks that have no risk_tracking in the model
    # (heuristic: check if synthetic_id appears as a key in the diff output)
    has_untracked_critical = has_critical  # conservative: assume untracked until proven otherwise

    set_output('new_risks_count',       str(len(result['new_risks'])))
    set_output('has_critical',          'true' if has_critical else 'false')
    set_output('has_untracked_critical','true' if has_untracked_critical else 'false')

    print(f"\nDiff summary:")
    print(f"  New risks:     {len(result['new_risks'])}")
    print(f"  Removed risks: {len(result['removed_risks'])}")
    print(f"  Total current: {result['total_current']}")

    if result['new_risks']:
        print(f"\nNew risks:")
        for r in result['new_risks']:
            print(f"  [{r.get('severity','?').upper()}] {r.get('synthetic_id', r.get('id','unknown'))}")


if __name__ == '__main__':
    main()
