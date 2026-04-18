# VaultNote

A deliberately realistic note-taking application purpose-built as a threat modeling demo. It combines a React SPA, Nginx reverse proxy, Node.js/Express API, PostgreSQL, Redis, and MinIO — and intentional misconfigurations that each of the three threat modeling approaches will detect.

## Architecture

```
Browser (React) → [HTTPS] → Nginx → [HTTP ⚠️] → API Server
                                                  ├── PostgreSQL (no encryption at rest ⚠️)
                                                  ├── Redis      (no encryption at rest ⚠️)
                                                  └── MinIO      (default creds ⚠️, HTTP ⚠️)
```

The `⚠️` markers are **intentional misconfigurations** that the threat modeling tools will identify.

## Prerequisites

- Docker ≥ 24 + Docker Compose v2
- `openssl` (usually pre-installed)
- Python 3.10+ (for CI/CD scripts)

## Quick Start

```bash
# 1. Generate self-signed TLS certs for Nginx
mkdir -p nginx/certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/certs/server.key \
  -out    nginx/certs/server.crt \
  -subj "/CN=vaultnote.local"

# 2. Build the React frontend
cd frontend && npm install && npm run build && cd ..

# 3. Bring up the full stack
docker-compose up --build -d

# 4. Check health
curl -k https://localhost/api/health
```

Open **https://localhost** in your browser (accept the self-signed cert warning).

Demo credentials: `demo@vaultnote.local` / `demo1234`

## Quick API Test

```bash
# Register
curl -sk -X POST https://localhost/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@test.com","password":"testpass1"}'

# Login
TOKEN=$(curl -sk -X POST https://localhost/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"test@test.com","password":"testpass1"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# Create a note
curl -sk -X POST https://localhost/api/notes \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"title":"My first note","content":"Hello, VaultNote!"}'
```

---

## Approach 1: Threagile (Threat Modeling as Code)

Threagile reads `threagile/threagile.yaml` and runs 40+ built-in risk rules against the architecture declaration.

### Setup

```bash
# Pull Threagile image
docker pull threagile/threagile

# Create output directory
mkdir -p threagile/output
```

### Run Analysis

```bash
docker run --rm \
  -v $(pwd)/threagile:/app/work \
  threagile/threagile \
  analyze \
  -model /app/work/threagile.yaml \
  -output /app/work/output
```

### Output Files

| File | Description |
|------|-------------|
| `threagile/output/data-flow-diagram.png` | Auto-generated DFD |
| `threagile/output/report.pdf` | Full risk report with executive summary |
| `threagile/output/risks.xlsx` | Risk register for tracking |
| `threagile/output/risks.json` | Machine-readable output for CI/CD |

### Expected Findings

| Risk | Severity | Trigger |
|------|----------|---------|
| Unencrypted communication (Nginx → API) | **High** | `protocol: http` on internal link carrying credentials |
| Missing encryption at rest (PostgreSQL) | **High** | `encryption: none` on `strictly-confidential` datastore |
| Missing encryption at rest (MinIO) | **Medium** | `encryption: none` on `confidential` datastore |
| Missing encryption at rest (Redis) | **Medium** | Session tokens stored without encryption |
| Missing authentication (Nginx → API) | **Medium** | `authentication: none` on internal link |
| Container platform escape | **Medium** | Container-based deployment without hardening |
| SQL injection risk | **Medium** | REST API accessing database |
| Cross-site scripting | **Medium** | Browser SPA processing user-generated content |

---

## Approach 2: OWASP Threat Dragon (Visual)

Install and run Threat Dragon, then import `threat-dragon/vaultnote-model.json` to see the visual DFD with STRIDE threat annotations.

```bash
# Run via Docker
docker pull owasp/threat-dragon:v2.6.0
docker run -p 8080:3000 owasp/threat-dragon:v2.6.0
# Open http://localhost:8080
```

---

## Approach 3: CI/CD Pipeline

The GitHub Actions workflow at `.github/workflows/threat-model.yml` runs automatically when:
- `threagile/threagile.yaml` is modified
- `docker-compose.yml` changes
- API routes or middleware change

See `scripts/threat-model-diff.py` and `scripts/create-tickets.py` for the diff and ticketing automation.

---

## Project Structure

```
vaultnote/
├── docker-compose.yml          # Multi-service orchestration
├── nginx/
│   ├── nginx.conf              # Reverse proxy (TLS termination)
│   └── certs/                  # Self-signed TLS (git-ignored)
├── api/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── index.js            # Express entrypoint
│       ├── routes/             # auth, notes, files
│       ├── middleware/         # JWT auth, rate limiting
│       └── config/             # DB, Redis, MinIO clients
├── db/
│   └── init.sql                # Schema + seed data
├── frontend/
│   └── src/                    # React SPA
├── threagile/
│   ├── threagile.yaml          # ← Threat model (Approach 1)
│   └── output/                 # Generated reports
├── threat-dragon/
│   └── vaultnote-model.json    # ← Visual model (Approach 2)
├── scripts/
│   ├── threat-model-diff.py    # Risk diff for CI
│   └── create-tickets.py       # Auto-issue creation
└── .github/
    └── workflows/
        └── threat-model.yml    # ← CI/CD pipeline (Approach 3)
```

## Key Design Decisions (for Threat Modeling Discussion)

| Decision | Why It Matters |
|----------|---------------|
| HTTP between Nginx and API | Simulates a common real-world mistake. Credentials and session tokens cross this link in plaintext. |
| No encryption at rest on PostgreSQL | Disk exfiltration (volume backup theft) exposes all user data and credentials. |
| MinIO with default credentials | Hardcoded `minioadmin`/`minioadmin` — trivially exploitable by any process on `backend-net`. |
| Two Docker networks (`frontend-net` + `backend-net internal`) | Simulates real network segmentation. `backend-net` has no external routing. |
| API bridges both networks | The API container is the critical pivot point — its compromise gives full data tier access. |
| JWT with Redis revocation list | Allows immediate session invalidation on logout — a security control Threagile can credit. |
