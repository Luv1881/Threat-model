# Security policy

## This is a deliberately vulnerable application

VaultNote exists to be threat modeled. Its weaknesses are the test data: the
repository ships default credentials, plain-HTTP service links, unencrypted
storage, an unauthenticated LLM endpoint and more — all of it marked
`INTENTIONAL:` in [`threagile/`](./threagile) and tracked with a status,
justification and ticket in
[`threagile/feature_risk_review.yaml`](./threagile/feature_risk_review.yaml).

**Reported "vulnerabilities" that correspond to a tracked, intentional weakness
will be closed as working as intended.** The threat model is the authoritative
list; run `threagile review` (or read the tracking file) before reporting.

## Reporting a genuine issue

A genuine issue is anything *not* covered by the model: an exploit that
contradicts a tracked mitigation (for example, an IDOR that bypasses the
per-user checks the model claims), a leaked credential that is not part of the
demo fixtures, or a supply-chain problem in the pipeline itself.

Open a GitHub issue with reproduction steps and the affected revision. There is
no bug-bounty programme; this is a demonstration project.

## Audit status (last review: 2026-09)

Remediated:

- **Secret hygiene** — a TLS private key and a duplicate certificate directory
  were committed; all certificate material is now generated locally by
  `setup.sh` and ignored by git.
- **Repository hygiene** — 40,998 vendored `node_modules` files were tracked
  (they predate the ignore rule); the tracked tree is now 536 files and both
  Dockerfiles install from `package-lock.json`.
- **Stack could not start** — `minio/minio` no longer serves pulls from Docker
  Hub; the reference moved to `quay.io/minio/minio`, and all four compose images
  are pinned by digest (the direction the model's VAULT-155 image-integrity wave
  prescribes).
- **Dependencies** — API advisories 10 → 8 (minio 7 → 8 removes the
  fast-xml-parser/query-string/tar chain that dominated the report); frontend
  advisories 46 → 26 (the remainder is the react-scripts 5 webpack-dev-server
  chain, which is dev-time only — the shipped artefact is the static `build/`
  bundle — and unfixable without leaving CRA 5). Dependabot watches both
  lockfiles and the workflow actions.
- **CI hardening** — every action is pinned by commit digest (and kept current
  by Dependabot), the `GITHUB_TOKEN` flows through the environment instead of
  `argv`, and the analysis now also re-runs for `api/src/config/**` and
  `terraform/**` changes, which it previously ignored.
- **Model completeness** — five internet-exposed assets gained
  `entry_point_type` (PASTA surface) and the LLM endpoint was attached to its
  AI Services trust boundary; the risk set was verified unchanged.

Open items (tracked, not accidental):

- Image signing/scanning and digest pinning for ECS deployments (VAULT-155).
- mTLS between Nginx and the API (PR #47), strict CORS origin (VAULT-142),
  second-factor authentication, a WAF and a CSP — each has a tracking entry.
- The rate limiter is in-memory, so limits are per-instance once the API is
  scaled horizontally.
- Three trust boundaries (Internet, DMZ, Application Network) intentionally
  hold a single asset each; the linter notes them as advisories.

## Local security checks

```sh
docker compose config --quiet          # compose sanity
npm audit --package-lock-only -C api   # API advisories
npm audit --package-lock-only -C frontend
../better-threagile/bin/threagile validate --model threagile/threagile.yaml --fail-on-secrets
../better-threagile/bin/threagile gate --model threagile/threagile.yaml --policy threagile/gate-policy.yaml
```
