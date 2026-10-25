import { useCallback, useEffect, useState } from 'react'
import { deletePreset, fetchPresets, recallPreset, savePreset } from '../api'

// Routes listed on a tile before collapsing the rest into "+N more".
const PREVIEW_ROUTES = 3

const TILE_FOCUS =
  'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-400'

// A preset endpoint is a device name, or a real port for unnamed ports.
function endpointLabel(endpoint) {
  return endpoint.device ?? `${endpoint.client_name} · ${endpoint.port_name}`
}

function routeLabel(route) {
  return `${endpointLabel(route.source)} → ${endpointLabel(route.destination)}`
}

function plural(count, word) {
  return `${count} ${word}${count === 1 ? '' : 's'}`
}

function PresetSummary({ preset }) {
  const shown = preset.routes.slice(0, PREVIEW_ROUTES)
  const hidden = preset.routes.length - shown.length

  return (
    <>
      <div className="flex min-w-0 items-baseline justify-between gap-2">
        <span
          className={`min-w-0 truncate text-base font-semibold ${
            preset.current ? 'text-amber-300' : 'text-neutral-100'
          }`}
        >
          {preset.name}
        </span>
        {preset.current && <span className="shrink-0 text-[11px] text-amber-300">Current</span>}
      </div>
      <ul className="mt-1 min-w-0 space-y-0.5 text-[11px] text-neutral-400">
        {preset.routes.length === 0 && <li className="text-neutral-500">No routes</li>}
        {shown.map((route) => (
          <li key={routeLabel(route)} className="truncate">
            {routeLabel(route)}
          </li>
        ))}
        {hidden > 0 && <li className="text-neutral-500">+{hidden} more</li>}
      </ul>
    </>
  )
}

function PresetTile({ preset, managing, busy, confirming, onRecall, onConfirm, onUpdate, onDelete }) {
  // The preset matching the current routing is lit like a connected matrix cell.
  const frame = [
    'flex min-h-24 min-w-0 flex-col rounded-lg border bg-neutral-900 p-3 text-left',
    preset.current
      ? 'border-amber-400/60 shadow-[0_0_10px_1px_rgba(251,191,36,0.35)]'
      : 'border-neutral-800',
  ].join(' ')

  if (!managing) {
    return (
      <button
        type="button"
        disabled={busy}
        onClick={onRecall}
        aria-current={preset.current || undefined}
        className={[
          frame,
          TILE_FOCUS,
          'transition-colors active:bg-neutral-800 disabled:cursor-wait',
          !preset.current && 'hover:border-neutral-600',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        <PresetSummary preset={preset} />
      </button>
    )
  }

  const buttonClass =
    'rounded-md px-3 py-1.5 text-sm font-medium disabled:opacity-50'

  return (
    <div className={frame}>
      <PresetSummary preset={preset} />
      <div className="mt-auto flex flex-wrap gap-1 pt-2">
        {confirming === 'update' && (
          <button
            type="button"
            disabled={busy}
            onClick={onUpdate}
            className={`${buttonClass} bg-amber-400 text-neutral-950 active:bg-amber-300`}
          >
            Overwrite with current
          </button>
        )}
        {confirming === 'delete' && (
          <button
            type="button"
            disabled={busy}
            onClick={onDelete}
            className={`${buttonClass} bg-red-500 text-neutral-950 active:bg-red-400`}
          >
            Delete preset
          </button>
        )}
        {confirming ? (
          <button
            type="button"
            disabled={busy}
            onClick={() => onConfirm(null)}
            className={`${buttonClass} bg-neutral-800 text-neutral-100 hover:bg-neutral-700`}
          >
            Cancel
          </button>
        ) : (
          <>
            <button
              type="button"
              disabled={busy}
              onClick={() => onConfirm('update')}
              className={`${buttonClass} bg-neutral-800 text-neutral-100 hover:bg-neutral-700`}
            >
              Update
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => onConfirm('delete')}
              className={`${buttonClass} bg-neutral-800 text-neutral-300 hover:bg-neutral-700`}
            >
              Delete
            </button>
          </>
        )}
      </div>
    </div>
  )
}

function PresetsView() {
  const [presets, setPresets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)
  const [managing, setManaging] = useState(false)
  const [confirm, setConfirm] = useState(null)
  const [draft, setDraft] = useState('')

  const load = useCallback(() => fetchPresets().then(setPresets), [])

  useEffect(() => {
    load()
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [load])

  // Every action can change which preset matches the current routing, so
  // the list is reloaded after each one. Resolves to whether it succeeded.
  const run = async (action) => {
    setBusy(true)
    setError(null)
    setConfirm(null)

    try {
      setStatus(await action())
      await load()
      return true
    } catch (err) {
      setStatus(null)
      setError(err.message)
      return false
    } finally {
      setBusy(false)
    }
  }

  const recall = (name) =>
    run(async () => {
      const result = await recallPreset(name)
      return { message: `Recalled “${name}”.`, skipped: result.skipped }
    })

  const save = (name, message) =>
    run(async () => {
      await savePreset(name)
      return { message, skipped: [] }
    })

  const remove = (name) =>
    run(async () => {
      await deletePreset(name)
      return { message: `Deleted “${name}”.`, skipped: [] }
    })

  const name = draft.trim()
  const replacing = presets.some((preset) => preset.name === name)

  const submit = async (event) => {
    event.preventDefault()
    const saved = await save(
      name,
      replacing ? `Replaced “${name}” with the current routing.` : `Saved “${name}”.`,
    )
    if (saved) {
      setDraft('')
    }
  }

  return (
    <div className="flex h-full flex-col gap-2 p-2">
      <div className="flex shrink-0 flex-wrap items-center gap-1">
        <form onSubmit={submit} className="flex min-w-0 flex-1 items-center gap-1">
          <input
            type="text"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Name the current routing"
            disabled={busy}
            className="min-w-0 flex-1 rounded-md border border-neutral-700 bg-neutral-950 px-2 py-1.5 text-sm text-neutral-100 outline-none placeholder:text-neutral-600 focus:border-amber-400 sm:max-w-sm"
          />
          <button
            type="submit"
            disabled={busy || !name}
            className="shrink-0 rounded-md bg-amber-400 px-3 py-1.5 text-sm font-medium text-neutral-950 active:bg-amber-300 disabled:opacity-50"
          >
            {replacing ? 'Replace preset' : 'Save preset'}
          </button>
        </form>
        {presets.length > 0 && (
          <button
            type="button"
            onClick={() => {
              setManaging((value) => !value)
              setConfirm(null)
            }}
            aria-pressed={managing}
            className="shrink-0 rounded-md bg-neutral-800 px-4 py-1.5 text-sm font-medium text-neutral-100 hover:bg-neutral-700 active:bg-neutral-700"
          >
            {managing ? 'Done' : 'Manage'}
          </button>
        )}
      </div>

      {error && <p className="shrink-0 text-sm text-red-400">{error}</p>}

      {status && (
        <div className="shrink-0 rounded-md bg-neutral-900 px-2 py-1.5 text-sm text-neutral-300">
          <div className="flex items-start justify-between gap-2">
            <p>
              {status.message}
              {status.skipped.length > 0 &&
                ` ${plural(status.skipped.length, 'route')} couldn't be made right now:`}
            </p>
            <button
              type="button"
              onClick={() => setStatus(null)}
              className="shrink-0 text-neutral-500 hover:text-neutral-300"
            >
              Dismiss
            </button>
          </div>
          {status.skipped.length > 0 && (
            <ul className="mt-0.5 space-y-0.5 text-xs text-neutral-400">
              {status.skipped.map((item) => (
                <li key={routeLabel(item.route)}>
                  {routeLabel(item.route)}: {item.reason}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-auto">
        {loading && <p className="text-sm text-neutral-500">Loading presets…</p>}

        {!loading && !error && presets.length === 0 && (
          <p className="text-sm text-neutral-500">
            No presets yet. Set up routes in the Matrix, then name the routing above and save it.
          </p>
        )}

        {presets.length > 0 && (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(11rem,1fr))] gap-2">
            {presets.map((preset) => (
              <PresetTile
                key={preset.name}
                preset={preset}
                managing={managing}
                busy={busy}
                confirming={confirm?.name === preset.name ? confirm.action : null}
                onRecall={() => recall(preset.name)}
                onConfirm={(action) => setConfirm(action && { name: preset.name, action })}
                onUpdate={() =>
                  save(preset.name, `Updated “${preset.name}” with the current routing.`)
                }
                onDelete={() => remove(preset.name)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default PresetsView
