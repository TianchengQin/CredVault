import axios from 'axios'

// Tokens live in sessionStorage: they die with the tab and aren't shared across
// tabs/windows, which narrows what a stolen browser profile or XSS can reach.
const SESSION = 'cv_session'
const VAULT = 'cv_vault'

const store = {
  get: (k) => { try { return sessionStorage.getItem(k) || '' } catch { return '' } },
  set: (k, v) => { try { v ? sessionStorage.setItem(k, v) : sessionStorage.removeItem(k) } catch { /* storage disabled */ } },
}

export const session = {
  get token() { return store.get(SESSION) },
  get vaultToken() { return store.get(VAULT) },
  setToken: (t) => store.set(SESSION, t),
  setVaultToken: (t) => store.set(VAULT, t),
  clear: () => { store.set(SESSION, ''); store.set(VAULT, '') },
}

const api = axios.create({ baseURL: '/api', timeout: 30_000 })

api.interceptors.request.use((config) => {
  if (session.token) config.headers.Authorization = `Bearer ${session.token}`
  if (session.vaultToken) config.headers['X-Vault-Token'] = session.vaultToken
  return config
})

// Broadcast auth failures so the app can drop back to the right screen.
api.interceptors.response.use(undefined, (error) => {
  const res = error.response
  if (res?.status === 401 && session.token) {
    const event = res.headers?.['x-session-expired'] === '1' ? 'cv:signed-out'
      : res.headers?.['x-vault-locked'] === '1' ? 'cv:vault-locked' : null
    if (event) window.dispatchEvent(new CustomEvent(event, { detail: res.data?.detail }))
  }
  return Promise.reject(error)
})

export function errorMessage(err, fallback = 'Something went wrong') {
  if (err && !err.isAxiosError && err.message) return err.message // local validation
  const detail = err?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail[0]?.msg) {
    const field = detail[0].loc?.slice(-1)[0]
    return field ? `${field}: ${detail[0].msg}` : detail[0].msg
  }
  if (err?.code === 'ECONNABORTED') return 'The server took too long to respond'
  if (!err?.response) return 'Cannot reach the server'
  return fallback
}

export default api
