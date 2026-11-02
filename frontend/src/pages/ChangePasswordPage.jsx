import { useState } from 'react'
import api, { errorMessage } from '../lib/api.js'
import { Field, OtpInput, PasswordInput, StrengthMeter } from '../components/ui.jsx'
import { AuthCard, AuthLayout, SignedInAs } from './AuthLayout.jsx'

/** Shown when an admin reset (or created) the account with a temporary password. */
export default function ChangePasswordPage({ username, mfaEnabled, onChanged, onLogout }) {
  const [form, setForm] = useState({ current: '', next: '', confirm: '', code: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: typeof e === 'string' ? e : e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (form.next !== form.confirm) return setError('New passwords do not match')
    setLoading(true)
    try {
      const { data } = await api.post('/auth/change-password', { current_password: form.current, new_password: form.next, mfa_code: form.code })
      onChanged(data)
    } catch (err) {
      setError(errorMessage(err, 'Could not change password'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <SignedInAs username={username} note="Temporary password" onLogout={onLogout} />
      <AuthCard title="Choose a new password" onSubmit={submit} error={error} loading={loading} submitLabel="Set password"
        subtitle="Your account uses a temporary password. Pick a permanent one — it signs you in; your vault master password is separate.">
        <Field label="Temporary password" htmlFor="cp">
          <PasswordInput id="cp" value={form.current} onChange={set('current')} autoFocus />
        </Field>
        <Field label="New password" htmlFor="np">
          <PasswordInput id="np" value={form.next} onChange={set('next')} autoComplete="new-password" />
          <StrengthMeter password={form.next} />
        </Field>
        <Field label="Confirm new password" htmlFor="np2">
          <PasswordInput id="np2" value={form.confirm} onChange={set('confirm')} autoComplete="new-password" />
        </Field>
        {mfaEnabled && (
          <Field label="Authentication code" htmlFor="mfa" hint="Required because 2FA is on.">
            <OtpInput id="mfa" value={form.code} onChange={set('code')} />
          </Field>
        )}
      </AuthCard>
    </AuthLayout>
  )
}
