import { useState } from 'react'
import { errorMessage } from '../../lib/api.js'
import { generatePassword } from '../../lib/secrets.js'
import { Icon } from '../../components/icons.jsx'
import { Field, FormError, Modal, PasswordInput, Spinner, StrengthMeter, cx } from '../../components/ui.jsx'

const EMPTY = { name: '', secret: '', url: '', username: '', description: '', category: '', favorite: false }
const FIELDS = Object.keys(EMPTY)

function Generator({ onUse }) {
  const [opts, setOpts] = useState({ length: 20, upper: true, lower: true, digits: true, symbols: true })
  const [value, setValue] = useState(() => generatePassword(opts))
  const update = (patch) => { const next = { ...opts, ...patch }; setOpts(next); setValue(generatePassword(next)) }
  return (
    <div className="mt-2 rounded-xl border border-line bg-raised p-3.5 space-y-3 animate-rise">
      <div className="flex items-center gap-2">
        <code className="mono flex-1 min-w-0 truncate rounded-lg bg-sunken px-3 py-2">{value}</code>
        <button type="button" className="icon-btn" onClick={() => setValue(generatePassword(opts))} title="Regenerate" aria-label="Regenerate"><Icon.refresh /></button>
        <button type="button" className="btn-primary btn-sm" onClick={() => onUse(value)}>Use</button>
      </div>
      <div className="flex items-center gap-3">
        <label htmlFor="gen-len" className="text-[12px] text-muted w-16">Length {opts.length}</label>
        <input id="gen-len" type="range" min={8} max={64} value={opts.length} onChange={(e) => update({ length: +e.target.value })} className="flex-1" />
      </div>
      <div className="flex flex-wrap gap-1.5">
        {[['upper', 'A–Z'], ['lower', 'a–z'], ['digits', '0–9'], ['symbols', '!@#']].map(([k, label]) => (
          <button key={k} type="button" onClick={() => update({ [k]: !opts[k] })} className={cx('chip', opts[k] && 'chip-active')} aria-pressed={opts[k]}>{label}</button>
        ))}
      </div>
    </div>
  )
}

/** Create or edit a credential. `onSave(form)` should throw on failure. */
export default function CredentialForm({ initial, categories = [], onSave, onClose }) {
  const [form, setForm] = useState(() => ({ ...EMPTY, ...Object.fromEntries(FIELDS.map((k) => [k, initial?.[k] ?? EMPTY[k]])) }))
  const [showGen, setShowGen] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))

  const submit = async (e) => {
    e.preventDefault()
    if (!form.name.trim() || !form.secret) return setError('Name and password are required')
    setBusy(true); setError('')
    try { await onSave(form); onClose() } catch (err) { setError(errorMessage(err, 'Save failed')); setBusy(false) }
  }

  return (
    <Modal title={initial ? 'Edit item' : 'New item'} onClose={onClose} size="lg"
      footer={<>
        <button type="button" onClick={onClose} className="btn-ghost">Cancel</button>
        <button type="submit" form="cred-form" className="btn-primary" disabled={busy}>{busy && <Spinner />}{initial ? 'Save changes' : 'Create item'}</button>
      </>}>
      <form id="cred-form" onSubmit={submit} className="space-y-4">
        <div className="grid sm:grid-cols-[1fr_180px] gap-4">
          <Field label="Name" htmlFor="cf-name" required>
            <input id="cf-name" className="input" value={form.name} onChange={set('name')} maxLength={200} autoFocus placeholder="e.g. Production database" />
          </Field>
          <Field label="Category" htmlFor="cf-cat">
            <input id="cf-cat" className="input" value={form.category} onChange={set('category')} maxLength={64} list="cf-categories" placeholder="e.g. servers" />
            <datalist id="cf-categories">{categories.map((c) => <option key={c} value={c} />)}</datalist>
          </Field>
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          <Field label="Username" htmlFor="cf-user">
            <input id="cf-user" className="input" value={form.username} onChange={set('username')} autoComplete="off" spellCheck={false} />
          </Field>
          <Field label="Website" htmlFor="cf-url">
            <input id="cf-url" className="input" value={form.url} onChange={set('url')} placeholder="https://" spellCheck={false} />
          </Field>
        </div>
        <Field label="Password" htmlFor="cf-secret" required>
          <div className="flex gap-2">
            <div className="flex-1 min-w-0">
              <PasswordInput id="cf-secret" value={form.secret} onChange={set('secret')} autoComplete="new-password" mono />
            </div>
            <button type="button" onClick={() => setShowGen((s) => !s)} className={cx('btn-secondary shrink-0', showGen && '!text-accent')} aria-expanded={showGen}>
              <Icon.sliders className="w-4 h-4" /><span className="hidden sm:inline">Generate</span>
            </button>
          </div>
          <StrengthMeter password={form.secret} />
          {showGen && <Generator onUse={(v) => { setForm((f) => ({ ...f, secret: v })); setShowGen(false) }} />}
        </Field>
        <Field label="Notes" htmlFor="cf-notes">
          <textarea id="cf-notes" className="input resize-y min-h-[72px]" rows={3} value={form.description} onChange={set('description')} maxLength={5000} />
        </Field>
        <label className="inline-flex items-center gap-2.5 text-[13.5px] cursor-pointer select-none">
          <input type="checkbox" checked={form.favorite} onChange={set('favorite')} className="w-4 h-4 accent-[rgb(var(--accent))]" />
          Add to favorites
        </label>
        <FormError>{error}</FormError>
      </form>
    </Modal>
  )
}
