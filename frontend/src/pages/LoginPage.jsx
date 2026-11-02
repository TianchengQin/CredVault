import { useEffect, useState } from 'react'
import api, { errorMessage } from '../lib/api.js'
import { Field, OtpInput, PasswordInput, StrengthMeter } from '../components/ui.jsx'
import { AuthCard, AuthLayout } from './AuthLayout.jsx'

export default function LoginPage({ onSession }) {
  const [mode, setMode] = useState('login') // login | register | mfa
  const [config, setConfig] = useState({ allow_registration: true, min_password: 10 })
  const [form, setForm] = useState({ username: '', password: '', confirm: '', code: '' })
  const [mfaToken, setMfaToken] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => { api.get('/auth/config').then((r) => setConfig(r.data)).catch(() => {}) }, [])

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: typeof e === 'string' ? e : e.target.value }))
  const switchTo = (m) => { setMode(m); setError(''); setForm((f) => ({ ...f, password: '', confirm: '', code: '' })) }

  const run = (fn) => async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try { await fn() } catch (err) { setError(errorMessage(err, 'Sign-in failed')) } finally { setLoading(false) }
  }

  const login = run(async () => {
    if (!form.username || !form.password) throw new Error('Enter your username and password')
    const { data } = await api.post('/auth/login', { username: form.username, password: form.password })
    if (data.mfa_required) { setMfaToken(data.mfa_token); setMode('mfa') } else onSession(data)
  })

  const register = run(async () => {
    if (form.password.length < config.min_password) throw new Error(`Password must be at least ${config.min_password} characters`)
    if (form.password !== form.confirm) throw new Error('Passwords do not match')
    const { data } = await api.post('/auth/register', { username: form.username, password: form.password })
    onSession(data)
  })

  const confirmMfa = run(async () => {
    const { data } = await api.post('/auth/2fa/confirm', { mfa_token: mfaToken, code: form.code })
    onSession(data)
  })

  if (mode === 'mfa') {
    return (
      <AuthLayout>
        <AuthCard title="Two-factor authentication" subtitle="Enter the 6-digit code from your authenticator app."
          onSubmit={confirmMfa} error={error} loading={loading} submitLabel="Verify"
          footer={<button className="text-accent hover:underline" onClick={() => { setMfaToken(''); switchTo('login') }}>Use a different account</button>}>
          <Field label="Authentication code" htmlFor="code"><OtpInput id="code" value={form.code} onChange={set('code')} autoFocus /></Field>
        </AuthCard>
      </AuthLayout>
    )
  }

  if (mode === 'register') {
    return (
      <AuthLayout>
        <AuthCard title="Create your account" subtitle="You'll get your own vault, encrypted with a master password you choose next."
          onSubmit={register} error={error} loading={loading} submitLabel="Create account"
          footer={<>Already have an account? <button className="text-accent font-medium hover:underline" onClick={() => switchTo('login')}>Sign in</button></>}>
          <Field label="Username" htmlFor="ru" hint="Letters, digits and . _ @ -">
            <input id="ru" className="input" value={form.username} onChange={set('username')} autoComplete="username" autoFocus />
          </Field>
          <Field label="Password" htmlFor="rp">
            <PasswordInput id="rp" value={form.password} onChange={set('password')} autoComplete="new-password" />
            <StrengthMeter password={form.password} />
          </Field>
          <Field label="Confirm password" htmlFor="rc">
            <PasswordInput id="rc" value={form.confirm} onChange={set('confirm')} autoComplete="new-password" />
          </Field>
        </AuthCard>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout>
      <AuthCard title="Welcome back" subtitle="Sign in to unlock your vault."
        onSubmit={login} error={error} loading={loading} submitLabel="Sign in"
        footer={config.allow_registration && <>New here? <button className="text-accent font-medium hover:underline" onClick={() => switchTo('register')}>Create an account</button></>}>
        <Field label="Username" htmlFor="u">
          <input id="u" className="input" value={form.username} onChange={set('username')} autoComplete="username" autoFocus />
        </Field>
        <Field label="Password" htmlFor="p">
          <PasswordInput id="p" value={form.password} onChange={set('password')} />
        </Field>
      </AuthCard>
    </AuthLayout>
  )
}
