import { useRef, useState } from 'react'
import api, { errorMessage } from '../../lib/api.js'
import { Icon } from '../../components/icons.jsx'
import { FormError, PageHeader, Section, Spinner, useToast } from '../../components/ui.jsx'

const MAX_IMPORT_BYTES = 5 * 1024 * 1024

export default function BackupView({ onImported }) {
  const toast = useToast()
  const fileRef = useRef(null)
  const [text, setText] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')

  const download = async () => {
    setBusy('export'); setError('')
    try {
      const { data } = await api.post('/vault/export', null, { responseType: 'blob' })
      const url = URL.createObjectURL(data)
      const a = Object.assign(document.createElement('a'), { href: url, download: `credvault-backup-${new Date().toISOString().slice(0, 10)}.json` })
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
      toast('Backup downloaded — it contains plaintext secrets')
    } catch (e) { setError(errorMessage(e, 'Export failed')) } finally { setBusy('') }
  }

  const pickFile = async (e) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    if (file.size > MAX_IMPORT_BYTES) return setError('File is larger than 5 MB')
    setText(await file.text())
  }

  const restore = async () => {
    setError('')
    let items
    try {
      const parsed = JSON.parse(text)
      items = Array.isArray(parsed) ? parsed : parsed.items
      if (!Array.isArray(items)) throw new Error()
    } catch {
      return setError('That isn’t a CredVault backup (expected a JSON array or { "items": [...] })')
    }
    setBusy('import')
    try {
      const { data } = await api.post('/vault/import', { items })
      setText('')
      toast(`Imported ${data.imported} item${data.imported === 1 ? '' : 's'}`)
      onImported?.()
    } catch (e) { setError(errorMessage(e, 'Import failed')) } finally { setBusy('') }
  }

  return (
    <div className="max-w-3xl mx-auto px-5 sm:px-8 py-8 space-y-5">
      <PageHeader title="Backup & restore" subtitle="Move your vault in and out as JSON." />

      <div className="flex gap-3 rounded-2xl bg-warn-soft px-4 py-3 text-[13px] text-warn">
        <Icon.alert className="w-4 h-4 mt-0.5 shrink-0" />
        <p>Exports are <strong>unencrypted</strong>. Store them on encrypted media and delete copies you no longer need.</p>
      </div>

      <Section title="Export" description="Download every item in your vault (shared-with-me items are not included).">
        <button className="btn-primary" onClick={download} disabled={!!busy}>{busy === 'export' ? <Spinner /> : <Icon.download className="w-4 h-4" />}Download backup</button>
      </Section>

      <Section title="Import" description="Items are added alongside your existing ones — nothing is overwritten."
        aside={<button className="btn-secondary btn-sm" onClick={() => fileRef.current?.click()}><Icon.upload className="w-4 h-4" />Choose file</button>}>
        <input ref={fileRef} type="file" accept="application/json,.json" className="hidden" onChange={pickFile} />
        <textarea className="input mono resize-y min-h-[140px]" value={text} onChange={(e) => setText(e.target.value)} spellCheck={false}
          placeholder='{"items": [{"name": "db", "secret": "…", "username": "root", "url": "", "category": "infra"}]}' aria-label="Backup JSON" />
        <FormError>{error}</FormError>
        <button className="btn-primary mt-3" onClick={restore} disabled={!!busy || !text.trim()}>{busy === 'import' ? <Spinner /> : <Icon.upload className="w-4 h-4" />}Import</button>
      </Section>
    </div>
  )
}
