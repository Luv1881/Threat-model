import React, { useState, useEffect, useCallback, useRef } from 'react';

const API = '/api';

// ── Helpers ──────────────────────────────────────────────────────────────────
function getToken() { return localStorage.getItem('vn_token'); }
function getUser()  { try { return JSON.parse(localStorage.getItem('vn_user')); } catch { return null; } }

async function apiFetch(path, opts = {}) {
  const token = getToken();
  const res = await fetch(`${API}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...opts.headers,
    },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${res.status}`);
  }
  return res.json();
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) +
         ' ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function formatBytes(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes/1024).toFixed(1)} KB`;
  return `${(bytes/1024/1024).toFixed(1)} MB`;
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function Toast({ msg, type, onDone }) {
  useEffect(() => { const t = setTimeout(onDone, 3000); return () => clearTimeout(t); }, [onDone]);
  return <div className={`toast ${type}`}>{msg}</div>;
}

// ── Auth Page ─────────────────────────────────────────────────────────────────
function AuthPage({ onLogin }) {
  const [tab, setTab]         = useState('login');
  const [email, setEmail]     = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]     = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const data = await apiFetch(`/auth/${tab}`, {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      });
      if (tab === 'login') {
        localStorage.setItem('vn_token', data.token);
        localStorage.setItem('vn_user', JSON.stringify(data.user));
        onLogin(data.user);
      } else {
        setTab('login');
        setError('');
        setEmail(''); setPassword('');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <div className="auth-logo-icon">🔒</div>
          <h1>Vault<span>Note</span></h1>
        </div>

        <div className="auth-tabs">
          <button className={`auth-tab${tab === 'login' ? ' active' : ''}`} onClick={() => { setTab('login'); setError(''); }}>Sign In</button>
          <button className={`auth-tab${tab === 'register' ? ' active' : ''}`} onClick={() => { setTab('register'); setError(''); }}>Create Account</button>
        </div>

        <form onSubmit={submit}>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input id="auth-email" className="form-input" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" required autoFocus />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input id="auth-password" className="form-input" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder={tab === 'register' ? 'at least 8 characters' : ''} required />
          </div>
          <button id="auth-submit" className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? <span className="spinner" /> : (tab === 'login' ? 'Sign In' : 'Create Account')}
          </button>
          {error && <p className="error-msg">{error}</p>}
        </form>

        {tab === 'login' && (
          <p style={{ marginTop: 18, fontSize: 12, color: 'var(--text-dim)', textAlign: 'center' }}>
            Demo: <strong>demo@vaultnote.local</strong> / <strong>demo1234</strong>
          </p>
        )}
      </div>
    </div>
  );
}

// ── Attachment Panel ──────────────────────────────────────────────────────────
function AttachmentsPanel({ noteId }) {
  const [attachments, setAttachments] = useState([]);
  const [uploading, setUploading]     = useState(false);
  const fileRef = useRef();

  const load = useCallback(() => {
    if (!noteId) return;
    apiFetch(`/files/attachments/${noteId}`).then(d => setAttachments(d.attachments)).catch(() => {});
  }, [noteId]);

  useEffect(() => { load(); }, [load]);

  const upload = async (e) => {
    const file = e.target.files[0]; if (!file) return;
    setUploading(true);
    const fd = new FormData(); fd.append('file', file);
    try {
      await fetch(`${API}/files/upload?noteId=${noteId}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getToken()}` },
        body: fd,
      });
      load();
    } catch (_) {}
    setUploading(false);
    e.target.value = '';
  };

  const download = async (att) => {
    const token = getToken();
    const res = await fetch(`${API}/files/download/${att.id}`, { headers: { Authorization: `Bearer ${token}` } });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = att.filename; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="attachments-panel">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <span className="attachments-title">Attachments ({attachments.length})</span>
        <label className="file-input-label" htmlFor="file-upload">
          {uploading ? <span className="spinner" style={{ width: 14, height: 14 }} /> : '📎 Attach'}
          <input id="file-upload" type="file" ref={fileRef} style={{ display: 'none' }} onChange={upload} />
        </label>
      </div>
      {attachments.map(att => (
        <div className="attachment-item" key={att.id}>
          <span style={{ fontSize: 16 }}>📄</span>
          <span className="attachment-name">{att.filename}</span>
          <span className="attachment-size">{formatBytes(att.size_bytes)}</span>
          <button className="btn btn-ghost btn-sm" id={`download-${att.id}`} onClick={() => download(att)}>↓</button>
        </div>
      ))}
    </div>
  );
}

// ── Main Notes App ────────────────────────────────────────────────────────────
function NotesApp({ user, onLogout }) {
  const [notes, setNotes]           = useState([]);
  const [activeNote, setActiveNote] = useState(null);
  const [title, setTitle]           = useState('');
  const [content, setContent]       = useState('');
  const [saving, setSaving]         = useState(false);
  const [toast, setToast]           = useState(null);
  const saveTimer = useRef(null);

  const showToast = (msg, type = 'success') => setToast({ msg, type });

  const loadNotes = useCallback(async () => {
    try { const d = await apiFetch('/notes'); setNotes(d.notes); } catch (_) {}
  }, []);

  useEffect(() => { loadNotes(); }, [loadNotes]);

  const selectNote = (note) => {
    setActiveNote(note);
    setTitle(note.title);
    setContent(note.content);
  };

  const newNote = async () => {
    try {
      const d = await apiFetch('/notes', { method: 'POST', body: JSON.stringify({ title: 'New Note', content: '' }) });
      await loadNotes();
      selectNote(d.note);
    } catch (err) { showToast(err.message, 'error'); }
  };

  const save = useCallback(async (t, c) => {
    if (!activeNote) return;
    setSaving(true);
    try {
      await apiFetch(`/notes/${activeNote.id}`, { method: 'PUT', body: JSON.stringify({ title: t, content: c }) });
      await loadNotes();
    } catch (err) { showToast(err.message, 'error'); }
    setSaving(false);
  }, [activeNote, loadNotes]);

  const handleTitleChange = (e) => {
    setTitle(e.target.value);
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => save(e.target.value, content), 1200);
  };

  const handleContentChange = (e) => {
    setContent(e.target.value);
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => save(title, e.target.value), 1200);
  };

  const deleteNote = async () => {
    if (!activeNote || !window.confirm('Delete this note?')) return;
    try {
      await apiFetch(`/notes/${activeNote.id}`, { method: 'DELETE' });
      setActiveNote(null); setTitle(''); setContent('');
      await loadNotes();
      showToast('Note deleted');
    } catch (err) { showToast(err.message, 'error'); }
  };

  const logout = async () => {
    await apiFetch('/auth/logout', { method: 'POST' }).catch(() => {});
    localStorage.clear();
    onLogout();
  };

  return (
    <div className="app">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <div className="sidebar-logo-icon">🔒</div>
            <h2>Vault<span>Note</span></h2>
          </div>
        </div>

        <div className="sidebar-actions">
          <button id="new-note-btn" className="btn btn-primary" onClick={newNote}>+ New Note</button>
        </div>

        <div className="sidebar-note-list">
          {notes.length === 0 && (
            <p style={{ fontSize: 13, color: 'var(--text-dim)', textAlign: 'center', padding: '20px 8px' }}>
              No notes yet.<br />Create your first note!
            </p>
          )}
          {notes.map(note => (
            <div
              key={note.id}
              id={`note-item-${note.id}`}
              className={`sidebar-note-item${activeNote?.id === note.id ? ' active' : ''}`}
              onClick={() => selectNote(note)}
            >
              <div className="sidebar-note-title">{note.title || 'Untitled'}</div>
              <div className="sidebar-note-date">{formatDate(note.updated_at)}</div>
            </div>
          ))}
        </div>

        <div className="sidebar-footer">
          <span className="user-email" title={user.email}>{user.email}</span>
          <button id="logout-btn" className="btn btn-ghost btn-sm" onClick={logout}>←  Out</button>
        </div>
      </aside>

      {/* Main area */}
      <main className="main-area">
        {activeNote ? (
          <>
            <div className="editor-toolbar">
              <input
                id="note-title"
                className="note-title-input"
                value={title}
                onChange={handleTitleChange}
                placeholder="Note title…"
              />
              {saving && <span className="spinner" />}
              <button id="save-btn" className="btn btn-ghost btn-sm" onClick={() => save(title, content)}>Save</button>
              <button id="delete-btn" className="btn btn-danger btn-sm" onClick={deleteNote}>Delete</button>
            </div>
            <div className="editor-area">
              <textarea
                id="note-content"
                className="note-textarea"
                value={content}
                onChange={handleContentChange}
                placeholder="Write your note here…"
              />
            </div>
            <AttachmentsPanel noteId={activeNote.id} />
          </>
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">📝</div>
            <h3>Select or create a note</h3>
            <p>Your secure notes are end-to-end encrypted.</p>
            <button id="empty-new-note-btn" className="btn btn-primary" style={{ marginTop: 8 }} onClick={newNote}>Create Note</button>
          </div>
        )}
      </main>

      {toast && <Toast msg={toast.msg} type={toast.type} onDone={() => setToast(null)} />}
    </div>
  );
}

// ── Root App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [user, setUser] = useState(() => getUser());

  if (!user || !getToken()) {
    return <AuthPage onLogin={(u) => setUser(u)} />;
  }
  return <NotesApp user={user} onLogout={() => setUser(null)} />;
}
