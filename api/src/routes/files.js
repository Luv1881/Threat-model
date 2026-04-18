// files.js — POST /upload, GET /download/:id, GET /attachments/:noteId
const express = require('express');
const multer = require('multer');
const { v4: uuidv4 } = require('uuid');
const db = require('../config/db');
const { minioClient, BUCKET_NAME } = require('../config/minio');
const authMiddleware = require('../middleware/authMiddleware');

const router = express.Router();
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 10 * 1024 * 1024 }, // 10 MB
});

router.use(authMiddleware);

// POST /upload?noteId=N — upload a file attachment to a note
router.post('/upload', upload.single('file'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file provided' });

  const { noteId } = req.query;
  if (!noteId) return res.status(400).json({ error: 'noteId query param required' });

  // Verify note belongs to user
  const noteCheck = await db.query(
    'SELECT id FROM notes WHERE id = $1 AND user_id = $2',
    [noteId, req.user.id]
  );
  if (!noteCheck.rows[0]) return res.status(404).json({ error: 'Note not found' });

  const objectKey = `${req.user.id}/${noteId}/${uuidv4()}-${req.file.originalname}`;

  try {
    // Upload to MinIO (HTTP — intentionally insecure for demo)
    await minioClient.putObject(
      BUCKET_NAME,
      objectKey,
      req.file.buffer,
      req.file.size,
      { 'Content-Type': req.file.mimetype }
    );

    const result = await db.query(
      `INSERT INTO attachments (note_id, user_id, filename, object_key, size_bytes, mime_type)
       VALUES ($1, $2, $3, $4, $5, $6) RETURNING *`,
      [noteId, req.user.id, req.file.originalname, objectKey, req.file.size, req.file.mimetype]
    );

    res.status(201).json({ attachment: result.rows[0] });
  } catch (err) {
    console.error('[files:upload]', err.message);
    res.status(500).json({ error: 'Upload failed' });
  }
});

// GET /download/:id — stream a file back to the client
router.get('/download/:id', async (req, res) => {
  try {
    const result = await db.query(
      'SELECT * FROM attachments WHERE id = $1 AND user_id = $2',
      [req.params.id, req.user.id]
    );
    const attachment = result.rows[0];
    if (!attachment) return res.status(404).json({ error: 'File not found' });

    const stream = await minioClient.getObject(BUCKET_NAME, attachment.object_key);
    res.setHeader('Content-Disposition', `attachment; filename="${attachment.filename}"`);
    res.setHeader('Content-Type', attachment.mime_type || 'application/octet-stream');
    stream.pipe(res);
  } catch (err) {
    console.error('[files:download]', err.message);
    res.status(500).json({ error: 'Download failed' });
  }
});

// GET /attachments/:noteId — list files for a note
router.get('/attachments/:noteId', async (req, res) => {
  try {
    const result = await db.query(
      'SELECT id, filename, size_bytes, mime_type, created_at FROM attachments WHERE note_id = $1 AND user_id = $2 ORDER BY created_at DESC',
      [req.params.noteId, req.user.id]
    );
    res.json({ attachments: result.rows });
  } catch (err) {
    console.error('[files:list]', err.message);
    res.status(500).json({ error: 'Internal server error' });
  }
});

module.exports = router;
