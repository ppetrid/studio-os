async function getJSON(path) {
  const response = await fetch(path)
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`)
  }
  return response.json()
}

export function fetchSources() {
  return getJSON('/api/ports/sources')
}

export function fetchDestinations() {
  return getJSON('/api/ports/destinations')
}

export function fetchRoutes() {
  return getJSON('/api/routes')
}

async function sendJSON(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(`${method} ${path} returned ${response.status}`)
  }
  if (response.status === 204) {
    return null
  }
  return response.json()
}

export function createRoute(route) {
  return sendJSON('POST', '/api/routes', route)
}

export function deleteRoute(route) {
  return sendJSON('DELETE', '/api/routes', route)
}
