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
| [`lint/`](./lint) | `lint --json` | Style / best-practice findings as JSON |
| [`gate/`](./gate) | `gate --policy …` | Policy-as-code CI gate verdict (exit 3 on violation) |
| [`policy/`](./policy) | `policy init --profile …` | Secure-by-default gate policies (prototype/balanced/strict/regulated) |
| [`quantify/`](./quantify) | `quantify --estimates …` | FAIR Monte-Carlo ALE (financial risk) |

## Exports / interoperability

| Dir | Command | What it shows |
|-----|---------|---------------|
| [`stix/`](./stix) | `stix` | STIX 2.1 bundle (with `x_threagile_version` / `x_model_sha256` provenance) |
| [`oscal/`](./oscal) | `oscal` | NIST OSCAL assessment-results (compliance evidence, with provenance props) |
| [`attack-navigator/`](./attack-navigator) | `attack-navigator` | MITRE ATT&CK Navigator layer |
| [`attack-tree/`](./attack-tree) | `attack-tree --format dot` | Goal-oriented attack trees (Graphviz DOT) |
| [`attack-paths/`](./attack-paths) | `paths` | Shortest attack paths from internet to crown-jewel data |
| [`d3fend/`](./d3fend) | `d3fend` | MITRE D3FEND defensive countermeasures |
| [`mermaid/`](./mermaid) | `mermaid` | Data-flow diagram that renders natively in GitHub/GitLab Markdown |
| [`sbom/`](./sbom) | `sbom --sbom …` | CycloneDX SBOM correlated with KEV/EPSS threat intel |

## Architecture importers (infra-as-code → model)

| Dir | Command | Source |
|-----|---------|--------|
| [`import-compose/`](./import-compose) | `import compose` | `docker-compose.yml` |
| [`import-kubernetes/`](./import-kubernetes) | `import kubernetes` | `threagile/imports/vaultnote-k8s.yaml` |
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
