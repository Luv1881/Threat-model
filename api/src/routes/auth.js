// auth.js — POST /register, /login, /logout
const express = require('express');
const bcrypt = require('bcrypt');
const jwt = require('jsonwebtoken');
const db = require('../config/db');
const redis = require('../config/redis');
const { authLimiter } = require('../middleware/rateLimiter');

const router = express.Router();
const JWT_SECRET = process.env.JWT_SECRET || 'change-me-in-production';
const TOKEN_TTL_SECONDS = 60 * 60 * 8; // 8 hours

// POST /register
router.post('/register', authLimiter, async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) {
    return res.status(400).json({ error: 'email and password are required' });
  }
  if (password.length < 8) {
    return res.status(400).json({ error: 'Password must be at least 8 characters' });
  }

  try {
    const hash = await bcrypt.hash(password, 10);
    const result = await db.query(
      'INSERT INTO users (email, password) VALUES ($1, $2) RETURNING id, email, created_at',
      [email.toLowerCase().trim(), hash]
    );
    res.status(201).json({ user: result.rows[0] });
  } catch (err) {
    if (err.code === '23505') {
      return res.status(409).json({ error: 'Email already registered' });
    }
    console.error('[register]', err.message);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /login
router.post('/login', authLimiter, async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) {
    return res.status(400).json({ error: 'email and password are required' });
  }

  try {
    const result = await db.query('SELECT * FROM users WHERE email = $1', [email.toLowerCase().trim()]);
    const user = result.rows[0];

    if (!user || !(await bcrypt.compare(password, user.password))) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    const token = jwt.sign(
      { sub: user.id, email: user.email },
      JWT_SECRET,
      { expiresIn: TOKEN_TTL_SECONDS }
    );

    // Store session in Redis for tracking
    await redis.setex(`session:${user.id}:${token.slice(-8)}`, TOKEN_TTL_SECONDS, user.id.toString());

    res.json({ token, user: { id: user.id, email: user.email } });
  } catch (err) {
    console.error('[login]', err.message);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /logout
router.post('/logout', async (req, res) => {
  const authHeader = req.headers['authorization'];
  if (authHeader && authHeader.startsWith('Bearer ')) {
    const token = authHeader.slice(7);
    try {
      const payload = jwt.decode(token);
      const ttl = payload?.exp ? payload.exp - Math.floor(Date.now() / 1000) : 3600;
      if (ttl > 0) {
        await redis.setex(`revoked:${token}`, ttl, '1');
      }
    } catch (_) {
      // ignore malformed tokens
    }
  }
  res.json({ message: 'Logged out successfully' });
});

module.exports = router;
