import { useEffect, useState } from 'react'
import api, { errorMessage } from '../lib/api.js'
import { Icon } from '../components/icons.jsx'
import { Field, PasswordInput, Skeleton, StrengthMeter } from '../components/ui.jsx'
import { AuthCard, AuthLayout, SignedInAs } from './AuthLayout.jsx'

export default function UnlockPage({ username, onUnlocked, onLogout }) {
  const [mode, setMode] = useState(null) // setup | unlock
  const [minLength, setMinLength] = useState(12)
  const [master, setMaster] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.get('/vault/status').then((r) => setMode(r.data.setup_required ? 'setup' : 'unlock')).catch(() => setMode('unlock'))
    api.get('/auth/config').then((r) => setMinLength(r.data.min_master_password)).catch(() => {})
  }, [])

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (mode === 'setup') {
      if (master.length < minLength) return setError(`Use at least ${minLength} characters`)
      if (master !== confirm) return setError('Master passwords do not match')
    }
    setLoading(true)
    try {
      const { data } = await api.post(mode === 'setup' ? '/vault/setup' : '/vault/unlock', { master_password: master })
      if (data.setup_required) { setMode('setup'); return }
      onUnlocked(data)
    } catch (err) {
      setError(errorMessage(err, 'Unlock failed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <SignedInAs username={username} note="Signed in" onLogout={onLogout} />
      {!mode ? (
        <div className="space-y-4"><Skeleton className="h-7 w-2/3" /><Skeleton className="h-4 w-full" /><Skeleton className="h-11 w-full" /></div>
      ) : mode === 'setup' ? (
        <AuthCard title="Create your vault" onSubmit={submit} error={error} loading={loading} submitLabel="Create vault"
          subtitle="Your master password encrypts everything. It is never stored and cannot be recovered — not even by an admin.">
          <Field label="Master password" htmlFor="m">
            <PasswordInput id="m" value={master} onChange={(e) => setMaster(e.target.value)} autoComplete="new-password" autoFocus />
            <StrengthMeter password={master} />
          </Field>
          <Field label="Confirm master password" htmlFor="m2">
            <PasswordInput id="m2" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" />
          </Field>
          <p className="flex gap-2 rounded-lg bg-warn-soft px-3 py-2.5 text-[12.5px] text-warn">
            <Icon.alert className="w-4 h-4 shrink-0 mt-px" />Write it down somewhere safe. Forgetting it means losing this vault.
          </p>
        </AuthCard>
      ) : (
        <AuthCard title="Unlock your vault" onSubmit={submit} error={error} loading={loading} submitLabel="Unlock"
          subtitle="Enter your master password to decrypt your credentials for this session.">
          <Field label="Master password" htmlFor="m">
            <PasswordInput id="m" value={master} onChange={(e) => setMaster(e.target.value)} autoComplete="current-password" autoFocus />
          </Field>
          <p className="flex items-center gap-2 text-[12px] text-subtle"><Icon.clock className="w-3.5 h-3.5" />The vault locks itself after a period of inactivity.</p>
        </AuthCard>
      )}
    </AuthLayout>
  )
}
