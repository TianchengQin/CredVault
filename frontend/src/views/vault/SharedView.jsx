import { useCallback, useEffect, useState } from 'react'
import api, { errorMessage } from '../../lib/api.js'
import { Icon } from '../../components/icons.jsx'
import { EmptyState, useConfirm, useToast } from '../../components/ui.jsx'
import CredentialForm from './CredentialForm.jsx'
import ItemBrowser from './ItemBrowser.jsx'

/** Credentials other people shared with the current user. */
export default function SharedView() {
  const toast = useToast()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [editing, setEditing] = useState(null)
  const [dialog, confirm] = useConfirm()

  const load = useCallback(async () => {
    setError('')
    try { setItems((await api.get('/vault/shared')).data) } catch (e) { setError(errorMessage(e, 'Could not load shared items')) } finally { setLoading(false) }
  }, [])
  useEffect(() => { load() }, [load])

  const save = async (form) => {
    await api.put(`/vault/shared/${editing.share_id}`, form)
    await load()
    toast('Changes saved')
  }

  const remove = (s) => confirm({
    title: 'Remove shared item',
    message: `Remove “${s.name}” from your vault? ${s.owner} keeps their original.`,
    confirmLabel: 'Remove',
    onConfirm: async () => { await api.delete(`/vault/shared/${s.share_id}`); await load(); toast('Removed') },
  })

  return (
    <>
      <ItemBrowser
        title="Shared with me" items={items} loading={loading} error={error} onRetry={load}
        emptyState={<EmptyState icon={Icon.share} title="Nothing shared with you yet">When someone shares an item with you, it appears here.</EmptyState>}
        badge={(s) => <span className="badge-neutral hidden sm:inline-flex">{s.owner}</span>}
        detailActions={(s) => <>
          {s.permission === 'write' && <button className="btn-secondary btn-sm" onClick={() => setEditing(s)}><Icon.edit className="w-4 h-4" />Edit</button>}
          <button className="btn-danger-ghost btn-sm ml-auto" onClick={() => remove(s)}><Icon.trash className="w-4 h-4" />Remove</button>
        </>}
      />
      {editing && <CredentialForm initial={editing} onSave={save} onClose={() => setEditing(null)} />}
      {dialog}
    </>
  )
}
