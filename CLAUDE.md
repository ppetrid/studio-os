# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project goal

A browser-based control surface for a home studio, meant to run on a Raspberry Pi (likely with a touchscreen). The first part is a MIDI router. Later parts are launching and managing a headless Pianoteq instance, and a custom Pi image that starts everything on boot.

Router features and where each one stands:

| Feature | Description | Status |
|---|---|---|
| Matrix mode | Conductive Labs MRCC-style source × destination grid; tap a cell to connect or disconnect | Implemented (`MatrixView` / `PortMatrix`) |
| Preset mode | Save the current routing as a named preset and recall it | Backend only. Called **scenes** in code (`SceneStore`, `/api/scenes`, `scenes.json`); no UI, no `api.js` client functions |
| Aliases | Friendly port names (e.g. "CP88" instead of "Miditech 8x8 Port 1 - Midi In"), aimed at multi-port 5-pin DIN interfaces | Read-only. `AliasStore` has get/set/delete, but only `get` is exposed (as `alias` on port listings). Edit `aliases.json` by hand for now |
| Pianoteq | Launch and manage headless Pianoteq | Not started |
| Pi image | Custom image that autostarts the app | Not started |

## Commands

Run the backend from the **repo root**. Every JSON store path is relative to the current working directory (see below).

```shell
pip install -r requirements.txt                          # Python 3.10+ (uses match and X | None)
uvicorn api.app:app --reload                              # real ALSA backend, :8000
STUDIO_MIDI_BACKEND=mock uvicorn api.app:app --reload     # fake ports, no MIDI hardware needed

python main.py connect <source> <destination>             # CLI; always uses real ALSA
python main.py save-scene <name> "src:dst" ...
python main.py activate-scene <name>
python main.py list-scenes
```

```shell
cd frontend
npm install
npm run dev       # Vite on :5173, proxies /api to localhost:8000
npm run lint      # oxlint (.oxlintrc.json)
npm run build     # outputs frontend/dist; FastAPI serves it at / when present
```

There is no test suite and no Python linter or formatter config yet. To check real ALSA routing, compare against `aconnect -l`.

In development, open `:5173`. If `frontend/dist` exists, `:8000/` serves that old build, not your current source.

## Architecture

The backend is a Python package, `studio_midi/`, with no web dependencies. A thin FastAPI layer, `api/`, sits on top of it. The frontend is a separate Vite app in `frontend/`.

### `studio_midi/`

- **`models.py`**: `Endpoint(device, port?)` and `Route(source, destination, processor?)`. Both are frozen dataclasses and are hashed into sets. An `Endpoint` identifies a port by **name**, never by ALSA client:port ids, because ALSA reassigns those on reconnect or restart. `Route.processor` is reserved for future processed routes (filtering, mapping, and so on). Any non-null processor currently raises `ProcessedRouteNotImplementedError`, which the API returns as 501.
- **`backend.py`**: the `Backend` base class. It has list/connect/disconnect/close plus the shared name resolution in `_resolve`. `AlsaBackend` wraps `alsa_midi.SequencerClient` (client name `studio-router`) and lists only ports that are both `MIDI_GENERIC` and `HARDWARE` (`list_ports` requires every bit in the filter). Software clients such as Pianoteq will therefore probably not appear until that filter changes.
  - Resolution is case-insensitive. An exact match (`device` equals the client name and `port` equals the port name) wins. Otherwise it falls back to substring matching for loose CLI input, where `device` can match the client name or the port name. No match raises `PortNotFoundError` (404); more than one raises `AmbiguousPortError` (400).
  - Two identical devices (same client and port names) can't be told apart by name and always raise `AmbiguousPortError`.
- **`mock_backend.py`**: `MockBackend`, used for UI work. On first run it seeds `mock_ports.json`, which you can edit by hand to add fake devices. It saves connections to `mock_connections.json`. It also defines `SEED_ALIASES`, which `api/app.py` writes to `mock_aliases.json` on first run in mock mode. All three mock files are gitignored and get created as needed.
- **`router.py`**: `Router` keeps no state of its own. `Router.routes` reads the live connections from `backend.list_connections()` on every call. For ALSA that's the subscription graph; for the mock it's `mock_connections.json`.
  - Routes therefore survive app restarts and include connections made outside the app (e.g. with `aconnect`).
  - ALSA subscriptions do **not** survive a reboot or a device unplug. Restoring the routing at boot would be a separate feature.
  - Routes are built as `device=client_name, port=port name`, which is what the frontend's `portToEndpoint` matches against.
  - `connect` and `disconnect` are idempotent.
- **`replace_routes()`**: makes the connections between listed ports match a desired set, at the resolved-port level. Scene activation uses it.
  - It resolves every desired route first, so a bad port fails before anything changes.
  - It then disconnects everything not in the set, **including connections this app didn't make**, and connects the missing ones.
  - If a connect fails, it tries to restore what it removed.
- **`scenes.py`** / **`aliases.py`**: JSON-file stores that re-read the file on every call. Scenes are stored as `{name: [route dicts]}`. Aliases are stored as `{client_name: {port_name: alias}}`. Both default to `scenes.json` and `aliases.json` relative to the CWD. In mock mode, scenes still use the real `scenes.json`.

### `api/`

- `app.py` builds the backend, `Router`, `SceneStore` and `AliasStore` once at startup (`lifespan`) and puts them on `app.state`. `dependencies.py` hands them to endpoints through `Depends`.
- `schemas.py` contains Pydantic models with `to_domain()` / `from_domain()` that convert to and from the `studio_midi` dataclasses. It imports `alsa_midi.PortInfo`, so `alsa-midi` (and the system libasound) is needed even in mock mode.
- `errors.py` maps domain exceptions to HTTP statuses. It maps **every** `KeyError` to 404, which is meant for unknown scenes. A bug that raises `KeyError` will therefore show up as a 404, not a 500.
- Routes:
  - `/api/ports/{sources,destinations}`
  - `/api/routes`: GET lists routes, POST connects, DELETE disconnects. POST and DELETE both take a `RouteModel` JSON body.
  - `/api/scenes`: list, get, `PUT /{name}` (save), delete, `POST /{name}/activate`.
- CORS is fully open.

### `frontend/`

- React 19, Vite 8 and Tailwind v4 (via `@tailwindcss/vite`, with no Tailwind config file). Plain JSX, not TypeScript. No router library or state library: `App.jsx` switches views with `useState`, and each view fetches its own data through `src/api.js`.
- `routeUtils.js` is the bridge between the UI and the backend's name-based identity:
  - `portToEndpoint` turns a port into `{device: client_name, port: name}`.
  - `portKey` (`client_id:port_id`) is used only for React keys and pending-cell tracking. It is never sent to the API or persisted.
- `PortMatrix.jsx` is a CSS grid built for touch. Labels show a tooltip on tap. Column and row minimums are sized so roughly 14 columns fit on screen, and rows stay at least 2.75rem tall before the grid starts scrolling. The header height and label width have to stay literal values, because the size calculations subtract them. The comments in that file explain why.
- Ports display as the alias if one is set, otherwise the device name, with the real `client · port` name as a muted second line. Keep the real name visible somewhere so the physical port can still be identified.
- Visual style is dark neutral with amber for active and highlighted elements.
