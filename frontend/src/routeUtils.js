export function portToEndpoint(port) {
  return { device: port.client_name ?? '', port: port.name }
}

function endpointsEqual(a, b) {
  return a.device === b.device && a.port === b.port
}

export function routesEqual(a, b) {
  return (
    endpointsEqual(a.source, b.source) &&
    endpointsEqual(a.destination, b.destination)
  )
}

export function findRoute(routes, sourcePort, destPort) {
  const candidate = {
    source: portToEndpoint(sourcePort),
    destination: portToEndpoint(destPort),
  }
  return routes.find((route) => routesEqual(route, candidate))
}

export function portKey(port) {
  return `${port.client_id}:${port.port_id}`
}
