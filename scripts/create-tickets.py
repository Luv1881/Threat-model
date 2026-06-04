#!/usr/bin/env python3
"""
scripts/create-tickets.py

Full bidirectional GitHub Issues sync for threagile findings.

Behaviour:
  - Ensures all required labels exist on the repo before creating issues
  - Creates issues for new findings not already tracked
  - Closes issues for findings in --mitigated (resolved/accepted)
  - Reopens issues for findings that re-emerged after being closed
  - Skips issues that are already open and unchanged

Issue bodies include KEV (CISA Known Exploited Vulnerabilities) and EPSS
(Exploit Prediction Scoring System) data for any CVE-YYYY-NNNNN references
found in the risk data.

Usage:
  python3 scripts/create-tickets.py \\
    --risks threagile/output/risks.json \\
    --repo owner/repo \\
    --token "$GITHUB_TOKEN"

Environment:
  GITHUB_TOKEN  fallback if --token is not provided
"""
import json
import re
import sys
import os
import argparse
import time
import urllib.request
import urllib.parse
import urllib.error


# ── Constants ─────────────────────────────────────────────────────────────────

GITHUB_API   = "https://api.github.com"
KEV_FEED_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
EPSS_API_URL = "https://api.first.org/data/v1/epss"
LABEL_PREFIX = "threagile:"
SEV_LABEL    = "threat-severity:"
CVE_PATTERN  = re.compile(r'CVE-\d{4}-\d{4,7}', re.IGNORECASE)

# Colour map used when creating severity labels
SEV_COLOURS = {
    "critical":  "b60205",
    "high":      "d93f0b",
    "elevated":  "e4e669",
    "medium":    "0075ca",
    "low":       "cfd3d7",
}


# ── GitHub API helpers ────────────────────────────────────────────────────────

def _gh_request(method, path, token, payload=None):
    url = GITHUB_API + path
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "threagile-sync/1.0")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:300]
        raise RuntimeError(f"GitHub API {method} {path}: HTTP {e.code}: {body}") from e


def _gh_request_raw(method, path, token, payload=None):
    """Like _gh_request but returns (status_code, body_bytes)."""
    url = GITHUB_API + path
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "threagile-sync/1.0")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def ensure_label(repo, token, name, colour, description="", dry_run=False):
    """Create the label if it does not already exist. Idempotent."""
    if dry_run:
        return
    status, _ = _gh_request_raw(
        "GET", f"/repos/{repo}/labels/{urllib.parse.quote(name, safe='')}", token
    )
    if status == 200:
        return  # already exists
    try:
        _gh_request("POST", f"/repos/{repo}/labels", token,
                    {"name": name, "color": colour, "description": description})
    except RuntimeError as e:
        # 422 = label already exists (race); anything else re-raise
        if "422" not in str(e):
            raise


def ensure_labels_for_risk(repo, token, syn_id, sev, dry_run=False):
    """Ensure the threagile tracking label and the severity label both exist."""
    tracking_label = LABEL_PREFIX + syn_id
    sev_label_name = SEV_LABEL + sev
    colour = SEV_COLOURS.get(sev.lower(), "ededed")

    ensure_label(repo, token, tracking_label, "5319e7",
                 f"Threagile finding: {syn_id}", dry_run)
    ensure_label(repo, token, sev_label_name, colour,
                 f"Threat severity: {sev}", dry_run)
    ensure_label(repo, token, "security",     "ee0701",
                 "Security finding", dry_run)
    ensure_label(repo, token, "threat-model", "0075ca",
                 "Threagile threat model", dry_run)


def list_threagile_issues(repo, token):
    """Return {label_name: issue} for every issue that carries a threagile: label.
    Paginates through all pages so no issue is missed."""
    result = {}
    page = 1
    while True:
        path = f"/repos/{repo}/issues?state=all&per_page=100&page={page}"
        issues = _gh_request("GET", path, token)
        if not issues:
            break
        for iss in issues:
            for lbl in iss.get("labels", []):
                if lbl["name"].startswith(LABEL_PREFIX):
                    result[lbl["name"]] = iss
        if len(issues) < 100:
            break  # last page
        page += 1
    return result


def create_issue(repo, token, title, body, labels, dry_run=False):
    if dry_run:
        print(f"  [dry-run] would create: {title}")
        return None
    iss = _gh_request("POST", f"/repos/{repo}/issues", token,
                      {"title": title, "body": body, "labels": labels})
    return iss["number"]


def close_issue(repo, token, number, dry_run=False):
    if dry_run:
        print(f"  [dry-run] would close issue #{number}")
        return
    _gh_request("PATCH", f"/repos/{repo}/issues/{number}", token, {"state": "closed"})


def reopen_issue(repo, token, number, dry_run=False):
    if dry_run:
        print(f"  [dry-run] would reopen issue #{number}")
        return
    _gh_request("PATCH", f"/repos/{repo}/issues/{number}", token, {"state": "open"})


# ── Threat-intel helpers ──────────────────────────────────────────────────────

def fetch_kev():
    """Download the CISA KEV catalog. Returns a dict keyed by CVE ID or {} on error."""
    try:
        req = urllib.request.Request(KEV_FEED_URL,
                                     headers={"User-Agent": "threagile-sync/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            catalog = json.loads(resp.read())
        return {v["cveID"].upper(): v for v in catalog.get("vulnerabilities", [])}
    except Exception as exc:
        print(f"  [intel] KEV feed unavailable: {exc}", file=sys.stderr)
        return {}


def fetch_epss_batch(cve_ids):
    """Batch-fetch EPSS scores. Returns a dict keyed by upper-case CVE ID or {}."""
    if not cve_ids:
        return {}
    try:
        param = urllib.parse.quote(",".join(cve_ids))
        url = f"{EPSS_API_URL}?cve={param}"
        req = urllib.request.Request(url, headers={"User-Agent": "threagile-sync/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        return {s["cve"].upper(): s for s in data.get("data", [])}
    except Exception as exc:
        print(f"  [intel] EPSS fetch failed: {exc}", file=sys.stderr)
        return {}


def extract_cves(risk):
    """Return a deduplicated list of CVE IDs found in any string field of the risk."""
    seen = set()
    result = []
    text = " ".join(filter(None, [
        risk.get("title", ""),
        risk.get("category", ""),
        risk.get("description", ""),
        risk.get("mitigation", ""),
        " ".join(risk.get("risk_explanation", [])),
        " ".join(risk.get("rating_explanation", [])),
    ]))
    for m in CVE_PATTERN.findall(text):
        upper = m.upper()
        if upper not in seen:
            seen.add(upper)
            result.append(upper)
    return result


# ── Issue body formatting ─────────────────────────────────────────────────────

def strip_html(s):
    return re.sub(r'<[^>]+>', '', s or '')


def format_issue_body(risk, intel_for_risk):
    """Build a rich GitHub issue markdown body."""
    syn_id   = risk.get("synthetic_id", "unknown")
    category = risk.get("category", "N/A")
    sev      = risk.get("severity", "N/A")
    lh       = risk.get("exploitation_likelihood", "N/A")
    impact   = risk.get("exploitation_impact", "N/A")
    asset    = risk.get("most_relevant_technical_asset", "N/A")

    lines = [
        f"## Threat Finding: {category}",
        "",
        f"**Severity:** {sev}  ",
        f"**Likelihood:** {lh}  ",
        f"**Impact:** {impact}  ",
        f"**Synthetic ID:** `{syn_id}`  ",
        f"**Most Relevant Asset:** {asset}  ",
        "",
    ]

    if risk.get("description"):
        lines += ["**Description:**", risk["description"], ""]

    if risk.get("mitigation"):
        lines += ["**Suggested Mitigation:**", risk["mitigation"], ""]

    # Threat intelligence section
    lines.append("### Threat Intelligence")
    lines.append("")

    if not intel_for_risk:
        lines.append("_No CVE IDs referenced in this finding (architectural risk pattern)._  ")
        lines.append("_To associate CVEs, add them to the finding's description or risk_explanation._")
    else:
        for ci in intel_for_risk:
            cve_id = ci["cve_id"]
            lines.append(f"**{cve_id}**")
            lines.append("")

            kev = ci.get("kev")
            if kev:
                name    = kev.get("vulnerabilityName", "")
                product = f"{kev.get('vendorProject', '')} {kev.get('product', '')}".strip()
                added   = kev.get("dateAdded", "")
                due     = kev.get("dueDate", "")
                action  = kev.get("requiredAction", "")
                ransom  = kev.get("knownRansomwareCampaignUse", "")
                lines.append(f"- **KEV (CISA):** YES — {name} ({product})")
                lines.append(f"  - Date added: {added} | Patch due: {due}")
                lines.append(f"  - Required action: {action}")
                lines.append(f"  - Known ransomware use: {ransom}")
            else:
                lines.append("- **KEV (CISA):** Not in known-exploited catalog")

            epss = ci.get("epss")
            if epss:
                score      = float(epss.get("epss", 0)) * 100
                percentile = float(epss.get("percentile", 0)) * 100
                date       = epss.get("date", "")
                lines.append(f"- **EPSS:** {score:.2f}% exploitation probability "
                              f"({percentile:.0f}th percentile, {date})")
            else:
                lines.append("- **EPSS:** Not in EPSS database")

            lines.append("")

    lines += [
        "---",
        "*Auto-generated by the VaultNote threat modelling pipeline — do not edit manually.*",
        "*Add a `risk_tracking` entry to `threagile/threagile.yaml` to acknowledge this risk.*",
    ]

    return "\n".join(lines)


# ── Risk loading ──────────────────────────────────────────────────────────────

def load_risks(path):
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict):
        risks = []
        for syn_id, r in data.items():
            r.setdefault("synthetic_id", syn_id)
            risks.append(r)
        return risks
    return data


# ── Main sync loop ────────────────────────────────────────────────────────────

def sync(args):
    token = args.token or os.environ.get("GITHUB_TOKEN", "")
    if not token:
        sys.exit("Error: provide --token or set GITHUB_TOKEN")

    severity_order = ["low", "medium", "elevated", "high", "critical"]
    try:
        min_idx = severity_order.index(args.min_severity.lower())
    except ValueError:
        print(f"Unknown severity '{args.min_severity}', defaulting to 'medium'.", file=sys.stderr)
        min_idx = severity_order.index("medium")

    risks = load_risks(args.risks)

    # Apply severity filter
    def sev_idx(r):
        s = r.get("severity", "low").lower()
        return severity_order.index(s) if s in severity_order else 0

    risks = [r for r in risks if sev_idx(r) >= min_idx]

    mitigated_ids = set()
    if args.mitigated:
        mitigated_ids = {m.strip() for m in args.mitigated.split(",") if m.strip()}

    print(f"Loaded {len(risks)} findings at or above '{args.min_severity}' severity.")

    # Collect all CVEs across findings for batch EPSS fetch
    cves_per_risk = {}
    all_cves = set()
    for risk in risks:
        cves = extract_cves(risk)
        syn_id = risk.get("synthetic_id", "")
        if cves:
            cves_per_risk[syn_id] = cves
            all_cves.update(cves)

    # Fetch threat intel (non-fatal)
    kev_catalog = {}
    epss_scores = {}
    if all_cves:
        print(f"Fetching threat intel for {len(all_cves)} CVE(s)...")
        kev_catalog = fetch_kev()
        epss_scores = fetch_epss_batch(list(all_cves))
    else:
        print("No CVE IDs referenced in findings — skipping KEV/EPSS fetch.")

    def build_intel(syn_id):
        return [
            {
                "cve_id": cve_id,
                "kev":    kev_catalog.get(cve_id),
                "epss":   epss_scores.get(cve_id),
            }
            for cve_id in cves_per_risk.get(syn_id, [])
        ]

    # Fetch existing threagile-tracked issues (paginated)
    print(f"Listing existing threagile issues in {args.repo}...")
    existing = list_threagile_issues(args.repo, token)
    print(f"Found {len(existing)} tracked issue(s).")

    current_by_syn = {r.get("synthetic_id", ""): r for r in risks}

    created = closed = reopened = skipped = failed = 0

    for risk in risks:
        syn_id  = risk.get("synthetic_id", "unknown")
        sev     = risk.get("severity", "medium")
        label   = LABEL_PREFIX + syn_id
        title   = f"[{sev.upper()}] {strip_html(risk.get('title', syn_id))}"
        body    = format_issue_body(risk, build_intel(syn_id))
        labels  = [label, SEV_LABEL + sev, "security", "threat-model"]

        existing_issue = existing.get(label)

        if syn_id in mitigated_ids:
            if existing_issue and existing_issue["state"] == "open":
                try:
                    close_issue(args.repo, token, existing_issue["number"], args.dry_run)
                    print(f"  - #{existing_issue['number']} closed (mitigated): {syn_id}")
                    closed += 1
                except RuntimeError as e:
                    print(f"  ! close failed {syn_id}: {e}", file=sys.stderr)
                    failed += 1
            continue

        # Ensure all labels exist before applying them to an issue.
        # GitHub silently drops labels that don't exist on the repo.
        try:
            ensure_labels_for_risk(args.repo, token, syn_id, sev, args.dry_run)
        except RuntimeError as e:
            print(f"  ! label setup failed for {syn_id}: {e}", file=sys.stderr)
            failed += 1
            continue

        if existing_issue is None:
            try:
                num = create_issue(args.repo, token, title, body, labels, args.dry_run)
                if num:
                    print(f"  + #{num} created: {syn_id}")
                created += 1
                time.sleep(0.5)  # avoid secondary rate limit
            except RuntimeError as e:
                print(f"  ! create failed {syn_id}: {e}", file=sys.stderr)
                failed += 1
        elif existing_issue["state"] == "closed":
            try:
                reopen_issue(args.repo, token, existing_issue["number"], args.dry_run)
                print(f"  ~ #{existing_issue['number']} reopened: {syn_id}")
                reopened += 1
            except RuntimeError as e:
                print(f"  ! reopen failed {syn_id}: {e}", file=sys.stderr)
                failed += 1
        else:
            skipped += 1

    # Close issues for risks no longer present in the current run
    for label, iss in existing.items():
        syn_id = label[len(LABEL_PREFIX):]
        if syn_id not in current_by_syn and syn_id not in mitigated_ids:
            if iss["state"] == "open":
                try:
                    close_issue(args.repo, token, iss["number"], args.dry_run)
                    print(f"  - #{iss['number']} closed (resolved): {syn_id}")
                    closed += 1
                except RuntimeError as e:
                    print(f"  ! close failed {syn_id}: {e}", file=sys.stderr)
                    failed += 1

    print(f"\nSync complete: +{created} created, -{closed} closed, "
          f"~{reopened} reopened, ={skipped} skipped, !{failed} failed")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Sync threagile findings to GitHub Issues with KEV/EPSS enrichment"
    )
    parser.add_argument("--risks",        required=True, help="Path to risks.json")
    parser.add_argument("--repo",         required=True, help="GitHub repo in owner/name format")
    parser.add_argument("--token",        default="",    help="GitHub personal access token")
    parser.add_argument("--min-severity", default="medium",
                        help="Minimum severity to sync (low|medium|elevated|high|critical)")
    parser.add_argument("--mitigated",    default="",
                        help="Comma-separated synthetic IDs to close (mitigated/accepted risks)")
    parser.add_argument("--dry-run",      action="store_true",
                        help="Print actions without making API calls")
    args = parser.parse_args()
    sync(args)


if __name__ == "__main__":
    main()
