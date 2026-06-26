#!/usr/bin/env python3
"""
scripts/create-tickets.py

Full bidirectional GitHub Issues sync for threagile findings.

Severity is calculated from multiple signals — mirroring GitHub's native
security scanning (Dependabot / CodeQL / Secret Scanning):

  1. CVSS v3 base score from NIST NVD (when a CVE is referenced)
  2. CISA KEV membership  → bump to at least 8.5 (actively exploited)
  3. EPSS score           → exploitation probability bonus (+0.5 … +2.0)
  4. RAA (threagile)      → relative attacker attractiveness bonus
  5. Exploitation impact + likelihood from threagile model

Issue bodies include:
  - CVSS score + vector string
  - KEV patch deadline and ransomware campaign flag
  - EPSS percentile ranking
  - Exploit / PoC URLs from NVD references + ExploitDB search link
  - Full scoring breakdown

Behaviour:
  - Ensures all required labels exist on the repo before creating issues
  - Creates issues for new findings not already tracked
  - Closes issues for findings in --mitigated (resolved/accepted)
  - Reopens issues for findings that re-emerged after being closed
  - Skips issues that are already open and unchanged

Usage:
  python3 scripts/create-tickets.py \\
    --risks  threagile/output/risks.json \\
    --repo   owner/repo \\
    --token  "$GITHUB_TOKEN"

  technical-assets.json is auto-detected from the same directory as risks.json.

Environment:
  GITHUB_TOKEN  fallback if --token is not provided
"""
import hashlib
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
NVD_API_URL  = "https://services.nvd.nist.gov/rest/json/cves/2.0"
KEV_FEED_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
EPSS_API_URL = "https://api.first.org/data/v1/epss"
LABEL_PREFIX = "threagile:"
GH_LABEL_MAX = 50  # GitHub rejects label names longer than this
CVE_PATTERN  = re.compile(r'CVE-\d{4}-\d{4,7}', re.IGNORECASE)


def tracking_label(syn_id):
    """Build the GitHub tracking label for a finding's synthetic ID.

    Synthetic IDs can be much longer than GitHub's 50-char label limit
    (e.g. chained "a@b>c@d@e" identifiers), so long ones are truncated
    and suffixed with a short content hash to stay unique and stable.
    """
    label = LABEL_PREFIX + syn_id
    if len(label) <= GH_LABEL_MAX:
        return label
    digest = hashlib.sha1(syn_id.encode()).hexdigest()[:8]
    avail = GH_LABEL_MAX - len(LABEL_PREFIX) - len(digest) - 1
    return f"{LABEL_PREFIX}{syn_id[:avail]}-{digest}"

# Base scores when no CVSS is available — midpoints of GitHub severity bands
THREAGILE_BASE_SCORES = {
    "critical": 9.5,
    "high":     8.0,
    "elevated": 6.5,
    "medium":   5.0,
    "low":      2.5,
}

# GitHub-native security label colours (match Dependabot/CodeQL palette)
SEV_COLOURS = {
    "critical": "B60205",
    "high":     "D93F0B",
    "medium":   "E4E669",
    "low":      "0075CA",
}

IMPACT_BONUS = {
    "critical": 0.75, "high": 0.5, "medium": 0.25, "low": 0.0, "": 0.0,
}
LIKELIHOOD_BONUS = {
    "very-likely": 0.75, "likely": 0.5, "possible": 0.25,
    "unlikely": 0.0, "very-unlikely": -0.5, "": 0.0,
}
SEV_BADGE = {
    "critical": "🔴 CRITICAL",
    "high":     "🟠 HIGH",
    "medium":   "🟡 MEDIUM",
    "low":      "🟢 LOW",
}


# ── NVD API ───────────────────────────────────────────────────────────────────

def fetch_nvd_cve(cve_id):
    """Return the raw NVD CVE object for cve_id, or None on any error."""
    try:
        url = f"{NVD_API_URL}?cveId={urllib.parse.quote(cve_id)}"
        req = urllib.request.Request(url, headers={"User-Agent": "threagile-sync/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        vulns = data.get("vulnerabilities", [])
        return vulns[0]["cve"] if vulns else None
    except Exception:
        return None


def fetch_nvd_batch(cve_ids, delay=0.7):
    """Fetch NVD data for each CVE sequentially, honouring the 5 req/30 s limit."""
    result = {}
    for cve_id in cve_ids:
        cve = fetch_nvd_cve(cve_id)
        if cve:
            result[cve_id.upper()] = cve
        time.sleep(delay)
    return result


def get_cvss(nvd_cve):
    """Return (base_score, severity_label, vector_string, version) from NVD."""
    if not nvd_cve:
        return None, None, None, None
    metrics = nvd_cve.get("metrics", {})
    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        entries = metrics.get(key, [])
        if entries:
            d   = entries[0].get("cvssData", {})
            ver = "v2" if key == "cvssMetricV2" else "v3"
            return (
                float(d.get("baseScore", 0)),
                d.get("baseSeverity", "").upper(),
                d.get("vectorString", ""),
                ver,
            )
    return None, None, None, None


def get_poc_links(nvd_cve):
    """Return up to 5 exploit/PoC reference dicts from NVD."""
    if not nvd_cve:
        return []
    return [
        {"url": r["url"], "tags": r.get("tags", [])}
        for r in nvd_cve.get("references", [])
        if "Exploit" in r.get("tags", [])
    ][:5]


# ── Severity calculation ──────────────────────────────────────────────────────

def calculate_severity(risk, tech_assets, kev_entry, epss_entry, nvd_cve):
    """
    Compute an adjusted severity score (0–10) and GitHub-native label using:
      CVSS → KEV boost → EPSS boost → RAA boost → impact/likelihood
    Returns (score: float, label: str, reasoning: list[str])
    """
    base_sev   = (risk.get("severity") or "medium").lower()
    base_score = THREAGILE_BASE_SCORES.get(base_sev, 5.0)
    reasoning  = [f"Base (threagile `{base_sev}`): {base_score:.1f}"]

    # 1. Override base with CVSS when a CVE is available
    cvss_score, cvss_sev, cvss_vector, cvss_ver = get_cvss(nvd_cve)
    if cvss_score is not None:
        base_score = cvss_score
        reasoning  = [f"Base (CVSS {cvss_ver} `{cvss_sev}`): {base_score:.1f} — `{cvss_vector}`"]

    score = base_score

    # 2. KEV: CISA actively-exploited → floor at 8.5
    if kev_entry:
        if score < 8.5:
            boost = round(8.5 - score, 2)
            score = 8.5
            reasoning.append(f"KEV boost (CISA active exploit): +{boost} → {score:.1f}")
        else:
            reasoning.append("KEV: actively exploited (score already ≥ 8.5)")

    # 3. EPSS: exploitation probability in the next 30 days
    if epss_entry:
        p = float(epss_entry.get("epss", 0))
        boost = 2.0 if p >= 0.7 else 1.0 if p >= 0.3 else 0.5 if p >= 0.1 else 0.0
        if boost:
            score = min(10.0, score + boost)
            reasoning.append(f"EPSS boost ({p:.1%} exploitation probability): +{boost} → {score:.1f}")

    # 4. RAA: relative attacker attractiveness
    asset_id = risk.get("most_relevant_technical_asset", "")
    if asset_id and tech_assets:
        raa = float(tech_assets.get(asset_id, {}).get("raa", 0))
        boost = 1.0 if raa >= 75 else 0.5 if raa >= 50 else 0.0
        if boost:
            score = min(10.0, score + boost)
            reasoning.append(f"RAA boost ({raa:.0f}/100 attacker attractiveness): +{boost} → {score:.1f}")

    # 5. Threagile impact + likelihood
    ib = IMPACT_BONUS.get((risk.get("exploitation_impact") or "").lower(), 0.0)
    lb = LIKELIHOOD_BONUS.get((risk.get("exploitation_likelihood") or "").lower(), 0.0)
    if ib or lb:
        score = min(10.0, score + ib + lb)
        reasoning.append(
            f"Impact/likelihood ({risk.get('exploitation_impact','?')}/"
            f"{risk.get('exploitation_likelihood','?')}): +{ib+lb:.2f} → {score:.1f}"
        )

    label = (
        "critical" if score >= 9.0 else
        "high"     if score >= 7.0 else
        "medium"   if score >= 4.0 else
        "low"
    )
    return round(score, 2), label, reasoning


# ── GitHub API helpers ────────────────────────────────────────────────────────

def _gh_request(method, path, token, payload=None):
    url  = GITHUB_API + path
    data = json.dumps(payload).encode() if payload else None
    req  = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization",  f"Bearer {token}")
    req.add_header("Accept",         "application/vnd.github+json")
    req.add_header("User-Agent",     "threagile-sync/1.0")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:300]
        raise RuntimeError(f"GitHub API {method} {path}: HTTP {e.code}: {body}") from e


def _gh_get_status(path, token):
    url = GITHUB_API + path
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept",        "application/vnd.github+json")
    req.add_header("User-Agent",    "threagile-sync/1.0")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def ensure_label(repo, token, name, colour, description="", dry_run=False):
    """Create the label if it does not already exist. Idempotent."""
    if dry_run:
        return
    if _gh_get_status(
        f"/repos/{repo}/labels/{urllib.parse.quote(name, safe='')}", token
    ) == 200:
        return
    try:
        _gh_request("POST", f"/repos/{repo}/labels", token,
                    {"name": name, "color": colour, "description": description})
    except RuntimeError as e:
        if "422" not in str(e):  # 422 = already exists (race)
            raise


def ensure_labels_for_risk(repo, token, syn_id, computed_sev, dry_run=False):
    """Ensure the tracking label, severity label, and base labels all exist."""
    colour = SEV_COLOURS.get(computed_sev, "ededed")
    ensure_label(repo, token, tracking_label(syn_id), "5319e7",
                 f"Threagile finding: {syn_id}", dry_run)
    ensure_label(repo, token, f"severity: {computed_sev}", colour,
                 f"Security severity: {computed_sev}", dry_run)
    ensure_label(repo, token, "security",     "ee0701", "Security finding",      dry_run)
    ensure_label(repo, token, "threat-model", "0075ca", "Threagile threat model", dry_run)


def list_threagile_issues(repo, token):
    """Return {tracking_label: issue} for all issues with a threagile: label (paginated)."""
    result, page = {}, 1
    while True:
        issues = _gh_request(
            "GET", f"/repos/{repo}/issues?state=all&per_page=100&page={page}", token
        )
        if not issues:
            break
        for iss in issues:
            for lbl in iss.get("labels", []):
                if lbl["name"].startswith(LABEL_PREFIX):
                    result[lbl["name"]] = iss
        if len(issues) < 100:
            break
        page += 1
    return result


def create_issue(repo, token, title, body, labels, dry_run=False):
    if dry_run:
        print(f"  [dry-run] would create: {title}")
        return None
    iss = _gh_request("POST", f"/repos/{repo}/issues", token,
                      {"title": title, "body": body, "labels": labels})
    # Issue was created (no HTTPError raised); issue number may still be
    # absent/unparseable in the response — don't fail the sync over it.
    try:
        return iss["number"]
    except (KeyError, TypeError):
        return None


def close_issue(repo, token, number, dry_run=False):
    if dry_run:
        print(f"  [dry-run] would close #{number}")
        return
    _gh_request("PATCH", f"/repos/{repo}/issues/{number}", token, {"state": "closed"})


def reopen_issue(repo, token, number, dry_run=False):
    if dry_run:
        print(f"  [dry-run] would reopen #{number}")
        return
    _gh_request("PATCH", f"/repos/{repo}/issues/{number}", token, {"state": "open"})


# ── Threat-intel helpers ──────────────────────────────────────────────────────

def fetch_kev():
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
    if not cve_ids:
        return {}
    try:
        param = urllib.parse.quote(",".join(cve_ids))
        req = urllib.request.Request(f"{EPSS_API_URL}?cve={param}",
                                     headers={"User-Agent": "threagile-sync/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read())
        return {s["cve"].upper(): s for s in data.get("data", [])}
    except Exception as exc:
        print(f"  [intel] EPSS fetch failed: {exc}", file=sys.stderr)
        return {}


def extract_cves(risk):
    seen, result = set(), []
    text = " ".join(filter(None, [
        risk.get("title", ""),        risk.get("category", ""),
        risk.get("description", ""),  risk.get("mitigation", ""),
        " ".join(risk.get("risk_explanation", [])),
        " ".join(risk.get("rating_explanation", [])),
    ]))
    for m in CVE_PATTERN.findall(text):
        u = m.upper()
        if u not in seen:
            seen.add(u)
            result.append(u)
    return result


# ── Issue body ────────────────────────────────────────────────────────────────

def strip_html(s):
    return re.sub(r'<[^>]+>', '', s or '')


def format_issue_body(risk, tech_assets, intel):
    syn_id   = risk.get("synthetic_id", "unknown")
    category = risk.get("category", "N/A")
    asset_id = risk.get("most_relevant_technical_asset", "N/A")
    raa      = tech_assets.get(asset_id, {}).get("raa") if tech_assets else None

    score        = intel["score"]
    computed_sev = intel["severity"]
    reasoning    = intel["reasoning"]
    cve_intels   = intel["cves"]

    badge = SEV_BADGE.get(computed_sev, computed_sev.upper())

    lines = [
        f"## {badge} — {strip_html(risk.get('title', category))}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| **Adjusted Score** | `{score}/10` |",
        f"| **Category** | `{category}` |",
        f"| **Affected Asset** | `{asset_id}` |",
    ]
    if raa is not None:
        lines.append(f"| **RAA (Attacker Attractiveness)** | `{raa:.0f}/100` |")
    lines += [
        f"| **Threagile Likelihood** | `{risk.get('exploitation_likelihood', 'N/A')}` |",
        f"| **Threagile Impact** | `{risk.get('exploitation_impact', 'N/A')}` |",
        f"| **Synthetic ID** | `{syn_id}` |",
        "",
    ]

    if risk.get("description"):
        lines += ["### Description", "", risk["description"], ""]

    if risk.get("mitigation"):
        lines += ["### Suggested Mitigation", "", risk["mitigation"], ""]

    # Scoring breakdown
    lines += ["### Severity Scoring Breakdown", "", "```"]
    for r in reasoning:
        lines.append(f"  {r}")
    lines += ["```", ""]

    # CVE intelligence + PoC
    if cve_intels:
        lines += ["### CVE Intelligence", ""]
        for ci in cve_intels:
            cve_id    = ci["cve_id"]
            kev       = ci.get("kev")
            epss      = ci.get("epss")
            nvd_cve   = ci.get("nvd")
            poc_links = get_poc_links(nvd_cve)

            lines.append(f"#### {cve_id}")
            lines.append("")

            cvss_score, cvss_sev, cvss_vector, cvss_ver = get_cvss(nvd_cve)
            if cvss_score is not None:
                lines.append(
                    f"**CVSS {cvss_ver}:** `{cvss_score}` ({cvss_sev}) "
                    f"— `{cvss_vector}`  "
                )

            if epss:
                p   = float(epss.get("epss", 0)) * 100
                pct = float(epss.get("percentile", 0)) * 100
                lines.append(
                    f"**EPSS:** {p:.2f}% exploitation probability in next 30 days "
                    f"({pct:.0f}th percentile, {epss.get('date', '')})  "
                )

            if kev:
                lines += [
                    "**KEV (CISA):** ⚠️ ACTIVELY EXPLOITED IN THE WILD  ",
                    f"- Product: {kev.get('vendorProject','')} {kev.get('product','')}  ",
                    f"- Added: {kev.get('dateAdded','')} | Patch due: {kev.get('dueDate','')}  ",
                    f"- Required action: {kev.get('requiredAction','')}  ",
                    f"- Known ransomware use: {kev.get('knownRansomwareCampaignUse','')}  ",
                ]
            else:
                lines.append("**KEV (CISA):** Not in known-exploited catalog  ")

            lines.append("")
            if poc_links:
                lines.append("**Proof of Concept / Exploit References:**")
                lines.append("")
                for ref in poc_links:
                    tag_str = ", ".join(ref["tags"])
                    lines.append(f"- [{ref['url']}]({ref['url']}) _{tag_str}_")
            else:
                lines.append("**PoC / Exploit:** No public exploit references in NVD  ")

            lines.append(
                f"\n🔍 [ExploitDB search for {cve_id}]"
                f"(https://www.exploit-db.com/search?cve={cve_id.replace('CVE-','')})"
                f"  ·  [NVD entry](https://nvd.nist.gov/vuln/detail/{cve_id})"
            )
            lines.append("")
    else:
        lines += [
            "### Threat Intelligence",
            "",
            "_No CVE IDs referenced — architectural risk pattern._  ",
            "_Severity scored from threagile model attributes (likelihood, impact, RAA)._",
            "",
        ]

    lines += [
        "---",
        "*Auto-generated by [better-threagile](https://github.com/Luv1881/better-threagile) "
        "— severity adjusted via CVSS · KEV · EPSS · RAA.*",
        "*Add a `risk_tracking` entry in `threagile/threagile.yaml` to acknowledge this risk.*",
    ]
    return "\n".join(lines)


# ── Risk / asset loading ──────────────────────────────────────────────────────

def load_risks(path):
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, dict):
        result = []
        for syn_id, r in data.items():
            r.setdefault("synthetic_id", syn_id)
            result.append(r)
        return result
    return data


def load_tech_assets(path):
    if not path or not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


# ── Main sync loop ────────────────────────────────────────────────────────────

def sync(args):
    token = args.token or os.environ.get("GITHUB_TOKEN", "")
    if not token:
        sys.exit("Error: provide --token or set GITHUB_TOKEN")

    severity_order = ["low", "medium", "elevated", "high", "critical"]
    min_idx = (severity_order.index(args.min_severity.lower())
               if args.min_severity.lower() in severity_order else 1)

    risks = load_risks(args.risks)

    # Auto-detect technical-assets.json
    assets_path = args.assets or os.path.join(
        os.path.dirname(os.path.abspath(args.risks)), "technical-assets.json"
    )
    tech_assets = load_tech_assets(assets_path)
    if tech_assets:
        print(f"Loaded {len(tech_assets)} technical assets for RAA scoring.")

    def sev_idx(r):
        s = (r.get("severity") or "low").lower()
        return severity_order.index(s) if s in severity_order else 0

    risks = [r for r in risks if sev_idx(r) >= min_idx]
    mitigated_ids = {m.strip() for m in (args.mitigated or "").split(",") if m.strip()}
    print(f"Loaded {len(risks)} findings at or above '{args.min_severity}'.")

    # Collect CVEs
    cves_per_risk = {}
    all_cves = set()
    for risk in risks:
        cves = extract_cves(risk)
        if cves:
            cves_per_risk[risk.get("synthetic_id", "")] = cves
            all_cves.update(cves)

    # Fetch intel
    kev_catalog = {}
    epss_scores = {}
    nvd_data    = {}

    if all_cves:
        cve_list = sorted(all_cves)
        print("Fetching CISA KEV catalog...")
        kev_catalog = fetch_kev()

        print(f"Fetching EPSS scores for {len(cve_list)} CVE(s)...")
        epss_scores = fetch_epss_batch(cve_list)

        print(f"Fetching NVD data for {len(cve_list)} CVE(s) "
              f"(~{len(cve_list)*0.7:.0f}s, rate-limited)...")
        nvd_data = fetch_nvd_batch(cve_list)
    else:
        print("No CVE IDs in findings — severity based on threagile model attributes.")

    def build_intel(risk):
        syn_id     = risk.get("synthetic_id", "")
        cve_intels = [
            {"cve_id": c,
             "kev":  kev_catalog.get(c),
             "epss": epss_scores.get(c),
             "nvd":  nvd_data.get(c)}
            for c in cves_per_risk.get(syn_id, [])
        ]
        kev_entry  = next((ci["kev"]  for ci in cve_intels if ci["kev"]),  None)
        epss_entry = next((ci["epss"] for ci in cve_intels if ci["epss"]), None)
        nvd_cve    = next((ci["nvd"]  for ci in cve_intels if ci["nvd"]),  None)
        score, sev_label, reasoning = calculate_severity(
            risk, tech_assets, kev_entry, epss_entry, nvd_cve
        )
        return {"score": score, "severity": sev_label,
                "reasoning": reasoning, "cves": cve_intels}

    # Fetch existing tracked issues (paginated)
    print(f"Listing existing threagile issues in {args.repo}...")
    existing = list_threagile_issues(args.repo, token)
    print(f"Found {len(existing)} tracked issue(s).")

    current_by_syn = {r.get("synthetic_id", ""): r for r in risks}
    created = closed = reopened = skipped = failed = 0

    for risk in risks:
        syn_id = risk.get("synthetic_id", "unknown")
        label  = tracking_label(syn_id)
        intel  = build_intel(risk)
        csev   = intel["severity"]
        title  = (
            f"[{csev.upper()}] "
            f"{strip_html(risk.get('title', syn_id))} "
            f"(score: {intel['score']})"
        )
        body   = format_issue_body(risk, tech_assets, intel)
        labels = [label, f"severity: {csev}", "security", "threat-model"]

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

        try:
            ensure_labels_for_risk(args.repo, token, syn_id, csev, args.dry_run)
        except RuntimeError as e:
            print(f"  ! label setup failed {syn_id}: {e}", file=sys.stderr)
            failed += 1
            continue

        if existing_issue is None:
            try:
                num = create_issue(args.repo, token, title, body, labels, args.dry_run)
                if num:
                    print(f"  + #{num} created [{csev}] {syn_id}")
                created += 1
                time.sleep(0.5)
            except RuntimeError as e:
                print(f"  ! create failed {syn_id}: {e}", file=sys.stderr)
                failed += 1
        elif existing_issue["state"] == "closed":
            try:
                reopen_issue(args.repo, token, existing_issue["number"], args.dry_run)
                print(f"  ~ #{existing_issue['number']} reopened [{csev}]: {syn_id}")
                reopened += 1
            except RuntimeError as e:
                print(f"  ! reopen failed {syn_id}: {e}", file=sys.stderr)
                failed += 1
        else:
            skipped += 1

    # Close issues for findings no longer present.
    # Long synthetic IDs are truncated+hashed in their tracking label, so the
    # syn_id can't be recovered by stripping the prefix — build a reverse map
    # from every known (current + mitigated) syn_id instead.
    label_to_syn = {tracking_label(sid): sid for sid in set(current_by_syn) | mitigated_ids}
    for lbl, iss in existing.items():
        syn_id = label_to_syn.get(lbl, lbl[len(LABEL_PREFIX):])
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
    p = argparse.ArgumentParser(
        description="Sync threagile findings to GitHub Issues — CVSS/KEV/EPSS/RAA severity"
    )
    p.add_argument("--risks",        required=True,
                   help="Path to risks.json")
    p.add_argument("--assets",       default=None,
                   help="Path to technical-assets.json (auto-detected if omitted)")
    p.add_argument("--repo",         required=True,
                   help="GitHub repo in owner/name format")
    p.add_argument("--token",        default="",
                   help="GitHub PAT (or set GITHUB_TOKEN)")
    p.add_argument("--min-severity", default="medium",
                   help="Minimum threagile severity (low|medium|elevated|high|critical)")
    p.add_argument("--mitigated",    default="",
                   help="Comma-separated synthetic IDs to close")
    p.add_argument("--dry-run",      action="store_true",
                   help="Print actions without making API calls")
    args = p.parse_args()
    sync(args)


if __name__ == "__main__":
    main()
