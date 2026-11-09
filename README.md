# studio-os

## Run the development server

### Python

```shell
uvicorn api.app:app --reload
```

To run with mock midi inputs / outputs

```shell
STUDIO_MIDI_BACKEND=mock uvicorn api.app:app --reload
```

### UI

```shell
cd frontend
npm run dev
```

Navigate to http://localhost:5173/

## Run on the Raspberry Pi

On the Pi:

```shell
git clone <repo-url> studio-os
cd studio-os
deploy/install.sh
```

`install.sh` sets up `.venv`, installs the `studio-os` systemd service (from
`deploy/studio-os.service`) and restarts it. The app is then on port 8000,
serving the UI and the API, and starts on boot. It's safe to re-run.

To update:

```shell
git pull && deploy/install.sh
```

- Node isn't needed on the Pi, because the built frontend (`frontend/dist`) is
  committed. Run `npm run build` and commit `dist` along with any frontend
  change.
- `devices.json` and `presets.json` aren't in git. Each machine keeps its own,
  edited through the UI.
- Stop any dev `uvicorn` on the Pi first, since the service needs port 8000.
- The Pi user must be in the `audio` group. If `pip` fails building
  `alsa-midi`, run `sudo apt install libasound2-dev` on the Pi.
- Logs: `journalctl -u studio-os -f`.
