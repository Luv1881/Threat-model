#!/usr/bin/env bash
# setup.sh — One-shot setup for VaultNote threat modeling demo
# Run from the project root: bash setup.sh
set -euo pipefail

echo "═══════════════════════════════════════════════════════"
echo "  VaultNote — Threat Modeling Demo Setup"
echo "═══════════════════════════════════════════════════════"

# ── Docker permission detection ───────────────────────────────────────────────
# Determine if we can talk to Docker directly or need sudo.
DOCKER_CMD="docker"
if ! docker info > /dev/null 2>&1; then
  if sudo -n docker info > /dev/null 2>&1; then
    echo "  ℹ  Docker requires sudo — using 'sudo docker' for all container commands."
    DOCKER_CMD="sudo docker"
  else
    echo "  ✗ ERROR: Cannot reach the Docker daemon."
    echo ""
    echo "    Fix option 1 — add yourself to the docker group (requires re-login):"
    echo "      sudo usermod -aG docker \$USER"
    echo "      newgrp docker"
    echo ""
    echo "    Fix option 2 — run this script with sudo:"
    echo "      sudo bash setup.sh"
    exit 1
  fi
fi

# Determine docker compose command (v2 plugin vs legacy standalone)
if $DOCKER_CMD compose version > /dev/null 2>&1; then
  COMPOSE_CMD="$DOCKER_CMD compose"
elif command -v docker-compose > /dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
elif sudo -n docker-compose --version > /dev/null 2>&1; then
  COMPOSE_CMD="sudo docker-compose"
else
  echo "  ✗ ERROR: neither 'docker compose' nor 'docker-compose' found."
  exit 1
fi

echo "  ✓ Docker:  $DOCKER_CMD"
echo "  ✓ Compose: $COMPOSE_CMD"

# ── 1. TLS Certificates ───────────────────────────────────────────────────────
echo ""
echo "▶ Generating self-signed TLS certificates..."
mkdir -p nginx/certs

if [ -f nginx/certs/server.crt ] && [ -f nginx/certs/server.key ]; then
  echo "  ✓ Certificates already exist, skipping"
else
  python3 scripts/generate-certs.py
fi

# ── 2. React Frontend Build ───────────────────────────────────────────────────
echo ""
echo "▶ Building React frontend..."
cd frontend
if [ ! -d node_modules ]; then
  npm install --silent
fi
npm run build
cd ..
echo "  ✓ Frontend built → frontend/build/"

# ── 3. Pull Docker images ─────────────────────────────────────────────────────
echo ""
echo "▶ Pulling Docker images..."
$DOCKER_CMD pull threagile/threagile --quiet
echo "  ✓ Threagile image ready"
$DOCKER_CMD pull owasp/threat-dragon:stable --quiet
echo "  ✓ Threat Dragon image ready"

# ── 4. Start the stack ────────────────────────────────────────────────────────
echo ""
echo "▶ Starting VaultNote stack..."
$COMPOSE_CMD up --build -d
echo "  ✓ Stack started"

# ── 5. Wait for health checks ─────────────────────────────────────────────────
echo ""
echo "▶ Waiting for API to be healthy (up to 60s)..."
HEALTHY=0
for i in $(seq 1 30); do
  if curl -sk https://localhost/api/health 2>/dev/null | grep -q '"status":"ok"'; then
    echo ""
    echo "  ✓ API is healthy"
    HEALTHY=1
    break
  fi
  echo -n "."
  sleep 2
done
if [ $HEALTHY -eq 0 ]; then
  echo ""
  echo "  ⚠  API did not become healthy in 60s."
  echo "     Check logs with: $COMPOSE_CMD logs api"
fi

# ── 6. Run Threagile Analysis (Approach 1) ────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  APPROACH 1 — Threagile Threat Analysis"
echo "═══════════════════════════════════════════════════════"
mkdir -p threagile/output

echo ""
echo "▶ Running Threagile analysis..."
$DOCKER_CMD run --rm \
  -v "$(pwd)/threagile:/app/work" \
  threagile/threagile \
  -model /app/work/threagile.yaml \
  -output /app/work/output

# ── 7. Launch Threat Dragon (Approach 2) ─────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  APPROACH 2 — OWASP Threat Dragon (Visual STRIDE)"
echo "═══════════════════════════════════════════════════════"

# Stop any existing Threat Dragon container
$DOCKER_CMD rm -f threat-dragon 2>/dev/null || true

echo ""
echo "▶ Starting Threat Dragon on http://localhost:8080 ..."
$DOCKER_CMD run -d \
  --name threat-dragon \
  -p 8080:3000 \
  -e "ENCRYPTION_KEYS=[{\"isPrimary\":true,\"id\":0,\"value\":\"vaultnote-demo-key-1234567890ab\"}]" \
  -e "ENCRYPTION_JWT_SIGNING_KEY=vaultnote-threat-dragon-demo-signing-key" \
  -e "ENCRYPTION_JWT_REFRESH_SIGNING_KEY=vaultnote-threat-dragon-demo-refresh-key" \
  -e "SERVER_API_PROTOCOL=http" \
  -e "NODE_ENV=production" \
  owasp/threat-dragon:stable
echo "  ✓ Threat Dragon running"

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  ✅ SETUP COMPLETE"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "  Application:     https://localhost"
echo "  Demo login:      demo@vaultnote.local / demo1234"
echo ""
echo "  APPROACH 1 — Threagile output:"
echo "    📊 DFD:           threagile/output/data-flow-diagram.png"
echo "    📄 Report:        threagile/output/report.pdf"
echo "    📋 Risk register: threagile/output/risks.xlsx"
echo "    🔧 JSON:          threagile/output/risks.json"
echo ""
echo "  APPROACH 2 — Threat Dragon:"
echo "    🌐 GUI:           http://localhost:8080"
echo "    📁 Model file:    threat-dragon/vaultnote-model.json"
echo "    → Open the GUI, choose 'Open Existing' and load the model file"
echo "    → Stop when done: docker rm -f threat-dragon"
echo ""
echo "  APPROACH 3 — CI/CD Pipeline (GitHub Actions):"
echo "    📄 Workflow:      .github/workflows/threat-model.yml"
echo "    🔀 Triggers on:   threagile/threagile.yaml, docker-compose.yml,"
echo "                      nginx/nginx.conf, api/src/routes/**, api/src/middleware/**"
echo "    → Simulate a new risk by adding a component to threagile.yaml,"
echo "      opening a PR, and watching the risk-diff comment appear."
echo "    → Demo local diff:"
echo "      cp threagile/output/risks.json /tmp/risks-baseline.json"
echo "      # (edit threagile.yaml to add a new asset)"
echo "      docker run --rm -v \$(pwd)/threagile:/app/work threagile/threagile \\"
echo "        -model /app/work/threagile.yaml -output /app/work/output -ignore-orphaned-risk-tracking"
echo "      python3 scripts/threat-model-diff.py \\"
echo "        --previous /tmp/risks-baseline.json \\"
echo "        --current  threagile/output/risks.json \\"
echo "        --model    threagile/threagile.yaml \\"
echo "        --output   /tmp/diff-report.json"
echo ""
echo "  Stack management:"
echo "    Logs:   $COMPOSE_CMD logs -f"
echo "    Stop:   $COMPOSE_CMD down && docker rm -f threat-dragon"
echo "    Status: $DOCKER_CMD ps"
echo ""
echo "  Quick API test:"
echo '    TOKEN=$(curl -sk -X POST https://localhost/api/auth/login \'
echo '      -H "Content-Type: application/json" \'
echo '      -d "{\"email\":\"demo@vaultnote.local\",\"password\":\"demo1234\"}" \'
echo '      | python3 -c "import sys,json; print(json.load(sys.stdin)[\"token\"])")'
echo '    curl -sk https://localhost/api/notes -H "Authorization: Bearer $TOKEN"'
echo ""
