import { Icon, Logo } from '../components/icons.jsx'
import { FormError, Spinner } from '../components/ui.jsx'

const FEATURES = [
  [Icon.lock, 'AES-256-GCM encryption', 'Keys derived from your master password with Argon2id.'],
  [Icon.shieldCheck, 'Zero-knowledge by design', 'Admins manage accounts — never your secrets.'],
  [Icon.share, 'Share without exposure', 'Copies are sealed to the recipient’s own key.'],
  [Icon.terminal, 'Agent-ready', 'Scoped API tokens and an MCP server for AI agents.'],
]

export function AuthLayout({ children }) {
  return (
    <div className="min-h-[100dvh] grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <aside className="relative hidden lg:flex flex-col justify-between overflow-hidden p-12 bg-surface border-r border-line">
        <div aria-hidden="true" className="absolute inset-0 opacity-70"
          style={{ background: 'radial-gradient(60% 50% at 20% 10%, rgb(var(--accent) / .22), transparent 70%), radial-gradient(50% 40% at 90% 90%, rgb(59 130 246 / .16), transparent 70%)' }} />
        <div className="relative flex items-center gap-3">
          <Logo size={38} />
          <span className="text-[17px] font-semibold">CredVault</span>
        </div>
        <div className="relative max-w-md">
          <h2 className="text-[34px] leading-tight font-semibold">Your secrets,<br />encrypted with a key<br /><span className="text-accent">only you hold.</span></h2>
          <ul className="mt-10 space-y-5">
            {FEATURES.map(([I, title, text]) => (
              <li key={title} className="flex gap-4">
                <span className="grid place-items-center w-9 h-9 shrink-0 rounded-xl bg-accent-soft text-accent"><I className="w-[18px] h-[18px]" /></span>
                <span><span className="block font-medium">{title}</span><span className="text-[13px] text-muted">{text}</span></span>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-[12px] text-subtle">Self-hosted · open source · MIT</p>
      </aside>
      <main className="flex items-center justify-center p-5 sm:p-10">
        <div className="w-full max-w-[380px] animate-rise">
          <div className="lg:hidden flex items-center gap-3 mb-10"><Logo size={36} /><span className="text-[17px] font-semibold">CredVault</span></div>
          {children}
        </div>
      </main>
    </div>
  )
}

export function AuthCard({ title, subtitle, onSubmit, error, loading, submitLabel, children, footer }) {
  return (
    <>
      <h1 className="text-[24px] font-semibold">{title}</h1>
      {subtitle && <p className="mt-2 text-[13.5px] text-muted leading-relaxed">{subtitle}</p>}
      <form onSubmit={onSubmit} className="mt-7 space-y-4" noValidate>
        {children}
        <FormError>{error}</FormError>
        <button type="submit" disabled={loading} className="btn-primary w-full !py-2.5 mt-2">
          {loading && <Spinner />}{submitLabel}
        </button>
      </form>
      {footer && <div className="mt-6 text-center text-[13px] text-muted">{footer}</div>}
    </>
  )
}

export function SignedInAs({ username, note, onLogout }) {
  return (
    <div className="flex items-center justify-between mb-8 rounded-xl bg-surface shadow-card px-3 py-2.5">
      <div className="flex items-center gap-3 min-w-0">
        <span className="grid place-items-center w-8 h-8 rounded-full bg-accent-soft text-accent"><Icon.user className="w-4 h-4" /></span>
        <div className="min-w-0">
          <p className="text-[13.5px] font-medium truncate">{username || '…'}</p>
          <p className="text-[12px] text-subtle">{note}</p>
        </div>
      </div>
      <button onClick={onLogout} className="btn-ghost btn-sm"><Icon.logout className="w-4 h-4" />Sign out</button>
    </div>
  )
}
