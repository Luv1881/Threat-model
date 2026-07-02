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

## Core analysis

| Dir | Command | What it shows |
|-----|---------|---------------|
| [`analyze/`](./analyze) | `analyze-model` | The core run: generated `risks.json`, `stats.json`, `technical-assets.json` for the whole model (STRIDE + all packs) |

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
| [`fmt/`](./fmt) | `fmt` | Canonical, normalised model YAML (stdout) — keeps diffs clean |

## Risk delta & drift gate (pull-request review)

The `diff/` artifacts compare an "approved baseline" (the model **before** the
AI feature was added) against the current model, so both surface the 7 new
findings the AI services introduced.

| Dir | Command | What it shows |
|-----|---------|---------------|
| [`diff/`](./diff) | `diff <old> <new> --format markdown` | Risk delta (+added / −resolved / ~changed) as a PR-ready table |
| [`diff/drift-gate.txt`](./diff) | `diff <old> <new> --fail-on-new-high` | New findings vs an approved baseline, as a CI drift gate (exit 3 on new High/Critical) |

## Compliance & explainability

| Dir | Command | What it shows |
|-----|---------|---------------|
| [`coverage/`](./coverage) | `coverage --framework …` | Which rules cover each control of OWASP Top 10 (2021) & NIST 800-53 |
| [`explain/`](./explain) | `explain risk <id>` / `list-risk-rules` | Why a specific risk fired (full detail) + the entire rule catalogue |
| [`intel/`](./intel) | `intel status` | Age/size of the cached KEV/EPSS threat-intel feeds |

## CI code-scanning outputs

| Dir | Command | What it shows |
|-----|---------|---------------|
| [`code-scanning/`](./code-scanning) | `analyze-model` | `risks.sarif` (SARIF 2.1.0 for GitHub code scanning) + `risks.gl-sast.json` (GitLab SAST report) |
| [`gate/gate-result.xml`](./gate) | `gate --format junit` | JUnit XML gate verdict for Jenkins/GitLab/CircleCI/Azure test reports |

## Analysis / diagrams / interoperability

| Dir | Command | What it shows |
|-----|---------|---------------|
| [`attack-paths/`](./attack-paths) | `paths` | Shortest attack paths from internet to crown-jewel data |
| [`mermaid/`](./mermaid) | `mermaid` | Data-flow diagram that renders natively in GitHub/GitLab Markdown |
| [`sbom/`](./sbom) | `sbom --sbom …` | CycloneDX SBOM correlated with KEV/EPSS threat intel |

## Architecture importers (infra-as-code → model)

| Dir | Command | Source |
|-----|---------|--------|
| [`import-compose/`](./import-compose) | `import compose` | `docker-compose.yml` |
| [`import-kubernetes/`](./import-kubernetes) | `import kubernetes` | `threagile/imports/vaultnote-k8s.yaml` |
| [`import-terraform/`](./import-terraform) | `import terraform` | `threagile/imports/vaultnote-terraform-plan.json` (`terraform show -json`) |
| [`import-threat-dragon/`](./import-threat-dragon) | `import threat-dragon --scaffold=false` | `threat-dragon/vaultnote-model.json` |

## Diagram → mock model (no AI, editable scaffold)

Every diagram importer is **deterministic** — no AI — and defaults to
**scaffold output**: heuristically inferred fields get a `# TODO(review): …`
comment, and every generated element is tagged `review-<importer>` until a
human confirms it (see [`review/`](./review) below). `--mapping` (shown here)
lets a team encode its own box-label nomenclature and diagram color/style
conventions instead of relying only on the built-in heuristics — see
`threagile/imports/vaultnote-mapping.yaml`.

| Dir | Command | Source |
|-----|---------|--------|
| [`import-drawio/`](./import-drawio) | `import drawio --mapping …` | `threagile/imports/vaultnote.drawio.xml` (mxGraph) |
| [`import-otm/`](./import-otm) | `import otm --mapping …` | `threagile/imports/vaultnote.otm.json` (Open Threat Model) |
| [`import-mermaid/`](./import-mermaid) | `import mermaid --mapping …` | `threagile/imports/vaultnote.mmd` (flowchart) — both the annotated scaffold (`from-mermaid.yaml`) and a plain `--scaffold=false` fragment (`from-mermaid-plain.yaml`) for comparison |
| [`import-merge/`](./import-merge) | `import drawio --merge …` | Redrawn diagram reconciled onto a hand-edited model without clobbering confirmed fields — see below |
| [`import-boundary/`](./import-boundary) | `import drawio --boundary "Application VPC"` | One trust boundary's subsystem scoped out of a larger diagram — see below |

## Re-import without clobbering hand edits

[`import-merge/`](./import-merge) simulates the full loop: `import drawio` produces
`model-before-merge.yaml`; a human then confirms the "MinIO Bucket" datastore
(drops its `review-drawio` tag, sets real `technology`/`encryption` values);
the diagram is redrawn (bucket renamed to "Object Storage", a new "Session
Cache" added — see `threagile/imports/vaultnote-v2.drawio.xml`) and re-imported
with `--merge` onto the same file (`model-after-merge.yaml`). Result
(`merge-summary.txt`): the new cache asset is appended, every still-importer-owned
field refreshes from the redrawn diagram, and the confirmed bucket's fields are
left untouched but gain a `merge-conflict:technology`/`merge-conflict:encryption`
tag flagging that the diagram now disagrees — nothing a human confirmed is ever
silently overwritten. See [docs/import-merge.md](../../../better-threagile/docs/import-merge.md).

## Boundary scoping (one subsystem out of a larger diagram)

[`import-boundary/`](./import-boundary) imports
`threagile/imports/vaultnote-multi-boundary.drawio.xml` (two trust boundaries:
"Application VPC" and a separate "Admin VPC" with its own admin console) two
ways: `from-full-diagram.yaml` (everything) vs.
`from-application-vpc-only.yaml` (`--boundary "Application VPC"`) — the latter
contains only that boundary's subsystem, with the Admin VPC and its console
entirely absent. Useful for importing one service at a time out of an
enterprise-wide diagram instead of producing one unreviewable mega-fragment.

## Human-in-the-loop review

| Dir | Command | What it shows |
|-----|---------|---------------|
| [`review/`](./review) | `review --format markdown\|json` | Every element still carrying a `review-<importer>`/`stub-data-asset` tag after the Mermaid import above — the checklist a human works through before trusting an imported model. `gate`'s `fail_on_unreviewed: true` policy key blocks CI on the same signal. |

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
