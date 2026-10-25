// Prefer the API's own explanation (FastAPI's `detail`) over a bare status.
async function errorMessage(response, fallback) {
  try {
    const body = await response.json()
    if (typeof body.detail === 'string') {
      return body.detail
    }
  } catch {
    // Not a JSON body; use the fallback.
  }
  return fallback
}

async function getJSON(path) {
  const response = await fetch(path)
  if (!response.ok) {
    throw new Error(await errorMessage(response, `${path} returned ${response.status}`))
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

export function fetchBlockedRoutes() {
  return getJSON('/api/routes/blocked')
}

async function sendJSON(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(
      await errorMessage(response, `${method} ${path} returned ${response.status}`),
    )
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

// `direction` is 'sources' or 'destinations'. Giving a source and a
// destination the same device name links them as one device.
export function assignDevice(direction, port, device) {
  return sendJSON('PUT', `/api/ports/${direction}/device`, {
    client_name: port.client_name,
    port_name: port.name,
    device,
  })
}

export function unassignDevice(direction, port) {
  return sendJSON('DELETE', `/api/ports/${direction}/device`, {
    client_name: port.client_name,
    port_name: port.name,
  })
}
