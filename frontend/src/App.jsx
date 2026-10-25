import { useState } from 'react'
import InfoView from './components/InfoView'
import MatrixView from './components/MatrixView'
import PresetsView from './components/PresetsView'

const VIEWS = [
  { id: 'matrix', label: 'Matrix', component: MatrixView },
  { id: 'presets', label: 'Presets', component: PresetsView },
  { id: 'info', label: 'Ports Info', component: InfoView },
]

function App() {
  const [view, setView] = useState('matrix')
  const ActiveView = VIEWS.find((item) => item.id === view).component

  return (
    <div className="flex h-full flex-col overflow-hidden bg-neutral-950">
      <header className="flex shrink-0 items-center justify-between gap-2 border-b border-neutral-800 px-2 py-1">
        <h1 className="truncate text-sm font-bold text-neutral-100">Studio MIDI Router</h1>
        <nav className="flex shrink-0 gap-1 rounded-lg bg-neutral-900 p-1 text-sm font-medium">
          {VIEWS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setView(item.id)}
              className={`rounded-md px-4 py-1.5 transition-colors ${
                view === item.id
                  ? 'bg-neutral-700 text-neutral-100'
                  : 'text-neutral-400 active:bg-neutral-800'
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="min-h-0 flex-1">
        <ActiveView />
      </main>
    </div>
  )
}

export default App
