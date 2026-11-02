import { useCallback, useState } from 'react'
import api from '../../lib/api.js'
import { Icon } from '../../components/icons.jsx'
import { EmptyState, useConfirm, useToast } from '../../components/ui.jsx'
import CredentialForm from './CredentialForm.jsx'
import ItemBrowser from './ItemBrowser.jsx'
import ShareDialog from './ShareDialog.jsx'

const TITLES = { all: 'All items', favorites: 'Favorites' }

/** The user's own credentials. `vault` comes from useCredentials() in the shell. */
export default function VaultView({ vault, scope }) {
  const toast = useToast()
  const [editing, setEditing] = useState(null) // {} for new, cred for edit
  const [sharing, setSharing] = useState(null)
  const [dialog, confirm] = useConfirm()

  const filter = useCallback((c) => {
    if (scope.kind === 'favorites') return c.favorite
    if (scope.kind === 'category') return c.category === scope.value
    return true
  }, [scope])

  const save = async (form) => {
    if (editing?.id) await api.put(`/vault/credentials/${editing.id}`, form)
    else await api.post('/vault/credentials', form)
    await vault.reload()
    toast(editing?.id ? 'Changes saved' : 'Item created')
  }

  const toggleFavorite = async (c) => {
    await api.patch(`/vault/credentials/${c.id}`, { favorite: !c.favorite })
    vault.reload()
  }

  const remove = (c) => confirm({
    title: 'Delete item',
    message: `“${c.name}” will be permanently deleted. Copies you shared with others are kept by them.`,
    confirmLabel: 'Delete',
    onConfirm: async () => { await api.delete(`/vault/credentials/${c.id}`); await vault.reload(); toast('Item deleted') },
  })

  const newButton = (
    <button className="btn-primary btn-sm" onClick={() => setEditing({})}><Icon.plus className="w-4 h-4" />New</button>
  )

  return (
    <>
      <ItemBrowser
        title={scope.kind === 'category' ? scope.value : TITLES[scope.kind]}
        items={vault.items} loading={vault.loading} error={vault.error} onRetry={vault.reload}
        filter={filter} actions={newButton}
        emptyState={scope.kind === 'all'
          ? <EmptyState icon={Icon.key} title="Your vault is empty" action={newButton}>Add your first password, API key or secret.</EmptyState>
          : <EmptyState icon={Icon.star} title="Nothing here yet">Items you mark as favorite or categorise show up here.</EmptyState>}
        detailActions={(c) => <>
          <button className="btn-secondary btn-sm" onClick={() => setEditing(c)}><Icon.edit className="w-4 h-4" />Edit</button>
          <button className="btn-secondary btn-sm" onClick={() => setSharing(c)}><Icon.share className="w-4 h-4" />Share</button>
          <button className="btn-secondary btn-sm" onClick={() => toggleFavorite(c)}>
            <Icon.star className={c.favorite ? 'w-4 h-4 fill-warn text-warn' : 'w-4 h-4'} />{c.favorite ? 'Unfavorite' : 'Favorite'}
          </button>
          <button className="btn-danger-ghost btn-sm ml-auto" onClick={() => remove(c)}><Icon.trash className="w-4 h-4" />Delete</button>
        </>}
      />
      {editing && <CredentialForm initial={editing.id ? editing : null} categories={vault.categories} onSave={save} onClose={() => setEditing(null)} />}
      {sharing && <ShareDialog cred={sharing} onClose={() => setSharing(null)} />}
      {dialog}
    </>
  )
}
