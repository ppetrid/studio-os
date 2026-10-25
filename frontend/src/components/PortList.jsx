import { useState } from 'react'
import { deleteAlias, setAlias } from '../api'

function PortRow({ port, direction, onAliasChange }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const startEditing = () => {
    setDraft(port.alias ?? '')
    setError(null)
    setEditing(true)
  }

  const save = async (event) => {
    event.preventDefault()
    const alias = draft.trim()

    if (alias === (port.alias ?? '')) {
      setEditing(false)
      return
    }

    setSaving(true)
    setError(null)

    try {
      // An empty name clears the alias, falling back to the real name.
      if (alias) {
        await setAlias(direction, port, alias)
      } else {
        await deleteAlias(direction, port)
      }
      onAliasChange(port, alias || null)
      setEditing(false)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (editing) {
    return (
      <li className="min-w-0 py-1">
        <form onSubmit={save} className="flex items-center gap-1">
          <input
            type="text"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => event.key === 'Escape' && setEditing(false)}
            placeholder={port.client_name ?? port.name}
            disabled={saving}
            autoFocus
            className="min-w-0 flex-1 rounded-md border border-neutral-700 bg-neutral-950 px-2 py-1.5 text-sm text-neutral-100 outline-none placeholder:text-neutral-600 focus:border-amber-400"
          />
          <button
            type="submit"
            disabled={saving}
            className="shrink-0 rounded-md bg-amber-400 px-3 py-1.5 text-sm font-medium text-neutral-950 active:bg-amber-300 disabled:opacity-50"
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => setEditing(false)}
            disabled={saving}
            className="shrink-0 rounded-md bg-neutral-800 px-3 py-1.5 text-sm font-medium text-neutral-100 hover:bg-neutral-700 active:bg-neutral-700 disabled:opacity-50"
          >
            Cancel
          </button>
        </form>
        <div className="mt-0.5 truncate text-xs text-neutral-500">
          {error ? (
            <span className="text-red-400">{error}</span>
          ) : (
            <>
              {port.client_name ?? '(unknown)'} · {port.name} — leave empty to use the real name
            </>
          )}
        </div>
      </li>
    )
  }

  return (
    <li className="flex min-w-0 items-center gap-2 py-1">
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-1.5">
          <span className="min-w-0 truncate font-medium text-neutral-100">
            {port.alias || port.client_name || '(unknown)'}
          </span>
          {port.alias && (
            <span className="shrink-0 rounded bg-neutral-800 px-1 text-[10px] font-semibold tracking-wide text-neutral-400 uppercase">
              Alias
            </span>
          )}
        </div>
        <div className="truncate text-sm text-neutral-400">
          {port.alias
            ? `${port.client_name ?? '(unknown)'} · ${port.name}`
            : port.name}{' '}
          <span className="text-neutral-600">
            ({port.client_id}:{port.port_id})
          </span>
        </div>
      </div>
      {port.client_name != null && (
        <button
          type="button"
          onClick={startEditing}
          className="shrink-0 rounded-md bg-neutral-800 px-3 py-1.5 text-sm font-medium text-neutral-300 hover:bg-neutral-700 active:bg-neutral-700"
        >
          Rename
        </button>
      )}
    </li>
  )
}

function PortList({ title, direction, ports, loading, error, onAliasChange }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col rounded-lg border border-neutral-800 bg-neutral-900 p-2">
      <h2 className="mb-1 shrink-0 text-sm font-semibold text-neutral-200">{title}</h2>

      {loading && <p className="text-sm text-neutral-500">Loading…</p>}
      {error && <p className="text-sm text-red-400">{error}</p>}
      {!loading && !error && ports.length === 0 && (
        <p className="text-sm text-neutral-500">No ports found.</p>
      )}

      {!loading && !error && ports.length > 0 && (
        <ul className="min-h-0 flex-1 divide-y divide-neutral-800 overflow-auto">
          {ports.map((port) => (
            <PortRow
              key={`${port.client_id}:${port.port_id}`}
              port={port}
              direction={direction}
              onAliasChange={onAliasChange}
            />
          ))}
        </ul>
      )}
    </div>
  )
}

export default PortList
