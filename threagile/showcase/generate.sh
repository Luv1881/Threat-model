#!/usr/bin/env bash
# Regenerate the per-feature showcase for VaultNote.
#
# Each better-threagile feature that upstream Threagile does NOT have gets its
# own directory under threagile/showcase/<feature>/ with a real artifact run
# against the VaultNote model, so adopters can see every capability at a glance.
#
# Usage:  THREAGILE=/path/to/threagile  ./threagile/showcase/generate.sh
# Default binary: ../better-threagile/bin/threagile (built if missing).
set -u

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

THREAGILE="${THREAGILE:-../better-threagile/bin/threagile}"
if [ ! -x "$THREAGILE" ]; then
  echo ">> building better-threagile binary"
  (cd ../better-threagile && go build -o bin/threagile ./cmd/threagile/) || {
    echo "could not build threagile binary; set THREAGILE=..." >&2; exit 1; }
  THREAGILE="../better-threagile/bin/threagile"
fi
# absolute path so it still resolves after we cd into throwaway dirs
THREAGILE="$(cd "$(dirname "$THREAGILE")" && pwd)/$(basename "$THREAGILE")"

MODEL="threagile/threagile.yaml"
IGN="--ignore-orphaned-risk-tracking"
SHOW="threagile/showcase"
run() { echo "  - $1"; shift; "$@"; }   # label + command

# data-emitting commands write to stdout; analysis commands need IGN.
mkdir -p "$SHOW"

echo ">> analyze-model (the core: full risk analysis of the model)"
mkdir -p "$SHOW/analyze"
TMPAN="$(mktemp -d)"
"$THREAGILE" analyze-model --model "$MODEL" $IGN --output "$TMPAN" \
  --skip-report-pdf --skip-report-adoc --skip-data-flow-diagram --skip-data-asset-diagram \
  --skip-risks-excel --skip-tags-excel >/dev/null 2>&1 || true
cp "$TMPAN/risks.json"             "$SHOW/analyze/risks.json"             2>/dev/null || true
cp "$TMPAN/stats.json"             "$SHOW/analyze/stats.json"             2>/dev/null || true
cp "$TMPAN/technical-assets.json"  "$SHOW/analyze/technical-assets.json"  2>/dev/null || true
rm -rf "$TMPAN"

echo ">> scoring & dev-workflow"
mkdir -p "$SHOW/score"
"$THREAGILE" score --model "$MODEL" $IGN > "$SHOW/score/score.md" 2>/dev/null
"$THREAGILE" score --model "$MODEL" $IGN --format shields > "$SHOW/score/badge.json" 2>/dev/null

mkdir -p "$SHOW/summary"
"$THREAGILE" summary --model "$MODEL" $IGN --format markdown > "$SHOW/summary/summary.md" 2>/dev/null

mkdir -p "$SHOW/prioritize"
"$THREAGILE" prioritize --model "$MODEL" $IGN --top 10 --format markdown > "$SHOW/prioritize/prioritized-findings.md" 2>/dev/null

mkdir -p "$SHOW/requirements"
"$THREAGILE" requirements --model "$MODEL" $IGN --format markdown > "$SHOW/requirements/security-requirements.md" 2>/dev/null
"$THREAGILE" requirements --model "$MODEL" $IGN --format gherkin > "$SHOW/requirements/security-requirements.feature" 2>/dev/null

mkdir -p "$SHOW/validate"
"$THREAGILE" validate --model "$MODEL" --json > "$SHOW/validate/validation.json" 2>/dev/null || true

mkdir -p "$SHOW/lint"
"$THREAGILE" lint --model "$MODEL" --json > "$SHOW/lint/lint.json" 2>/dev/null || true

mkdir -p "$SHOW/gate"
cp threagile/gate-policy.yaml "$SHOW/gate/policy.yaml" 2>/dev/null
"$THREAGILE" gate --model "$MODEL" $IGN --policy threagile/gate-policy.yaml --format markdown \
  > "$SHOW/gate/gate-result.md" 2>/dev/null || true

mkdir -p "$SHOW/policy"
for p in prototype balanced strict regulated; do
  "$THREAGILE" policy init --profile "$p" -o "$SHOW/policy/policy-$p.yaml" --force 2>/dev/null || true
done

mkdir -p "$SHOW/quantify"
"$THREAGILE" quantify --model "$MODEL" $IGN --estimates threagile/fair-estimates.yaml \
  --output-json "$SHOW/quantify/quantify.json" > "$SHOW/quantify/quantify.txt" 2>/dev/null || true

echo ">> analysis / diagrams"
mkdir -p "$SHOW/attack-tree";     "$THREAGILE" attack-tree --model "$MODEL" $IGN --format dot > "$SHOW/attack-tree/attack-tree.dot" 2>/dev/null
mkdir -p "$SHOW/attack-paths";    "$THREAGILE" paths --model "$MODEL" $IGN > "$SHOW/attack-paths/attack-paths.txt" 2>/dev/null
mkdir -p "$SHOW/mermaid";         "$THREAGILE" mermaid --model "$MODEL" $IGN --format markdown > "$SHOW/mermaid/data-flow.mmd.md" 2>/dev/null
mkdir -p "$SHOW/sbom";            "$THREAGILE" sbom --sbom threagile/imports/vaultnote-sbom.cdx.json > "$SHOW/sbom/sbom-report.txt" 2>/dev/null || true

echo ">> importers (architecture-as-code -> model)"
mkdir -p "$SHOW/import-compose"
"$THREAGILE" import compose --compose docker-compose.yml > "$SHOW/import-compose/from-compose.yaml" 2>/dev/null || true
mkdir -p "$SHOW/import-kubernetes"
"$THREAGILE" import kubernetes --manifests threagile/imports/vaultnote-k8s.yaml > "$SHOW/import-kubernetes/from-k8s.yaml" 2>/dev/null || true
mkdir -p "$SHOW/import-threat-dragon"
"$THREAGILE" import threat-dragon --tdmodel threat-dragon/vaultnote-model.json > "$SHOW/import-threat-dragon/from-threat-dragon.yaml" 2>/dev/null || true

echo ">> CI scaffolding"
mkdir -p "$SHOW/generate-ci"
"$THREAGILE" generate-ci --model "$MODEL" --target gate-pr --policy-path policy.yaml --ci-output "$SHOW/generate-ci" 2>/dev/null || true

echo ">> git hooks (rendered into a throwaway repo, then copied)"
mkdir -p "$SHOW/hooks"
TMPH="$(mktemp -d)"; ( cd "$TMPH" && git init -q && cp "$ROOT/$MODEL" threagile.yaml \
  && "$THREAGILE" hooks install --model threagile.yaml >/dev/null 2>&1 )
cp "$TMPH/.git/hooks/pre-commit" "$SHOW/hooks/pre-commit" 2>/dev/null || true
cp "$TMPH/.git/hooks/pre-push"   "$SHOW/hooks/pre-push"   2>/dev/null || true
rm -rf "$TMPH"

echo ">> bootstrap (zero-config: scan a repo -> starter model + policy)"
mkdir -p "$SHOW/bootstrap"
TMPB="$(mktemp -d)"; cp "$ROOT/docker-compose.yml" "$TMPB/" 2>/dev/null
( cd "$TMPB" && "$THREAGILE" bootstrap --dir . --output threagile.yaml --policy-profile balanced >/dev/null 2>&1 )
cp "$TMPB/threagile.yaml" "$SHOW/bootstrap/threagile.yaml" 2>/dev/null || true
cp "$TMPB/policy.yaml"    "$SHOW/bootstrap/policy.yaml"    2>/dev/null || true
rm -rf "$TMPB"

echo ">> methodology rule packs (fork-only)"
mkdir -p "$SHOW/methodologies"
for pack in linddun pasta vast octave trike cloud-native supply-chain ai-ml; do
  mkdir -p "$SHOW/methodologies/$pack"
  "$THREAGILE" analyze-model --model "$MODEL" $IGN --rule-pack "$pack" \
    --output "$SHOW/methodologies/$pack" \
    --skip-report-pdf --skip-report-adoc --skip-data-flow-diagram --skip-data-asset-diagram \
    --skip-risks-excel --skip-tags-excel >/dev/null 2>&1 || true
  # keep only the risks json (the showcase artifact); drop the rest
  find "$SHOW/methodologies/$pack" -type f ! -name 'risks.json' -delete 2>/dev/null || true
done

echo ">> compliance coverage (control-framework mapping)"
mkdir -p "$SHOW/coverage"
"$THREAGILE" coverage --model "$MODEL" $IGN --framework owasp_top10_2021 > "$SHOW/coverage/owasp-top10-2021.txt" 2>/dev/null || true
"$THREAGILE" coverage --model "$MODEL" $IGN --framework nist_800_53 > "$SHOW/coverage/nist-800-53.txt" 2>/dev/null || true

echo ">> explain (why a risk fired / all rules)"
mkdir -p "$SHOW/explain"
"$THREAGILE" explain risk "accidental-secret-leak@source-repo" --model "$MODEL" $IGN > "$SHOW/explain/explain-risk.txt" 2>/dev/null || true
"$THREAGILE" explain rules > "$SHOW/explain/all-risk-rules.txt" 2>/dev/null || true

echo ">> threat-intel cache status (KEV/EPSS)"
mkdir -p "$SHOW/intel"
"$THREAGILE" intel status > "$SHOW/intel/status.txt" 2>/dev/null || true

echo ">> fmt (canonical model formatting, stdout)"
mkdir -p "$SHOW/fmt"
"$THREAGILE" fmt --model "$MODEL" > "$SHOW/fmt/formatted-model.yaml" 2>/dev/null || true

echo ">> import terraform (terraform show -json plan -> model)"
mkdir -p "$SHOW/import-terraform"
"$THREAGILE" import terraform --plan threagile/imports/vaultnote-terraform-plan.json \
  > "$SHOW/import-terraform/from-terraform.yaml" 2>/dev/null || true

echo ">> CI code-scanning outputs (SARIF for GitHub, GitLab SAST report, JUnit gate)"
mkdir -p "$SHOW/code-scanning"
TMPA="$(mktemp -d)"
"$THREAGILE" analyze-model --model "$MODEL" $IGN --output "$TMPA" \
  --skip-report-pdf --skip-report-adoc --skip-data-flow-diagram --skip-data-asset-diagram \
  --skip-risks-excel --skip-tags-excel >/dev/null 2>&1 || true
cp "$TMPA/risks.sarif"        "$SHOW/code-scanning/risks.sarif"        2>/dev/null || true
cp "$TMPA/risks.gl-sast.json" "$SHOW/code-scanning/risks.gl-sast.json" 2>/dev/null || true
rm -rf "$TMPA"
"$THREAGILE" gate --model "$MODEL" $IGN --policy threagile/gate-policy.yaml --format junit \
  > "$SHOW/gate/gate-result.xml" 2>/dev/null || true

echo ">> diff + drift (an added AI feature = 7 new findings vs an approved baseline)"
mkdir -p "$SHOW/diff" "$SHOW/drift"
TMPD="$(mktemp -d)"; cp threagile/*.yaml "$TMPD/" 2>/dev/null
# the "approved baseline" is the model BEFORE the AI feature was added
sed -i '/- feature_ai.yaml/d' "$TMPD/threagile.yaml" 2>/dev/null || true
# sanitise the throwaway temp path so the committed artifacts are reproducible
"$THREAGILE" diff "$TMPD/threagile.yaml" "$MODEL" $IGN --format markdown 2>/dev/null \
  | sed "s#${TMPD}/threagile.yaml#approved-baseline.yaml#g" > "$SHOW/diff/risk-delta.md" || true
"$THREAGILE" drift --baseline "$TMPD/threagile.yaml" --current "$MODEL" $IGN 2>/dev/null \
  | sed "s#${TMPD}/threagile.yaml#approved-baseline.yaml#g" > "$SHOW/drift/drift-report.txt" || true
rm -rf "$TMPD"

echo ">> done. tree:"
find "$SHOW" -maxdepth 2 -type f | sort
