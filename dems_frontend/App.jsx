import { useState, useEffect, useCallback, useRef } from 'react';
import './App.css';
import * as api from './api';

// ─── Helpers ─────────────────────────────────────────────────────────────────
const fmt = (d) => d ? new Date(d).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '—';
const fmtDate = (d) => d ? new Date(d).toLocaleDateString('en-IN', { dateStyle: 'medium' }) : '—';

/** Auto-dismiss a state value after `ms` milliseconds */
function useAutoClear(setter, ms = 3500) {
  const timer = useRef(null);
  return (val) => {
    setter(val);
    clearTimeout(timer.current);
    if (val) timer.current = setTimeout(() => setter(''), ms);
  };
}

const RoleBadge = ({ role }) => (
  <span className={`sidebar-user-role role-${role}`}>{role}</span>
);

const StatusBadge = ({ status }) => (
  <span className={`badge ${status === 'ACTIVE' ? 'badge-active' : 'badge-inactive'}`}>{status}</span>
);

const CaseStatusBadge = ({ status }) => (
  <span className={`badge ${status === 'ACTIVE' || status === 'Open' ? 'badge-open' : 'badge-closed'}`}>{status}</span>
);

// ─── Modal ────────────────────────────────────────────────────────────────────
const Modal = ({ title, sub, children, onClose, footer, large }) => (
  <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
    <div className={`modal${large ? ' modal-lg' : ''}`}>
      <div className="modal-header">
        <div>
          <div className="modal-title">{title}</div>
          {sub && <div className="modal-sub">{sub}</div>}
        </div>
        <button className="btn btn-ghost btn-icon btn-sm" onClick={onClose} style={{ fontSize: 18 }}>✕</button>
      </div>
      <div className="modal-body">{children}</div>
      {footer && <div className="modal-footer">{footer}</div>}
    </div>
  </div>
);

// ─── Alert ────────────────────────────────────────────────────────────────────
const Alert = ({ type = 'error', msg }) =>
  msg ? <div className={`alert alert-${type}`}>{msg}</div> : null;

// ─── Loading ──────────────────────────────────────────────────────────────────
const Loading = () => (
  <div className="loading"><span className="spinner" /> Loading…</div>
);

const Empty = ({ icon = '📭', msg = 'No records found' }) => (
  <div className="empty">
    <div className="empty-icon">{icon}</div>
    <div className="empty-title">{msg}</div>
    <div className="empty-subtitle">Try adjusting filters or adding a new record to get started.</div>
  </div>
);

const ThemeToggle = ({ isDark, onToggle, className = '' }) => (
  <button
    type="button"
    className={`theme-toggle ${className}`.trim()}
    onClick={onToggle}
    aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
    title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
  >
    <span>{isDark ? '☀' : '🌙'}</span>
    <span>{isDark ? 'Light Mode' : 'Night Mode'}</span>
  </button>
);

// ─── Login View ───────────────────────────────────────────────────────────────
const LoginView = ({ onLogin, isDarkMode, onToggleTheme }) => {
  const [badge, setBadge] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      const { access_token } = await api.login(badge, password);
      const user = await api.getMe(access_token);
      onLogin(access_token, user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-root">
      <div className="login-grid" />
      <ThemeToggle isDark={isDarkMode} onToggle={onToggleTheme} className="theme-toggle-login" />
      <div className="login-card">
        <div className="login-logo">
          <img src="/logo.jpeg" alt="DEMS logo" className="login-logo-image" />
          <div>
            <div className="login-logo-text">DE<span>MS</span></div>
            <div className="login-subtitle">Digital Evidence Management System</div>
          </div>
        </div>
        <div className="login-title">Secure Access Portal</div>
        <div className="login-desc">Enter your badge number and password to continue.</div>
        {error && <div className="login-error">⚠ {error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Badge Number</label>
            <input value={badge} onChange={e => setBadge(e.target.value)} placeholder="e.g. INS12345" autoFocus required />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" required />
          </div>
          <button className="btn btn-primary btn-full" type="submit" disabled={loading}>
            {loading ? <><span className="spinner" /> Authenticating…</> : '→ Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
};

// ─── Users View (Admin only) ──────────────────────────────────────────────────
const UsersView = ({ token }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [limit, setLimit] = useState(10);
  const [skip, setSkip] = useState(0);
  const [modal, setModal] = useState(null);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({ Name: '', Role: 'officer', Contact: '', Email: '', Status: 'ACTIVE' });
  const [err, setErr] = useState('');
  const [success, setSuccess] = useState('');
  const [saving, setSaving] = useState(false);
  const setSuccessAuto = useAutoClear(setSuccess);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (search) params.search = search;
      if (statusFilter) params.status_isActive = statusFilter;
      params.limit = String(limit);
      params.skip = String(skip);
      setUsers(await api.getUsers(token, params));
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  }, [token, search, statusFilter, limit, skip]);

  useEffect(() => { load(); }, [load]);

  const openCreate = () => {
    setForm({ Name: '', Role: 'officer', Contact: '', Email: '', Status: 'ACTIVE' });
    setErr(''); setModal('create');
  };
  const openEdit = (u) => {
    setSelected(u);
    setForm({ Name: u.Name, Role: u.Role, Contact: u.Contact || '', Status: u.Status });
    setErr(''); setModal('edit');
  };
  const openDelete = (u) => { setSelected(u); setErr(''); setModal('delete'); };

  const handleCreate = async () => {
    setSaving(true); setErr('');
    try {
      await api.createUser(token, form);
      setSuccessAuto('User created — credentials sent via email.');
      setModal(null); load();
    } catch (e) { setErr(e.message); } finally { setSaving(false); }
  };

  const handleEdit = async () => {
    setSaving(true); setErr('');
    try {
      await api.updateUser(token, selected.BadgeNumber, {
        Name: form.Name,
        Role: form.Role,
        Contact: form.Contact,
        Status: form.Status,
      });
      setSuccessAuto('User updated.');
      setModal(null); load();
    } catch (e) { setErr(e.message); } finally { setSaving(false); }
  };

  const handleDelete = async () => {
    setSaving(true); setErr('');
    try {
      await api.deleteUser(token, selected.BadgeNumber);
      setSuccessAuto('User deleted.');
      setModal(null); load();
    } catch (e) { setErr(e.message); } finally { setSaving(false); }
  };

  const F = (k) => ({ value: form[k], onChange: e => setForm(p => ({ ...p, [k]: e.target.value })) });

  return (
    <>
      {success && <Alert type="success" msg={success} />}
      <div className="table-wrap">
        <div className="table-toolbar">
          <div className="table-toolbar-left">
            <input className="search-input" placeholder="Search by name…" value={search} onChange={e => setSearch(e.target.value)} />
            <select className="search-input" style={{ width: 140 }} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
              <option value="">All Status</option>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
            </select>
            <input
              className="search-input"
              style={{ width: 90 }}
              type="number"
              min={1}
              value={limit}
              onChange={e => setLimit(Math.max(1, Number(e.target.value) || 1))}
              placeholder="Limit"
            />
            <input
              className="search-input"
              style={{ width: 90 }}
              type="number"
              min={0}
              value={skip}
              onChange={e => setSkip(Math.max(0, Number(e.target.value) || 0))}
              placeholder="Skip"
            />
          </div>
          <button className="btn btn-primary btn-sm" onClick={openCreate}>+ New User</button>
        </div>
        {loading ? <Loading /> : users.length === 0 ? <Empty /> : (
          <table>
            <thead><tr>
              <th>Name</th><th>Badge #</th><th>Role</th><th>Email</th><th>Contact</th><th>Status</th><th>Last Login</th><th>Actions</th>
            </tr></thead>
            <tbody>
              {users.map(u => (
                <tr key={u.UserID}>
                  <td>{u.Name}</td>
                  <td><span className="mono">{u.BadgeNumber}</span></td>
                  <td><RoleBadge role={u.Role} /></td>
                  <td>{u.Email}</td>
                  <td>{u.Contact || '—'}</td>
                  <td><StatusBadge status={u.Status} /></td>
                  <td>{fmt(u.LastLogin)}</td>
                  <td>
                    <div className="td-actions">
                      <button className="btn btn-secondary btn-sm" onClick={() => openEdit(u)}>Edit</button>
                      <button className="btn btn-danger btn-sm" onClick={() => openDelete(u)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create Modal */}
      {modal === 'create' && (
        <Modal title="Add New User" sub="Credentials will be emailed automatically" onClose={() => setModal(null)}
          footer={<>
            <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleCreate} disabled={saving}>{saving ? 'Creating…' : 'Create User'}</button>
          </>}>
          <Alert msg={err} />
          <div className="field"><label>Full Name</label><input {...F('Name')} placeholder="John Doe" /></div>
          <div className="field-row">
            <div className="field"><label>Role</label>
              <select {...F('Role')}>
                <option value="officer">Officer</option>
                <option value="inspector">Inspector</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div className="field"><label>Status</label>
              <select {...F('Status')}><option value="ACTIVE">Active</option><option value="INACTIVE">Inactive</option></select>
            </div>
          </div>
          <div className="field"><label>Email</label><input {...F('Email')} type="email" placeholder="user@dept.gov" /></div>
          <div className="field"><label>Contact</label><input {...F('Contact')} placeholder="+91 9876543210" /></div>
        </Modal>
      )}

      {/* Edit Modal */}
      {modal === 'edit' && (
        <Modal title="Edit User" sub={`Badge: ${selected?.BadgeNumber}`} onClose={() => setModal(null)}
          footer={<>
            <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleEdit} disabled={saving}>{saving ? 'Saving…' : 'Save Changes'}</button>
          </>}>
          <Alert msg={err} />
          <div className="field"><label>Full Name</label><input {...F('Name')} /></div>
          <div className="field-row">
            <div className="field"><label>Role</label>
              <select {...F('Role')}>
                <option value="officer">Officer</option>
                <option value="inspector">Inspector</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div className="field"><label>Status</label>
              <select {...F('Status')}><option value="ACTIVE">Active</option><option value="INACTIVE">Inactive</option></select>
            </div>
          </div>
          <div className="field"><label>Contact</label><input {...F('Contact')} /></div>
        </Modal>
      )}

      {/* Delete Modal */}
      {modal === 'delete' && (
        <Modal title="Delete User" onClose={() => setModal(null)}
          footer={<>
            <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancel</button>
            <button className="btn btn-danger" onClick={handleDelete} disabled={saving}>{saving ? 'Deleting…' : 'Confirm Delete'}</button>
          </>}>
          <Alert msg={err} />
          <p>Are you sure you want to delete <strong>{selected?.Name}</strong> (<span className="mono">{selected?.BadgeNumber}</span>)?<br />
            <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>This action cannot be undone.</span></p>
        </Modal>
      )}
    </>
  );
};

// ─── Cases View ───────────────────────────────────────────────────────────────
const CasesView = ({ token, user, onOpenCase }) => {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [modal, setModal] = useState(null);
  const [selected, setSelected] = useState(null);
  const [err, setErr] = useState('');
  const [success, setSuccess] = useState('');
  const [saving, setSaving] = useState(false);
  const [officers, setOfficers] = useState([]);
  const [selectedOfficerId, setSelectedOfficerId] = useState('');
  const [form, setForm] = useState({ Title: '', Type: '', Status: 'Open', Description: '', AssignedOfficerIDs: [] });
  const [editForm, setEditForm] = useState({});
  const isAdmin = user.Role === 'admin';
  const isInspector = user.Role === 'inspector';
  const setSuccessAuto = useAutoClear(setSuccess);

  const load = useCallback(async () => {
    setLoading(true); setErr('');
    try {
      let data;
      if (isAdmin || isInspector) {
        const params = {};
        if (search) params.search = search;
        if (statusFilter) params.is_active = statusFilter;
        data = await api.getCases(token, params);
      } else {
        data = await api.getAssignedCases(token);
      }
      setCases(data);
    } catch (e) { setErr(e.message); }
    finally { setLoading(false); }
  }, [token, user.Role, search, statusFilter, isAdmin, isInspector]);

  useEffect(() => { load(); }, [load]);

  const loadOfficers = async () => {
    try {
      const all = await api.getActiveOfficers(token, { limit: 200 });
      setOfficers(all);
    }
    catch { setOfficers([]); }
  };

  const openCreate = async () => {
    await loadOfficers();
    setForm({ Title: '', Type: '', Status: 'Open', Description: '', AssignedOfficerIDs: [] });
    setSelectedOfficerId('');
    setErr(''); setModal('create');
  };

  const addOfficerToCase = () => {
    const id = Number(selectedOfficerId);
    if (!id) return;
    setForm((p) => ({
      ...p,
      AssignedOfficerIDs: p.AssignedOfficerIDs.includes(id)
        ? p.AssignedOfficerIDs
        : [...p.AssignedOfficerIDs, id],
    }));
    setSelectedOfficerId('');
  };

  const removeOfficerFromCase = (id) => {
    setForm((p) => ({
      ...p,
      AssignedOfficerIDs: p.AssignedOfficerIDs.filter((x) => x !== id),
    }));
  };

  const handleCreate = async () => {
    if (!form.Title.trim()) { setErr('Case title is required'); return; }
    if (!form.Type.trim()) { setErr('Case type is required'); return; }
    setSaving(true); setErr('');
    try {
      await api.createCase(token, form);
      setSuccessAuto('Case created.');
      setModal(null); load();
    } catch (e) { setErr(e.message); } finally { setSaving(false); }
  };

  const openEdit = (c) => {
    setSelected(c);
    setEditForm({ Title: c.Title, Type: c.Type, Status: c.Status, Description: c.Description || '' });
    setErr(''); setModal('edit');
  };

  const handleEdit = async () => {
    setSaving(true); setErr('');
    try {
      await api.updateCase(token, selected.CaseID, editForm);
      setSuccessAuto('Case updated.');
      setModal(null); load();
    } catch (e) { setErr(e.message); } finally { setSaving(false); }
  };

  const handleClose = async (c) => {
    if (!window.confirm(`Close case "${c.Title}"?`)) return;
    try { await api.closeCase(token, c.CaseID); setSuccessAuto('Case closed.'); load(); }
    catch (e) { setErr(e.message); }
  };

  const handleDelete = async (c) => {
    if (!window.confirm(`Delete case "${c.Title}"? This cannot be undone.`)) return;
    try { await api.deleteCase(token, c.CaseID); setSuccessAuto('Case deleted.'); load(); }
    catch (e) { setErr(e.message); }
  };

  const handleReactivate = async (c) => {
    if (!window.confirm(`Reactivate case "${c.Title}"?`)) return;
    try {
      await api.reactivateCase(token, c.CaseID);
      setSuccessAuto('Case reactivated.');
      load();
    } catch (e) {
      setErr(e.message);
    }
  };

  const EF = (k) => ({ value: editForm[k] ?? '', onChange: e => setEditForm(p => ({ ...p, [k]: e.target.value })) });
  const CF = (k) => ({ value: form[k], onChange: e => setForm(p => ({ ...p, [k]: e.target.value })) });

  return (
    <>
      {success && <Alert type="success" msg={success} />}
      {err && <Alert msg={err} />}
      <div className="table-wrap">
        <div className="table-toolbar">
          <div className="table-toolbar-left">
            {(isAdmin || isInspector) && <>
              <input className="search-input" placeholder="Search title…" value={search} onChange={e => setSearch(e.target.value)} />
              <select className="search-input" style={{ width: 140 }} value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                <option value="">All Status</option>
                <option value="Open">Open</option>
                <option value="INACTIVE">Closed</option>
              </select>
            </>}
          </div>
          {isInspector && <button className="btn btn-primary btn-sm" onClick={openCreate}>+ New Case</button>}
        </div>
        {loading ? <Loading /> : cases.length === 0 ? <Empty icon="📁" msg="No cases found" /> : (
          <table>
            <thead><tr>
              <th>ID</th><th>Title</th><th>Type</th><th>Inspector ID</th><th>Status</th><th>Opened</th><th>Closed</th><th>Actions</th>
            </tr></thead>
            <tbody>
              {cases.map(c => (
                <tr key={c.CaseID}>
                  <td><span className="mono">#{c.CaseID}</span></td>
                  <td>
                    <span onClick={() => onOpenCase(c)} style={{ cursor: 'pointer', color: 'var(--accent)' }}>
                      {c.Title}
                    </span>
                  </td>
                  <td>{c.Type}</td>
                  <td><span className="mono">{c.ActingInspectorID}</span></td>
                  <td><CaseStatusBadge status={c.Status} /></td>
                  <td>{fmtDate(c.DateOpened)}</td>
                  <td>{fmtDate(c.DateClosed)}</td>
                  <td>
                    <div className="td-actions">
                      <button className="btn btn-secondary btn-sm" onClick={() => onOpenCase(c)}>View</button>
                      {isInspector && c.ActingInspectorID === user.UserID && c.Status !== 'INACTIVE' && (
                        <>
                          <button className="btn btn-secondary btn-sm" onClick={() => openEdit(c)}>Edit</button>
                          <button className="btn btn-amber btn-sm" onClick={() => handleClose(c)}>Close</button>
                        </>
                      )}
                      {(isInspector && c.ActingInspectorID === user.UserID) && c.Status === 'INACTIVE' && (
                        <button className="btn btn-primary btn-sm" onClick={() => handleReactivate(c)}>Reactivate</button>
                      )}
                      {isAdmin && <button className="btn btn-danger btn-sm" onClick={() => handleDelete(c)}>Delete</button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create Case Modal */}
      {modal === 'create' && (
        <Modal title="Create New Case" sub="You will be set as the acting inspector" onClose={() => setModal(null)} large
          footer={<>
            <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleCreate} disabled={saving}>{saving ? 'Creating…' : 'Create Case'}</button>
          </>}>
          <Alert msg={err} />
          <div className="field"><label>Case Title</label><input {...CF('Title')} placeholder="Brief case title" /></div>
          <div className="field-row">
            <div className="field"><label>Type</label><input {...CF('Type')} placeholder="e.g. Fraud, Theft…" /></div>
            <div className="field"><label>Status</label>
              <select {...CF('Status')}>
                <option value="Open">Open</option>
                <option value="Under Investigation">Under Investigation</option>
              </select>
            </div>
          </div>
          <div className="field"><label>Description</label><textarea {...CF('Description')} placeholder="Describe the case…" /></div>
          <div className="field">
            <label>Assign Officers (optional)</label>
            <div className="field-row" style={{ marginBottom: 8 }}>
              <select
                value={selectedOfficerId}
                onChange={(e) => setSelectedOfficerId(e.target.value)}
                disabled={officers.length === 0}
              >
                <option value="">Select officer</option>
                {officers.map((o) => (
                  <option key={o.UserID} value={o.UserID}>
                    {o.Name} ({o.BadgeNumber}) - #{o.UserID}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={addOfficerToCase}
                disabled={!selectedOfficerId}
              >
                Add
              </button>
            </div>
            <div style={{ maxHeight: 180, overflowY: 'auto', border: '1px solid var(--border2)', borderRadius: 6, padding: '6px 0' }}>
              {officers.length === 0 ? (
                <div style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: 12 }}>No active officers found</div>
              ) : form.AssignedOfficerIDs.length === 0 ? (
                <div style={{ padding: '12px 16px', color: 'var(--text-muted)', fontSize: 12 }}>No officers selected</div>
              ) : (
                officers
                  .filter((o) => form.AssignedOfficerIDs.includes(o.UserID))
                  .map((o) => (
                    <div key={o.UserID} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, padding: '8px 14px' }}>
                      <div>
                        <span>{o.Name}</span>{' '}
                        <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>{o.BadgeNumber}</span>
                      </div>
                      <button type="button" className="btn btn-danger btn-sm" onClick={() => removeOfficerFromCase(o.UserID)}>Remove</button>
                    </div>
                  ))
              )}
            </div>
          </div>
        </Modal>
      )}

      {/* Edit Case Modal */}
      {modal === 'edit' && (
        <Modal title="Edit Case" sub={`Case #${selected?.CaseID}`} onClose={() => setModal(null)}
          footer={<>
            <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleEdit} disabled={saving}>{saving ? 'Saving…' : 'Save Changes'}</button>
          </>}>
          <Alert msg={err} />
          <div className="field"><label>Title</label><input {...EF('Title')} /></div>
          <div className="field-row">
            <div className="field"><label>Type</label><input {...EF('Type')} /></div>
            <div className="field"><label>Status</label><input {...EF('Status')} /></div>
          </div>
          <div className="field"><label>Description</label><textarea {...EF('Description')} /></div>
        </Modal>
      )}
    </>
  );
};

// ─── Evidence Tab ─────────────────────────────────────────────────────────────
const EvidenceTab = ({ token, user, caseData }) => {
  const [evidence, setEvidence] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [selected, setSelected] = useState(null);
  const [err, setErr] = useState('');
  const [success, setSuccess] = useState('');
  const [saving, setSaving] = useState(false);
  const [file, setFile] = useState(null);
  const [addForm, setAddForm] = useState({ CaseID: caseData.CaseID, EvidenceType: '', SourceOrigin: '', Description: '' });
  const [editForm, setEditForm] = useState({});
  const setSuccessAuto = useAutoClear(setSuccess);

  const isAdmin = user.Role === 'admin';
  const isInspector = user.Role === 'inspector';
  const isOfficer = user.Role === 'officer';
  const isOwnCase = isInspector && caseData.ActingInspectorID === user.UserID;
  const caseActive = caseData.Status !== 'INACTIVE';

  const load = useCallback(async () => {
    setLoading(true);
    try { setEvidence(await api.listEvidence(token, caseData.CaseID, { limit: 100 })); }
    catch (e) { setErr(e.message); } finally { setLoading(false); }
  }, [token, caseData.CaseID]);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async () => {
    if (!file) { setErr('Please select a file'); return; }
    if (!addForm.EvidenceType.trim()) { setErr('Evidence type is required'); return; }
    if (!addForm.SourceOrigin.trim()) { setErr('Source / origin is required'); return; }
    setSaving(true); setErr('');
    try {
      const fd = new FormData();
      fd.append('CaseID', addForm.CaseID);
      fd.append('EvidenceType', addForm.EvidenceType);
      fd.append('SourceOrigin', addForm.SourceOrigin);
      if (addForm.Description) fd.append('Description', addForm.Description);
      fd.append('file', file);
      await api.addEvidence(token, fd);
      setSuccessAuto('Evidence added.');
      setModal(null); load();
    } catch (e) { setErr(e.message); } finally { setSaving(false); }
  };

  const handleEdit = async () => {
    setSaving(true); setErr('');
    try {
      await api.updateEvidence(token, caseData.CaseID, selected.EvidenceID, editForm);
      setSuccessAuto('Evidence updated.');
      setModal(null); load();
    } catch (e) { setErr(e.message); } finally { setSaving(false); }
  };

  const handleDelete = async (ev) => {
    if (!window.confirm('Delete this evidence record and its file?')) return;
    try { await api.deleteEvidence(token, ev.EvidenceID); setSuccessAuto('Evidence deleted.'); load(); }
    catch (e) { setErr(e.message); }
  };

  const handleDownload = async (ev) => {
    try { await api.downloadEvidence(token, caseData.CaseID, ev.EvidenceID); }
    catch (e) { setErr(e.message); }
  };

  // Officers can add evidence only if case is active (backend also checks assignment)
  const canAdd = (isOwnCase || isOfficer) && caseActive;
  const AF = (k) => ({ value: addForm[k], onChange: e => setAddForm(p => ({ ...p, [k]: e.target.value })) });
  const EF = (k) => ({ value: editForm[k] ?? '', onChange: e => setEditForm(p => ({ ...p, [k]: e.target.value })) });

  return (
    <>
      {err && <Alert msg={err} />}
      {success && <Alert type="success" msg={success} />}
      <div className="table-wrap">
        <div className="table-toolbar">
          <div className="table-toolbar-left" />
          {canAdd && (
            <button className="btn btn-primary btn-sm" onClick={() => {
              setAddForm({ CaseID: caseData.CaseID, EvidenceType: '', SourceOrigin: '', Description: '' });
              setFile(null); setErr(''); setModal('add');
            }}>+ Add Evidence</button>
          )}
        </div>
        {loading ? <Loading /> : evidence.length === 0 ? <Empty icon="🗂" msg="No evidence items yet" /> : (
          <table>
            <thead><tr>
              <th>ID</th><th>Type</th><th>Source / Origin</th><th>Description</th><th>Collected</th><th>File</th><th>Actions</th>
            </tr></thead>
            <tbody>
              {evidence.map(ev => (
                <tr key={ev.EvidenceID}>
                  <td><span className="mono">#{ev.EvidenceID}</span></td>
                  <td><span className="badge badge-info">{ev.EvidenceType}</span></td>
                  <td>{ev.SourceOrigin}</td>
                  <td style={{ maxWidth: 200 }}>{ev.Description || '—'}</td>
                  <td>{ev.DateCollected ? fmt(ev.DateCollected) : '—'}</td>
                  <td>
                    {ev.FilePath
                      ? <button className="btn btn-ghost btn-sm" onClick={() => handleDownload(ev)}>⬇ Download</button>
                      : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                  </td>
                  <td>
                    <div className="td-actions">
                      {(isOwnCase || isOfficer) && caseActive && (
                        <button className="btn btn-secondary btn-sm" onClick={() => {
                          setSelected(ev);
                          setEditForm({ Description: ev.Description || '', EvidenceType: ev.EvidenceType, SourceOrigin: ev.SourceOrigin });
                          setErr(''); setModal('edit');
                        }}>Edit</button>
                      )}
                      {isAdmin && (
                        <button className="btn btn-danger btn-sm" onClick={() => handleDelete(ev)}>Delete</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modal === 'add' && (
        <Modal title="Add Evidence" sub={`Case #${caseData.CaseID}`} onClose={() => setModal(null)}
          footer={<>
            <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleAdd} disabled={saving}>{saving ? 'Uploading…' : 'Add Evidence'}</button>
          </>}>
          <Alert msg={err} />
          <div className="field-row">
            <div className="field"><label>Evidence Type</label><input {...AF('EvidenceType')} placeholder="e.g. Document, Photo…" /></div>
            <div className="field"><label>Source / Origin</label><input {...AF('SourceOrigin')} placeholder="Scene, Person…" /></div>
          </div>
          <div className="field"><label>Description</label><textarea {...AF('Description')} placeholder="Optional details…" /></div>
          <div className="field">
            <label>Evidence File</label>
            <div className="file-input-wrap">
              <input type="file" onChange={e => setFile(e.target.files[0])} />
              <div>📎 Click to select file</div>
              {file && <div className="file-name">{file.name}</div>}
            </div>
          </div>
        </Modal>
      )}

      {modal === 'edit' && (
        <Modal title="Edit Evidence" sub={`Evidence #${selected?.EvidenceID}`} onClose={() => setModal(null)}
          footer={<>
            <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleEdit} disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
          </>}>
          <Alert msg={err} />
          <div className="field-row">
            <div className="field"><label>Evidence Type</label><input {...EF('EvidenceType')} /></div>
            <div className="field"><label>Source / Origin</label><input {...EF('SourceOrigin')} /></div>
          </div>
          <div className="field"><label>Description</label><textarea {...EF('Description')} /></div>
        </Modal>
      )}
    </>
  );
};

// ─── Custody Tab ──────────────────────────────────────────────────────────────
// BUG FIX: Previously loaded all global custody records with no case filter.
// Fix: Load this case's evidence IDs first, then filter custody records by those IDs.
const CustodyTab = ({ token, user, caseData }) => {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null);
  const [selected, setSelected] = useState(null);
  const [err, setErr] = useState('');
  const [success, setSuccess] = useState('');
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ EvidenceID: '', ActingOfficerID: '', Notes: '' });
  const [editForm, setEditForm] = useState({});
  const [activeOfficers, setActiveOfficers] = useState([]);
  const [caseEvidenceIds, setCaseEvidenceIds] = useState(new Set());
  const [caseEvidenceList, setCaseEvidenceList] = useState([]);
  const isAdmin = user.Role === 'admin';
  const isInspector = user.Role === 'inspector';
  const isOwnCase = isInspector && caseData.ActingInspectorID === user.UserID;
  const caseActive = caseData.Status !== 'INACTIVE';
  const canAddCustody = isOwnCase && caseActive;
  const setSuccessAuto = useAutoClear(setSuccess);

  const load = useCallback(async () => {
    setLoading(true); setErr('');
    try {
      // Step 1: get evidence IDs belonging to this case
      const evidenceList = await api.listEvidence(token, caseData.CaseID, { limit: 200 });
      setCaseEvidenceList(evidenceList);
      const ids = new Set(evidenceList.map(e => e.EvidenceID));
      setCaseEvidenceIds(ids);

      if (ids.size === 0) {
        // No evidence → no custody records possible
        setRecords([]);
        return;
      }

      // Step 2: fetch all custody records and filter by this case's evidence IDs
      const allCustody = await api.getCustody(token, { limit: 1000 });
      setRecords(allCustody.filter(r => ids.has(r.EvidenceID)));
    } catch (e) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }, [token, caseData.CaseID]);

  useEffect(() => { load(); }, [load]);

  const handleAdd = async () => {
    const evidenceId = Number(form.EvidenceID);
    const officerId = Number(form.ActingOfficerID);
    if (!evidenceId) { setErr('Evidence ID is required'); return; }
    if (!officerId) { setErr('Acting Officer ID is required'); return; }
    if (!caseEvidenceIds.has(evidenceId)) {
      setErr(`Evidence #${evidenceId} does not belong to this case`);
      return;
    }
    setSaving(true); setErr('');
    try {
      await api.addCustody(token, {
        EvidenceID: evidenceId,
        ActingOfficerID: officerId,
        Notes: form.Notes || undefined,
      });
      setSuccessAuto('Custody record added.');
      setModal(null); load();
    } catch (e) { setErr(e.message); } finally { setSaving(false); }
  };

  const handleEdit = async () => {
    setSaving(true); setErr('');
    try {
      await api.updateCustody(token, selected.RecordID, {
        Notes: editForm.Notes || undefined,
        ActingOfficerID: Number(editForm.ActingOfficerID) || undefined,
      });
      setSuccessAuto('Record updated.');
      setModal(null); load();
    } catch (e) { setErr(e.message); } finally { setSaving(false); }
  };

  const handleDelete = async (r) => {
    if (!window.confirm('Delete this custody record?')) return;
    try { await api.deleteCustody(token, r.RecordID); setSuccessAuto('Record deleted.'); load(); }
    catch (e) { setErr(e.message); }
  };

  const loadActiveOfficers = async () => {
    try {
      const list = await api.getActiveOfficers(token, { limit: 200 });
      setActiveOfficers(list);
    } catch {
      setActiveOfficers([]);
    }
  };

  const FF = (k) => ({ value: form[k], onChange: e => setForm(p => ({ ...p, [k]: e.target.value })) });
  const EF = (k) => ({ value: editForm[k] ?? '', onChange: e => setEditForm(p => ({ ...p, [k]: e.target.value })) });

  // Hint: show the valid evidence IDs for this case in the add form
  const evidenceHint = caseEvidenceIds.size > 0
    ? `Valid IDs for this case: ${[...caseEvidenceIds].join(', ')}`
    : 'No evidence items exist for this case yet';

  return (
    <>
      {err && <Alert msg={err} />}
      {success && <Alert type="success" msg={success} />}
      <div className="table-wrap">
        <div className="table-toolbar">
          <div />
          {canAddCustody && (
            <button className="btn btn-primary btn-sm" onClick={async () => {
              await loadActiveOfficers();
              setForm({ EvidenceID: '', ActingOfficerID: '', Notes: '' });
              setErr(''); setModal('add');
            }}>+ Add Custody Record</button>
          )}
        </div>
        {loading ? <Loading /> : records.length === 0 ? <Empty icon="🔗" msg="No custody records for this case" /> : (
          <table>
            <thead>
              <tr>
                <th>Record ID</th><th>Evidence ID</th><th>Officer ID</th><th>Notes</th><th>Timestamp</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {records.map(r => (
                <tr key={r.RecordID}>
                  <td><span className="mono">#{r.RecordID}</span></td>
                  <td><span className="mono">{r.EvidenceID}</span></td>
                  <td><span className="mono">{r.ActingOfficerID}</span></td>
                  <td>{r.Notes || '—'}</td>
                  <td>{fmt(r.Timestamp)}</td>
                  <td>
                    <div className="td-actions">
                      {isOwnCase && caseActive && (
                        <button className="btn btn-secondary btn-sm" onClick={() => {
                          setSelected(r);
                          setEditForm({ ActingOfficerID: r.ActingOfficerID, Notes: r.Notes || '' });
                          setErr(''); setModal('edit');
                        }}>Edit</button>
                      )}
                      {isAdmin && (
                        <button className="btn btn-danger btn-sm" onClick={() => handleDelete(r)}>Delete</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {modal === 'add' && (
        <Modal title="Add Custody Record" sub={`Case #${caseData.CaseID}`} onClose={() => setModal(null)}
          footer={<>
            <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleAdd} disabled={saving}>{saving ? 'Saving…' : 'Add Record'}</button>
          </>}>
          <Alert msg={err} />
          <div className="field-row">
            <div className="field">
              <label>Evidence ID</label>
              <select {...FF('EvidenceID')}>
                <option value="">Select evidence</option>
                {caseEvidenceList.map((ev) => (
                  <option key={ev.EvidenceID} value={ev.EvidenceID}>
                    #{ev.EvidenceID} - {ev.EvidenceType}
                  </option>
                ))}
              </select>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 5, fontFamily: 'var(--mono)' }}>{evidenceHint}</div>
            </div>
            <div className="field">
              <label>Acting Officer ID</label>
              <select {...FF('ActingOfficerID')}>
                <option value="">Select officer</option>
                {activeOfficers.map((o) => (
                  <option key={o.UserID} value={o.UserID}>
                    {o.Name} ({o.BadgeNumber}) - #{o.UserID}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="field"><label>Notes</label><textarea {...FF('Notes')} placeholder="Optional notes…" /></div>
        </Modal>
      )}

      {modal === 'edit' && (
        <Modal title="Edit Custody Record" sub={`Record #${selected?.RecordID}`} onClose={() => setModal(null)}
          footer={<>
            <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleEdit} disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
          </>}>
          <Alert msg={err} />
          <div className="field"><label>Acting Officer ID</label><input {...EF('ActingOfficerID')} type="number" /></div>
          <div className="field"><label>Notes</label><textarea {...EF('Notes')} /></div>
        </Modal>
      )}
    </>
  );
};

// ─── Officers Tab (Acting Inspector of the case only) ─────────────────────────
// Backend endpoint checks case.ActingInspectorID == current_user.UserID.
// Keep this tab inspector-only in the UI to avoid role mismatch/confusion.
const OfficersTab = ({ token, user, caseData }) => {
  const [officers, setOfficers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [allOfficers, setAllOfficers] = useState([]);
  const [assignIds, setAssignIds] = useState([]);
  const [modal, setModal] = useState(null);
  const [err, setErr] = useState('');
  const [success, setSuccess] = useState('');
  const [saving, setSaving] = useState(false);
  const setSuccessAuto = useAutoClear(setSuccess);

  const isOwnCase = user.Role === 'inspector' && caseData.ActingInspectorID === user.UserID;
  const canView = isOwnCase;
  const caseActive = caseData.Status !== 'INACTIVE';
  const canManage = isOwnCase && caseActive;

  const load = useCallback(async () => {
    setLoading(true);
    try { setOfficers(await api.getAssignedOfficers(token, caseData.CaseID)); }
    catch { setOfficers([]); } finally { setLoading(false); }
  }, [token, caseData.CaseID]);

  useEffect(() => { load(); }, [load]);

  const openAssign = async () => {
    try {
      const all = await api.getActiveOfficers(token, { limit: 200 });
      setAllOfficers(all);
    }
    catch { setAllOfficers([]); }
    setAssignIds([]); setErr(''); setModal('assign');
  };

  const handleAssign = async () => {
    if (assignIds.length === 0) { setErr('Select at least one officer'); return; }
    setSaving(true); setErr('');
    try {
      await api.assignOfficers(token, caseData.CaseID, assignIds);
      setSuccessAuto('Officers assigned.');
      setModal(null); load();
    } catch (e) { setErr(e.message); } finally { setSaving(false); }
  };

  const handleRemove = async (o) => {
    if (!window.confirm(`Remove ${o.Name} from this case?`)) return;
    try { await api.removeOfficers(token, caseData.CaseID, [o.UserID]); setSuccessAuto('Officer removed.'); load(); }
    catch (e) { setErr(e.message); }
  };

  if (!canView) {
    return (
      <div className="empty">
        <div className="empty-icon">🔒</div>
        <div>Only the acting inspector can view assigned officers.</div>
      </div>
    );
  }

  return (
    <>
      {err && <Alert msg={err} />}
      {success && <Alert type="success" msg={success} />}
      <div className="table-wrap">
        <div className="table-toolbar">
          <div />
          {canManage && <button className="btn btn-primary btn-sm" onClick={openAssign}>+ Assign Officers</button>}
        </div>
        {loading ? <Loading /> : officers.length === 0 ? <Empty icon="👮" msg="No officers assigned" /> : (
          <table>
            <thead><tr><th>Name</th><th>Badge #</th><th>Role</th><th>Contact</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {officers.map(o => (
                <tr key={o.UserID}>
                  <td>{o.Name}</td>
                  <td><span className="mono">{o.BadgeNumber}</span></td>
                  <td><RoleBadge role={o.Role} /></td>
                  <td>{o.Contact || '—'}</td>
                  <td><StatusBadge status={o.Status} /></td>
                  <td>
                    {canManage ? <button className="btn btn-danger btn-sm" onClick={() => handleRemove(o)}>Remove</button> : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {canManage && modal === 'assign' && (
        <Modal title="Assign Officers" sub={`Case #${caseData.CaseID}`} onClose={() => setModal(null)}
          footer={<>
            <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleAssign} disabled={saving}>{saving ? 'Assigning…' : 'Assign'}</button>
          </>}>
          <Alert msg={err} />
          {allOfficers.length === 0
            ? <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: 12 }}>No active officers found.</div>
            : (
              <div style={{ maxHeight: 240, overflowY: 'auto', border: '1px solid var(--border2)', borderRadius: 6, padding: '6px 0' }}>
                {allOfficers.map(o => (
                  <label key={o.UserID} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 14px', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={assignIds.includes(o.UserID)}
                      onChange={() => setAssignIds(p => p.includes(o.UserID) ? p.filter(x => x !== o.UserID) : [...p, o.UserID])}
                    />
                    <span>{o.Name}</span>
                    <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>{o.BadgeNumber}</span>
                    <StatusBadge status={o.Status} />
                  </label>
                ))}
              </div>
            )}
        </Modal>
      )}
    </>
  );
};

// ─── Case Detail View ─────────────────────────────────────────────────────────
const CaseDetailView = ({ token, user, caseData, onBack, onReactivate }) => {
  const [tab, setTab] = useState('evidence');
  const isInspector = user.Role === 'inspector';
  const isOwnCase = isInspector && caseData.ActingInspectorID === user.UserID;
  const canViewOfficers = isOwnCase;

  const tabs = [
    { id: 'evidence', label: '🗂 Evidence' },
    { id: 'custody', label: '🔗 Custody Chain' },
    ...(canViewOfficers ? [{ id: 'officers', label: '👮 Assigned Officers' }] : []),
  ];

  return (
    <div>
      <div className="back-btn" onClick={onBack}>← Back to Cases</div>
      <div className="case-header">
        <div className="case-header-left">
          <div className="case-header-title">{caseData.Title}</div>
          <div className="case-meta">
            <span><span className="mono">#{caseData.CaseID}</span></span>
            <span>Type: {caseData.Type}</span>
            <span><CaseStatusBadge status={caseData.Status} /></span>
            <span>Opened: {fmtDate(caseData.DateOpened)}</span>
            {caseData.DateClosed && <span>Closed: {fmtDate(caseData.DateClosed)}</span>}
            <span style={{ color: 'var(--text-muted)', fontSize: 11, fontFamily: 'var(--mono)' }}>
              Inspector ID: {caseData.ActingInspectorID}
            </span>
          </div>
          {caseData.Description && (
            <p style={{ marginTop: 10, fontSize: 13, color: 'var(--text-dim)' }}>{caseData.Description}</p>
          )}
          {(isOwnCase) && caseData.Status === 'INACTIVE' && (
            <div style={{ marginTop: 12 }}>
              <button className="btn btn-primary btn-sm" onClick={() => onReactivate(caseData)}>
                Reactivate Case
              </button>
            </div>
          )}
        </div>
      </div>
      <div className="tabs">
        {tabs.map(t => (
          <div key={t.id} className={`tab${tab === t.id ? ' active' : ''}`} onClick={() => setTab(t.id)}>
            {t.label}
          </div>
        ))}
      </div>
      {tab === 'evidence' && <EvidenceTab token={token} user={user} caseData={caseData} />}
      {tab === 'custody' && <CustodyTab token={token} user={user} caseData={caseData} />}
      {tab === 'officers' && <OfficersTab token={token} user={user} caseData={caseData} />}
    </div>
  );
};

// ─── Audit View (Admin only) ──────────────────────────────────────────────────
const AuditView = ({ token }) => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [userId, setUserId] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [limit, setLimit] = useState(100);
  const [skip, setSkip] = useState(0);
  const [err, setErr] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setErr('');
    try {
      const params = {};
      if (search) params.search = search;
      if (userId) params.user_id = userId;
      if (fromDate) params.from_date = `${fromDate}T00:00:00`;
      if (toDate) params.to_date = `${toDate}T23:59:59.999`;
      params.limit = String(limit);
      params.skip = String(skip);
      setLogs(await api.getAuditLogs(token, params));
    } catch (e) { setErr(e.message); } finally { setLoading(false); }
  }, [token, search, userId, fromDate, toDate, limit, skip]);

  useEffect(() => { load(); }, [load]);

  const eventColor = (t) => ({
    READ: 'badge-info',
    CREATE: 'badge-active',
    UPDATE: 'badge-amber',
    DELETE: 'badge-inactive',
  }[t] || 'badge-info');

  return (
    <>
      {err && <Alert msg={err} />}
      <div className="table-wrap">
        <div className="table-toolbar">
          <div className="table-toolbar-left">
            <input className="search-input" placeholder="Search details…" value={search} onChange={e => setSearch(e.target.value)} />
            <input className="search-input" placeholder="Filter by User ID…" type="number" style={{ width: 160 }} value={userId} onChange={e => setUserId(e.target.value)} />
            <input
              className="search-input"
              type="date"
              style={{ width: 170 }}
              value={fromDate}
              onChange={e => setFromDate(e.target.value)}
              title="From date (starts at midnight)"
            />
            <input
              className="search-input"
              type="date"
              style={{ width: 170 }}
              value={toDate}
              onChange={e => setToDate(e.target.value)}
              title="To date (ends at 23:59:59)"
            />
            <input
              className="search-input"
              placeholder="Limit"
              type="number"
              min={1}
              max={1000}
              style={{ width: 100 }}
              value={limit}
              onChange={e => setLimit(Math.max(1, Math.min(1000, Number(e.target.value) || 1)))}
            />
            <input
              className="search-input"
              placeholder="Skip"
              type="number"
              min={0}
              style={{ width: 100 }}
              value={skip}
              onChange={e => setSkip(Math.max(0, Number(e.target.value) || 0))}
            />
          </div>
          <button className="btn btn-secondary btn-sm" onClick={load}>↺ Refresh</button>
        </div>
        {loading ? <Loading /> : logs.length === 0 ? <Empty icon="📋" msg="No audit logs" /> : (
          <table>
            <thead>
              <tr><th>Log ID</th><th>Timestamp</th><th>User ID</th><th>Event</th><th>Details</th></tr>
            </thead>
            <tbody>
              {logs.map(l => (
                <tr key={l.LogID}>
                  <td><span className="mono">#{l.LogID}</span></td>
                  <td style={{ whiteSpace: 'nowrap' }}>{fmt(l.Timestamp)}</td>
                  <td><span className="mono">{l.UserID}</span></td>
                  <td><span className={`badge ${eventColor(l.EventType)}`}>{l.EventType}</span></td>
                  <td style={{ maxWidth: 420, fontSize: 12, color: 'var(--text-dim)' }}>{l.Details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
};

// ─── Profile / Change Password View ──────────────────────────────────────────
const ProfileView = ({ token, user }) => {
  const [form, setForm] = useState({ oldPassword: '', newPassword: '', confirm: '' });
  const [err, setErr] = useState('');
  const [success, setSuccess] = useState('');
  const [saving, setSaving] = useState(false);
  const setSuccessAuto = useAutoClear(setSuccess);

  const handleSubmit = async (e) => {
    e.preventDefault(); setErr(''); setSuccess('');
    if (form.newPassword !== form.confirm) { setErr('New passwords do not match'); return; }
    if (form.newPassword.length < 6) { setErr('Password must be at least 6 characters'); return; }
    if (form.newPassword === form.oldPassword) { setErr('New password cannot be same as old password'); return; }
    setSaving(true);
    try {
      await api.changePassword(token, form.oldPassword, form.newPassword);
      setSuccessAuto('Password updated successfully.');
      setForm({ oldPassword: '', newPassword: '', confirm: '' });
    } catch (e) { setErr(e.message); } finally { setSaving(false); }
  };

  return (
    <div style={{ maxWidth: 480 }}>
      <div className="table-wrap" style={{ padding: 24 }}>
        <div style={{ marginBottom: 20 }}>
          <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>{user.Name}</div>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            <span className="mono" style={{ color: 'var(--accent)', fontSize: 13 }}>{user.BadgeNumber}</span>
            <RoleBadge role={user.Role} />
            <StatusBadge status={user.Status} />
          </div>
          <div style={{ marginTop: 8, fontSize: 13, color: 'var(--text-dim)' }}>{user.Email}</div>
          {user.LastLogin && (
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>Last login: {fmt(user.LastLogin)}</div>
          )}
        </div>

        <div style={{ borderTop: '1px solid var(--border)', paddingTop: 20, marginTop: 8 }}>
          <div style={{ fontWeight: 600, marginBottom: 16 }}>Change Password</div>
          <Alert msg={err} />
          <Alert type="success" msg={success} />
          <form onSubmit={handleSubmit}>
            <div className="field">
              <label>Current Password</label>
              <input type="password" value={form.oldPassword} onChange={e => setForm(p => ({ ...p, oldPassword: e.target.value }))} required />
            </div>
            <div className="field">
              <label>New Password</label>
              <input type="password" value={form.newPassword} onChange={e => setForm(p => ({ ...p, newPassword: e.target.value }))} required />
            </div>
            <div className="field">
              <label>Confirm New Password</label>
              <input type="password" value={form.confirm} onChange={e => setForm(p => ({ ...p, confirm: e.target.value }))} required />
            </div>
            <button className="btn btn-primary" type="submit" disabled={saving}>
              {saving ? 'Updating…' : 'Update Password'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

// ─── Dashboard View ───────────────────────────────────────────────────────────
const DashboardView = ({ token, user, onOpenCase }) => {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const isAdmin = user.Role === 'admin';
  const isInspector = user.Role === 'inspector';

  useEffect(() => {
    const load = async () => {
      try {
        const data = isAdmin || isInspector
          ? await api.getCases(token, { limit: 5 })
          : await api.getAssignedCases(token);
        setCases(data);
      } catch { setCases([]); } finally { setLoading(false); }
    };
    load();
  }, [token, user.Role, isAdmin, isInspector]);

  const open = cases.filter(c => c.Status !== 'INACTIVE').length;
  const closed = cases.filter(c => c.Status === 'INACTIVE').length;

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="title">Welcome, {user.Name.split(' ')[0]}</div>
          <div className="subtitle">Logged in as <strong>{user.BadgeNumber}</strong> · Role: <strong>{user.Role}</strong></div>
        </div>
      </div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Total Cases</div>
          <div className="stat-value">{cases.length}</div>
          <div className="stat-icon">📁</div>
        </div>
        <div className="stat-card green">
          <div className="stat-label">Active Cases</div>
          <div className="stat-value" style={{ color: 'var(--green)' }}>{open}</div>
          <div className="stat-icon">🟢</div>
        </div>
        <div className="stat-card red">
          <div className="stat-label">Closed Cases</div>
          <div className="stat-value" style={{ color: 'var(--text-muted)' }}>{closed}</div>
          <div className="stat-icon">🔒</div>
        </div>
      </div>
      <div style={{ fontWeight: 600, marginBottom: 14, fontSize: 14 }}>Recent Cases</div>
      <div className="table-wrap">
        {loading ? <Loading /> : cases.length === 0 ? <Empty icon="📁" msg="No cases yet" /> : (
          <table>
            <thead><tr><th>ID</th><th>Title</th><th>Type</th><th>Inspector ID</th><th>Status</th><th>Opened</th><th></th></tr></thead>
            <tbody>
              {cases.slice(0, 5).map(c => (
                <tr key={c.CaseID}>
                  <td><span className="mono">#{c.CaseID}</span></td>
                  <td>{c.Title}</td>
                  <td>{c.Type}</td>
                  <td><span className="mono">{c.ActingInspectorID}</span></td>
                  <td><CaseStatusBadge status={c.Status} /></td>
                  <td>{fmtDate(c.DateOpened)}</td>
                  <td><button className="btn btn-ghost btn-sm" onClick={() => onOpenCase(c)}>View →</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

// ─── Endpoint Directory (role filtered) ───────────────────────────────────────
const ENDPOINTS = [
  { method: 'POST', path: '/login', description: 'Authenticate user and return JWT', roles: ['admin', 'inspector', 'officer'] },
  { method: 'GET', path: '/me', description: 'Get current user profile', roles: ['admin', 'inspector', 'officer'] },
  { method: 'POST', path: '/users/change-password', description: 'Change own account password', roles: ['admin', 'inspector', 'officer'] },

  { method: 'GET', path: '/users/', description: 'List users', roles: ['admin'] },
  { method: 'GET', path: '/users/officers/active', description: 'List active officers', roles: ['admin', 'inspector'] },
  { method: 'POST', path: '/users/', description: 'Create user', roles: ['admin'] },
  { method: 'PUT', path: '/users/{badge_number}', description: 'Update user', roles: ['admin'] },
  { method: 'DELETE', path: '/users/{badge_number}', description: 'Delete user', roles: ['admin'] },

  { method: 'GET', path: '/cases/', description: 'List cases', roles: ['admin', 'inspector'] },
  { method: 'GET', path: '/cases/assigned', description: 'Get assigned/owned cases', roles: ['inspector', 'officer'] },
  { method: 'GET', path: '/cases/assigned/{officer_id}', description: 'Get cases for officer', roles: ['admin', 'inspector'] },
  { method: 'GET', path: '/cases/assigned-officers/{case_id}', description: 'List officers assigned to case', roles: ['admin', 'inspector'] },
  { method: 'POST', path: '/cases/', description: 'Create case', roles: ['inspector'] },
  { method: 'PUT', path: '/cases/{case_id}', description: 'Update case', roles: ['inspector'] },
  { method: 'PUT', path: '/cases/{case_id}/close', description: 'Close case', roles: ['inspector'] },
  { method: 'PUT', path: '/cases/{case_id}/reactivate', description: 'Reactivate inactive case', roles: ['officer', 'inspector'] },
  { method: 'DELETE', path: '/cases/{case_id}', description: 'Delete case', roles: ['admin'] },
  { method: 'POST', path: '/cases/{case_id}/assign', description: 'Assign officers to case', roles: ['inspector'] },
  { method: 'POST', path: '/cases/{case_id}/remove-officers', description: 'Remove officers from case', roles: ['inspector'] },

  { method: 'GET', path: '/evidence/case/{case_id}', description: 'List evidence for a case', roles: ['admin', 'inspector', 'officer'] },
  { method: 'POST', path: '/evidence/', description: 'Upload/add evidence', roles: ['inspector', 'officer'] },
  { method: 'PUT', path: '/evidence/{case_id}/{evidence_id}', description: 'Update evidence metadata', roles: ['inspector', 'officer'] },
  { method: 'DELETE', path: '/evidence/{evidence_id}', description: 'Delete evidence', roles: ['admin'] },
  { method: 'GET', path: '/evidence/{case_id}/{evidence_id}/download', description: 'Download evidence file', roles: ['admin', 'inspector', 'officer'] },

  { method: 'GET', path: '/custody/', description: 'List custody records', roles: ['admin', 'inspector', 'officer'] },
  { method: 'GET', path: '/custody/{record_id}', description: 'Get custody record', roles: ['admin', 'inspector', 'officer'] },
  { method: 'POST', path: '/custody/', description: 'Add custody record', roles: ['inspector'] },
  { method: 'PUT', path: '/custody/{record_id}', description: 'Update custody record', roles: ['inspector'] },
  { method: 'DELETE', path: '/custody/{record_id}', description: 'Delete custody record', roles: ['admin'] },

  { method: 'GET', path: '/audit/', description: 'Read audit logs', roles: ['admin'] },
];

const EndpointDirectoryView = ({ user }) => {
  const visibleEndpoints = ENDPOINTS.filter((ep) => ep.roles.includes(user.Role));

  return (
    <div className="table-wrap">
      <div className="table-toolbar">
        <div className="table-toolbar-left">
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            Showing endpoints available to role: <strong>{user.Role}</strong>
          </div>
        </div>
      </div>
      {visibleEndpoints.length === 0 ? <Empty icon="🔒" msg="No endpoints available for this role" /> : (
        <table>
          <thead>
            <tr>
              <th>Method</th>
              <th>Path</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {visibleEndpoints.map((ep) => (
              <tr key={`${ep.method}-${ep.path}`}>
                <td><span className="badge badge-info">{ep.method}</span></td>
                <td><span className="mono">{ep.path}</span></td>
                <td>{ep.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

// ─── Sidebar Nav ──────────────────────────────────────────────────────────────
const NAV = (role) => {
  const items = [
    { id: 'dashboard', icon: '⬡', label: 'Dashboard', roles: ['admin', 'inspector', 'officer'] },
    { id: 'cases',     icon: '📁', label: 'Cases',     roles: ['admin', 'inspector', 'officer'] },
    // { id: 'endpoints', icon: '🔌', label: 'Endpoints', roles: ['admin', 'inspector', 'officer'] },
    { id: 'users',     icon: '👥', label: 'Users',     roles: ['admin'] },
    { id: 'audit',     icon: '📋', label: 'Audit Log', roles: ['admin'] },
    { id: 'profile',   icon: '🔑', label: 'Profile',   roles: ['admin', 'inspector', 'officer'] },
  ];
  return items.filter(i => i.roles.includes(role));
};

// ─── App Root ─────────────────────────────────────────────────────────────────
export default function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem('dems_token') || '');
  const [user, setUser] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem('dems_user') || 'null'); } catch { return null; }
  });
  const [view, setView] = useState('dashboard');
  const [openCase, setOpenCase] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(() => localStorage.getItem('dems_theme') === 'dark');

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
    localStorage.setItem('dems_theme', isDarkMode ? 'dark' : 'light');
  }, [isDarkMode]);

  const handleLogin = (t, u) => {
    setToken(t); setUser(u);
    sessionStorage.setItem('dems_token', t);
    sessionStorage.setItem('dems_user', JSON.stringify(u));
    setView('dashboard');
  };

  const handleLogout = () => {
    setToken(''); setUser(null); setOpenCase(null);
    sessionStorage.removeItem('dems_token');
    sessionStorage.removeItem('dems_user');
  };

  const handleOpenCase = (c) => { setOpenCase(c); setView('case-detail'); };
  const handleBackFromCase = () => { setOpenCase(null); setView('cases'); };
  const handleNav = (id) => { setView(id); setOpenCase(null); };
  const handleReactivateCase = async (c) => {
    try {
      await api.reactivateCase(token, c.CaseID);
      setOpenCase((prev) => prev && prev.CaseID === c.CaseID ? { ...prev, Status: 'Open', DateClosed: null } : prev);
    } catch (e) {
      // Keep behavior simple and visible with native alert for detail-view action.
      alert(e.message || 'Failed to reactivate case');
    }
  };

  if (!token || !user) {
    return <LoginView onLogin={handleLogin} isDarkMode={isDarkMode} onToggleTheme={() => setIsDarkMode((v) => !v)} />;
  }

  const navItems = NAV(user.Role);
  const VIEW_TITLES = {
    dashboard:   ['Dashboard',        'Overview'],
    cases:       ['Cases',            user.Role === 'officer' ? 'Your assigned cases' : 'All cases'],
    endpoints:   ['Endpoints',        'Role-based API access'],
    users:       ['User Management',  'Admin only'],
    audit:       ['Audit Log',        'System activity log'],
    profile:     ['Profile',          'Account settings'],
    'case-detail': [openCase?.Title || 'Case Detail', `Case #${openCase?.CaseID}`],
  };
  const [title, sub] = VIEW_TITLES[view] || ['DEMS', ''];

  return (
    <div className={`layout${sidebarCollapsed ? ' sidebar-collapsed' : ''}`}>
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <img src="/logo.jpeg" alt="DEMS logo" className="sidebar-brand-image" />
            <div className="sidebar-brand-name">DE<span>MS</span></div>
          </div>
          <div className="sidebar-version">v1.0 · Secure</div>
        </div>
        <div className="sidebar-user">
          <div className="sidebar-user-name">{user.Name}</div>
          <div className="sidebar-user-badge">{user.BadgeNumber}</div>
          <RoleBadge role={user.Role} />
        </div>
        <nav className="sidebar-nav">
          <div className="nav-section-row">
            <div className="nav-section">Navigation</div>
            <button
              className="btn btn-ghost btn-sm sidebar-toggle"
              type="button"
              onClick={() => setSidebarCollapsed((s) => !s)}
              aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
              title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {sidebarCollapsed ? '☰' : '☷'}
            </button>
          </div>
          {navItems.map(item => (
            <div
              key={item.id}
              className={`nav-item${view === item.id || (view === 'case-detail' && item.id === 'cases') ? ' active' : ''}`}
              onClick={() => handleNav(item.id)}
              title={sidebarCollapsed ? item.label : ''}
            >
              <span className="nav-item-icon">{item.icon}</span>
              <span className="nav-item-label">{item.label}</span>
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="btn btn-ghost btn-sm" onClick={handleLogout} style={{ width: '100%', justifyContent: 'flex-start' }}>
            ⎋ Sign Out
          </button>
        </div>
      </aside>

      <main className="main">
        <div className="topbar">
          <div>
            <div className="topbar-title">{title}</div>
            {sub && <div className="topbar-sub">{sub}</div>}
          </div>
          <div className="topbar-actions">
            <ThemeToggle isDark={isDarkMode} onToggle={() => setIsDarkMode((v) => !v)} className="theme-toggle-main" />
            <span style={{ fontSize: 12, color: 'rgba(255,255,255,0.9)', fontFamily: 'var(--mono)' }}>
              {new Date().toLocaleDateString('en-IN', { dateStyle: 'medium' })}
            </span>
            <div className="profile-circle" title={user.Name} style={{ marginLeft: 8 }}>{user.Name ? user.Name.split(' ')[0][0] : 'U'}</div>
          </div>
        </div>

        <div className="content">
          {view === 'dashboard'   && <DashboardView token={token} user={user} onOpenCase={handleOpenCase} />}
          {view === 'cases'       && <CasesView token={token} user={user} onOpenCase={handleOpenCase} />}
          {view === 'endpoints'   && <EndpointDirectoryView user={user} />}
          {view === 'case-detail' && openCase && <CaseDetailView token={token} user={user} caseData={openCase} onBack={handleBackFromCase} onReactivate={handleReactivateCase} />}
          {view === 'users'       && user.Role === 'admin' && <UsersView token={token} />}
          {view === 'audit'       && user.Role === 'admin' && <AuditView token={token} />}
          {view === 'profile'     && <ProfileView token={token} user={user} />}
        </div>
      </main>
    </div>
  );
}
