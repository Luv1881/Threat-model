# VaultNote — reference threat-model target

VaultNote is a small, deliberately imperfect note-taking application (React SPA,
Express API, PostgreSQL, Redis, MinIO, Nginx) whose purpose is to be **threat
modeled**. It is the reference target for the
[better-threagile](https://github.com/Luv1881/better-threagile) fork: every
intentional weakness below is represented, tracked and gated in the threat
model under [`threagile/`](./threagile), and the CI pipeline in
[`.github/workflows/threat-model.yml`](./.github/workflows/threat-model.yml)
re-analyzes, diffs and tickets the findings on every relevant change.

> [!WARNING]
> This application is **not** production software. It ships default
> credentials, plain-HTTP service links and unencrypted storage on purpose.
> See [SECURITY.md](./SECURITY.md) before deploying anything or reporting a
> "vulnerability".

## Quick start

```sh
bash setup.sh          # generates TLS certs, builds the SPA, starts the stack
```

| What | Where |
|---|---|
| Web app (React SPA, TLS) | https://localhost |
| API health through Nginx | https://localhost/api/health |
| MinIO console | http://localhost:9001 (not published by default — see compose) |

Register an account in the UI (any email, password ≥ 8 characters) and create
notes; file attachments are stored in MinIO.

Stop the stack with `docker compose down` (add `-v` to delete the volumes).

## What's in the repository

| Path | Contents |
|---|---|
| `api/` | Express API: bcrypt password hashing, JWT sessions with Redis-backed logout revocation, per-route authorization, rate limiting, MinIO uploads |
| `frontend/` | React SPA (Create React App); `frontend/build` is the bundle Nginx serves |
| `nginx/` | TLS termination and API reverse proxy (`nginx/certs` is generated, never committed) |
| `db/` | PostgreSQL schema and seed SQL |
| `terraform/` | AWS reference architecture mirroring the compose stack (ALB, ECS, RDS, ElastiCache, S3, Secrets Manager) with the same intentional misconfigurations |
| `threagile/` | The multi-file threagile model: 18 technical assets, 7 trust boundaries, 9 methodology packs, risk tracking, gate policy, FAIR estimates, and import fixtures |
| `vaultnote-iriusrisk.otm` | The same model as an IriusRisk OTM document |
| `threat-dragon/` | OWASP Threat Dragon diagram |
| `scripts/` | CI helpers: risk diff, ticket sync, SARIF/issue glue, certificate generation |
| `setup.sh` | One-shot local setup (certs → SPA build → `docker compose up`) |

Additional model formats live under `threagile/imports/` (draw.io with single
and nested boundaries, Mermaid, Kubernetes and compose snapshots, an SBOM, and
attack-path output).

## How the threat modeling works here

On every change to the model, compose file, Nginx config, API routes,
middleware or config, and Terraform:

1. **analyze** — `better-threagile` runs the model (STRIDE plus, on main, the
   cloud-native / supply-chain / ai-ml packs) and writes `risks.json`, the SARIF
   report and the risk register into `threagile/output/`.
2. **gate** — a pull request that introduces critical or elevated risks without
   a `risk_tracking` entry is blocked (see `threagile/gate-policy.yaml`).
3. **review** — the risk delta is posted as a PR comment; SARIF findings land in
   the repository's code-scanning tab.
4. **ticket** — on `main`, every finding at or above `medium` is synced to a
   GitHub issue, keyed by the risk's synthetic ID, so accepted risks stay
   visible instead of being silently forgotten.

Run the same analysis locally:

```sh
go build -C ../better-threagile -o bin/threagile ./cmd/threagile/
../better-threagile/bin/threagile analyze-model \
  --model threagile/threagile.yaml \
  --output threagile/output \
  --app-dir ../better-threagile
```

`threagile/gate-policy.yaml` drives `threagile gate`, and
`threagile/fair-estimates.yaml` feeds `threagile prioritize` risk-adjusted
estimates.

## Documentation of the weaknesses

The threat model *is* the documentation: each intentional weakness carries an
`INTENTIONAL:` note on its asset and a `risk_tracking` entry with status,
justification, ticket and reviewer (`threagile/feature_risk_review.yaml`).
[SECURITY.md](./SECURITY.md) summarises the posture, lists what a recent audit
fixed, and explains how to report a genuine issue.
