// notes.js — CRUD /notes
const express = require('express');
const db = require('../config/db');
const authMiddleware = require('../middleware/authMiddleware');

const router = express.Router();

// All notes routes require auth
router.use(authMiddleware);

// GET /notes — list all notes for the authenticated user
router.get('/', async (req, res) => {
  try {
    const result = await db.query(
      `SELECT id, title, LEFT(content, 200) AS excerpt, created_at, updated_at
       FROM notes WHERE user_id = $1 ORDER BY updated_at DESC`,
      [req.user.id]
    );
    res.json({ notes: result.rows });
  } catch (err) {
    console.error('[notes:list]', err.message);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// GET /notes/:id — get a single note
router.get('/:id', async (req, res) => {
  try {
    const result = await db.query(
      'SELECT * FROM notes WHERE id = $1 AND user_id = $2',
      [req.params.id, req.user.id]
    );
    if (!result.rows[0]) return res.status(404).json({ error: 'Note not found' });
    res.json({ note: result.rows[0] });
  } catch (err) {
    console.error('[notes:get]', err.message);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /notes — create a note
router.post('/', async (req, res) => {
  const { title = 'Untitled', content = '' } = req.body;
  try {
    const result = await db.query(
      'INSERT INTO notes (user_id, title, content) VALUES ($1, $2, $3) RETURNING *',
      [req.user.id, title, content]
    );
    res.status(201).json({ note: result.rows[0] });
  } catch (err) {
    console.error('[notes:create]', err.message);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// PUT /notes/:id — update a note
router.put('/:id', async (req, res) => {
  const { title, content } = req.body;
  try {
    const result = await db.query(
      `UPDATE notes SET
         title = COALESCE($1, title),
         content = COALESCE($2, content),
         updated_at = NOW()
       WHERE id = $3 AND user_id = $4
       RETURNING *`,
      [title, content, req.params.id, req.user.id]
    );
    if (!result.rows[0]) return res.status(404).json({ error: 'Note not found' });
    res.json({ note: result.rows[0] });
  } catch (err) {
    console.error('[notes:update]', err.message);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// DELETE /notes/:id — delete a note
router.delete('/:id', async (req, res) => {
  try {
    const result = await db.query(
      'DELETE FROM notes WHERE id = $1 AND user_id = $2 RETURNING id',
      [req.params.id, req.user.id]
    );
    if (!result.rows[0]) return res.status(404).json({ error: 'Note not found' });
    res.json({ message: 'Note deleted', id: req.params.id });
  } catch (err) {
    console.error('[notes:delete]', err.message);
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router;
