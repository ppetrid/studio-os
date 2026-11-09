#!/usr/bin/env bash
# Sets up and (re)starts studio-os as a systemd service on this machine.
#
# Run it on the Pi from a clone of the repo, after cloning and after each
# `git pull`. Safe to re-run.
set -euo pipefail

PORT=8000
SERVICE=studio-os
UNIT_PATH="/etc/systemd/system/$SERVICE.service"

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="$(id -un)"
cd "$APP_DIR"

if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
  echo "error: Python 3.10+ is required, found $(python3 --version)" >&2
  exit 1
fi

if [ ! -d frontend/dist ]; then
  echo "warning: frontend/dist is missing, so only the API will be served" >&2
fi

# Otherwise the service can't bind, and the health check below would be
# answered by whatever is holding the port.
if ! systemctl is-active --quiet "$SERVICE" && ss -Hltn "sport = :$PORT" | grep -q .; then
  echo "error: something else is listening on port $PORT (a dev uvicorn?). Stop it first." >&2
  exit 1
fi

if ! id -nG "$RUN_USER" | grep -qw audio; then
  echo "warning: $RUN_USER isn't in the audio group, so ALSA access will likely fail." >&2
  echo "         Fix with: sudo usermod -aG audio $RUN_USER" >&2
fi

echo "==> Python dependencies"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install --quiet --disable-pip-version-check -r requirements.txt

echo "==> systemd unit"
unit="$(sed -e "s|@USER@|$RUN_USER|g" \
            -e "s|@APP_DIR@|$APP_DIR|g" \
            -e "s|@PORT@|$PORT|g" \
            deploy/studio-os.service)"

if cmp -s <(printf '%s\n' "$unit") "$UNIT_PATH"; then
  echo "$UNIT_PATH is up to date"
else
  echo "Installing $UNIT_PATH"
  printf '%s\n' "$unit" | sudo tee "$UNIT_PATH" >/dev/null
  sudo systemctl daemon-reload
  sudo systemctl enable "$SERVICE"
fi

echo "==> Restarting $SERVICE"
sudo systemctl restart "$SERVICE"

for _ in $(seq 30); do
  if .venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$PORT/api/ports/sources', timeout=1)" 2>/dev/null; then
    echo "$SERVICE is up on port $PORT"
    exit 0
  fi
  sleep 0.5
done

echo "error: $SERVICE didn't respond on port $PORT. Recent logs:" >&2
sudo journalctl -u "$SERVICE" -n 30 --no-pager >&2
exit 1
