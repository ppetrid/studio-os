function PortList({ title, ports, loading, error }) {
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
            <li
              key={`${port.client_id}:${port.port_id}`}
              className="min-w-0 py-1"
            >
              <div className="truncate font-medium text-neutral-100">
                {port.alias || port.client_name || '(unknown)'}
              </div>
              <div className="truncate text-sm text-neutral-400">
                {port.alias
                  ? `${port.client_name ?? '(unknown)'} · ${port.name}`
                  : port.name}{' '}
                <span className="text-neutral-600">
                  ({port.client_id}:{port.port_id})
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default PortList
