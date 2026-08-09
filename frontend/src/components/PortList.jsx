function PortList({ title, ports, loading, error }) {
  return (
    <div className="flex-1 rounded border border-slate-300 p-4">
      <h2 className="mb-3 text-lg font-semibold text-slate-800">{title}</h2>

      {loading && <p className="text-sm text-slate-500">Loading…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {!loading && !error && ports.length === 0 && (
        <p className="text-sm text-slate-500">No ports found.</p>
      )}

      {!loading && !error && ports.length > 0 && (
        <ul className="divide-y divide-slate-200">
          {ports.map((port) => (
            <li
              key={`${port.client_id}:${port.port_id}`}
              className="py-2"
            >
              <div className="font-medium text-slate-900">
                {port.client_name ?? '(unknown)'}
              </div>
              <div className="text-sm text-slate-500">
                {port.name}{' '}
                <span className="text-slate-400">
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
