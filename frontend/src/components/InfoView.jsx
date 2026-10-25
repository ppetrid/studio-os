import { useCallback, useEffect, useState } from 'react'
import { fetchDestinations, fetchSources } from '../api'
import PortList from './PortList'

function usePorts(fetcher) {
  const [ports, setPorts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    fetcher()
      .then(setPorts)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [fetcher])

  useEffect(() => {
    load()
  }, [load])

  // Aliases are keyed by real names, so every listed port sharing them
  // (e.g. two identical devices) picks up the change.
  const onAliasChange = useCallback((target, alias) => {
    setPorts((prev) =>
      prev.map((port) =>
        port.client_name === target.client_name && port.name === target.name
          ? { ...port, alias }
          : port,
      ),
    )
  }, [])

  return { ports, loading, error, reload: load, onAliasChange }
}

function InfoView() {
  const sources = usePorts(fetchSources)
  const destinations = usePorts(fetchDestinations)

  const refreshAll = () => {
    sources.reload()
    destinations.reload()
  }

  return (
    <div className="flex h-full flex-col gap-1 p-1">
      <div className="flex shrink-0 justify-end">
        <button
          type="button"
          onClick={refreshAll}
          className="rounded-md bg-neutral-800 px-4 py-1.5 text-sm font-medium text-neutral-100 hover:bg-neutral-700 active:bg-neutral-700"
        >
          Refresh
        </button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-2 sm:flex-row">
        <PortList title="Sources" direction="sources" {...sources} />
        <PortList title="Destinations" direction="destinations" {...destinations} />
      </div>
    </div>
  )
}

export default InfoView
