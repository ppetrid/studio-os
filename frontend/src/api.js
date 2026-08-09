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
