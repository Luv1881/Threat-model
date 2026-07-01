# better-threagile feature showcase (VaultNote)

Every capability **better-threagile adds on top of upstream Threagile**, run
against the VaultNote model, one directory per feature so you can see each at a
glance. Regenerate everything with:

```sh
THREAGILE=../better-threagile/bin/threagile ./threagile/showcase/generate.sh
```

All commands run against `threagile/threagile.yaml` with
`--ignore-orphaned-risk-tracking` (the model tracks risks for every methodology
at once). Outputs are deterministic — re-running yields byte-identical files.

## Developer workflow

| Dir | Command | What it shows |
|-----|---------|---------------|
| [`score/`](./score) | `score` | One 0–100 / A–F health score + a Shields.io badge JSON to track each sprint |
| [`summary/`](./summary) | `summary` | One-pass sprint/PR scorecard (score + top fixes) |
| [`prioritize/`](./prioritize) | `prioritize --top 10` | "Fix these first": findings ranked by exploitability, with remediation |
| [`requirements/`](./requirements) | `requirements` | Security-requirements backlog (Markdown checklist) + Gherkin test cases |
| [`validate/`](./validate) | `validate --json` | Machine-readable model validation (CI-consumable) |
| [`lint/`](./lint) | `lint --format json\|sarif` | Style / best-practice findings as JSON (`lint.json`, with stable rule IDs + file:line) and **SARIF** (`lint.sarif`) for code-scanning upload |
| [`gate/`](./gate) | `gate --policy …` | Policy-as-code CI gate verdict (exit 3 on violation); `gate-strict-result.md` shows a failing run that **lists the offending findings** per rule |
| [`policy/`](./policy) | `policy init --profile …` | Secure-by-default gate policies (prototype/balanced/strict/regulated) |
| [`quantify/`](./quantify) | `quantify --estimates …` | FAIR Monte-Carlo ALE (financial risk) |
| [`fmt/`](./fmt) | `fmt` | Canonical, normalised model YAML (stdout) — keeps diffs clean |

## Risk delta & drift (pull-request review)

The `diff`/`drift` artifacts compare an "approved baseline" (the model **before**
the AI feature was added) against the current model, so both surface the 7 new
findings the AI services introduced.

| Dir | Command | What it shows |
|-----|---------|---------------|
| [`diff/`](./diff) | `diff <old> <new> --format markdown` | Risk delta (+added / −resolved / ~changed) as a PR-ready table |
| [`drift/`](./drift) | `drift --baseline … --current …` | New findings vs an approved baseline (`--fail-on-new-high` gates CI) |

## Compliance & explainability

| Dir | Command | What it shows |
|-----|---------|---------------|
| [`coverage/`](./coverage) | `coverage --framework …` | Which rules cover each control of OWASP Top 10 (2021) & NIST 800-53 |
| [`explain/`](./explain) | `explain risk <id>` / `explain rules` | Why a specific risk fired (full detail) + the entire rule catalogue |
| [`intel/`](./intel) | `intel status` | Age/size of the cached KEV/EPSS threat-intel feeds |

## CI code-scanning outputs

| Dir | Command | What it shows |
|-----|---------|---------------|
| [`code-scanning/`](./code-scanning) | `analyze-model` | `risks.sarif` (SARIF 2.1.0 for GitHub code scanning) + `risks.gl-sast.json` (GitLab SAST report) |
| [`gate/gate-result.xml`](./gate) | `gate --format junit` | JUnit XML gate verdict for Jenkins/GitLab/CircleCI/Azure test reports |

## Analysis / diagrams / interoperability

| Dir | Command | What it shows |
|-----|---------|---------------|
| [`attack-tree/`](./attack-tree) | `attack-tree --format dot` | Goal-oriented attack trees (Graphviz DOT) |
| [`attack-paths/`](./attack-paths) | `paths` | Shortest attack paths from internet to crown-jewel data |
| [`mermaid/`](./mermaid) | `mermaid` | Data-flow diagram that renders natively in GitHub/GitLab Markdown |
| [`sbom/`](./sbom) | `sbom --sbom …` | CycloneDX SBOM correlated with KEV/EPSS threat intel |

## Architecture importers (infra-as-code → model)

| Dir | Command | Source |
|-----|---------|--------|
| [`import-compose/`](./import-compose) | `import compose` | `docker-compose.yml` |
| [`import-kubernetes/`](./import-kubernetes) | `import kubernetes` | `threagile/imports/vaultnote-k8s.yaml` |
| [`import-terraform/`](./import-terraform) | `import terraform` | `threagile/imports/vaultnote-terraform-plan.json` (`terraform show -json`) |
| [`import-threat-dragon/`](./import-threat-dragon) | `import threat-dragon` | `threat-dragon/vaultnote-model.json` |

## Onboarding & CI

| Dir | Command | What it shows |
|-----|---------|---------------|
| [`bootstrap/`](./bootstrap) | `bootstrap` | Zero-config: scan a repo → starter model + secure-by-default policy |
| [`hooks/`](./hooks) | `hooks install` | Generated git pre-commit / pre-push guard scripts |
| [`generate-ci/`](./generate-ci) | `generate-ci --target gate-pr` | Ready-to-commit GitHub Actions gate-PR workflow |

## Methodology rule packs (fork-only)

[`methodologies/`](./methodologies) — the same model analysed through each
fork-added pack (`risks.json` per pack): `linddun`, `pasta`, `vast`, `octave`,
`trike`, `cloud-native`, `supply-chain`, `ai-ml`. Upstream Threagile is
STRIDE-only.
