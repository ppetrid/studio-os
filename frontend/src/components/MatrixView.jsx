import { useCallback, useEffect, useState } from 'react'
import {
  createRoute,
  deleteRoute,
  fetchBlockedRoutes,
  fetchDestinations,
  fetchRoutes,
  fetchSources,
} from '../api'
import { portKey, portToEndpoint, routesEqual } from '../routeUtils'
import PortMatrix from './PortMatrix'

function MatrixView() {
  const [sources, setSources] = useState([])
  const [destinations, setDestinations] = useState([])
  const [routes, setRoutes] = useState([])
  const [blockedRoutes, setBlockedRoutes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [pendingKeys, setPendingKeys] = useState(new Set())

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    Promise.all([fetchSources(), fetchDestinations(), fetchRoutes(), fetchBlockedRoutes()])
      .then(([sourcePorts, destinationPorts, existingRoutes, blocked]) => {
        setSources(sourcePorts)
        setDestinations(destinationPorts)
        setRoutes(existingRoutes)
        setBlockedRoutes(blocked)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const toggle = useCallback(async (source, destination, connected) => {
    const cellKey = `${portKey(source)}->${portKey(destination)}`
    const route = {
      source: portToEndpoint(source),
      destination: portToEndpoint(destination),
    }

    setPendingKeys((prev) => new Set(prev).add(cellKey))
    setError(null)

    try {
      if (connected) {
        await deleteRoute(route)
        setRoutes((prev) => prev.filter((r) => !routesEqual(r, route)))
      } else {
        const created = await createRoute(route)
        setRoutes((prev) => [...prev, created])
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setPendingKeys((prev) => {
        const next = new Set(prev)
        next.delete(cellKey)
        return next
      })
    }
  }, [])

  return (
    <div className="flex h-full flex-col gap-1 p-1">
      {loading && <p className="shrink-0 text-sm text-neutral-500">Loading matrix…</p>}
      {error && <p className="shrink-0 text-sm text-red-400">{error}</p>}
      {!loading && (
        <div className="min-h-0 flex-1">
          <PortMatrix
            sources={sources}
            destinations={destinations}
            routes={routes}
            blockedRoutes={blockedRoutes}
            pendingKeys={pendingKeys}
            onToggle={toggle}
          />
        </div>
      )}
    </div>
  )
}

export default MatrixView
