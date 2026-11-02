import { useCallback, useEffect, useState } from 'react'
import api, { errorMessage } from '../../lib/api.js'
import { timeAgo } from '../../lib/secrets.js'
import { Icon } from '../../components/icons.jsx'
import {
  CopyButton, ErrorBanner, FormError, ListSkeleton, Monogram, PageHeader, PasswordInput, Section, Spinner, cx, useConfirm, useToast,
} from '../../components/ui.jsx'

const RISKY = /fail|delete|revoke|reset|disabled|unshare|remove|export/

function Users() {
  const toast = useToast()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ username: '', password: '' })
  const [formError, setFormError] = useState('')
  const [busy, setBusy] = useState(false)
  const [temp, setTemp] = useState(null)
  const [dialog, confirm] = useConfirm()

  const load = useCallback(async () => {
    try { setUsers((await api.get('/users')).data); setError('') } catch (e) { setError(errorMessage(e)) } finally { setLoading(false) }
  }, [])
  useEffect(() => { load() }, [load])

  const add = async (e) => {
    e.preventDefault()
    setBusy(true); setFormError('')
    try {
      await api.post('/users', form)
      toast(`Created ${form.username} — they’ll pick a new password at first sign-in`)
      setForm({ username: '', password: '' })
      load()
    } catch (err) { setFormError(errorMessage(err)) } finally { setBusy(false) }
  }

  const actions = (u) => ({
    resetPassword: () => confirm({
      title: `Reset ${u.username}’s password`, tone: 'primary', confirmLabel: 'Reset password',
      message: 'They’ll be signed out everywhere and must choose a new password with the temporary one. Their vault is untouched.',
      onConfirm: async () => { setTemp((await api.post(`/users/${u.id}/reset-password`)).data); load() },
    }),
    resetVault: () => confirm({
      title: `Reset ${u.username}’s vault`, confirmLabel: 'Wipe vault',
      message: 'Use only if they lost their master password. All of their items, API tokens and shares they received are permanently deleted.',
      onConfirm: async () => { await api.post(`/users/${u.id}/reset-vault`); toast('Vault reset'); load() },
    }),
    remove: () => confirm({
      title: `Delete ${u.username}`, confirmLabel: 'Delete user',
      message: 'The account, its vault and everything shared to or from it will be permanently deleted.',
      onConfirm: async () => { await api.delete(`/users/${u.id}`); toast(`Deleted ${u.username}`); load() },
    }),
  })

  return (
    <>
      {temp && (
        <div className="mb-5 rounded-2xl border border-warn/30 bg-warn-soft p-4 animate-rise">
          <p className="text-[13px] font-medium text-warn">Temporary password for {temp.username} — hand it over securely. It’s shown only once.</p>
          <div className="mt-3 flex items-center gap-2">
            <code className="mono flex-1 min-w-0 break-all select-all rounded-lg bg-surface px-3 py-2">{temp.temp_password}</code>
            <CopyButton value={temp.temp_password} label="temporary password" sensitive />
            <button className="icon-btn" onClick={() => setTemp(null)} aria-label="Dismiss"><Icon.close /></button>
          </div>
        </div>
      )}

      <Section title="Add a user" description="Admin-created accounts start with a temporary password that must be changed at first sign-in.">
        <form onSubmit={add} className="flex flex-col sm:flex-row gap-2">
          <input className="input flex-1" placeholder="Username" value={form.username} autoComplete="off" aria-label="Username"
            onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))} />
          <div className="flex-1"><PasswordInput placeholder="Temporary password" value={form.password} autoComplete="new-password" aria-label="Temporary password"
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))} /></div>
          <button className="btn-primary" disabled={busy || !form.username || !form.password}>{busy ? <Spinner /> : <Icon.plus className="w-4 h-4" />}Add</button>
        </form>
        <FormError>{formError}</FormError>
      </Section>

      <Section className="mt-5 !p-0 overflow-hidden">
        <h2 className="px-5 sm:px-6 pt-5 pb-3 text-[15px] font-semibold">Users{users.length ? ` (${users.length})` : ''}</h2>
        {error && <div className="px-5 sm:px-6 pb-3"><ErrorBanner message={error} onRetry={load} /></div>}
        {loading ? <ListSkeleton rows={3} /> : (
          <ul className="divide-y divide-line border-t border-line">
            {users.map((u) => {
              const a = actions(u)
              return (
                <li key={u.id} className="flex flex-wrap items-center gap-3 px-5 sm:px-6 py-3.5">
                  <Monogram name={u.username} size={34} />
                  <div className="min-w-0 flex-1">
                    <p className="flex items-center gap-2 font-medium"><span className="truncate">{u.username}</span>
                      {u.is_admin && <span className="badge-accent">admin</span>}</p>
                    <p className="flex flex-wrap gap-x-3 text-[12px] text-subtle">
                      <span>{u.vault_initialized ? 'Vault set up' : 'No vault yet'}</span>
                      <span className={u.mfa_enabled ? 'text-ok' : ''}>{u.mfa_enabled ? '2FA on' : '2FA off'}</span>
                      {u.created_at && <span>joined {timeAgo(u.created_at)}</span>}
                    </p>
                  </div>
                  {!u.is_admin && (
                    <div className="flex gap-1">
                      <button className="btn-ghost btn-sm" onClick={a.resetPassword}>Reset password</button>
                      <button className="btn-ghost btn-sm" onClick={a.resetVault}>Reset vault</button>
                      <button className="icon-btn hover:!text-danger" onClick={a.remove} title="Delete user" aria-label={`Delete ${u.username}`}><Icon.trash /></button>
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </Section>
      {dialog}
    </>
  )
}

function AuditLog() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try { setRows((await api.get('/users/audit-log', { params: { limit: 500 } })).data); setError('') } catch (e) { setError(errorMessage(e)) } finally { setLoading(false) }
  }, [])
  useEffect(() => { load() }, [load])

  const q = query.toLowerCase()
  const visible = rows.filter((r) => !q || [r.action, r.username, r.detail, r.ip].some((v) => v?.toLowerCase().includes(q)))

  return (
    <Section className="!p-0 overflow-hidden">
      <div className="flex items-center gap-2 p-4 border-b border-line">
        <div className="relative flex-1">
          <Icon.search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-subtle" />
          <input className="input !pl-9 !py-2" placeholder="Filter by action, user, IP…" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Filter audit log" />
        </div>
        <button className="icon-btn" onClick={load} title="Refresh" aria-label="Refresh"><Icon.refresh /></button>
      </div>
      {error && <div className="p-4"><ErrorBanner message={error} onRetry={load} /></div>}
      {loading ? <ListSkeleton rows={6} /> : (
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead className="text-left text-[11.5px] uppercase tracking-wide text-subtle">
              <tr><th className="px-4 py-2.5 font-medium">Event</th><th className="px-4 py-2.5 font-medium">User</th><th className="px-4 py-2.5 font-medium hidden md:table-cell">Detail</th><th className="px-4 py-2.5 font-medium hidden sm:table-cell">IP</th><th className="px-4 py-2.5 font-medium text-right">When</th></tr>
            </thead>
            <tbody className="divide-y divide-line">
              {visible.map((r) => (
                <tr key={r.id} className="hover:bg-sunken/50">
                  <td className="px-4 py-2.5"><span className={cx(RISKY.test(r.action) ? 'badge-danger' : 'badge-neutral', 'font-mono')}>{r.action}</span></td>
                  <td className="px-4 py-2.5 whitespace-nowrap">{r.username || <span className="text-subtle">—</span>}</td>
                  <td className="px-4 py-2.5 text-muted hidden md:table-cell max-w-[280px] truncate" title={r.detail}>{r.detail}</td>
                  <td className="px-4 py-2.5 mono text-subtle hidden sm:table-cell">{r.ip}</td>
                  <td className="px-4 py-2.5 text-right text-subtle whitespace-nowrap" title={new Date(r.created_at).toLocaleString()}>{timeAgo(r.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {visible.length === 0 && <p className="p-8 text-center text-muted">No events.</p>}
        </div>
      )}
    </Section>
  )
}

export default function AdminView() {
  const [tab, setTab] = useState('users')
  return (
    <div className="max-w-4xl mx-auto px-5 sm:px-8 py-8">
      <PageHeader title="Administration" subtitle="Manage accounts and review activity. Admins can never read vault contents."
        actions={
          <div className="inline-flex rounded-xl bg-sunken p-1" role="tablist">
            {[['users', 'Users', Icon.users], ['audit', 'Audit log', Icon.activity]].map(([id, label, I]) => (
              <button key={id} role="tab" aria-selected={tab === id} onClick={() => setTab(id)}
                className={cx('btn btn-sm', tab === id ? 'bg-surface text-ink shadow-card' : 'text-muted hover:text-ink')}>
                <I className="w-4 h-4" />{label}
              </button>
            ))}
          </div>
        } />
      {tab === 'users' ? <Users /> : <AuditLog />}
    </div>
  )
}
