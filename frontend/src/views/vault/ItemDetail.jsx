import { useState } from 'react'
import { Icon } from '../../components/icons.jsx'
import { CopyButton, Monogram, StrengthMeter, cx } from '../../components/ui.jsx'
import { displayHost, safeHref, timeAgo } from '../../lib/secrets.js'

function Row({ label, children, actions, mono }) {
  return (
    <div className="group flex items-center gap-3 px-4 py-3">
      <div className="min-w-0 flex-1">
        <p className="text-[11.5px] font-medium uppercase tracking-wide text-subtle">{label}</p>
        <div className={cx('mt-0.5 break-all', mono && 'mono text-[14px]')}>{children}</div>
      </div>
      <div className="flex items-center gap-0.5 shrink-0">{actions}</div>
    </div>
  )
}

export default function ItemDetail({ item, onBack, actions }) {
  const [revealed, setRevealed] = useState(false)
  const href = safeHref(item.url)

  return (
    <div className="max-w-2xl mx-auto px-5 sm:px-8 py-6 lg:py-10 animate-rise">
      <button onClick={onBack} className="lg:hidden btn-ghost btn-sm -ml-2 mb-4"><Icon.chevronLeft className="w-4 h-4" />Back</button>

      <header className="flex items-start gap-4">
        <Monogram name={item.name} size={56} />
        <div className="min-w-0 flex-1">
          <h2 className="text-[22px] font-semibold break-words">{item.name}</h2>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            {item.category && <span className="badge-neutral"><Icon.tag className="w-3 h-3" />{item.category}</span>}
            {item.favorite && <span className="badge-warn"><Icon.star className="w-3 h-3 fill-current" />Favorite</span>}
            {item.owner && <span className="badge-accent"><Icon.share className="w-3 h-3" />from {item.owner}</span>}
            {item.permission && <span className={item.permission === 'write' ? 'badge-ok' : 'badge-neutral'}>{item.permission === 'write' ? 'Can edit' : 'Read only'}</span>}
          </div>
        </div>
      </header>

      {actions && <div className="mt-5 flex flex-wrap gap-2">{actions}</div>}

      <div className="mt-6 card divide-y divide-line overflow-hidden">
        {item.username && (
          <Row label="Username" actions={<CopyButton value={item.username} label="username" />}>{item.username}</Row>
        )}
        <Row label="Password" mono actions={<>
          <button className="icon-btn" onClick={() => setRevealed((r) => !r)} title={revealed ? 'Hide' : 'Reveal'} aria-label={revealed ? 'Hide password' : 'Reveal password'}>
            {revealed ? <Icon.eyeOff /> : <Icon.eye />}
          </button>
          <CopyButton value={item.secret} label="password" sensitive />
        </>}>
          <span className={cx(!revealed && 'tracking-[0.2em] text-muted')}>{revealed ? item.secret : '•'.repeat(Math.min(item.secret.length, 16))}</span>
          <div className="max-w-[220px]"><StrengthMeter password={item.secret} /></div>
        </Row>
        {item.url && (
          <Row label="Website" actions={<>
            <CopyButton value={item.url} label="URL" />
            {href && <a className="icon-btn" href={href} target="_blank" rel="noopener noreferrer" title="Open"><Icon.external /></a>}
          </>}>
            {href ? <a href={href} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">{displayHost(item.url)}</a> : <span>{item.url}</span>}
          </Row>
        )}
        {item.description && (
          <Row label="Notes"><p className="whitespace-pre-wrap break-words text-[13.5px] leading-relaxed">{item.description}</p></Row>
        )}
      </div>

      {item.updated_at && <p className="mt-4 text-[12px] text-subtle">Last modified {timeAgo(item.updated_at)}</p>}
    </div>
  )
}
