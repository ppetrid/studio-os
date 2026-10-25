import { Fragment, useState } from 'react'
import { findRoute, portKey } from '../routeUtils'

// Columns shrink as they're added, but never below the size that fits
// this many on screen at once — beyond that the grid scrolls.
const MIN_VISIBLE_COLS = 14

// Fixed chrome sizes for the header row / label column. These have to be
// literal (not "auto"/a range) so they can be subtracted from 100% below —
// otherwise the row/column minimums are computed against the *whole* grid
// height/width, which already includes this chrome, and the grid always
// overflows by exactly this much no matter how large the container is.
const HEADER_ROW_HEIGHT = '2.5rem'
const LABEL_COL_WIDTH = '7rem'

// Absolute floor so rows stay touch-usable when there are enough sources,
// or the container is short enough, that dividing the available height
// evenly between them would otherwise shrink rows past this — beyond that
// the grid scrolls instead of shrinking further.
const MIN_ROW_HEIGHT = '2.75rem'

function portLabel(port) {
  const realName = `${port.client_name ?? '(unknown)'} · ${port.name}`
  return port.device_name ? `${port.device_name} (${realName})` : realName
}

// Primary label: the user's device name when the port has one, else the
// ALSA client name.
function portPrimaryLabel(port) {
  return port.device_name || port.client_name || '(unknown)'
}

// Secondary (muted) label: real client · port name, so the physical port
// stays identifiable even when the primary label is a device name.
function portSecondaryLabel(port) {
  return port.device_name ? `${port.client_name ?? '(unknown)'} · ${port.name}` : port.name
}

const CELL_CONNECTED =
  'block border-amber-300/40 bg-amber-400 shadow-[0_0_6px_2px_rgba(251,191,36,0.65)]'
const CELL_BLOCKED = 'block cursor-not-allowed border-transparent bg-transparent'
const CELL_OPEN =
  'block border-neutral-700 bg-neutral-800 hover:border-neutral-500 hover:bg-neutral-700'

function TapLabel({ id, tooltip, openId, onOpen, tooltipClassName, children }) {
  const isOpen = openId === id

  return (
    <div
      className="relative flex min-w-0 w-full flex-col overflow-hidden"
      title={tooltip}
      onClick={(event) => {
        event.stopPropagation()
        onOpen(isOpen ? null : id)
      }}
    >
      {children}
      {isOpen && (
        <div
          className={`absolute z-30 max-w-[70vw] rounded bg-neutral-800 px-2 py-1 text-xs whitespace-nowrap text-neutral-100 shadow-lg ${tooltipClassName}`}
        >
          {tooltip}
        </div>
      )}
    </div>
  )
}

function PortMatrix({ sources, destinations, routes, blockedRoutes, pendingKeys, onToggle }) {
  const [hoveredSource, setHoveredSource] = useState(null)
  const [hoveredDest, setHoveredDest] = useState(null)
  const [openTooltip, setOpenTooltip] = useState(null)

  if (sources.length === 0 || destinations.length === 0) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border border-neutral-800 bg-neutral-900 p-6 text-sm text-neutral-500">
        No ports available to patch.
      </div>
    )
  }

  return (
    <div
      className="h-full overflow-auto rounded-lg border border-neutral-800 bg-neutral-900 p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]"
      onClick={() => setOpenTooltip(null)}
    >
      <div
        className="grid h-full w-full"
        style={{
          gridTemplateColumns: `${LABEL_COL_WIDTH} repeat(${destinations.length}, minmax(calc((100% - ${LABEL_COL_WIDTH}) / ${MIN_VISIBLE_COLS}), 1fr))`,
          gridTemplateRows: `${HEADER_ROW_HEIGHT} repeat(${sources.length}, minmax(max(${MIN_ROW_HEIGHT}, calc((100% - ${HEADER_ROW_HEIGHT}) / ${sources.length})), 1fr))`,
        }}
      >
        <div className="sticky top-0 left-0 z-20 bg-neutral-900" />

        {destinations.map((dest) => {
          const destKey = portKey(dest)
          return (
            <div
              key={destKey}
              className="sticky top-0 z-10 flex items-center justify-center bg-neutral-900 px-1 py-1"
            >
              <TapLabel
                id={`dest:${destKey}`}
                tooltip={portLabel(dest)}
                openId={openTooltip}
                onOpen={setOpenTooltip}
                tooltipClassName="top-full left-1/2 mt-1 -translate-x-1/2"
              >
                <div
                  className={`truncate text-center text-[11px] font-medium ${
                    hoveredDest === destKey ? 'text-amber-300' : 'text-neutral-300'
                  }`}
                >
                  {portPrimaryLabel(dest)}
                </div>
                <div className="truncate text-center text-[10px] text-neutral-500">
                  {portSecondaryLabel(dest)}
                </div>
              </TapLabel>
            </div>
          )
        })}

        {sources.map((src) => {
          const srcKey = portKey(src)
          return (
            <Fragment key={srcKey}>
              <div className="sticky left-0 z-10 flex items-center justify-end bg-neutral-900 pr-2">
                <TapLabel
                  id={`src:${srcKey}`}
                  tooltip={portLabel(src)}
                  openId={openTooltip}
                  onOpen={setOpenTooltip}
                  tooltipClassName="top-full right-0 mt-1"
                >
                  <div
                    className={`truncate text-right text-[11px] font-medium ${
                      hoveredSource === srcKey ? 'text-amber-300' : 'text-neutral-200'
                    }`}
                  >
                    {portPrimaryLabel(src)}
                  </div>
                  <div className="truncate text-right text-[10px] text-neutral-500">
                    {portSecondaryLabel(src)}
                  </div>
                </TapLabel>
              </div>

              {destinations.map((dest) => {
                const destKey = portKey(dest)
                const connected = Boolean(findRoute(routes, src, dest))
                // A blocked route that's already connected (e.g. it predates
                // naming the device) stays tappable, so it can be disconnected.
                const blocked = !connected && Boolean(findRoute(blockedRoutes, src, dest))
                const cellKey = `${srcKey}->${destKey}`
                const pending = pendingKeys.has(cellKey)

                return (
                  <div
                    key={cellKey}
                    className="p-[3px]"
                    onMouseEnter={() => {
                      setHoveredSource(srcKey)
                      setHoveredDest(destKey)
                    }}
                    onMouseLeave={() => {
                      setHoveredSource(null)
                      setHoveredDest(null)
                    }}
                  >
                    <button
                      type="button"
                      disabled={pending || blocked}
                      onClick={() => onToggle(src, dest, connected)}
                      aria-pressed={connected}
                      title={`${portLabel(src)} → ${portLabel(dest)}${
                        blocked ? ' (blocked: same device)' : ''
                      }`}
                      className={[
                        'h-full w-full rounded-sm border transition-all duration-100',
                        !blocked && (pending ? 'cursor-wait opacity-50' : 'cursor-pointer'),
                        connected ? CELL_CONNECTED : blocked ? CELL_BLOCKED : CELL_OPEN,
                      ]
                        .filter(Boolean)
                        .join(' ')}
                    />
                  </div>
                )
              })}
            </Fragment>
          )
        })}
      </div>
    </div>
  )
}

export default PortMatrix
