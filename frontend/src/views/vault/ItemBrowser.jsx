import { useEffect, useMemo, useRef, useState } from 'react'
import { Icon } from '../../components/icons.jsx'
import { CopyButton, EmptyState, ErrorBanner, ListSkeleton, Monogram, cx } from '../../components/ui.jsx'
import { displayHost } from '../../lib/secrets.js'
import ItemDetail from './ItemDetail.jsx'

const matches = (item, q) =>
  !q || [item.name, item.username, item.url, item.category, item.owner].some((v) => v?.toLowerCase().includes(q))

/**
 * Two-pane list + detail browser shared by "My vault" and "Shared with me".
 * On small screens the detail replaces the list.
 */
export default function ItemBrowser({ items, loading, error, onRetry, filter, title, subtitle, actions, emptyState, detailActions, badge }) {
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const searchRef = useRef(null)

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    return items
      .filter((i) => (filter ? filter(i) : true) && matches(i, q))
      .sort((a, b) => (b.favorite - a.favorite) || a.name.localeCompare(b.name))
  }, [items, filter, query])

  const selected = visible.find((i) => i.id === selectedId) || null

  // keep a sensible selection on wide screens
  useEffect(() => {
    if (!selected && visible.length && window.matchMedia('(min-width: 1024px)').matches) setSelectedId(visible[0].id)
  }, [visible, selected])

  // "/" focuses search
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === '/' && !/input|textarea|select/i.test(document.activeElement?.tagName)) { e.preventDefault(); searchRef.current?.focus() }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <div className="h-full flex min-h-0">
      {/* list pane */}
      <section className={cx('w-full lg:w-[380px] xl:w-[420px] shrink-0 flex flex-col min-h-0 border-r border-line bg-surface/40', selected && 'hidden lg:flex')}>
        <div className="px-5 pt-6 pb-3">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <h1 className="text-[20px] font-semibold truncate">{title}</h1>
              <p className="text-[12.5px] text-subtle">{subtitle ?? `${visible.length} item${visible.length === 1 ? '' : 's'}`}</p>
            </div>
            {actions}
          </div>
          <div className="relative mt-4">
            <Icon.search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-subtle pointer-events-none" />
            <input ref={searchRef} className="input !pl-9 !pr-10 !py-2" placeholder="Search" value={query}
              onChange={(e) => setQuery(e.target.value)} aria-label="Search items" />
            <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 hidden sm:block rounded border border-line px-1.5 text-[11px] text-subtle">/</kbd>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-3 pb-4">
          {error && <div className="px-2 pb-3"><ErrorBanner message={error} onRetry={onRetry} /></div>}
          {loading ? <ListSkeleton /> : visible.length === 0 ? (
            query ? <EmptyState icon={Icon.search} title="No matches">Try a different search.</EmptyState> : emptyState
          ) : (
            <ul className="space-y-0.5" role="listbox" aria-label={title}>
              {visible.map((item) => (
                <li key={item.id} role="option" aria-selected={item.id === selectedId}>
                  <div onClick={() => setSelectedId(item.id)}
                    className={cx('group flex items-center gap-3 rounded-xl px-2.5 py-2 cursor-pointer transition',
                      item.id === selectedId ? 'bg-accent-soft' : 'hover:bg-sunken')}>
                    <Monogram name={item.name} size={36} />
                    <div className="min-w-0 flex-1">
                      <p className={cx('flex items-center gap-1.5 font-medium truncate', item.id === selectedId && 'text-accent')}>
                        <span className="truncate">{item.name}</span>
                        {item.favorite && <Icon.star className="w-3 h-3 shrink-0 fill-warn text-warn" />}
                      </p>
                      <p className="text-[12.5px] text-subtle truncate">{item.username || displayHost(item.url) || 'No username'}</p>
                    </div>
                    {badge?.(item)}
                    <span className="opacity-0 group-hover:opacity-100 transition flex">
                      <CopyButton value={item.secret} label="password" sensitive className="!w-7 !h-7" />
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      {/* detail pane */}
      <section className={cx('flex-1 min-w-0 overflow-y-auto', !selected && 'hidden lg:block')}>
        {selected ? (
          <ItemDetail key={selected.id} item={selected} onBack={() => setSelectedId(null)} actions={detailActions?.(selected)} />
        ) : (
          <div className="h-full grid place-items-center">
            <EmptyState icon={Icon.lock} title="Select an item">Pick something from the list to see its details.</EmptyState>
          </div>
        )}
      </section>
    </div>
  )
}
