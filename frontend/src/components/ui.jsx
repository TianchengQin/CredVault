import { createContext, useCallback, useContext, useEffect, useId, useRef, useState } from 'react'
import { Icon } from './icons.jsx'
import { errorMessage } from '../lib/api.js'
import { initials, monogramColor, passwordStrength } from '../lib/secrets.js'

export function cx(...parts) {
  return parts.filter(Boolean).join(' ')
}

export function Spinner({ className = 'w-4 h-4' }) {
  return (
    <svg className={cx('animate-spin', className)} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity=".25" strokeWidth="3" />
      <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  )
}

// ---------------------------------------------------------------- toasts

const ToastContext = createContext(() => {})
export const useToast = () => useContext(ToastContext)

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const push = useCallback((message, tone = 'ok') => {
    const id = crypto.randomUUID()
    setToasts((t) => [...t.slice(-3), { id, message, tone }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3500)
  }, [])
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="fixed bottom-4 inset-x-4 sm:inset-x-auto sm:right-5 z-[100] flex flex-col items-center sm:items-end gap-2 pointer-events-none" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} role="status" className="animate-rise pointer-events-auto flex items-center gap-2.5 rounded-xl bg-raised px-4 py-2.5 text-[13.5px] shadow-pop">
            <span className={cx('grid place-items-center w-5 h-5 rounded-full', t.tone === 'error' ? 'bg-danger-soft text-danger' : 'bg-ok-soft text-ok')}>
              {t.tone === 'error' ? <Icon.alert className="w-3 h-3" /> : <Icon.check className="w-3 h-3" />}
            </span>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

// ---------------------------------------------------------------- dialogs

/** Closes via ✕, Cancel or Escape — never by an accidental click outside. */
export function Modal({ title, subtitle, onClose, children, footer, size = 'md' }) {
  const titleId = useId()
  const ref = useRef(null)
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    const prev = document.activeElement
    ref.current?.querySelector('[autofocus],input,select,textarea,button:not([data-close])')?.focus()
    return () => { window.removeEventListener('keydown', onKey); prev?.focus?.() }
  }, [onClose])
  const width = { sm: 'sm:max-w-sm', md: 'sm:max-w-md', lg: 'sm:max-w-xl' }[size]
  return (
    <div className="backdrop">
      <div ref={ref} role="dialog" aria-modal="true" aria-labelledby={titleId}
        className={cx('w-full max-h-[92dvh] flex flex-col rounded-t-2xl sm:rounded-2xl bg-surface shadow-pop animate-rise', width)}>
        <header className="flex items-start justify-between gap-4 px-6 pt-5 pb-4">
          <div className="min-w-0">
            <h2 id={titleId} className="text-[16px] font-semibold">{title}</h2>
            {subtitle && <p className="mt-1 text-[13px] text-muted leading-relaxed">{subtitle}</p>}
          </div>
          <button data-close onClick={onClose} className="icon-btn -mr-2 -mt-1" aria-label="Close"><Icon.close /></button>
        </header>
        <div className="px-6 pb-6 overflow-y-auto">{children}</div>
        {footer && <footer className="flex justify-end gap-2 px-6 py-4 border-t border-line bg-raised/60 rounded-b-2xl">{footer}</footer>}
      </div>
    </div>
  )
}

export function ConfirmDialog({ title, message, confirmLabel = 'Confirm', tone = 'danger', onConfirm, onClose }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const run = async () => {
    setBusy(true); setError('')
    try { await onConfirm(); onClose() } catch (e) { setError(errorMessage(e, 'Action failed')); setBusy(false) }
  }
  return (
    <Modal title={title} onClose={onClose} size="sm" footer={<>
      <button className="btn-ghost" onClick={onClose} disabled={busy}>Cancel</button>
      <button className={tone === 'danger' ? 'btn-danger' : 'btn-primary'} onClick={run} disabled={busy}>{busy && <Spinner />}{confirmLabel}</button>
    </>}>
      <p className="text-[13.5px] text-muted leading-relaxed">{message}</p>
      {error && <FormError>{error}</FormError>}
    </Modal>
  )
}

/** Hook: `const [dialog, confirm] = useConfirm()` then `confirm({...})` and render `{dialog}`. */
export function useConfirm() {
  const [state, setState] = useState(null)
  const dialog = state && <ConfirmDialog {...state} onClose={() => setState(null)} />
  return [dialog, setState]
}

// ---------------------------------------------------------------- form bits

export function Field({ label, hint, children, htmlFor, required }) {
  return (
    <div>
      {label && <label className="label" htmlFor={htmlFor}>{label}{required && <span className="text-accent"> *</span>}</label>}
      {children}
      {hint && <p className="hint">{hint}</p>}
    </div>
  )
}

export function FormError({ children }) {
  if (!children) return null
  return (
    <p role="alert" className="mt-3 flex items-start gap-2 rounded-lg bg-danger-soft px-3 py-2 text-[13px] text-danger">
      <Icon.alert className="w-4 h-4 mt-px shrink-0" />{children}
    </p>
  )
}

export function PasswordInput({ value, onChange, id, autoComplete = 'current-password', className = '', mono = false, ...rest }) {
  const [shown, setShown] = useState(false)
  return (
    <div className="relative">
      <input id={id} type={shown ? 'text' : 'password'} value={value} onChange={onChange} autoComplete={autoComplete}
        spellCheck={false} className={cx('input pr-11', mono && 'mono', className)} {...rest} />
      <button type="button" onClick={() => setShown((s) => !s)} className="icon-btn absolute right-1.5 top-1/2 -translate-y-1/2"
        aria-label={shown ? 'Hide' : 'Show'} title={shown ? 'Hide' : 'Show'}>
        {shown ? <Icon.eyeOff /> : <Icon.eye />}
      </button>
    </div>
  )
}

export function OtpInput({ value, onChange, id, autoFocus }) {
  return (
    <input id={id} className="input-otp" inputMode="numeric" autoComplete="one-time-code" maxLength={6} placeholder="••••••"
      value={value} onChange={(e) => onChange(e.target.value.replace(/\D/g, '').slice(0, 6))} autoFocus={autoFocus} />
  )
}

export function StrengthMeter({ password }) {
  const s = passwordStrength(password)
  const color = { danger: 'bg-danger', warn: 'bg-warn', ok: 'bg-ok' }[s.tone]
  const text = { danger: 'text-danger', warn: 'text-warn', ok: 'text-ok' }[s.tone]
  return (
    <div className="mt-2 flex items-center gap-3" aria-live="polite">
      <div className="flex flex-1 gap-1">
        {[0, 1, 2, 3].map((i) => (
          <span key={i} className={cx('h-1 flex-1 rounded-full transition-colors', password && i < Math.max(1, s.score) ? color : 'bg-sunken')} />
        ))}
      </div>
      {password && <span className={cx('text-[11.5px] font-medium', text)}>{s.label}</span>}
    </div>
  )
}

// ---------------------------------------------------------------- clipboard

const CLEAR_AFTER_MS = 30_000

export async function copyText(value, { sensitive = false } = {}) {
  await navigator.clipboard.writeText(value)
  if (sensitive) {
    // best effort: wipe the clipboard later if it still holds our secret
    setTimeout(async () => {
      try { if ((await navigator.clipboard.readText()) === value) await navigator.clipboard.writeText('') } catch { /* no permission */ }
    }, CLEAR_AFTER_MS)
  }
}

export function CopyButton({ value, label = 'value', sensitive = false, className = '' }) {
  const [copied, setCopied] = useState(false)
  const toast = useToast()
  const copy = async (e) => {
    e.stopPropagation()
    try {
      await copyText(value, { sensitive })
      setCopied(true)
      setTimeout(() => setCopied(false), 1400)
      if (sensitive) toast(`${label[0].toUpperCase()}${label.slice(1)} copied — clipboard clears in 30s`)
    } catch {
      toast('Clipboard unavailable (needs HTTPS)', 'error')
    }
  }
  return (
    <button type="button" onClick={copy} title={`Copy ${label}`} aria-label={`Copy ${label}`}
      className={cx('icon-btn', copied && '!text-ok', className)}>
      {copied ? <Icon.check /> : <Icon.copy />}
    </button>
  )
}

// ---------------------------------------------------------------- display bits

export function Monogram({ name, size = 36, className = '' }) {
  const hue = monogramColor(name)
  return (
    <div className={cx('grid place-items-center shrink-0 rounded-[30%] font-semibold select-none', className)}
      style={{ width: size, height: size, fontSize: size * 0.38, color: `hsl(${hue} 80% 70%)`, background: `hsl(${hue} 60% 50% / .16)`, boxShadow: `inset 0 0 0 1px hsl(${hue} 60% 60% / .22)` }}
      aria-hidden="true">
      {initials(name)}
    </div>
  )
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
      <div className="min-w-0">
        <h1 className="text-[22px] font-semibold">{title}</h1>
        {subtitle && <p className="mt-1 text-[13.5px] text-muted">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}

export function Section({ title, description, children, aside, className = '' }) {
  return (
    <section className={cx('card p-5 sm:p-6', className)}>
      {(title || aside) && (
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <h2 className="text-[15px] font-semibold">{title}</h2>
            {description && <p className="mt-1 text-[13px] text-muted leading-relaxed">{description}</p>}
          </div>
          {aside}
        </div>
      )}
      {children}
    </section>
  )
}

export function EmptyState({ icon: I = Icon.inbox, title, children, action }) {
  return (
    <div className="flex flex-col items-center text-center py-16 px-6 animate-rise">
      <div className="grid place-items-center w-14 h-14 rounded-2xl bg-accent-soft text-accent mb-4"><I className="w-6 h-6" /></div>
      <p className="font-medium">{title}</p>
      {children && <p className="mt-1 text-[13px] text-muted max-w-xs">{children}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function ErrorBanner({ message, onRetry }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl bg-danger-soft px-4 py-3 text-[13px] text-danger">
      <span className="flex items-center gap-2"><Icon.alert className="w-4 h-4" />{message}</span>
      {onRetry && <button onClick={onRetry} className="btn-sm btn-ghost !text-danger"><Icon.refresh className="w-4 h-4" />Retry</button>}
    </div>
  )
}

export function Skeleton({ className }) {
  return <div className={cx('skeleton', className)} />
}

export function ListSkeleton({ rows = 5 }) {
  return (
    <div className="space-y-2 p-2">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-3 p-2">
          <Skeleton className="w-9 h-9 !rounded-[30%]" />
          <div className="flex-1 space-y-2"><Skeleton className="h-3.5 w-1/2" /><Skeleton className="h-3 w-1/3" /></div>
        </div>
      ))}
    </div>
  )
}
