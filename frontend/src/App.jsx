import { useState } from 'react'
import InfoView from './components/InfoView'
import MatrixView from './components/MatrixView'

function App() {
  const [view, setView] = useState('matrix')

  return (
    <div className="flex h-full flex-col overflow-hidden bg-neutral-950">
      <header className="flex shrink-0 items-center justify-between gap-2 border-b border-neutral-800 px-2 py-1">
        <h1 className="truncate text-sm font-bold text-neutral-100">Studio MIDI Router</h1>
        <nav className="flex shrink-0 gap-1 rounded-lg bg-neutral-900 p-1 text-sm font-medium">
          <button
            type="button"
            onClick={() => setView('matrix')}
            className={`rounded-md px-4 py-1.5 transition-colors ${
              view === 'matrix'
                ? 'bg-neutral-700 text-neutral-100'
                : 'text-neutral-400 active:bg-neutral-800'
            }`}
          >
            Matrix
          </button>
          <button
            type="button"
            onClick={() => setView('info')}
            className={`rounded-md px-4 py-1.5 transition-colors ${
              view === 'info'
                ? 'bg-neutral-700 text-neutral-100'
                : 'text-neutral-400 active:bg-neutral-800'
            }`}
          >
            Ports Info
          </button>
        </nav>
      </header>

      <main className="min-h-0 flex-1">
        {view === 'matrix' ? <MatrixView /> : <InfoView />}
      </main>
    </div>
  )
}

export default App
