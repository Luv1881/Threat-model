# Automated Threat Modeling Demo — Execution Plan

## 1. The Demo Application: "VaultNote"

A deliberately realistic note-taking application with enough architectural surface area to make threat modeling interesting. Not a toy — it has auth, storage, file uploads, and crosses multiple trust boundaries.

### 1.1 Architecture

```
┌─────────────┐         ┌──────────────────┐         ┌──────────────────────────────────────┐
│   Browser    │─HTTPS──▶│  Nginx Reverse   │─HTTP───▶│  Docker Network (vaultnote-net)      │
│  (React SPA) │◀────────│  Proxy (:443)    │◀────────│                                      │
└─────────────┘         └──────────────────┘         │  ┌────────────┐   ┌───────────────┐  │
                                                      │  │  API Server │──▶│  PostgreSQL   │  │
                                                      │  │  (Node.js/ │   │  (:5432)      │  │
                                                      │  │  Express)  │   └───────────────┘  │
                                                      │  │  (:3000)   │                      │
                                                      │  │            │──▶┌───────────────┐  │
                                                      │  └────────────┘   │  Redis         │  │
                                                      │        │          │  (:6379)       │  │
                                                      │        ▼          └───────────────┘  │
                                                      │  ┌────────────┐                      │
                                                      │  │  MinIO/S3  │                      │
                                                      │  │  (file     │                      │
                                                      │  │  uploads)  │                      │
                                                      │  │  (:9000)   │                      │
                                                      │  └────────────┘                      │
                                                      └──────────────────────────────────────┘
```

### 1.2 Components and Their Purpose

| Component | Tech | Role | Why It Matters for Threat Modeling |
|-----------|------|------|-----------------------------------|
| **Frontend** | React SPA | User-facing UI, renders notes, handles auth flow | Client-side trust boundary, XSS surface |
| **Nginx** | Reverse proxy + TLS termination | Sits on the host, forwards to Docker | Trust boundary crossing (internet → internal), TLS termination point |
| **API Server** | Node.js + Express | REST API: auth, CRUD on notes, file upload/download | Core process — handles authn/authz, input validation, business logic |
| **PostgreSQL** | Relational DB | Stores users, notes, metadata | Contains PII + confidential data, SQL injection target |
| **Redis** | In-memory store | Session store + rate-limiting counters | Session hijacking surface, no persistence by default |
| **MinIO** | S3-compatible object store | File attachments for notes | Stores user-uploaded files, SSRF + path traversal surface |

### 1.3 Data Flows (These Are What You Threat Model)

| # | Flow | Protocol | Data Classification | Trust Boundaries Crossed |
|---|------|----------|---------------------|--------------------------|
| F1 | Browser → Nginx | HTTPS | Credentials, note content (confidential) | Internet → DMZ |
| F2 | Nginx → API Server | HTTP (internal) | Same as F1 minus TLS | DMZ → Application Network |
| F3 | API Server → PostgreSQL | TCP (pg wire) | SQL queries, user data (strictly confidential) | App → Data tier |
| F4 | API Server → Redis | TCP | Session tokens, rate-limit counters (internal) | App → Cache tier |
| F5 | API Server → MinIO | HTTP (S3 API) | File uploads/downloads (confidential) | App → Storage tier |
| F6 | Browser → MinIO (presigned URL) | HTTPS | File download (confidential) | Internet → Storage tier (bypass) |

### 1.4 Trust Boundaries

1. **Internet ↔ DMZ** (Nginx): All external traffic crosses here
2. **DMZ ↔ Application Network**: Nginx → API Server, unencrypted HTTP
3. **Application ↔ Data Tier**: API Server → PostgreSQL/Redis
4. **Application ↔ Storage Tier**: API Server → MinIO
5. **Internet ↔ Storage Tier** (if presigned URLs are used): Browser → MinIO direct

### 1.5 Building It — Step by Step

**Step 1: Project structure**
```
vaultnote/
├── docker-compose.yml
├── nginx/
│   ├── nginx.conf
│   └── certs/           # self-signed for demo
├── api/
│   ├── Dockerfile
│   ├── package.json
│   ├── src/
│   │   ├── index.js          # Express entrypoint
│   │   ├── routes/
│   │   │   ├── auth.js       # POST /login, /register, /logout
│   │   │   ├── notes.js      # CRUD /notes
│   │   │   └── files.js      # POST /upload, GET /download/:id
│   │   ├── middleware/
│   │   │   ├── authMiddleware.js
│   │   │   └── rateLimiter.js
│   │   ├── models/
│   │   │   ├── user.js
│   │   │   └── note.js
│   │   └── config/
│   │       └── db.js
├── db/
│   └── init.sql              # Schema + seed data
├── frontend/
│   ├── Dockerfile
│   ├── src/
│   └── public/
├── threagile/
│   └── threagile.yaml        # Approach 1
├── threat-dragon/
│   └── vaultnote-model.json  # Approach 2
├── .github/
│   └── workflows/
│       └── threat-model.yml  # Approach 3
└── README.md
```

**Step 2: docker-compose.yml**
```yaml
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    depends_on:
      - api
    networks:
      - frontend-net

  api:
    build: ./api
    environment:
      - DATABASE_URL=postgresql://vaultnote:secretpass@db:5432/vaultnote
      - REDIS_URL=redis://redis:6379
      - MINIO_ENDPOINT=minio
      - MINIO_PORT=9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=minioadmin
      - JWT_SECRET=change-me-in-production
      - SESSION_SECRET=also-change-me
    depends_on:
      - db
      - redis
      - minio
    networks:
      - frontend-net
      - backend-net

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: vaultnote
      POSTGRES_PASSWORD: secretpass
      POSTGRES_DB: vaultnote
    volumes:
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql
      - pgdata:/var/lib/postgresql/data
    networks:
      - backend-net

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass redispass
    networks:
      - backend-net

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    volumes:
      - miniodata:/data
    networks:
      - backend-net

networks:
  frontend-net:
    driver: bridge
  backend-net:
    driver: bridge
    internal: true    # No external access to backend

volumes:
  pgdata:
  miniodata:
```

Key architectural decisions that create threat surface intentionally:
- Two Docker networks simulate real segmentation (frontend-net is reachable, backend-net is internal-only)
- API server bridges both networks — this is the pivot point
- Hardcoded credentials in compose file — Threagile will catch this
- HTTP between Nginx and API — Threagile will flag unencrypted internal traffic
- MinIO with default creds — another detection target

**Step 3: Implement the API (minimal but real)**

The API needs just enough to be real: JWT-based auth, CRUD on notes with user isolation, file upload to MinIO. Keep it to ~300 lines. Use `express`, `pg`, `ioredis`, `minio`, `jsonwebtoken`, `bcrypt`, `multer`.

**Step 4: Nginx config**
```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/nginx/certs/server.crt;
    ssl_certificate_key /etc/nginx/certs/server.key;

    location /api/ {
        proxy_pass http://api:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        root /usr/share/nginx/html;
        try_files $uri /index.html;
    }
}
```

**Step 5: Bring it up**
```bash
# Generate self-signed certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/certs/server.key -out nginx/certs/server.crt \
  -subj "/CN=vaultnote.local"

docker-compose up --build -d
```

You now have a running application. Everything below threat-models *this exact system*.

---

## 2. Approach 1: Threagile (Rules-Based, Threat Modeling as Code)

### 2.1 What It Is

Threagile reads a YAML file that declares your architecture — every asset, every data flow, every trust boundary — and runs 40+ built-in risk rules against it. It produces a DFD, a PDF risk report, an Excel risk register, and JSON output. No GUI, no manual drawing. The model *is* the code.

### 2.2 Why It Matters for the Presentation

This is the "shift-left" showcase. The threat model lives in the same repo as the application code. It's diff-able, reviewable in PRs, and can run in CI. When you add a new component to the YAML, Threagile automatically evaluates it against every risk rule.

### 2.3 Detailed Workflow

**Step 1: Install Threagile**
```bash
# Pull the Docker image (no local Go install needed)
docker pull threagile/threagile

# Verify it works
docker run --rm threagile/threagile help

# Create a working directory
mkdir -p threagile/output
```

**Step 2: Generate the stub model**
```bash
docker run --rm -v $(pwd)/threagile:/app/work threagile/threagile \
  -create-stub-model -output /app/work
```
This drops a `threagile-stub-model.yaml` with the full schema and every available field. Use it as your reference while writing the real model.

**Step 3: Write the VaultNote threat model in YAML**

This is the core work. You're declaring every component from Section 1 in Threagile's schema. The key sections:

```yaml
threagile_version: 1.0.0
title: VaultNote Threat Model
author:
  name: "Your Name"
date: 2026-04-18

business_criticality: important

# ── DATA ASSETS ──────────────────────────────────────
data_assets:

  User Credentials:
    id: user-credentials
    usage: business
    origin: customer
    owner: VaultNote Team
    quantity: many
    confidentiality: strictly-confidential
    integrity: critical
    availability: operational
    justification_cia_rating: >
      Credentials grant full account access. Compromise = full account takeover.

  Note Content:
    id: note-content
    usage: business
    origin: customer
    owner: VaultNote Team
    quantity: many
    confidentiality: confidential
    integrity: critical
    availability: operational

  Session Tokens:
    id: session-tokens
    usage: business
    origin: customer
    owner: VaultNote Team
    quantity: many
    confidentiality: confidential
    integrity: critical
    availability: operational

  File Attachments:
    id: file-attachments
    usage: business
    origin: customer
    owner: VaultNote Team
    quantity: many
    confidentiality: confidential
    integrity: important
    availability: operational

# ── TECHNICAL ASSETS ─────────────────────────────────
technical_assets:

  Browser SPA:
    id: browser-spa
    type: external-entity
    usage: business
    used_as_client_by_human: true
    internet: true
    machine: physical
    technology: browser
    size: application
    encryption: none
    owner: End User
    confidentiality: public
    integrity: operational
    availability: operational
    multi_tenant: false
    redundant: false
    data_assets_processed:
      - user-credentials
      - note-content
    communication_links:
      HTTPS to Nginx:
        target: nginx-proxy
        protocol: https
        authentication: credentials
        authorization: enduser-identity-propagation
        data_assets_sent:
          - user-credentials
          - note-content
        data_assets_received:
          - note-content
          - file-attachments

  Nginx Reverse Proxy:
    id: nginx-proxy
    type: process
    usage: business
    used_as_client_by_human: false
    internet: false
    machine: container
    technology: reverse-proxy
    size: service
    encryption: none
    owner: VaultNote Team
    confidentiality: internal
    integrity: critical
    availability: critical
    multi_tenant: false
    redundant: false
    data_assets_processed:
      - user-credentials
      - note-content
    communication_links:
      HTTP to API:
        target: api-server
        protocol: http    # ← Intentionally insecure for Threagile to catch
        authentication: none
        authorization: none
        data_assets_sent:
          - user-credentials
          - note-content
        data_assets_received:
          - note-content

  API Server:
    id: api-server
    type: process
    usage: business
    used_as_client_by_human: false
    internet: false
    machine: container
    technology: web-service-rest
    size: service
    encryption: none
    owner: VaultNote Team
    confidentiality: confidential
    integrity: critical
    availability: critical
    multi_tenant: false
    redundant: false
    data_assets_processed:
      - user-credentials
      - note-content
      - session-tokens
      - file-attachments
    communication_links:
      PostgreSQL Connection:
        target: postgresql-db
        protocol: tcp
        authentication: credentials
        authorization: technical-user
        data_assets_sent:
          - user-credentials
          - note-content
        data_assets_received:
          - note-content
      Redis Connection:
        target: redis-cache
        protocol: tcp
        authentication: credentials
        authorization: technical-user
        data_assets_sent:
          - session-tokens
        data_assets_received:
          - session-tokens
      MinIO Connection:
        target: minio-storage
        protocol: http
        authentication: credentials
        authorization: technical-user
        data_assets_sent:
          - file-attachments
        data_assets_received:
          - file-attachments

  PostgreSQL Database:
    id: postgresql-db
    type: datastore
    usage: business
    used_as_client_by_human: false
    internet: false
    machine: container
    technology: database
    size: service
    encryption: none    # ← No encryption at rest — Threagile flags this
    owner: VaultNote Team
    confidentiality: strictly-confidential
    integrity: critical
    availability: critical
    multi_tenant: false
    redundant: false
    data_assets_stored:
      - user-credentials
      - note-content

  Redis Cache:
    id: redis-cache
    type: datastore
    usage: business
    used_as_client_by_human: false
    internet: false
    machine: container
    technology: database
    size: component
    encryption: none
    owner: VaultNote Team
    confidentiality: confidential
    integrity: operational
    availability: important
    multi_tenant: false
    redundant: false
    data_assets_stored:
      - session-tokens

  MinIO Object Storage:
    id: minio-storage
    type: datastore
    usage: business
    used_as_client_by_human: false
    internet: false
    machine: container
    technology: database
    size: service
    encryption: none
    owner: VaultNote Team
    confidentiality: confidential
    integrity: important
    availability: operational
    multi_tenant: false
    redundant: false
    data_assets_stored:
      - file-attachments

# ── TRUST BOUNDARIES ─────────────────────────────────
trust_boundaries:

  Internet:
    id: internet
    type: network-cloud-provider
    technical_assets_inside:
      - browser-spa

  DMZ:
    id: dmz
    type: network-cloud-provider
    technical_assets_inside:
      - nginx-proxy

  Application Network:
    id: application-network
    type: network-cloud-provider
    technical_assets_inside:
      - api-server

  Data Tier:
    id: data-tier
    type: network-cloud-provider
    technical_assets_inside:
      - postgresql-db
      - redis-cache
      - minio-storage
```

**Step 4: Run the analysis**
```bash
docker run --rm \
  -v $(pwd)/threagile:/app/work \
  threagile/threagile \
  analyze \
  -model /app/work/threagile.yaml \
  -output /app/work/output
```

**Step 5: Review the outputs**

Threagile generates these files in the output directory:
- `data-flow-diagram.png` — Auto-generated DFD with trust boundaries drawn
- `report.pdf` — Full risk report: executive summary, risk table, mitigation advice
- `risks.xlsx` — Risk register with severity, likelihood, category, tracking ID
- `risks.json` — Machine-readable version for programmatic consumption
- `technical-assets.json` — Parsed asset model
- `stats.json` — Summary statistics

**Step 6: Examine what Threagile found**

Expected findings for our deliberately insecure VaultNote setup:
| # | Risk | Severity | What Triggered It |
|---|------|----------|-------------------|
| 1 | Unencrypted communication (Nginx → API) | High | `protocol: http` on an internal link carrying credentials |
| 2 | Missing encryption at rest (PostgreSQL) | High | `encryption: none` on datastore holding `strictly-confidential` data |
| 3 | Missing encryption at rest (MinIO) | Medium | `encryption: none` on datastore holding `confidential` data |
| 4 | Missing encryption at rest (Redis) | Medium | Session tokens stored without encryption |
| 5 | Container platform escaping | Medium | Container-based deployment without hardening flags |
| 6 | Missing authentication (Nginx → API) | Medium | `authentication: none` on internal link |
| 7 | Missing network segmentation | Medium | Trust boundaries without strict isolation |
| 8 | Cross-site scripting | Medium | Browser SPA processing user-generated content |
| 9 | SQL injection | Medium | Database accessed via web service REST |
| 10 | Missing input validation | Medium | REST API processing external input |

**Step 7: Track risks in the YAML**

Add `risk_tracking` entries to the model file itself:
```yaml
risk_tracking:

  unencrypted-communication@nginx-proxy>api-server:
    status: in-progress
    justification: "Migrating to mTLS between Nginx and API server. PR #47 in review."
    ticket: VAULT-102
    date: 2026-04-18
    checked_by: "Your Name"

  missing-encryption-at-rest@postgresql-db:
    status: mitigated
    justification: "Enabled TDE on PostgreSQL. Verified with pg_stat_ssl."
    ticket: VAULT-89
    date: 2026-04-15
    checked_by: "Your Name"
```

This tracking state is version-controlled alongside the model. Anyone can see what's been triaged, what's pending, and what's accepted.

### 2.4 What to Show in the Presentation

1. The YAML file itself — "this is the threat model, 150 lines, lives next to the code"
2. Run the `analyze` command live → takes 2-3 seconds
3. Open the generated DFD → auto-drawn from YAML
4. Open the risk report PDF → flip to the risk table
5. Show the `risk_tracking` section → "this is how we close the loop"

### 2.5 Strengths to Highlight
- Zero manual diagramming — DFD is derived from the model
- Deterministic — same input always produces same output
- Fast — runs in seconds, can gate a pipeline
- Auditable — the YAML is the single source of truth, diff-able in Git

### 2.6 Limitations to Be Honest About
- Only finds what the rules know about (no novel threats, no business logic flaws)
- Requires someone to correctly describe the architecture in YAML — garbage in, garbage out
- No code awareness — doesn't know if you actually implemented input validation or not

---

## 3. Approach 2: OWASP Threat Dragon (Visual, Diagram-Driven)

### 3.1 What It Is

Threat Dragon is a free, open-source threat modeling tool with a visual drag-and-drop interface for building Data Flow Diagrams. You draw the system, define trust boundaries, and Threat Dragon's rule engine suggests threats per STRIDE categories for each element. It's the closest thing to the "classic whiteboard threat model" in digital form.

### 3.2 Why It Matters for the Presentation

This represents the visual/collaborative approach — the one that security teams and architects use in workshops. It's human-readable, intuitive, and produces outputs that non-technical stakeholders can follow.

### 3.3 Detailed Workflow

**Step 1: Install Threat Dragon**

Option A — Desktop (recommended for demo stability):
```bash
# Download from GitHub releases (v2.6.0 as of writing)
# macOS: .dmg, Windows: .exe, Linux: .AppImage or .snap
# https://github.com/OWASP/threat-dragon/releases

# Or via snap on Linux:
sudo snap install threat-dragon
```

Option B — Docker (web version):
```bash
docker pull owasp/threat-dragon:v2.6.0
docker run -p 8080:3000 owasp/threat-dragon:v2.6.0
# Open http://localhost:8080
```

Option C — npm (from source):
```bash
git clone https://github.com/owasp/threat-dragon
cd threat-dragon
npm install
npm run dev
```

**Step 2: Create a new model**

1. Open Threat Dragon → click "New Model" (plus icon)
2. Fill in model metadata:
   - **Title**: VaultNote Threat Model
   - **Owner**: Your Name
   - **Description**: Threat model for VaultNote — a containerized note-taking application with reverse proxy, REST API, PostgreSQL, Redis, and MinIO
3. Save to local filesystem (desktop) or GitHub repo (web)

**Step 3: Create the first diagram — "Main Data Flow"**

1. Click "Add a new diagram"
2. Name it: "VaultNote — Main Data Flow"
3. Select diagram type: STRIDE

**Step 4: Draw the architecture**

Add the following elements by dragging from the stencil panel:

Processes (circles):
- "Nginx Reverse Proxy"
- "API Server (Express)"

External Entities (rectangles):
- "Browser (User)"

Data Stores (parallel lines):
- "PostgreSQL"
- "Redis"
- "MinIO"

Trust Boundaries (dashed boxes):
- "Internet" — contains Browser
- "DMZ" — contains Nginx
- "Docker Internal Network" — contains API Server, PostgreSQL, Redis, MinIO

Data Flows (arrows) — draw these connecting elements:
1. Browser → Nginx: "HTTPS Request (credentials, note data)"
2. Nginx → Browser: "HTTPS Response (note content, files)"
3. Nginx → API Server: "HTTP Proxied Request"
4. API Server → Nginx: "HTTP Response"
5. API Server → PostgreSQL: "SQL Queries (user data, notes)"
6. PostgreSQL → API Server: "Query Results"
7. API Server → Redis: "Session Read/Write"
8. Redis → API Server: "Session Data"
9. API Server → MinIO: "S3 PutObject/GetObject"
10. MinIO → API Server: "File Data"

**Step 5: Add threats to each element**

Click on each element and each data flow. Threat Dragon will suggest STRIDE categories. For each one, fill in:

For the **Nginx → API Server** data flow:
- **Threat**: Eavesdropping on unencrypted internal traffic
- **STRIDE Category**: Information Disclosure
- **Priority**: High
- **Status**: Open
- **Description**: Traffic between Nginx and the API server uses plaintext HTTP. An attacker with access to the Docker network (container escape, compromised sidecar) can sniff credentials, session tokens, and note content.
- **Mitigation**: Implement mTLS between Nginx and the API server, or encrypt the Docker network overlay.

For the **API Server** process:
- **Threat**: Injection via unsanitized input
- **STRIDE Category**: Tampering
- **Priority**: High
- **Status**: Open
- **Description**: The API server accepts user input for note creation and search. Without parameterized queries and input validation, it's vulnerable to SQL injection and stored XSS.
- **Mitigation**: Use parameterized queries (pg library supports this natively). Sanitize HTML output. Implement Content Security Policy headers.

For the **PostgreSQL** data store:
- **Threat**: Data breach from unencrypted storage
- **STRIDE Category**: Information Disclosure
- **Priority**: High
- **Status**: Open
- **Description**: PostgreSQL stores user credentials and note content without encryption at rest. Disk access (volume mount, backup theft) exposes all data.
- **Mitigation**: Enable PostgreSQL TDE or use encrypted volumes. Ensure backups are encrypted.

For the **Redis** data store:
- **Threat**: Session hijacking via Redis exposure
- **STRIDE Category**: Elevation of Privilege
- **Priority**: Medium
- **Status**: Open
- **Description**: If Redis becomes accessible outside the backend network, session tokens can be extracted and replayed.
- **Mitigation**: Bind Redis to the internal network only. Use AUTH. Set session TTLs.

For **MinIO**:
- **Threat**: Unauthorized file access via default credentials
- **STRIDE Category**: Information Disclosure
- **Priority**: High
- **Status**: Open
- **Description**: MinIO runs with default minioadmin/minioadmin credentials. Anyone with network access can download all stored files.
- **Mitigation**: Rotate default credentials. Implement bucket policies. Use presigned URLs with short TTLs.

Continue this for every element and flow. Aim for 15–20 threats total.

**Step 6: Generate the report**

1. Go to the model overview page
2. Click "Report" in the bottom right
3. Configure which sections to include (diagrams, threats, mitigations)
4. Export as PDF or print

**Step 7: Export the model file**

Threat Dragon saves models as JSON files. Export `vaultnote-model.json` and commit it to the `threat-dragon/` directory in the repo.

### 3.4 What to Show in the Presentation

1. The visual DFD — "this is what everyone draws on the whiteboard, but now it's digital and versioned"
2. Click on a data flow → show the threat details panel with STRIDE categorization
3. The per-element threat list — "Threat Dragon suggests categories; the human fills in the specifics"
4. The generated report — "this goes to the security review board"
5. The JSON model file — "this can be checked into Git, but it's not human-readable like Threagile's YAML"

### 3.5 Strengths to Highlight
- Visual and intuitive — architects and PMs can follow along
- STRIDE-per-element approach is methodical and complete
- Free, open source, runs locally (no data leaves your machine)
- Good for collaborative threat modeling workshops

### 3.6 Limitations to Be Honest About
- Manual process — you draw everything by hand, you write every threat by hand
- No automation — the rule engine suggests STRIDE *categories* but not specific threats
- Doesn't scale to many microservices (imagine drawing 40 services)
- The JSON model format is not interoperable with Threagile or pytm

---

## 4. Approach 3: CI/CD Pipeline Integration (Continuous Threat Modeling)

### 4.1 What It Is

This approach integrates threat modeling directly into the GitHub Actions (or GitLab CI) pipeline. The threat model runs automatically on every relevant code change — no human trigger required. It combines Threagile for rules-based analysis with a diff engine that surfaces only *new or changed* risks, and auto-creates tickets for findings.

### 4.2 Why It Matters for the Presentation

This is the "where we're going" slide. It demonstrates that threat modeling isn't a quarterly exercise but a continuous, automated gate in the deployment pipeline — just like SAST, DAST, and dependency scanning.

### 4.3 Detailed Workflow

**Step 1: Set up the GitHub repository structure**

The VaultNote repo needs:
```
.github/
  workflows/
    threat-model.yml          # The CI pipeline
scripts/
  threat-model-diff.py        # Compares new vs previous risk output
  create-tickets.py           # Creates GitHub Issues for new high-severity risks
threagile/
  threagile.yaml              # The architecture model (from Approach 1)
  output/                     # Generated outputs (committed for history)
    risks.json                # Previous run's risk output
```

**Step 2: Write the GitHub Actions workflow**

```yaml
# .github/workflows/threat-model.yml
name: Continuous Threat Modeling

on:
  push:
    paths:
      - 'threagile/threagile.yaml'     # Model changes
      - 'docker-compose.yml'           # Infra changes
      - 'api/src/routes/**'            # New API endpoints
      - 'api/src/middleware/**'         # Auth/authz changes
      - 'nginx/nginx.conf'             # Proxy config changes
  pull_request:
    paths:
      - 'threagile/threagile.yaml'

jobs:
  threat-model-analysis:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      issues: write
      pull-requests: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 2    # Need previous commit for diff

      - name: Cache previous risk output
        id: cache-risks
        uses: actions/cache@v4
        with:
          path: threagile/output/risks-previous.json
          key: threat-model-risks-${{ github.sha }}
          restore-keys: threat-model-risks-

      - name: Copy current risks as baseline
        run: |
          if [ -f threagile/output/risks.json ]; then
            cp threagile/output/risks.json threagile/output/risks-previous.json
          else
            echo "[]" > threagile/output/risks-previous.json
          fi

      - name: Run Threagile analysis
        run: |
          docker run --rm \
            -v ${{ github.workspace }}/threagile:/app/work \
            threagile/threagile \
            analyze \
            -model /app/work/threagile.yaml \
            -output /app/work/output

      - name: Diff threat models
        id: diff
        run: |
          python3 scripts/threat-model-diff.py \
            --previous threagile/output/risks-previous.json \
            --current threagile/output/risks.json \
            --output threagile/output/diff-report.json

      - name: Comment on PR with new threats
        if: github.event_name == 'pull_request' && steps.diff.outputs.new_risks_count > 0
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const diff = JSON.parse(fs.readFileSync('threagile/output/diff-report.json', 'utf8'));
            let body = `## 🔒 Threat Model Update\n\n`;
            body += `**${diff.new_risks.length} new risk(s)** detected by this change:\n\n`;
            for (const risk of diff.new_risks) {
              const icon = risk.severity === 'critical' ? '🔴' :
                           risk.severity === 'elevated' ? '🟠' : '🟡';
              body += `${icon} **${risk.title}**\n`;
              body += `   - Severity: ${risk.severity}\n`;
              body += `   - Category: ${risk.category}\n`;
              body += `   - Affected: ${risk.most_relevant_technical_asset}\n\n`;
            }
            body += `\n> Full report available in the [workflow artifacts](${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}).`;

            github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: body
            });

      - name: Create issues for critical/elevated risks
        if: steps.diff.outputs.has_critical == 'true'
        run: |
          python3 scripts/create-tickets.py \
            --diff threagile/output/diff-report.json \
            --min-severity elevated \
            --repo ${{ github.repository }} \
            --token ${{ secrets.GITHUB_TOKEN }}

      - name: Fail if untracked critical risks
        if: steps.diff.outputs.has_untracked_critical == 'true'
        run: |
          echo "::error::New critical risks detected without risk_tracking entries."
          echo "Add risk_tracking entries to threagile.yaml before merging."
          exit 1

      - name: Upload threat model artifacts
        uses: actions/upload-artifact@v4
        with:
          name: threat-model-report
          path: |
            threagile/output/report.pdf
            threagile/output/data-flow-diagram.png
            threagile/output/risks.xlsx
            threagile/output/risks.json
            threagile/output/diff-report.json
```

**Step 3: Write the diff script**

```python
# scripts/threat-model-diff.py
import json
import argparse
import sys

def load_risks(filepath):
    with open(filepath) as f:
        data = json.load(f)
    # Threagile outputs risks as a dict keyed by synthetic ID
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

    new_ids = curr_ids - prev_ids
    removed_ids = prev_ids - curr_ids

    curr_map = {r.get('synthetic_id', r.get('id', '')): r for r in current}
    prev_map = {r.get('synthetic_id', r.get('id', '')): r for r in previous}

    new_risks = [curr_map[rid] for rid in new_ids]
    removed_risks = [prev_map[rid] for rid in removed_ids]

    return {
        'new_risks': new_risks,
        'removed_risks': removed_risks,
        'total_current': len(current),
        'total_previous': len(previous),
        'delta': len(current) - len(previous)
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--previous', required=True)
    parser.add_argument('--current', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()

    previous = load_risks(args.previous)
    current = load_risks(args.current)
    result = diff_risks(previous, current)

    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)

    has_critical = any(
        r.get('severity', '') in ('critical', 'elevated')
        for r in result['new_risks']
    )

    # Set GitHub Actions outputs
    print(f"::set-output name=new_risks_count::{len(result['new_risks'])}")
    print(f"::set-output name=has_critical::{'true' if has_critical else 'false'}")
    print(f"::set-output name=has_untracked_critical::{'true' if has_critical else 'false'}")

    print(f"\nDiff summary:")
    print(f"  New risks: {len(result['new_risks'])}")
    print(f"  Removed risks: {len(result['removed_risks'])}")
    print(f"  Total current: {result['total_current']}")

if __name__ == '__main__':
    main()
```

**Step 4: Write the ticket creation script**

```python
# scripts/create-tickets.py
import json
import argparse
import subprocess

def create_issue(repo, token, title, body, labels):
    """Create a GitHub issue using gh CLI or API."""
    import urllib.request
    url = f"https://api.github.com/repos/{repo}/issues"
    data = json.dumps({
        'title': title,
        'body': body,
        'labels': labels
    }).encode()

    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Authorization', f'token {token}')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Accept', 'application/vnd.github.v3+json')

    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        print(f"Created issue #{result['number']}: {result['title']}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--diff', required=True)
    parser.add_argument('--min-severity', default='elevated')
    parser.add_argument('--repo', required=True)
    parser.add_argument('--token', required=True)
    args = parser.parse_args()

    severity_order = ['low', 'medium', 'elevated', 'critical']
    min_idx = severity_order.index(args.min_severity)

    with open(args.diff) as f:
        diff = json.load(f)

    for risk in diff['new_risks']:
        sev = risk.get('severity', 'medium')
        if severity_order.index(sev) >= min_idx:
            title = f"[Threat Model] {risk.get('title', 'Unknown risk')}"
            body = (
                f"**Severity**: {sev}\n"
                f"**Category**: {risk.get('category', 'N/A')}\n"
                f"**Affected Asset**: {risk.get('most_relevant_technical_asset', 'N/A')}\n\n"
                f"**Description**:\n{risk.get('description', 'No description')}\n\n"
                f"**Suggested Mitigation**:\n{risk.get('mitigation', 'Review and mitigate')}\n\n"
                f"---\n*Auto-generated by the threat modeling pipeline.*"
            )
            create_issue(
                args.repo, args.token, title, body,
                labels=['security', 'threat-model', sev]
            )

if __name__ == '__main__':
    main()
```

**Step 5: Trigger and demo the pipeline**

To demonstrate the pipeline in action:

1. **Start with the baseline**: Push the initial `threagile.yaml` → pipeline runs → produces baseline risk output, no diff (first run)
2. **Make a change that introduces risk**: Add a new external entity (e.g., a webhook endpoint) to the YAML that accepts unauthenticated inbound requests
3. **Open a PR**: The pipeline runs, diffs against baseline, and posts a comment on the PR listing the new risks
4. **Show the pipeline failing**: If the new risk is critical and has no `risk_tracking` entry, the pipeline exits with a non-zero code → PR cannot merge
5. **Fix it**: Add a `risk_tracking` entry acknowledging the risk → pipeline passes → PR can merge

### 4.4 What to Show in the Presentation

1. The workflow YAML — "threat modeling triggers on the same paths as your code changes"
2. The PR comment with the risk diff — "the developer sees this before merge"
3. The auto-created GitHub Issue — "this goes into the backlog without anyone filing it"
4. The pipeline failure — "you cannot merge a critical untracked risk"
5. The fix — adding `risk_tracking` → pipeline passes

### 4.5 Strengths to Highlight
- Fully automated — no human has to remember to run the threat model
- Diff-based — only surfaces new risks, not the entire backlog every time
- Integrated with developer workflow — PR comments, Issues, pipeline gates
- Auditable trail — every risk decision is in Git history

### 4.6 Limitations to Be Honest About
- Still depends on someone maintaining the YAML model accurately
- Can create alert fatigue if the rules produce too many low-severity findings
- Requires organizational buy-in — security team must own the pipeline config
- Doesn't catch risks that the rules engine doesn't know about (same as Threagile)

---

## 5. Phased Execution Plan

### Phase 1: Build the Demo App (Days 1–3)

| Day | Tasks |
|-----|-------|
| 1 | Set up the project structure. Write docker-compose.yml. Create Nginx config with self-signed certs. Write the PostgreSQL init.sql schema (users, notes, attachments tables). |
| 2 | Build the API server: auth routes (register/login/logout with JWT + bcrypt), notes CRUD routes, file upload/download routes with MinIO. Wire up Redis for session storage. Test with curl/Postman. |
| 3 | Build a minimal React frontend (login page, notes list, note editor, file upload). Wire it through Nginx. Verify end-to-end: register → login → create note → attach file → download file. |

**Exit criteria**: `docker-compose up` brings up the full stack, and you can complete the user flow from browser to database and back.

### Phase 2: Threagile Model (Days 4–5)

| Day | Tasks |
|-----|-------|
| 4 | Write the `threagile.yaml` model from the template in Section 2. Define all data assets, technical assets, communication links, and trust boundaries. Run the analysis. Review the generated DFD and risk report. |
| 5 | Iterate on the model: fix any schema errors, adjust CIA ratings, add `risk_tracking` entries for 3–4 risks to demonstrate the tracking workflow. Prepare the demo script: what you'll show live, what you'll have pre-rendered as backup. |

**Exit criteria**: Threagile produces a clean DFD, a PDF report with 10+ identified risks, and the risk tracking section shows mitigation decisions.

### Phase 3: Threat Dragon Model (Days 5–6)

| Day | Tasks |
|-----|-------|
| 5 | Install Threat Dragon desktop. Create the VaultNote model. Draw the main DFD with all components, data flows, and trust boundaries. |
| 6 | Add STRIDE threats to each element and data flow (aim for 15–20 threats). Generate the report. Export the JSON model file. Compare the findings with Threagile's output — note overlap and gaps. |

**Exit criteria**: Threat Dragon has a complete DFD with threats documented per element, and a generated PDF report.

### Phase 4: CI/CD Pipeline (Days 6–8)

| Day | Tasks |
|-----|-------|
| 6 | Write the GitHub Actions workflow YAML. Write the diff script. Write the ticket creation script. |
| 7 | Push to GitHub. Trigger the pipeline with the initial model. Verify it runs Threagile, produces artifacts, and completes successfully. |
| 8 | Simulate the "introduce a risk" scenario: modify the model, open a PR, verify the PR comment appears. Verify the pipeline failure on untracked critical risks. Record screenshots/screen captures for the presentation. |

**Exit criteria**: The full pipeline works end-to-end: model change → Threagile analysis → diff → PR comment → Issue creation → pipeline gate.

### Phase 5: Presentation Prep (Days 8–9)

| Day | Tasks |
|-----|-------|
| 8 | Build the comparison slide: side-by-side table of the three approaches (input format, automation level, output format, CI/CD integration, learning curve, scalability). |
| 9 | Rehearse the demo flow. Prepare fallback screenshots in case live demos fail. Time each approach's walkthrough (aim for 5–7 min per approach, 25 min total with intro/outro). |

---

## 6. Comparison Matrix (For Your Presentation)

| Dimension | Threagile | Threat Dragon | CI/CD Pipeline |
|-----------|-----------|---------------|----------------|
| **Input** | YAML file (code) | Visual diagram (GUI) | YAML file (code) + pipeline config |
| **Output** | DFD + PDF + Excel + JSON | DFD + PDF report + JSON | PR comments + Issues + artifacts |
| **Automation** | Full (run a command, get results) | None (manual drawing + manual threat entry) | Full (triggers on code changes) |
| **CI/CD Ready** | Yes (Docker + GitHub Action) | No (desktop/web tool) | Yes (is the pipeline) |
| **Learning Curve** | Medium (YAML schema) | Low (drag and drop) | High (pipeline + scripting + Threagile) |
| **Scalability** | High (model many services in one YAML) | Low (manual for each service) | High (one pipeline, many models) |
| **Collaboration** | Git-based (PR reviews on YAML) | File-based (share JSON) | Git-based + PR comments + auto-tickets |
| **Threat Quality** | Rules-based (40+ built-in, consistent) | Human-written (high quality but variable) | Rules-based + diff (delta awareness) |
| **Business Logic Threats** | Cannot detect | Can capture (human writes them) | Cannot detect |
| **Best For** | DevSecOps teams, IaC shops | Security workshops, compliance | Mature orgs wanting continuous assurance |

---

## 7. Key Talking Points for Senior Director Audience

1. **The cost argument**: Manual threat modeling takes 2–4 hours per service per quarter. Threagile + CI/CD reduces this to maintaining a YAML file — minutes per change, with automated risk tracking.

2. **The coverage argument**: No single approach catches everything. Threagile catches infrastructure misconfigurations and data flow issues. Threat Dragon captures business logic threats that only a human can articulate. The CI/CD pipeline ensures nothing falls through the cracks between reviews.

3. **The compliance argument**: All three approaches produce auditable artifacts — PDFs, Excel risk registers, JSON exports, Git history of every risk decision. This is what auditors want to see.

4. **The recommendation**: Start with Threagile (low friction, high automation). Use Threat Dragon for quarterly deep-dives on critical services. Build toward CI/CD integration as the organization matures. The three are complementary, not competing.