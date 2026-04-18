// index.js — Express entrypoint
const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const { ensureBucket } = require('./config/minio');
const { apiLimiter } = require('./middleware/rateLimiter');

const authRoutes  = require('./routes/auth');
const notesRoutes = require('./routes/notes');
const filesRoutes = require('./routes/files');

const app  = express();
const PORT = process.env.PORT || 3000;

// ── Security middleware ──────────────────────────────────────────────────────
app.use(helmet());
app.use(cors({
  origin: process.env.CORS_ORIGIN || '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
}));

// ── Body parsing ─────────────────────────────────────────────────────────────
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: false }));

// ── General rate limiting ────────────────────────────────────────────────────
app.use(apiLimiter);

// ── Health check ─────────────────────────────────────────────────────────────
app.get('/health', (_req, res) => res.json({ status: 'ok', service: 'vaultnote-api' }));

// ── Routes ───────────────────────────────────────────────────────────────────
app.use('/auth',        authRoutes);
app.use('/notes',       notesRoutes);
app.use('/files',       filesRoutes);

// ── 404 handler ───────────────────────────────────────────────────────────────
app.use((_req, res) => res.status(404).json({ error: 'Not found' }));

// ── Error handler ─────────────────────────────────────────────────────────────
app.use((err, _req, res, _next) => {
  console.error('[unhandled]', err.message);
  res.status(500).json({ error: 'Internal server error' });
});

// ── Start ────────────────────────────────────────────────────────────────────
async function start() {
  try {
    // Wait briefly for DB to be ready (Docker healthcheck should handle this)
    await new Promise(r => setTimeout(r, 1000));

    // Ensure MinIO bucket exists
    await ensureBucket();

    app.listen(PORT, '0.0.0.0', () => {
      console.log(`VaultNote API listening on port ${PORT}`);
    });
  } catch (err) {
    console.error('Startup error:', err.message);
    process.exit(1);
  }
}

start();
