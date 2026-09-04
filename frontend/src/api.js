import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('cv_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  const vt = localStorage.getItem('cv_vault_token')
  if (vt) config.headers['X-Vault-Token'] = vt
  return config
})

export function setSession(token, vaultToken) {
  if (token) localStorage.setItem('cv_token', token)
  if (vaultToken !== undefined) {
    if (vaultToken) localStorage.setItem('cv_vault_token', vaultToken)
    else localStorage.removeItem('cv_vault_token')
  }
}

export function clearSession() {
  localStorage.removeItem('cv_token')
  localStorage.removeItem('cv_vault_token')
}

export default api
