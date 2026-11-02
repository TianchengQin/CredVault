import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import api, { errorMessage } from './lib/api.js'

/** Tiny hash router: "#/category/infra" -> ["category", "infra"]. */
export function useHashRoute(fallback = 'vault') {
  const read = () => window.location.hash.replace(/^#\/?/, '').split('/').map(decodeURIComponent).filter(Boolean)
  const [parts, setParts] = useState(read)
  useEffect(() => {
    const onChange = () => setParts(read())
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  const navigate = useCallback((...p) => { window.location.hash = '/' + p.map(encodeURIComponent).join('/') }, [])
  return [parts.length ? parts : [fallback], navigate]
}

/** Calls `onIdle` after `seconds` without user input. Returns a ref holding the deadline (ms). */
export function useIdleTimer(enabled, seconds, onIdle) {
  const deadline = useRef(0)
  const cb = useRef(onIdle)
  cb.current = onIdle
  useEffect(() => {
    if (!enabled || !seconds) return
    let timer
    const bump = () => {
      deadline.current = Date.now() + seconds * 1000
      clearTimeout(timer)
      timer = setTimeout(() => cb.current(), seconds * 1000)
    }
    const events = ['pointerdown', 'keydown', 'wheel', 'touchstart']
    events.forEach((e) => window.addEventListener(e, bump, { passive: true }))
    bump()
    return () => { clearTimeout(timer); events.forEach((e) => window.removeEventListener(e, bump)) }
  }, [enabled, seconds])
  return deadline
}

/** The current user's credentials plus derived categories. */
export function useCredentials() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const reload = useCallback(async () => {
    try { setItems((await api.get('/vault/credentials')).data); setError('') } catch (e) { setError(errorMessage(e, 'Could not load your vault')) } finally { setLoading(false) }
  }, [])
  useEffect(() => { reload() }, [reload])
  const categories = useMemo(() => [...new Set(items.map((c) => c.category).filter(Boolean))].sort((a, b) => a.localeCompare(b)), [items])
  return { items, loading, error, reload, categories }
}

export function useTheme() {
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem('cv_theme') || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark') } catch { return 'dark' }
  })
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    try { localStorage.setItem('cv_theme', theme) } catch { /* ignore */ }
  }, [theme])
  return [theme, () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))]
}
