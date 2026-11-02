import { useEffect, useState } from 'react'
import { Icon, Logo } from './components/icons.jsx'
import { Monogram, cx } from './components/ui.jsx'
import { useCredentials, useHashRoute } from './hooks.js'
import SharedView from './views/vault/SharedView.jsx'
import VaultView from './views/vault/VaultView.jsx'
import AdminView from './views/settings/AdminView.jsx'
import BackupView from './views/settings/BackupView.jsx'
import SecurityView from './views/settings/SecurityView.jsx'
import TokensView from './views/settings/TokensView.jsx'

function IdleCountdown({ deadline }) {
  const [, tick] = useState(0)
  useEffect(() => { const t = setInterval(() => tick((n) => n + 1), 1000); return () => clearInterval(t) }, [])
  const left = Math.max(0, Math.round((deadline.current - Date.now()) / 1000))
  if (!deadline.current) return null
  const mm = String(Math.floor(left / 60)).padStart(1, '0')
  const ss = String(left % 60).padStart(2, '0')
  return <span className={cx('tabular-nums', left < 60 && 'text-warn')}>{mm}:{ss}</span>
}

function NavButton({ active, icon: I, label, count, onClick }) {
  return (
    <button onClick={onClick} className={cx('nav-item', active && 'nav-item-active')} aria-current={active ? 'page' : undefined}>
      <I /><span className="flex-1 text-left truncate">{label}</span>
      {count != null && <span className="text-[11.5px] tabular-nums text-subtle">{count}</span>}
    </button>
  )
}

function NavGroup({ title, children }) {
  return (
    <div className="space-y-0.5">
      {title && <p className="px-3 pt-4 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-subtle">{title}</p>}
      {children}
    </div>
  )
}

export default function Shell({ user, theme, onToggleTheme, onLock, onLogout, idleDeadline }) {
  const [[view, arg], navigate] = useHashRoute('vault')
  const [drawer, setDrawer] = useState(false)
  const vault = useCredentials()

  useEffect(() => setDrawer(false), [view, arg])

  const go = (...p) => () => navigate(...p)
  const is = (v, a) => view === v && (a === undefined || arg === a)
  const favorites = vault.items.filter((c) => c.favorite).length

  const sidebar = (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2.5 px-5 h-16 shrink-0">
        <Logo size={30} /><span className="text-[15px] font-semibold">CredVault</span>
      </div>
      <nav className="flex-1 overflow-y-auto px-3 pb-4" aria-label="Main">
        <NavGroup>
          <NavButton icon={Icon.grid} label="All items" count={vault.items.length} active={is('vault')} onClick={go('vault')} />
          <NavButton icon={Icon.star} label="Favorites" count={favorites || null} active={is('favorites')} onClick={go('favorites')} />
          <NavButton icon={Icon.share} label="Shared with me" active={is('shared')} onClick={go('shared')} />
        </NavGroup>
        {vault.categories.length > 0 && (
          <NavGroup title="Categories">
            {vault.categories.map((c) => (
              <NavButton key={c} icon={Icon.tag} label={c} count={vault.items.filter((i) => i.category === c).length}
                active={is('category', c)} onClick={go('category', c)} />
            ))}
          </NavGroup>
        )}
        <NavGroup title="Settings">
          <NavButton icon={Icon.terminal} label="API tokens" active={is('tokens')} onClick={go('tokens')} />
          <NavButton icon={Icon.shield} label="Security" active={is('security')} onClick={go('security')} />
          <NavButton icon={Icon.download} label="Backup" active={is('backup')} onClick={go('backup')} />
          {user.is_admin && <NavButton icon={Icon.users} label="Administration" active={is('admin')} onClick={go('admin')} />}
        </NavGroup>
      </nav>
      <div className="p-3 border-t border-line">
        <div className="flex items-center gap-2.5 px-2 py-1.5">
          <Monogram name={user.username} size={32} />
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-medium truncate">{user.username}</p>
            <p className="flex items-center gap-1 text-[11.5px] text-subtle"><Icon.clock className="w-3 h-3" />Locks in <IdleCountdown deadline={idleDeadline} /></p>
          </div>
          <button className="icon-btn" onClick={onToggleTheme} title={theme === 'dark' ? 'Light mode' : 'Dark mode'} aria-label="Toggle theme">
            {theme === 'dark' ? <Icon.sun /> : <Icon.moon />}
          </button>
        </div>
        <div className="mt-2 grid grid-cols-2 gap-2">
          <button className="btn-secondary btn-sm" onClick={onLock}><Icon.lock className="w-4 h-4" />Lock</button>
          <button className="btn-ghost btn-sm" onClick={onLogout}><Icon.logout className="w-4 h-4" />Sign out</button>
        </div>
      </div>
    </div>
  )

  let content
  switch (view) {
    case 'favorites': content = <VaultView vault={vault} scope={{ kind: 'favorites' }} />; break
    case 'category': content = <VaultView vault={vault} scope={{ kind: 'category', value: arg }} />; break
    case 'shared': content = <SharedView />; break
    case 'tokens': content = <TokensView />; break
    case 'security': content = <SecurityView mfaEnabled={user.mfa_enabled} />; break
    case 'backup': content = <BackupView onImported={vault.reload} />; break
    case 'admin': content = user.is_admin ? <AdminView /> : null; break
    default: content = <VaultView vault={vault} scope={{ kind: 'all' }} />
  }

  return (
    <div className="h-[100dvh] flex">
      <aside className="hidden md:block w-[248px] shrink-0 border-r border-line bg-surface">{sidebar}</aside>

      {drawer && (
        <div className="md:hidden fixed inset-0 z-40 bg-black/50 animate-fade" onClick={() => setDrawer(false)}>
          <aside className="w-[272px] h-full bg-surface shadow-pop animate-rise" onClick={(e) => e.stopPropagation()}>{sidebar}</aside>
        </div>
      )}

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="md:hidden flex items-center justify-between h-14 px-3 border-b border-line bg-surface/80 backdrop-blur">
          <button className="icon-btn" onClick={() => setDrawer(true)} aria-label="Open menu"><Icon.menu /></button>
          <div className="flex items-center gap-2"><Logo size={26} /><span className="font-semibold">CredVault</span></div>
          <button className="icon-btn" onClick={onLock} aria-label="Lock vault"><Icon.lock /></button>
        </header>
        <main className="flex-1 min-h-0 overflow-y-auto">{content}</main>
      </div>
    </div>
  )
}
