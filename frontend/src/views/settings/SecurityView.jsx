import { useEffect, useState } from 'react'
import api, { errorMessage, session } from '../../lib/api.js'
import { Icon } from '../../components/icons.jsx'
import { CopyButton, Field, FormError, OtpInput, PageHeader, PasswordInput, Section, Spinner, StrengthMeter, useToast } from '../../components/ui.jsx'

function TwoFactor({ onChange }) {
  const toast = useToast()
  const [enabled, setEnabled] = useState(null)
  const [setup, setSetup] = useState(null)
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { api.get('/auth/2fa/status').then((r) => setEnabled(r.data.enabled)).catch(() => setEnabled(false)) }, [])
  useEffect(() => { if (enabled !== null) onChange(enabled) }, [enabled, onChange])

  const run = async (fn) => {
    setBusy(true); setError('')
    try { await fn() } catch (e) { setError(errorMessage(e)) } finally { setBusy(false) }
  }
  const start = () => run(async () => setSetup((await api.post('/auth/2fa/setup')).data))
  const enable = () => run(async () => { await api.post('/auth/2fa/verify', { code }); setEnabled(true); setSetup(null); setCode(''); toast('Two-factor authentication enabled') })
  const disable = () => run(async () => { await api.post('/auth/2fa/disable', { code }); setEnabled(false); setCode(''); toast('Two-factor authentication disabled') })

  return (
    <Section title="Two-factor authentication" description="Require a code from an authenticator app (1Password, Aegis, Google Authenticator…) when signing in."
      aside={enabled !== null && <span className={enabled ? 'badge-ok' : 'badge-neutral'}>{enabled ? 'On' : 'Off'}</span>}>
      {enabled === false && !setup && (
        <button className="btn-primary" onClick={start} disabled={busy}>{busy ? <Spinner /> : <Icon.shieldCheck className="w-4 h-4" />}Set up 2FA</button>
      )}
      {setup && (
        <ol className="space-y-4 text-[13.5px]">
          <li>
            <p className="font-medium">1. Add this key to your authenticator</p>
            <div className="mt-2 flex items-center gap-2">
              <code className="mono flex-1 min-w-0 break-all select-all rounded-lg bg-sunken px-3 py-2 tracking-wider">{setup.secret.match(/.{1,4}/g).join(' ')}</code>
              <CopyButton value={setup.secret} label="setup key" />
            </div>
            <p className="hint">Or paste the full <button type="button" className="text-accent hover:underline" onClick={() => navigator.clipboard.writeText(setup.otpauth_url).then(() => toast('otpauth link copied'))}>otpauth:// link</button> into apps that support it.</p>
          </li>
          <li>
            <p className="font-medium mb-2">2. Enter the 6-digit code it shows</p>
            <div className="flex gap-2 max-w-xs"><OtpInput value={code} onChange={setCode} autoFocus />
              <button className="btn-primary" onClick={enable} disabled={busy || code.length !== 6}>{busy && <Spinner />}Verify</button></div>
          </li>
        </ol>
      )}
      {enabled && (
        <div className="flex gap-2 max-w-xs">
          <OtpInput value={code} onChange={setCode} />
          <button className="btn-danger" onClick={disable} disabled={busy || code.length !== 6}>{busy && <Spinner />}Turn off</button>
        </div>
      )}
      <FormError>{error}</FormError>
    </Section>
  )
}

function ChangePassword({ mfaEnabled }) {
  const toast = useToast()
  const [form, setForm] = useState({ current: '', next: '', confirm: '', code: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: typeof e === 'string' ? e : e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    if (form.next !== form.confirm) return setError('New passwords do not match')
    setBusy(true); setError('')
    try {
      const { data } = await api.post('/auth/change-password', { current_password: form.current, new_password: form.next, mfa_code: form.code })
      session.setToken(data.token)
      // the server revoked every session and unlocked vault — re-lock locally too
      window.dispatchEvent(new CustomEvent('cv:vault-locked', { detail: 'Password changed — unlock your vault again' }))
      toast('Password changed. Other sessions were signed out.')
    } catch (err) { setError(errorMessage(err)) } finally { setBusy(false) }
  }

  return (
    <Section title="Login password" description="Used to sign in. Your vault master password is separate and never leaves this flow.">
      <form onSubmit={submit} className="grid sm:grid-cols-2 gap-4 max-w-xl">
        <div className="sm:col-span-2"><Field label="Current password" htmlFor="sp-cur"><PasswordInput id="sp-cur" value={form.current} onChange={set('current')} /></Field></div>
        <Field label="New password" htmlFor="sp-new"><PasswordInput id="sp-new" value={form.next} onChange={set('next')} autoComplete="new-password" /><StrengthMeter password={form.next} /></Field>
        <Field label="Confirm" htmlFor="sp-con"><PasswordInput id="sp-con" value={form.confirm} onChange={set('confirm')} autoComplete="new-password" /></Field>
        {mfaEnabled && <Field label="Authentication code" htmlFor="sp-mfa"><OtpInput id="sp-mfa" value={form.code} onChange={set('code')} /></Field>}
        <div className="sm:col-span-2"><FormError>{error}</FormError>
          <button className="btn-primary mt-1" disabled={busy || !form.current || !form.next}>{busy && <Spinner />}Change password</button></div>
      </form>
    </Section>
  )
}

export default function SecurityView({ mfaEnabled: initialMfa }) {
  const [mfaEnabled, setMfaEnabled] = useState(initialMfa)
  return (
    <div className="max-w-3xl mx-auto px-5 sm:px-8 py-8 space-y-5">
      <PageHeader title="Security" subtitle="Protect how you sign in." />
      <TwoFactor onChange={setMfaEnabled} />
      <ChangePassword mfaEnabled={mfaEnabled} />
    </div>
  )
}
