# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project goal

A browser-based control surface for a home studio, meant to run on a Raspberry Pi (likely with a touchscreen). The first part is a MIDI router. Later parts are launching and managing a headless Pianoteq instance, and a custom Pi image that starts everything on boot.

Router features and where each one stands:

| Feature | Description | Status |
|---|---|---|
| Matrix mode | Conductive Labs MRCC-style source × destination grid; tap a cell to connect or disconnect | Implemented (`MatrixView` / `PortMatrix`) |
| Preset mode | Save the current routing as a named preset and recall it | Implemented (`presets.py`, `PresetsView`). Presets reference **devices by name**, falling back to real port names for unnamed ports, so re-cabling only means updating the device. Not done yet: renaming a device doesn't update presets, and there's no restore of the last preset at boot |
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
python main.py save-preset <name>                         # snapshot the current routing
python main.py save-preset <name> "CP88:TG77" ...         # or explicit routes between device names
python main.py recall-preset <name>                       # prints any skipped routes
python main.py list-presets
```

```shell
cd frontend
npm install
npm run dev       # Vite on :5173, proxies /api to localhost:8000
npm run lint      # oxlint (.oxlintrc.json)
npm run build     # outputs frontend/dist; FastAPI serves it at / when present
```

```shell
deploy/install.sh   # on the Pi, in a clone: sets up .venv, installs + restarts the systemd service
```

**Deployment:** the Pi runs a git clone, and updating it means `git pull && deploy/install.sh`. The Pi has no Node, so **`frontend/dist` is committed**. Run `npm run build` and commit `dist` together with any `frontend/src` change, or the Pi keeps serving the old UI.
- `deploy/install.sh` renders `deploy/studio-os.service` (filling the `@USER@`/`@APP_DIR@`/`@PORT@` placeholders) into `/etc/systemd/system/`, then restarts the service and checks that it responds.
- Production is a single uvicorn process serving both `frontend/dist` and `/api`, with no nginx.
- `devices.json` and `presets.json` are gitignored. They're live config edited through the UI, so each machine keeps its own. Any new data file should be gitignored too, or `git pull` on the Pi will conflict with it.

There is no test suite and no Python linter or formatter config yet. To check real ALSA routing, compare against `aconnect -l`.

In development, open `:5173`. `:8000/` serves the committed `frontend/dist` build, not your current source.

## Architecture

The backend is a Python package, `studio_midi/`, with no web dependencies. A thin FastAPI layer, `api/`, sits on top of it. The frontend is a separate Vite app in `frontend/`.

### `studio_midi/`

- **`models.py`**: `Endpoint(device, port?)` and `Route(source, destination, processor?)`. Both are frozen dataclasses and are hashed into sets. An `Endpoint` identifies a port by **name**, never by ALSA client:port ids, because ALSA reassigns those on reconnect or restart. `Route.processor` is reserved for future processed routes (filtering, mapping, and so on). Any non-null processor currently raises `ProcessedRouteNotImplementedError`, which the API returns as 501.
  - Watch the naming: `Endpoint.device` is a (loose) **ALSA client name** query, not a user-defined device name from `devices.py`.
- **`backend.py`**: the `Backend` base class. It has list/connect/disconnect/close plus the shared name resolution in `_resolve`. `AlsaBackend` wraps `alsa_midi.SequencerClient` (client name `studio-router`) and lists only ports that are both `MIDI_GENERIC` and `HARDWARE` (`list_ports` requires every bit in the filter). Software clients such as Pianoteq will therefore probably not appear until that filter changes.
  - Resolution is case-insensitive. An exact match (`device` equals the client name and `port` equals the port name) wins. Otherwise it falls back to substring matching for loose CLI input, where `device` can match the client name or the port name. No match raises `PortNotFoundError` (404); more than one raises `AmbiguousPortError` (400).
  - Two identical devices (same client and port names) can't be told apart by name and always raise `AmbiguousPortError`.
- **`mock_backend.py`**: `MockBackend`, used for UI work. On first run it seeds `mock_ports.json`, which you can edit by hand to add fake devices. It saves connections to `mock_connections.json`. It also defines `SEED_DEVICES`, which `api/app.py` writes to `mock_devices.json` on first run in mock mode. The seed has one device whose self-route is blocked (Organ Rig) and one that allows it (Stage Piano). All the `mock_*.json` files are gitignored and get created as needed.
- **`router.py`**: `Router` keeps no state of its own. `Router.routes` reads the live connections from `backend.list_connections()` on every call. For ALSA that's the subscription graph; for the mock it's `mock_connections.json`.
  - Routes therefore survive app restarts and include connections made outside the app (e.g. with `aconnect`).
  - ALSA subscriptions do **not** survive a reboot or a device unplug. Restoring the routing at boot would be a separate feature.
  - Routes are built as `device=client_name, port=port name`, which is what the frontend's `portToEndpoint` matches against.
  - `connect` and `disconnect` are idempotent.
  - **Self-route blocking:** `Router` takes the `DeviceStore`. `connect` raises `SelfRouteBlockedError` (409) for a route from a device's source into its own destination, unless the device has `allow_self_route`. The check runs after the ports are resolved, so loose CLI names can't get around it. `blocked_routes` lists these routes for the matrix. `disconnect` is never blocked, so a self-route that existed before the device was named can still be removed.
- **`replace_routes()`**: makes the connections between listed ports match a desired set, at the resolved-port level. Preset recall uses it.
  - It resolves and checks every desired route first. Routes that can't be made right now are **skipped, not fatal**: a port that isn't plugged in or is ambiguous, a blocked self-route, or a processor. They're returned as `{route: reason}`.
  - It then disconnects everything not in the set, **including connections this app didn't make**, and connects the missing ones.
  - If a connect fails, it tries to restore what it removed.
  - `matches(routes)` reports whether the current connections are exactly the routes from that set that can be made right now. It's what marks a preset as "current".
- **`devices.py`**: `DeviceStore`, a store of user-named devices. Each device links **at most one source port and one destination port**, stored by real names as a `PortRef(client_name, port_name)`. The file is `{name: {"source"?: ref, "destination"?: ref, "allow_self_route"?: true}}`.
  - **The device is the stable identity.** A multi-port interface reports its In N and Out N jacks as a single ALSA port, but they may be cabled to different devices, and cables move. When you re-cable, only the device's ports change.
  - **`assign(direction, port, name)`** links a port to a device, creating the device if needed.
    - Names match case-insensitively: "cp88" joins an existing "CP88", and the API returns the canonical spelling.
    - A name already linked to a *different* port in the same direction raises `DeviceNameTakenError` (409).
    - Assigning a port removes it from any other device in that direction.
  - **A device whose ports are all cleared is dropped**, along with its `allow_self_route` setting.
  - `allow_self_route` can currently only be set by editing the file.
- **`presets.py`**: `PresetStore`, the named presets ("scenes" in older code and docs).
  - **Format:** each route end is a `DeviceRef(name)` or a `PortRef` for ports without a device. On disk that's `{name: [{"source": {"device": "CP88"} | {"client_name", "port_name"}, "destination": …}]}`.
  - **Saving:** `save_current()` snapshots `Router.routes` with `capture()`. A port belonging to a device in that direction is stored as the device name.
  - **Recalling:** `recall()` turns device names into their current ports, then calls `replace_routes`. It returns `SkippedRoute`s for an unknown device, a device missing that direction, and anything `replace_routes` skipped.
- **Stores:** `DeviceStore` and `PresetStore` are JSON-file stores that re-read the file on every call. They default to `devices.json` and `presets.json` relative to the CWD. In mock mode they use `mock_devices.json` and `mock_presets.json`, so presets of fake devices never land in the real files.

### `api/`

- `app.py` builds the backend, `DeviceStore`, `Router` and `PresetStore` once at startup (`lifespan`) and puts them on `app.state`. `dependencies.py` hands them to endpoints through `Depends`.
- `schemas.py` contains Pydantic models with `to_domain()` / `from_domain()` that convert to and from the `studio_midi` dataclasses. It imports `alsa_midi.PortInfo`, so `alsa-midi` (and the system libasound) is needed even in mock mode.
- `errors.py` maps the domain exceptions to HTTP statuses:
  - `PortNotFoundError` and `PresetNotFoundError` → 404
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
  - `/api/presets`: the preset name always goes in the JSON body `{name}`, because names can contain `/`.
    - GET lists presets with their routes and a `current` flag.
    - PUT saves the current routing under a name, replacing any preset with that name.
    - DELETE deletes a preset.
    - `POST /api/presets/recall` returns `{routes, skipped: [{route, reason}]}`.
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
- `PresetsView.jsx` is built for live use:
  - Tapping a tile recalls it.
  - Update and Delete only appear in Manage mode, each with a confirm step.
  - The tile flagged `current` glows amber like a connected matrix cell.
  - Skipped routes from a recall are listed with their reasons.
  - The list reloads after every action, because any action can change which preset is current.
- Visual style is dark neutral with amber for active and highlighted elements.
