# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project goal

A browser-based control surface for a home studio, meant to run on a Raspberry Pi (likely with a touchscreen). The first part is a MIDI router. Later parts are launching and managing a headless Pianoteq instance, and a custom Pi image that starts everything on boot.

Router features and where each one stands:

| Feature | Description | Status |
|---|---|---|
| Matrix mode | Conductive Labs MRCC-style source × destination grid; tap a cell to connect or disconnect | Implemented (`MatrixView` / `PortMatrix`) |
| Preset mode | Save the current routing as a named preset and recall it | Backend only. Called **scenes** in code (`SceneStore`, `/api/scenes`, `scenes.json`); no UI, no `api.js` client functions. Decided: presets will reference **devices by name**, falling back to real port names for unnamed ports. Re-cabling then only means updating the device, and renaming a device should eventually update the presets that use it |
| Aliases → devices | Friendly port names (e.g. "CP88" instead of "Miditech 8x8 Port 1 - Midi In"), aimed at multi-port 5-pin DIN interfaces | Implemented as **devices** (`devices.py`). Ports are named in the Ports Info view ("Rename"), where named ports carry a "Device" tag. The same name on a source and a destination links them into one device, and routing a device into itself is blocked |
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
  - Watch the naming: `Endpoint.device` is a (loose) **ALSA client name** query, not a user-defined device name from `devices.py`.
- **`backend.py`**: the `Backend` base class. It has list/connect/disconnect/close plus the shared name resolution in `_resolve`. `AlsaBackend` wraps `alsa_midi.SequencerClient` (client name `studio-router`) and lists only ports that are both `MIDI_GENERIC` and `HARDWARE` (`list_ports` requires every bit in the filter). Software clients such as Pianoteq will therefore probably not appear until that filter changes.
  - Resolution is case-insensitive. An exact match (`device` equals the client name and `port` equals the port name) wins. Otherwise it falls back to substring matching for loose CLI input, where `device` can match the client name or the port name. No match raises `PortNotFoundError` (404); more than one raises `AmbiguousPortError` (400).
  - Two identical devices (same client and port names) can't be told apart by name and always raise `AmbiguousPortError`.
- **`mock_backend.py`**: `MockBackend`, used for UI work. On first run it seeds `mock_ports.json`, which you can edit by hand to add fake devices. It saves connections to `mock_connections.json`. It also defines `SEED_DEVICES`, which `api/app.py` writes to `mock_devices.json` on first run in mock mode. The seed has one device whose self-route is blocked (Organ Rig) and one that allows it (Stage Piano). All three mock files are gitignored and get created as needed.
- **`router.py`**: `Router` keeps no state of its own. `Router.routes` reads the live connections from `backend.list_connections()` on every call. For ALSA that's the subscription graph; for the mock it's `mock_connections.json`.
  - Routes therefore survive app restarts and include connections made outside the app (e.g. with `aconnect`).
  - ALSA subscriptions do **not** survive a reboot or a device unplug. Restoring the routing at boot would be a separate feature.
  - Routes are built as `device=client_name, port=port name`, which is what the frontend's `portToEndpoint` matches against.
  - `connect` and `disconnect` are idempotent.
  - **Self-route blocking:** `Router` takes the `DeviceStore`. `connect` raises `SelfRouteBlockedError` (409) for a route from a device's source into its own destination, unless the device has `allow_self_route`. The check runs after the ports are resolved, so loose CLI names can't get around it. `blocked_routes` lists these routes for the matrix. `disconnect` is never blocked, so a self-route that existed before the device was named can still be removed.
- **`replace_routes()`**: makes the connections between listed ports match a desired set, at the resolved-port level. Scene activation uses it.
  - It resolves and checks every desired route first, so a bad or blocked route fails before anything changes.
  - It then disconnects everything not in the set, **including connections this app didn't make**, and connects the missing ones.
  - If a connect fails, it tries to restore what it removed.
- **`devices.py`**: `DeviceStore`, a store of user-named devices. Each device links **at most one source port and one destination port**, stored by real names as a `PortRef(client_name, port_name)`. The file is `{name: {"source"?: ref, "destination"?: ref, "allow_self_route"?: true}}`.
  - **The device is the stable identity.** A multi-port interface reports its In N and Out N jacks as a single ALSA port, but they may be cabled to different devices, and cables move. When you re-cable, only the device's ports change.
  - **`assign(direction, port, name)`** links a port to a device, creating the device if needed.
    - Names match case-insensitively: "cp88" joins an existing "CP88", and the API returns the canonical spelling.
    - A name already linked to a *different* port in the same direction raises `DeviceNameTakenError` (409).
    - Assigning a port removes it from any other device in that direction.
  - **A device whose ports are all cleared is dropped**, along with its `allow_self_route` setting.
  - `allow_self_route` can currently only be set by editing the file.
- **`scenes.py`**: `SceneStore`. Like `DeviceStore`, it's a JSON-file store that re-reads the file on every call. Scenes are stored as `{name: [route dicts]}`. The two stores default to `scenes.json` and `devices.json` relative to the CWD. In mock mode, devices use `mock_devices.json`, but scenes still use the real `scenes.json`.

### `api/`

- `app.py` builds the backend, `DeviceStore`, `Router` and `SceneStore` once at startup (`lifespan`) and puts them on `app.state`. `dependencies.py` hands them to endpoints through `Depends`.
- `schemas.py` contains Pydantic models with `to_domain()` / `from_domain()` that convert to and from the `studio_midi` dataclasses. It imports `alsa_midi.PortInfo`, so `alsa-midi` (and the system libasound) is needed even in mock mode.
- `errors.py` maps the domain exceptions to HTTP statuses:
  - `PortNotFoundError` and `SceneNotFoundError` → 404
  - `AmbiguousPortError` → 400
  - `SelfRouteBlockedError` and `DeviceNameTakenError` → 409
  - `ProcessedRouteNotImplementedError` → 501
  - Anything else is a 500. Signal a new expected failure with its own exception class, not a built-in like `KeyError`.
- Routes:
  - `/api/ports/{sources,destinations}`: each port includes its `device_name` for that direction.
  - `/api/ports/{sources,destinations}/device`:
    - PUT assigns a port to a device. The body is `{client_name, port_name, device}`, and the response is the updated device.
    - DELETE unassigns a port. The body is `{client_name, port_name}`.
    - Names always go in the JSON body, never in the URL, because client names can contain `/`.
  - `/api/routes`: GET lists routes, POST connects, DELETE disconnects. POST and DELETE both take a `RouteModel` JSON body. `GET /api/routes/blocked` lists the self-routes that `connect` would refuse.
  - `/api/scenes`: list, get, `PUT /{name}` (save), delete, `POST /{name}/activate`.
- CORS is fully open.

### `frontend/`

- React 19, Vite 8 and Tailwind v4 (via `@tailwindcss/vite`, with no Tailwind config file). Plain JSX, not TypeScript. No router library or state library: `App.jsx` switches views with `useState`, and each view fetches its own data through `src/api.js`.
- `routeUtils.js` is the bridge between the UI and the backend's name-based identity:
  - `portToEndpoint` turns a port into `{device: client_name, port: name}`.
  - `portKey` (`client_id:port_id`) is used only for React keys and pending-cell tracking. It is never sent to the API or persisted.
- `PortMatrix.jsx` is a CSS grid built for touch. Labels show a tooltip on tap. Column and row minimums are sized so roughly 14 columns fit on screen, and rows stay at least 2.75rem tall before the grid starts scrolling. The header height and label width have to stay literal values, because the size calculations subtract them. The comments in that file explain why.
- Ports display their `device_name` if one is set, otherwise the ALSA client name, with the real `client · port` name as a muted second line. Keep the real name visible somewhere so the physical port can still be identified.
- The matrix draws blocked routes (from `/api/routes/blocked`) as empty, disabled cells with a not-allowed cursor, unless that route is currently connected.
- `api.js` throws errors carrying FastAPI's `detail` message when there is one, so views can show it directly.
- Visual style is dark neutral with amber for active and highlighted elements.
