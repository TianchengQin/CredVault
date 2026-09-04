import { useState, useEffect, useCallback, useMemo } from 'react'
import api, { setSession, clearSession } from './api.js'

const icons = {
  lock: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>),
  copy: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><rect width="13" height="13" x="9" y="9" rx="2" /><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" /></svg>),
  check: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5" /></svg>),
  eye: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" /></svg>),
  eyeOff: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" /><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" /><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" /><line x1="2" x2="22" y1="2" y2="22" /></svg>),
  search: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></svg>),
  plus: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M5 12h14" /><path d="M12 5v14" /></svg>),
  logout: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><polyline points="16 17 21 12 16 7" /><line x1="21" x2="9" y1="12" y2="12" /></svg>),
  key: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="m21 2-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4" /></svg>),
  user: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>),
  vault: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" /></svg>),
  link: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" /></svg>),
  star: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2 15.09 8.26 22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg>),
  tag: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2H2v10l9.29 9.29a1 1 0 0 0 1.42 0l8.58-8.58a1 1 0 0 0 0-1.42L12 2z" /><circle cx="7" cy="7" r="1" /></svg>),
  shield: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" /></svg>),
  download: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" x2="12" y1="15" y2="3" /></svg>),
  upload: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" x2="12" y1="3" y2="15" /></svg>),
  trash: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18" /><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" /><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" /></svg>),
  history: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" /><path d="M3 3v5h5" /><path d="M12 7v5l4 2" /></svg>),
  close: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" x2="6" y1="6" y2="18" /><line x1="6" x2="18" y1="6" y2="18" /></svg>),
  sun: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4" /><path d="M12 2v2" /><path d="M12 20v2" /><path d="m4.93 4.93 1.41 1.41" /><path d="m17.66 17.66 1.41 1.41" /><path d="M2 12h2" /><path d="M20 12h2" /><path d="m6.34 17.66-1.41 1.41" /><path d="m19.07 4.93-1.41 1.41" /></svg>),
  moon: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" /></svg>),
  refresh: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M23 4v6h-6" /><path d="M1 20v-6h6" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10" /><path d="M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>),
  users: (<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>),
}

function Logo({ size = 38 }) {
  return (
    <div className="rounded-[11px] bg-emerald-500 flex items-center justify-center" style={{ width: size, height: size }} aria-hidden>
      <svg width={size * 0.56} height={size * 0.56} viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="11" width="18" height="11" rx="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
    </div>
  )
}

function Spinner({ className = 'h-4 w-4' }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden>
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-90" fill="currentColor" d="M4 12a8 8 0 0 1 8-8v4a4 4 0 0 0-4 4H4z" />
    </svg>
  )
}

// ---------- password generator (crypto-strong) ----------
const PW_POOLS = {
  upper: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
  lower: 'abcdefghijklmnopqrstuvwxyz',
  digits: '0123456789',
  symbols: '!@#$%^&*()-_=+[]{};:,.?',
}
function generatePassword(length = 20) {
  const pool = Object.values(PW_POOLS).join('')
  const bytes = new Uint32Array(length)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, (n) => pool[n % pool.length]).join('')
}

// ---------- Toast ----------
function useToasts() {
  const [toasts, setToasts] = useState([])
  const push = useCallback((message, type = 'success') => {
    const id = Math.random().toString(36).slice(2)
    setToasts((t) => [...t, { id, message, type }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3200)
  }, [])
  const toastHost = (
    <div className="fixed bottom-5 right-5 z-[100] flex flex-col gap-2 items-end pointer-events-none">
      {toasts.map((t) => (
        <div key={t.id} role="status" className={`animate-rise pointer-events-auto rounded-[14px] border px-4 py-2.5 text-[15px] shadow-toast backdrop-blur ${
          t.type === 'error' ? 'border-rose-300/70 bg-surface-900 text-rose-500' : 'border-emerald-500/40 bg-surface-900 text-emerald-500'
        }`}>
          {t.message}
        </div>
      ))}
    </div>
  )
  return { push, toastHost }
}

// ---------- generic modal: closes ONLY via explicit Close button ----------
function Modal({ title, subtitle, onClose, children, wide = false }) {
  return (
    <div className="modal-backdrop">
      <div role="dialog" aria-modal="true" className={`w-full ${wide ? 'max-w-lg' : 'max-w-md'} card p-6 max-h-[90vh] overflow-y-auto animate-rise relative`}>
        <button onClick={onClose} title="Close" aria-label="Close" className="icon-btn absolute right-4 top-4">
          <span className="w-5 h-5 block">{icons.close}</span>
        </button>
        <div className="mb-5 pr-8">
          <h2 className="text-base font-semibold text-zinc-100">{title}</h2>
          {subtitle && <p className="text-sm text-zinc-500 mt-1 leading-relaxed">{subtitle}</p>}
        </div>
        {children}
      </div>
    </div>
  )
}

function ConfirmModal({ title, message, confirmLabel = 'Confirm', onConfirm, onClose }) {
  const [busy, setBusy] = useState(false)
  return (
    <Modal title={title} onClose={onClose}>
      <p className="text-sm text-zinc-400 leading-relaxed">{message}</p>
      <div className="mt-6 flex justify-end gap-2">
        <button className="btn-ghost" onClick={onClose} disabled={busy}>Cancel</button>
        <button className="btn-primary !bg-rose-500 hover:!bg-rose-400" disabled={busy} onClick={async () => { setBusy(true); await onConfirm(); }}>
          {busy && <Spinner />}{confirmLabel}
        </button>
      </div>
    </Modal>
  )
}

// ---------- auth screens ----------
function AuthShell({ children }) {
  return (
    <div className="min-h-[100dvh] flex items-center justify-center p-6">
      <div className="w-full max-w-sm animate-rise">{children}</div>
    </div>
  )
}

function AuthForm({ title, subtitle, fields, submitLabel, onSubmit, loading, error }) {
  return (
    <div className="card p-6">
      <h1 className="text-lg font-semibold text-zinc-100">{title}</h1>
      {subtitle && <p className="text-sm text-zinc-400 mt-1 leading-relaxed">{subtitle}</p>}
      <form onSubmit={onSubmit} className="mt-5 space-y-4">
        {fields}
        {error && (
          <p role="alert" className="text-sm text-rose-400 flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-rose-400 shrink-0" />
            {error}
          </p>
        )}
        <button type="submit" disabled={loading} className="btn-primary w-full py-2.5">
          {loading && <Spinner />}{submitLabel}
        </button>
      </form>
    </div>
  )
}

function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [mfaToken, setMfaToken] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const r = await api.post('/auth/login', { username, password })
      if (r.data.mfa_required) {
        setMfaToken(r.data.mfa_token)
      } else {
        setSession(r.data.token, '')
        onLogin(r.data)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const submitMfa = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const r = await api.post('/auth/2fa/confirm', { mfa_token: mfaToken, code })
      setSession(r.data.token, '')
      onLogin(r.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid code')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell>
      <div className="flex flex-col items-center mb-8">
        <Logo size={54} />
        <h1 className="mt-4 text-xl font-semibold tracking-tight">CredVault</h1>
        <p className="text-sm text-zinc-500 mt-1">Encrypted credential manager</p>
      </div>
      {mfaToken ? (
        <AuthForm
          title="Two-factor authentication"
          subtitle="Enter the 6-digit code from your authenticator app."
          submitLabel="Verify"
          loading={loading}
          error={error}
          onSubmit={submitMfa}
          fields={
            <div>
              <label className="label" htmlFor="mfa">Authenticator code</label>
              <input id="mfa" className="input mono-val !text-lg tracking-[0.4em] text-center" inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} autoFocus />
            </div>
          }
        />
      ) : (
        <AuthForm
          title="Sign in"
          submitLabel="Sign in"
          loading={loading}
          error={error}
          onSubmit={submit}
          fields={
            <>
              <div>
                <label className="label" htmlFor="u">Username</label>
                <input id="u" className="input" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" autoFocus />
              </div>
              <div>
                <label className="label" htmlFor="p">Password</label>
                <input id="p" type="password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" />
              </div>
            </>
          }
        />
      )}
    </AuthShell>
  )
}

function UnlockPage({ username, onUnlocked, onLogout }) {
  const [mode, setMode] = useState(null)
  const [master, setMaster] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.get('/vault/status')
      .then((r) => setMode(r.data.setup_required ? 'setup' : 'unlock'))
      .catch((err) => {
        if (err.response?.status === 401) onLogout()
        else setMode('unlock')
      })
  }, [])

  if (!mode) {
    return (
      <AuthShell>
        <div className="card p-6 space-y-3">
          <div className="skeleton h-5 w-1/2" />
          <div className="skeleton h-4 w-3/4" />
          <div className="skeleton h-9 w-full" />
        </div>
      </AuthShell>
    )
  }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (mode === 'setup' && master.length < 10) {
      setError('Master password must be at least 10 characters')
      return
    }
    setLoading(true)
    try {
      const endpoint = mode === 'setup' ? '/vault/setup' : '/vault/unlock'
      const r = await api.post(endpoint, { master_password: master })
      setSession(null, r.data.vault_token)
      onUnlocked()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthShell>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-emerald-500/15 text-emerald-300 flex items-center justify-center">
            <span className="w-3.5 h-3.5">{icons.user}</span>
          </div>
          <div>
            <p className="text-sm font-medium text-zinc-100">{username}</p>
            <p className="text-xs text-zinc-500">Signed in</p>
          </div>
        </div>
        <button onClick={onLogout} className="text-sm text-zinc-400 hover:text-zinc-200 inline-flex items-center gap-1.5">
          <span className="w-3.5 h-3.5">{icons.logout}</span>
          Sign out
        </button>
      </div>
      <AuthForm
        title={mode === 'setup' ? 'Set up your vault' : 'Unlock your vault'}
        subtitle={
          mode === 'setup'
            ? 'Create a master password (min 10 chars). It encrypts your credentials and cannot be recovered.'
            : 'Enter your master password to decrypt your credentials.'
        }
        submitLabel={loading ? 'Please wait' : mode === 'setup' ? 'Create vault' : 'Unlock'}
        loading={loading}
        error={error}
        onSubmit={submit}
        fields={
          <div>
            <label className="label" htmlFor="m">Master password</label>
            <input id="m" type="password" className="input" value={master} onChange={(e) => setMaster(e.target.value)} autoFocus />
            <p className="mt-2 text-xs text-zinc-500 flex items-center gap-1.5">
              <span className="w-3 h-3">{icons.vault}</span>
              This password unlocks the vault for this session only. Vault auto-locks after inactivity.
            </p>
          </div>
        }
      />
    </AuthShell>
  )
}

// ---------- shared UI bits ----------
function CopyButton({ value, label, className = '' }) {
  const [copied, setCopied] = useState(false)
  const copy = async (e) => {
    e.stopPropagation()
    try {
      await navigator.clipboard.writeText(value)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = value
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 1200)
  }
  return (
    <button onClick={copy} title={`Copy ${label}`} className={`icon-btn ${copied ? '!text-emerald-400' : ''} ${className}`}>
      <span className="w-4 h-4 block">{copied ? icons.check : icons.copy}</span>
    </button>
  )
}

function ErrorBanner({ message, onRetry }) {
  return (
    <div className="rounded-lg border border-rose-700/60 bg-rose-950/40 px-4 py-3 text-sm text-rose-200 flex items-center justify-between gap-3">
      <span>{message}</span>
      {onRetry && (
        <button onClick={onRetry} className="inline-flex items-center gap-1.5 text-rose-100 hover:text-white shrink-0">
          <span className="w-4 h-4">{icons.refresh}</span> Retry
        </button>
      )}
    </div>
  )
}

function SecretRow({ secret, revealed, onToggle }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-zinc-800 bg-surface-950/60 px-3 py-2">
      <span className="text-[10px] uppercase tracking-[0.14em] text-zinc-500 shrink-0">Secret</span>
      <span className="mono-val text-zinc-300 truncate flex-1 text-right" title={revealed ? secret : undefined}>
        {revealed ? secret : '••••••••••••'}
      </span>
      <button onClick={onToggle} title={revealed ? 'Hide secret' : 'Reveal secret'} className="icon-btn shrink-0">
        <span className="w-4 h-4 block">{revealed ? icons.eyeOff : icons.eye}</span>
      </button>
      <CopyButton value={secret} label="secret" />
    </div>
  )
}

// ---------- credential card ----------
function CredentialCard({ cred, onEdit, onDelete, onToggleFav }) {
  const [revealed, setRevealed] = useState(false)
  const hasUrl = Boolean(cred.url)
  return (
    <article className="card p-4 transition-colors hover:border-zinc-700 animate-rise">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-lg bg-surface-800 border border-zinc-700/70 text-emerald-300 flex items-center justify-center shrink-0">
            <span className="w-4 h-4">{icons.lock}</span>
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-zinc-100 truncate">{cred.name}</p>
            <div className="flex items-center gap-1.5">
              {cred.username ? (
                <p className="text-xs text-zinc-500 truncate">{cred.username}</p>
              ) : (
                <p className="text-xs text-zinc-600">No username</p>
              )}
              {cred.category && (
                <span className="shrink-0 inline-flex items-center gap-0.5 text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded bg-zinc-700/60 text-zinc-300">
                  <span className="w-2.5 h-2.5">{icons.tag}</span>{cred.category}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button onClick={() => onToggleFav(cred)} title={cred.favorite ? 'Unfavorite' : 'Favorite'} className={`icon-btn ${cred.favorite ? '!text-amber-400' : ''}`}>
            <span className="w-4 h-4 block">{icons.star}</span>
          </button>
          <button onClick={onEdit} title="Edit" className="icon-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" /></svg>
          </button>
          <button onClick={onDelete} title="Delete" className="icon-btn hover:!text-rose-400">
            <span className="w-4 h-4 block">{icons.trash}</span>
          </button>
        </div>
      </div>
      <div className="mt-3 space-y-2">
        <SecretRow secret={cred.secret} revealed={revealed} onToggle={() => setRevealed(!revealed)} />
        {hasUrl && (
          <a href={cred.url} target="_blank" rel="noreferrer" className="flex items-center gap-1.5 text-xs text-emerald-400/90 hover:text-emerald-300 truncate">
            <span className="w-3 h-3 shrink-0">{icons.link}</span>
            <span className="truncate">{cred.url.replace(/^https?:\/\//, '')}</span>
          </a>
        )}
        {cred.description && <p className="text-xs text-zinc-500 leading-relaxed">{cred.description}</p>}
      </div>
    </article>
  )
}

// ---------- credential modal (with category, favorite, generator) ----------
function CredentialModal({ initial, onClose, onSave }) {
  const [form, setForm] = useState(initial || { name: '', secret: '', url: '', username: '', description: '', category: '', favorite: false })
  const [error, setError] = useState('')
  const [showSecret, setShowSecret] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const generate = () => setForm({ ...form, secret: generatePassword() })

  const submit = async (e) => {
    e.preventDefault()
    if (!form.name.trim() || !form.secret.trim()) {
      setError('Name and secret are required')
      return
    }
    try {
      await onSave(form)
      onClose()
    } catch (err) {
      setError(err.response?.data?.detail || 'Save failed')
    }
  }

  return (
    <Modal title={initial ? 'Edit credential' : 'Add credential'} onClose={onClose} wide>
      <form onSubmit={submit} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label">Name <span className="text-emerald-400">*</span></label>
            <input className="input" value={form.name} onChange={set('name')} autoFocus />
          </div>
          <div>
            <label className="label">Category</label>
            <input className="input" value={form.category} onChange={set('category')} placeholder="e.g. servers, db, cloud" />
          </div>
        </div>
        <div>
          <label className="label">Secret <span className="text-emerald-400">*</span></label>
          <div className="flex gap-2">
            <input className="input mono-val flex-1" value={form.secret} onChange={set('secret')} type={showSecret ? 'text' : 'password'} autoComplete="off" />
            <button type="button" onClick={() => setShowSecret(!showSecret)} title="Show/hide secret" className="btn-ghost !px-3 shrink-0">
              <span className="w-4 h-4">{showSecret ? icons.eyeOff : icons.eye}</span>
            </button>
            <button type="button" onClick={generate} title="Generate strong password" className="btn-ghost !px-3 shrink-0">
              <span className="w-4 h-4">{icons.refresh}</span> Generate
            </button>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="label">URL</label>
            <input className="input" value={form.url} onChange={set('url')} placeholder="https://" />
          </div>
          <div>
            <label className="label">Username</label>
            <input className="input" value={form.username} onChange={set('username')} autoComplete="off" />
          </div>
        </div>
        <div>
          <label className="label">Description</label>
          <textarea className="input resize-none" value={form.description} onChange={set('description')} rows={2} />
        </div>
        <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer select-none">
          <input type="checkbox" checked={form.favorite} onChange={(e) => setForm({ ...form, favorite: e.target.checked })} className="accent-emerald-500" />
          Mark as favorite
        </label>
        {error && <p role="alert" className="text-sm text-rose-400">{error}</p>}
        <div className="flex justify-end gap-2 pt-1">
          <button type="button" onClick={onClose} className="btn-ghost">Cancel</button>
          <button type="submit" className="btn-primary">Save</button>
        </div>
      </form>
    </Modal>
  )
}

// ---------- Tokens view (full page) ----------
function TokensView({ push }) {
  const [tokens, setTokens] = useState([])
  const [name, setName] = useState('')
  const [permission, setPermission] = useState('write')
  const [msg, setMsg] = useState('')
  const [newToken, setNewToken] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    setLoading(true); setError('')
    api.get('/tokens').then((r) => setTokens(r.data)).catch((e) => setError(e.response?.data?.detail || 'Failed to load tokens')).finally(() => setLoading(false))
  }, [])
  useEffect(load, [load])

  const add = async (e) => {
    e.preventDefault()
    setMsg('')
    setNewToken('')
    try {
      const r = await api.post('/tokens', { name, permission })
      setNewToken(r.data.token)
      setName('')
      load()
      push('Token created')
    } catch (err) {
      setMsg(err.response?.data?.detail || 'Failed')
    }
  }

  const revoke = async (id) => {
    try {
      await api.delete(`/tokens/${id}`)
      load()
      push('Token revoked')
    } catch (err) {
      setMsg(err.response?.data?.detail || 'Failed')
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">API tokens</h1>
        <p className="text-sm text-zinc-500 mt-1">Tokens let agents read or write your vault. The secret is shown only once.</p>
      </div>

      {newToken && (
        <div className="rounded-lg border border-emerald-600/40 bg-emerald-500/10 p-4">
          <p className="text-xs text-emerald-300 mb-2 flex items-center gap-1.5">
            <span className="w-3 h-3">{icons.key}</span>
            Copy this now - it won't be shown again
          </p>
          <div className="flex items-center gap-2">
            <code className="mono-val !text-[15px] text-emerald-200 break-all flex-1 select-all rounded-md bg-surface-950/60 px-3 py-2 border border-emerald-700/40">{newToken}</code>
            <CopyButton value={newToken} label="token" className="!p-2" />
          </div>
        </div>
      )}

      <form onSubmit={add} className="card p-4 flex flex-col sm:flex-row gap-2">
        <input className="input flex-1" placeholder="Token name, e.g. agent-ci" value={name} onChange={(e) => setName(e.target.value)} autoComplete="off" />
        <select className="input w-full sm:w-auto shrink-0" value={permission} onChange={(e) => setPermission(e.target.value)}>
          <option value="write">write</option>
          <option value="read">read</option>
        </select>
        <button className="btn-primary shrink-0"><span className="w-4 h-4">{icons.plus}</span>Create</button>
      </form>
      {msg && <p role="alert" className="text-sm text-rose-400">{msg}</p>}
      {error && <ErrorBanner message={error} onRetry={load} />}

      <div className="card divide-y divide-zinc-800/70">
        {loading ? (
          <div className="p-6 space-y-3"><div className="skeleton h-4 w-1/2" /><div className="skeleton h-4 w-2/3" /></div>
        ) : tokens.length === 0 ? (
          <div className="p-6 text-sm text-zinc-500 text-center">No tokens yet. Create one to let an agent in.</div>
        ) : (
          tokens.map((t) => (
            <div key={t.id} className="px-4 py-3 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-medium text-zinc-200 flex items-center gap-2">
                  <span className="truncate">{t.name}</span>
                  <span className={`shrink-0 text-[10px] font-medium uppercase tracking-wide px-1.5 py-0.5 rounded ${t.permission === 'write' ? 'bg-emerald-500/15 text-emerald-300' : 'bg-zinc-700/60 text-zinc-300'}`}>{t.permission}</span>
                </p>
                <p className="text-xs text-zinc-500">{t.last_used_at ? `Last used ${t.last_used_at}` : 'Never used'}</p>
              </div>
              <button onClick={() => revoke(t.id)} className="btn-ghost !text-rose-400 text-xs shrink-0">Revoke</button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

// ---------- Security / 2FA view ----------
function SecurityView({ push }) {
  const [status, setStatus] = useState({ enabled: false })
  const [setup, setSetup] = useState(null)
  const [code, setCode] = useState('')
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => api.get('/auth/2fa/status').then((r) => setStatus(r.data)).catch(() => {}), [])
  useEffect(() => { load() }, [load])

  const startSetup = async () => {
    setMsg('')
    try {
      const r = await api.get('/auth/2fa/setup')
      setSetup(r.data)
    } catch (err) {
      setMsg(err.response?.data?.detail || 'Failed')
    }
  }

  const confirmEnable = async () => {
    setBusy(true); setMsg('')
    try {
      await api.post('/auth/2fa/verify', { code })
      setSetup(null); setCode(''); await load(); push('2FA enabled')
    } catch (err) {
      setMsg(err.response?.data?.detail || 'Invalid code')
    } finally { setBusy(false) }
  }

  const disable = async () => {
    setBusy(true); setMsg('')
    try {
      await api.post('/auth/2fa/disable', { code })
      setCode(''); await load(); push('2FA disabled')
    } catch (err) {
      setMsg(err.response?.data?.detail || 'Invalid code')
    } finally { setBusy(false) }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Security</h1>
        <p className="text-sm text-zinc-500 mt-1">Optional two-factor authentication (TOTP) for your login.</p>
      </div>

      <div className="card p-5 max-w-xl">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-zinc-100">Two-factor authentication</p>
            <p className="text-xs text-zinc-500 mt-1">{status.enabled ? 'Enabled - a 6-digit code is required at sign-in.' : 'Disabled - protect your account with an authenticator app.'}</p>
          </div>
          <span className={`shrink-0 text-[10px] font-semibold uppercase tracking-wide px-2 py-1 rounded ${status.enabled ? 'bg-emerald-500/15 text-emerald-300' : 'bg-zinc-700/60 text-zinc-400'}`}>{status.enabled ? 'On' : 'Off'}</span>
        </div>

        {!setup && !status.enabled && (
          <button onClick={startSetup} className="btn-primary mt-4"><span className="w-4 h-4">{icons.shield}</span>Enable 2FA</button>
        )}

        {setup && (
          <div className="mt-4 space-y-3 rounded-lg border border-zinc-800 bg-surface-950/50 p-4">
            <p className="text-xs text-zinc-400">Scan or add this secret to your authenticator app, then enter the 6-digit code.</p>
            <div className="flex items-center gap-2">
              <code className="mono-val !text-[15px] text-emerald-200 break-all flex-1 select-all rounded bg-surface-900 px-3 py-2 border border-zinc-800">{setup.otpauth_url}</code>
              <CopyButton value={setup.otpauth_url} label="URL" />
            </div>
            <p className="text-xs text-zinc-500">Manual secret: <code className="mono-val text-zinc-300">{setup.secret}</code></p>
            <div className="flex gap-2">
              <input className="input mono-val !text-lg tracking-[0.4em] text-center max-w-[180px]" inputMode="numeric" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} placeholder="000000" />
              <button className="btn-primary" disabled={busy || code.length !== 6} onClick={confirmEnable}>{busy && <Spinner />}Enable</button>
            </div>
          </div>
        )}

        {status.enabled && (
          <div className="mt-4 flex gap-2">
            <input className="input mono-val !text-lg tracking-[0.4em] text-center max-w-[180px]" inputMode="numeric" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} placeholder="000000" />
            <button className="btn-primary !bg-rose-500 hover:!bg-rose-400" disabled={busy || code.length !== 6} onClick={disable}>{busy && <Spinner />}Disable</button>
          </div>
        )}

        {msg && <p role="alert" className="text-sm text-rose-400 mt-3">{msg}</p>}
      </div>
    </div>
  )
}

// ---------- Backup view ----------
function BackupView({ push }) {
  const [importText, setImportText] = useState('')
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)

  const doExport = async () => {
    setMsg('')
    try {
      const r = await api.get('/vault/export', { responseType: 'blob' })
      const url = URL.createObjectURL(r.data)
      const a = document.createElement('a')
      a.href = url
      a.download = 'credvault-backup.json'
      a.click()
      URL.revokeObjectURL(url)
      push('Backup downloaded')
    } catch (err) {
      setMsg(err.response?.data?.detail || 'Export failed')
    }
  }

  const doImport = async () => {
    setBusy(true); setMsg('')
    try {
      let items
      try {
        const parsed = JSON.parse(importText)
        items = Array.isArray(parsed) ? parsed : parsed.items
      } catch {
        setMsg('Invalid JSON')
        return
      }
      const r = await api.post('/vault/import', { items })
      push(`Imported ${r.data.imported} credential(s)`)
      setImportText('')
    } catch (err) {
      setMsg(err.response?.data?.detail || 'Import failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Backup</h1>
        <p className="text-sm text-zinc-500 mt-1">Export your vault to a JSON file, or restore from one. Backups are plaintext - store them safely.</p>
      </div>

      <div className="card p-5 max-w-xl">
        <p className="text-sm font-medium text-zinc-100">Export</p>
        <p className="text-xs text-zinc-500 mt-1 mb-3">Download all credentials as a JSON file for safe keeping.</p>
        <button onClick={doExport} className="btn-primary"><span className="w-4 h-4">{icons.download}</span>Download backup</button>
      </div>

      <div className="card p-5 max-w-xl">
        <p className="text-sm font-medium text-zinc-100">Import</p>
        <p className="text-xs text-zinc-500 mt-1 mb-3">Paste JSON (an array of {`{name, secret, url, username, description, category, favorite}`} objects) to restore or merge credentials.</p>
        <textarea className="input mono-val resize-none" rows={6} value={importText} onChange={(e) => setImportText(e.target.value)} placeholder='[{"name": "db", "secret": "pw", "category": "db"}]' />
        <div className="mt-3 flex items-center gap-3">
          <button className="btn-primary" disabled={busy || !importText.trim()} onClick={doImport}>{busy && <Spinner />}<span className="w-4 h-4">{icons.upload}</span>Import</button>
          {msg && <p role="alert" className="text-sm text-rose-400">{msg}</p>}
        </div>
      </div>
    </div>
  )
}

// ---------- Admin view (users + audit log) ----------
function AdminView({ push }) {
  const [tab, setTab] = useState('users')
  const [users, setUsers] = useState([])
  const [log, setLog] = useState([])
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)

  const loadUsers = useCallback(() => api.get('/users').then((r) => setUsers(r.data)).catch(() => {}), [])
  const loadLog = useCallback(() => api.get('/users/audit-log?limit=200').then((r) => setLog(r.data)).catch(() => {}), [])
  useEffect(() => { loadUsers() }, [loadUsers])
  useEffect(() => { if (tab === 'audit') loadLog() }, [tab, loadLog])

  const add = async (e) => {
    e.preventDefault(); setMsg('')
    try {
      await api.post('/users', { username, password })
      setUsername(''); setPassword(''); loadUsers(); push('User created')
    } catch (err) { setMsg(err.response?.data?.detail || 'Failed') }
  }

  const del = async (id, name) => {
    setBusy(true); setMsg('')
    try {
      await api.delete(`/users/${id}`); loadUsers(); push(`Deleted ${name}`)
    } catch (err) { setMsg(err.response?.data?.detail || 'Failed') } finally { setBusy(false) }
  }

  const resetVault = async (id, name) => {
    setBusy(true); setMsg('')
    try {
      await api.post(`/users/${id}/reset-vault`); loadUsers(); push(`Reset vault for ${name}`)
    } catch (err) { setMsg(err.response?.data?.detail || 'Failed') } finally { setBusy(false) }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Administration</h1>
          <p className="text-sm text-zinc-500 mt-1">Manage users and review the audit trail.</p>
        </div>
        <div className="flex gap-1">
          <button className={tab === 'users' ? 'btn-primary' : 'btn-ghost'} onClick={() => setTab('users')}>Users</button>
          <button className={tab === 'audit' ? 'btn-primary' : 'btn-ghost'} onClick={() => setTab('audit')}>Audit log</button>
        </div>
      </div>

      {msg && <p role="alert" className="text-sm text-rose-400">{msg}</p>}

      {tab === 'users' ? (
        <>
          <form onSubmit={add} className="card p-4 flex flex-col sm:flex-row gap-2 max-w-xl">
            <input className="input flex-1" placeholder="Username" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="off" />
            <input className="input flex-1" placeholder="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" />
            <button className="btn-primary shrink-0"><span className="w-4 h-4">{icons.plus}</span>Add</button>
          </form>
          <div className="card divide-y divide-zinc-800/70 max-w-xl">
            {users.map((u) => (
              <div key={u.id} className="px-4 py-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-zinc-200 truncate">{u.username}</p>
                    <p className="text-xs text-zinc-500">
                      {u.is_admin ? 'Administrator' : u.vault_initialized ? 'Vault configured' : 'No vault yet'}{u.mfa_enabled ? ' · 2FA on' : ''}
                    </p>
                  </div>
                  {!u.is_admin && (
                    <div className="flex items-center gap-2 shrink-0">
                      <button disabled={busy} onClick={() => { if (window.confirm(`Reset ${u.username}'s vault? Their credentials will be wiped.`)) resetVault(u.id, u.username) }} className="btn-ghost text-xs">Reset vault</button>
                      <button disabled={busy} onClick={() => { if (window.confirm(`Delete user ${u.username}?`)) del(u.id, u.username) }} className="btn-ghost !text-rose-400 text-xs">Delete</button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="card divide-y divide-zinc-800/70">
          {log.length === 0 ? (
            <div className="p-6 text-sm text-zinc-500 text-center">No audit events yet.</div>
          ) : (
            log.map((e) => (
              <div key={e.id} className="px-4 py-2.5 flex items-center gap-3">
                <span className={`shrink-0 text-[10px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded ${e.action.includes('fail') || e.action.includes('delete') || e.action.includes('revoke') ? 'bg-rose-500/15 text-rose-300' : 'bg-zinc-700/60 text-zinc-300'}`}>{e.action}</span>
                <div className="min-w-0 flex-1">
                  <p className="text-xs text-zinc-300 truncate">{e.username || 'system'} <span className="text-zinc-600">{e.detail}</span></p>
                </div>
                <div className="shrink-0 text-right">
                  <p className="text-[11px] text-zinc-500">{new Date(e.created_at).toLocaleString()}</p>
                  {e.ip && <p className="text-[10px] text-zinc-600">{e.ip}</p>}
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

// ---------- Credentials view ----------
function CredentialsView({ creds, loading, error, reload, onAdd, onEdit, onDelete, onToggleFav }) {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState('all') // all | favorites
  const [category, setCategory] = useState('')

  const categories = useMemo(() => [...new Set(creds.map((c) => c.category).filter(Boolean))], [creds])
  const filtered = creds.filter((c) => {
    if (filter === 'favorites' && !c.favorite) return false
    if (category && c.category !== category) return false
    const hay = (c.name + ' ' + (c.username || '') + ' ' + (c.url || '') + ' ' + (c.category || '')).toLowerCase()
    return hay.includes(search.toLowerCase())
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Credentials</h1>
          <p className="text-sm text-zinc-500 mt-1">{creds.length} {creds.length === 1 ? 'entry' : 'entries'} in your vault</p>
        </div>
        <button onClick={onAdd} className="btn-primary"><span className="w-4 h-4">{icons.plus}</span>Add credential</button>
      </div>

      <div className="relative max-w-md">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4">{icons.search}</span>
        <input className="input !pl-9" placeholder="Search credentials" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button onClick={() => setFilter('all')} className={`text-xs px-3 py-1.5 rounded-full border transition ${filter === 'all' ? 'border-emerald-500/60 bg-emerald-500/10 text-emerald-200' : 'border-zinc-700 text-zinc-400 hover:text-zinc-200'}`}>All</button>
        <button onClick={() => setFilter('favorites')} className={`inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition ${filter === 'favorites' ? 'border-amber-500/60 bg-amber-500/10 text-amber-200' : 'border-zinc-700 text-zinc-400 hover:text-zinc-200'}`}><span className="w-3 h-3">{icons.star}</span>Favorites</button>
        {categories.map((c) => (
          <button key={c} onClick={() => setCategory(category === c ? '' : c)} className={`inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border transition ${category === c ? 'border-emerald-500/60 bg-emerald-500/10 text-emerald-200' : 'border-zinc-700 text-zinc-400 hover:text-zinc-200'}`}><span className="w-3 h-3">{icons.tag}</span>{c}</button>
        ))}
      </div>

      {error && <ErrorBanner message={error} onRetry={reload} />}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">{[0, 1, 2, 3].map((i) => (
          <div key={i} className="card p-4 space-y-3"><div className="flex items-center gap-3"><div className="skeleton h-9 w-9 rounded-lg" /><div className="space-y-2 flex-1"><div className="skeleton h-4 w-2/3" /><div className="skeleton h-3 w-1/3" /></div></div><div className="skeleton h-9 w-full" /></div>
        ))}</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-20 animate-rise">
          <div className="mx-auto w-12 h-12 rounded-xl bg-surface-800 border border-zinc-700/60 text-emerald-400 flex items-center justify-center mb-4"><span className="w-6 h-6">{icons.key}</span></div>
          <p className="text-sm font-medium text-zinc-200">{search || filter !== 'all' || category ? 'No matches' : 'No credentials yet'}</p>
          <p className="text-sm text-zinc-500 mt-1">{search || filter !== 'all' || category ? 'Try adjusting filters.' : 'Add your first credential to get started.'}</p>
          {!search && filter === 'all' && !category && <button onClick={onAdd} className="btn-primary mt-5"><span className="w-4 h-4">{icons.plus}</span>Add credential</button>}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map((c) => (
            <CredentialCard key={c.id} cred={c} onEdit={() => onEdit(c)} onDelete={() => onDelete(c)} onToggleFav={() => onToggleFav(c)} />
          ))}
        </div>
      )}
    </div>
  )
}

// ---------- Dashboard with sidebar ----------
function Dashboard({ username, isAdmin, onLock, onLogout, push, dark, onToggleDark }) {
  const [view, setView] = useState('credentials')
  const [creds, setCreds] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [modal, setModal] = useState(null)
  const [confirm, setConfirm] = useState(null)

  const load = useCallback(() => {
    setLoading(true); setError('')
    api.get('/vault/credentials').then((r) => setCreds(r.data)).catch((e) => setError(e.response?.data?.detail || 'Failed to load credentials')).finally(() => setLoading(false))
  }, [])
  useEffect(load, [load])

  const save = async (form) => {
    if (modal?.cred) await api.put(`/vault/credentials/${modal.cred.id}`, form)
    else await api.post('/vault/credentials', form)
    load()
    push(modal?.cred ? 'Credential updated' : 'Credential added')
  }

  const doDelete = async (id) => {
    await api.delete(`/vault/credentials/${id}`)
    load()
    push('Credential deleted')
  }

  const toggleFav = async (cred) => {
    const next = { ...cred, favorite: !cred.favorite }
    await api.put(`/vault/credentials/${cred.id}`, {
      name: cred.name, secret: cred.secret, url: cred.url, username: cred.username,
      description: cred.description, category: cred.category, favorite: next.favorite,
    })
    load()
  }

  const navItems = [
    { id: 'credentials', label: 'Credentials', icon: icons.lock },
    { id: 'tokens', label: 'API tokens', icon: icons.key },
    { id: 'security', label: 'Security', icon: icons.shield },
    { id: 'backup', label: 'Backup', icon: icons.download },
    ...(isAdmin ? [{ id: 'admin', label: 'Admin', icon: icons.users }] : []),
  ]

  return (
    <div className="min-h-[100dvh] flex">
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-zinc-800/80 bg-surface-950/60 sticky top-0 h-[100dvh]">
        <div className="flex items-center gap-2.5 px-5 h-16 border-b border-zinc-800/80">
          <Logo size={30} />
          <span className="font-semibold tracking-tight">CredVault</span>
        </div>
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => (
            <button key={item.id} onClick={() => setView(item.id)} className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition ${view === item.id ? 'bg-emerald-500/10 text-emerald-200' : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/60'}`}>
              <span className="w-4 h-4">{item.icon}</span>{item.label}
            </button>
          ))}
        </nav>
        <div className="p-3 border-t border-zinc-800/80 space-y-1">
          <div className="px-3 py-2 text-sm text-zinc-300 truncate flex items-center gap-2"><span className="w-4 h-4">{icons.user}</span>{username}</div>
          <button onClick={onToggleDark} className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/60"><span className="w-4 h-4">{dark ? icons.sun : icons.moon}</span>{dark ? 'Light mode' : 'Dark mode'}</button>
          <button onClick={onLock} className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/60"><span className="w-4 h-4">{icons.vault}</span>Lock vault</button>
          <button onClick={onLogout} className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/60"><span className="w-4 h-4">{icons.logout}</span>Sign out</button>
        </div>
      </aside>

      {/* mobile top bar */}
      <div className="md:hidden sticky top-0 z-40 border-b border-zinc-800/80 bg-surface-950/85 backdrop-blur w-full">
        <div className="flex items-center justify-between h-14 px-4">
          <div className="flex items-center gap-2"><Logo size={28} /><span className="font-semibold tracking-tight">CredVault</span></div>
          <div className="flex gap-1">
            <button onClick={onToggleDark} className="btn-ghost !px-2"><span className="w-4 h-4">{dark ? icons.sun : icons.moon}</span></button>
            <button onClick={onLock} className="btn-ghost !px-2"><span className="w-4 h-4">{icons.vault}</span></button>
            <button onClick={onLogout} className="btn-ghost !px-2"><span className="w-4 h-4">{icons.logout}</span></button>
          </div>
        </div>
        <div className="flex gap-1 overflow-x-auto px-2 pb-2">
          {navItems.map((item) => (
            <button key={item.id} onClick={() => setView(item.id)} className={`shrink-0 inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full border ${view === item.id ? 'border-emerald-500/60 bg-emerald-500/10 text-emerald-200' : 'border-zinc-700 text-zinc-400'}`}><span className="w-3 h-3">{item.icon}</span>{item.label}</button>
          ))}
        </div>
      </div>

      <main className="flex-1 min-w-0">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
          {view === 'credentials' && (
            <CredentialsView creds={creds} loading={loading} error={error} reload={load}
              onAdd={() => setModal({})} onEdit={(c) => setModal({ cred: c })}
              onDelete={(c) => setConfirm({ title: 'Delete credential', message: `Delete "${c.name}"?`, onConfirm: () => doDelete(c.id) })}
              onToggleFav={toggleFav} />
          )}
          {view === 'tokens' && <TokensView push={push} />}
          {view === 'security' && <SecurityView push={push} />}
          {view === 'backup' && <BackupView push={push} />}
          {view === 'admin' && <AdminView push={push} />}
        </div>
      </main>

      {modal && <CredentialModal initial={modal.cred} onClose={() => setModal(null)} onSave={save} />}
      {confirm && <ConfirmModal title={confirm.title} message={confirm.message} onConfirm={async () => { await confirm.onConfirm(); setConfirm(null) }} onClose={() => setConfirm(null)} />}
    </div>
  )
}

// ---------- App root ----------
export default function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem('cv_token'))
  const [unlocked, setUnlocked] = useState(!!localStorage.getItem('cv_vault_token'))
  const [username, setUsername] = useState('')
  const [isAdmin, setIsAdmin] = useState(false)
  const { push, toastHost } = useToasts()

  const [dark, setDark] = useState(() => {
    const stored = localStorage.getItem('cv_theme')
    if (stored) return stored === 'dark'
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  })
  useEffect(() => {
    document.documentElement.classList.toggle('dark', dark)
    localStorage.setItem('cv_theme', dark ? 'dark' : 'light')
  }, [dark])

  useEffect(() => {
    if (!authed) return
    api.get('/auth/me').then((r) => { setUsername(r.data.username); setIsAdmin(r.data.is_admin) }).catch((err) => {
      if (err.response?.status === 401) { clearSession(); setAuthed(false); setUnlocked(false) }
    })
  }, [authed])

  // auto-lock after inactivity
  useEffect(() => {
    if (!unlocked) return
    let timer
    const reset = () => {
      clearTimeout(timer)
      timer = setTimeout(() => { clearSession(); setUnlocked(false); push('Vault locked due to inactivity', 'error') }, 10 * 60 * 1000)
    }
    const events = ['mousemove', 'keydown', 'click', 'scroll']
    events.forEach((ev) => window.addEventListener(ev, reset))
    reset()
    return () => { clearTimeout(timer); events.forEach((ev) => window.removeEventListener(ev, reset)) }
  }, [unlocked, push])

  const handleLogin = (data) => {
    setUsername(data.username)
    setIsAdmin(!!data.is_admin)
    setAuthed(true)
    setUnlocked(false)
  }
  const logout = () => { clearSession(); setAuthed(false); setUnlocked(false) }
  const lock = async () => {
    try { await api.post('/vault/lock') } catch {}
    setSession(null, '')
    setUnlocked(false)
  }

  return (
    <>
      {!authed ? <LoginPage onLogin={handleLogin} />
        : !unlocked ? <UnlockPage username={username} onUnlocked={() => setUnlocked(true)} onLogout={logout} />
          : <Dashboard username={username} isAdmin={isAdmin} onLock={lock} onLogout={logout} push={push} dark={dark} onToggleDark={() => setDark(!dark)} />}
      {toastHost}
    </>
  )
}
