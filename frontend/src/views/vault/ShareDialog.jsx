import { useCallback, useEffect, useState } from 'react'
import api, { errorMessage } from '../../lib/api.js'
import { Icon } from '../../components/icons.jsx'
import { Field, FormError, Modal, Monogram, Spinner, useToast } from '../../components/ui.jsx'

export default function ShareDialog({ cred, onClose }) {
  const toast = useToast()
  const [users, setUsers] = useState([])
  const [shares, setShares] = useState([])
  const [recipient, setRecipient] = useState('')
  const [permission, setPermission] = useState('read')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    const [u, s] = await Promise.all([api.get('/vault/shareable-users'), api.get(`/vault/credentials/${cred.id}/shares`)])
    setUsers(u.data)
    setShares(s.data)
  }, [cred.id])
  useEffect(() => { load().catch((e) => setError(errorMessage(e))) }, [load])

  const act = async (fn, message) => {
    setError('')
    try { await fn(); await load(); toast(message) } catch (e) { setError(errorMessage(e)) }
  }

  const add = async (e) => {
    e.preventDefault()
    if (!recipient) return
    setBusy(true)
    await act(() => api.post(`/vault/credentials/${cred.id}/share`, { username: recipient, permission }), `Shared with ${recipient}`)
    setRecipient('')
    setBusy(false)
  }

  const available = users.filter((u) => !shares.some((s) => s.recipient === u.username))

  return (
    <Modal title={`Share “${cred.name}”`} onClose={onClose}
      subtitle="The recipient gets a copy sealed to their own key — nobody else, including admins, can read it. Later edits on either side don’t sync.">
      <form onSubmit={add} className="flex flex-col sm:flex-row gap-2">
        <Field>
          <select className="input sm:w-56" value={recipient} onChange={(e) => setRecipient(e.target.value)} aria-label="Recipient">
            <option value="">{available.length ? 'Choose a person…' : 'Nobody left to share with'}</option>
            {available.map((u) => (
              <option key={u.id} value={u.username} disabled={!u.can_receive}>{u.username}{u.can_receive ? '' : ' (no vault yet)'}</option>
            ))}
          </select>
        </Field>
        <select className="input sm:w-32" value={permission} onChange={(e) => setPermission(e.target.value)} aria-label="Permission">
          <option value="read">Can view</option>
          <option value="write">Can edit</option>
        </select>
        <button className="btn-primary" disabled={busy || !recipient}>{busy ? <Spinner /> : <Icon.share className="w-4 h-4" />}Share</button>
      </form>
      <FormError>{error}</FormError>

      <div className="mt-6">
        <p className="text-[11.5px] font-medium uppercase tracking-wide text-subtle mb-2">People with access</p>
        {shares.length === 0 ? (
          <p className="text-[13px] text-muted py-3">Only you.</p>
        ) : (
          <ul className="divide-y divide-line rounded-xl border border-line">
            {shares.map((s) => (
              <li key={s.id} className="flex items-center gap-3 px-3 py-2.5">
                <Monogram name={s.recipient} size={30} />
                <span className="flex-1 min-w-0 truncate font-medium">{s.recipient}</span>
                <select className="input !w-auto !py-1.5 !text-[12.5px]" value={s.permission} aria-label={`Permission for ${s.recipient}`}
                  onChange={(e) => act(() => api.patch(`/vault/credentials/${cred.id}/shares/${s.id}`, { permission: e.target.value }), 'Permission updated')}>
                  <option value="read">Can view</option>
                  <option value="write">Can edit</option>
                </select>
                <button className="icon-btn hover:!text-danger" title="Remove access" aria-label={`Stop sharing with ${s.recipient}`}
                  onClick={() => act(() => api.delete(`/vault/credentials/${cred.id}/shares/${s.id}`), `Stopped sharing with ${s.recipient}`)}>
                  <Icon.close />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Modal>
  )
}
