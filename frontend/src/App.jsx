import { useCallback, useEffect, useState } from 'react'
import { fetchDestinations, fetchSources } from './api'
import PortList from './components/PortList'

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

  return { ports, loading, error, reload: load }
}

function App() {
  const sources = usePorts(fetchSources)
  const destinations = usePorts(fetchDestinations)

  const refreshAll = () => {
    sources.reload()
    destinations.reload()
  }

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Studio MIDI Router</h1>
        <button
          type="button"
          onClick={refreshAll}
          className="rounded bg-slate-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700"
        >
          Refresh
        </button>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row">
        <PortList title="Sources" {...sources} />
        <PortList title="Destinations" {...destinations} />
      </div>
    </div>
  )
}

export default App
