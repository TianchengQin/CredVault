import { useCallback, useEffect, useState } from 'react'
import api, { errorMessage } from '../../lib/api.js'
import { timeAgo } from '../../lib/secrets.js'
import { Icon } from '../../components/icons.jsx'
import { CopyButton, EmptyState, ErrorBanner, FormError, ListSkeleton, PageHeader, Section, Spinner, useConfirm, useToast } from '../../components/ui.jsx'

export default function TokensView() {
  const toast = useToast()
  const [tokens, setTokens] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [form, setForm] = useState({ name: '', permission: 'read' })
  const [created, setCreated] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [dialog, confirm] = useConfirm()

  const load = useCallback(async () => {
    setLoadError('')
    try { setTokens((await api.get('/tokens')).data) } catch (e) { setLoadError(errorMessage(e)) } finally { setLoading(false) }
  }, [])
  useEffect(() => { load() }, [load])

  const create = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) return setError('Give the token a name')
    setBusy(true); setError(''); setCreated(null)
    try {
      setCreated((await api.post('/tokens', form)).data)
      setForm({ name: '', permission: 'read' })
      load()
    } catch (err) { setError(errorMessage(err)) } finally { setBusy(false) }
  }

  const revoke = (t) => confirm({
    title: 'Revoke token',
    message: `Anything using “${t.name}” will immediately lose access.`,
    confirmLabel: 'Revoke',
    onConfirm: async () => { await api.delete(`/tokens/${t.id}`); await load(); toast('Token revoked') },
  })

  return (
    <div className="max-w-3xl mx-auto px-5 sm:px-8 py-8">
      <PageHeader title="API tokens" subtitle="Give scripts and AI agents scoped access to your vault via the REST API or the MCP server." />

      {created && (
        <div className="mb-5 rounded-2xl border border-ok/30 bg-ok-soft p-4 animate-rise">
          <p className="flex items-center gap-2 text-[13px] font-medium text-ok"><Icon.check className="w-4 h-4" />Token “{created.name}” created — copy it now, it won’t be shown again.</p>
          <div className="mt-3 flex items-center gap-2">
            <code className="mono flex-1 min-w-0 break-all select-all rounded-lg bg-surface px-3 py-2">{created.token}</code>
            <CopyButton value={created.token} label="token" sensitive />
            <button className="icon-btn" onClick={() => setCreated(null)} aria-label="Dismiss"><Icon.close /></button>
          </div>
        </div>
      )}

      <Section title="Create a token" description="Read tokens can list and fetch secrets. Write tokens can also create, update and delete. Tokens can never manage other tokens or export your vault.">
        <form onSubmit={create} className="flex flex-col sm:flex-row gap-2">
          <input className="input flex-1" placeholder="Name, e.g. ci-deploy" value={form.name} maxLength={100}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} aria-label="Token name" />
          <select className="input sm:w-36" value={form.permission} onChange={(e) => setForm((f) => ({ ...f, permission: e.target.value }))} aria-label="Permission">
            <option value="read">Read only</option>
            <option value="write">Read & write</option>
          </select>
          <button className="btn-primary" disabled={busy}>{busy ? <Spinner /> : <Icon.plus className="w-4 h-4" />}Create</button>
        </form>
        <FormError>{error}</FormError>
      </Section>

      <Section className="mt-5 !p-0 overflow-hidden">
        <h2 className="px-5 sm:px-6 pt-5 pb-3 text-[15px] font-semibold">Active tokens</h2>
        {loadError && <div className="px-5 sm:px-6 pb-3"><ErrorBanner message={loadError} onRetry={load} /></div>}
        {loading ? <ListSkeleton rows={2} /> : tokens.length === 0 ? (
          <EmptyState icon={Icon.terminal} title="No tokens yet">Create one above to connect an agent.</EmptyState>
        ) : (
          <ul className="divide-y divide-line border-t border-line">
            {tokens.map((t) => (
              <li key={t.id} className="flex items-center gap-3 px-5 sm:px-6 py-3.5">
                <span className="grid place-items-center w-9 h-9 rounded-xl bg-sunken text-muted"><Icon.key className="w-4 h-4" /></span>
                <div className="min-w-0 flex-1">
                  <p className="flex items-center gap-2 font-medium"><span className="truncate">{t.name}</span>
                    <span className={t.permission === 'write' ? 'badge-warn' : 'badge-neutral'}>{t.permission}</span></p>
                  <p className="text-[12px] text-subtle">Created {timeAgo(t.created_at)} · {t.last_used_at ? `last used ${timeAgo(t.last_used_at)}` : 'never used'}</p>
                </div>
                <button className="btn-danger-ghost btn-sm" onClick={() => revoke(t)}>Revoke</button>
              </li>
            ))}
          </ul>
        )}
      </Section>
      {dialog}
    </div>
  )
}
