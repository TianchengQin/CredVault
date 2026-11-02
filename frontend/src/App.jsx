import { useCallback, useEffect, useState } from 'react'
import api, { session } from './lib/api.js'
import { ToastProvider, Spinner, useToast } from './components/ui.jsx'
import { useIdleTimer, useTheme } from './hooks.js'
import ChangePasswordPage from './pages/ChangePasswordPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import UnlockPage from './pages/UnlockPage.jsx'
import Shell from './Shell.jsx'

const IDLE_KEY = 'cv_idle'

/**
 * Screen state machine:
 *   signed-out -> (must change password) -> locked -> unlocked
 */
function Root() {
  const toast = useToast()
  const [theme, toggleTheme] = useTheme()
  const [user, setUser] = useState(null)            // profile from /auth/me
  const [booting, setBooting] = useState(!!session.token)
  const [unlocked, setUnlocked] = useState(!!session.vaultToken)
  const [idleSeconds, setIdleSeconds] = useState(() => +sessionStorage.getItem(IDLE_KEY) || 900)

  const signOut = useCallback(async (message) => {
    if (session.vaultToken) api.post('/vault/lock').catch(() => {})
    session.clear()
    setUser(null)
    setUnlocked(false)
    if (typeof message === 'string') toast(message, 'error')
  }, [toast])

  const lock = useCallback(async (message) => {
    if (session.vaultToken) await api.post('/vault/lock').catch(() => {})
    session.setVaultToken('')
    setUnlocked(false)
    if (typeof message === 'string') toast(message, 'error')
  }, [toast])

  // restore an existing tab session
  useEffect(() => {
    if (!session.token) return
    api.get('/auth/me').then((r) => setUser(r.data)).catch(() => session.clear()).finally(() => setBooting(false))
  }, [])

  // server-side signals from the API client
  useEffect(() => {
    const onSignedOut = (e) => signOut(e.detail || 'Your session ended — please sign in again')
    const onLocked = (e) => { session.setVaultToken(''); setUnlocked(false); if (e.detail) toast(e.detail, 'error') }
    window.addEventListener('cv:signed-out', onSignedOut)
    window.addEventListener('cv:vault-locked', onLocked)
    return () => { window.removeEventListener('cv:signed-out', onSignedOut); window.removeEventListener('cv:vault-locked', onLocked) }
  }, [signOut, toast])

  const idleDeadline = useIdleTimer(unlocked, idleSeconds, () => lock('Vault locked after inactivity'))

  const onSession = (data) => {
    session.setToken(data.token)
    session.setVaultToken('')
    setUnlocked(false)
    setUser(data)
  }

  const onUnlocked = (data) => {
    session.setVaultToken(data.vault_token)
    if (data.idle_seconds) { setIdleSeconds(data.idle_seconds); sessionStorage.setItem(IDLE_KEY, String(data.idle_seconds)) }
    setUnlocked(true)
  }

  if (booting) return <div className="h-[100dvh] grid place-items-center text-subtle"><Spinner className="w-6 h-6" /></div>
  if (!user) return <LoginPage onSession={onSession} />
  if (user.must_change_password) {
    return <ChangePasswordPage username={user.username} mfaEnabled={user.mfa_enabled} onLogout={signOut}
      onChanged={(data) => onSession(data)} />
  }
  if (!unlocked) return <UnlockPage username={user.username} onUnlocked={onUnlocked} onLogout={signOut} />
  return <Shell user={user} theme={theme} onToggleTheme={toggleTheme} onLock={lock} onLogout={signOut} idleDeadline={idleDeadline} />
}

export default function App() {
  return <ToastProvider><Root /></ToastProvider>
}
