import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from studio_midi.backend import AlsaBackend, Backend
from studio_midi.devices import DeviceStore
from studio_midi.mock_backend import SEED_DEVICES, MockBackend
from studio_midi.presets import PresetStore
from studio_midi.router import Router

from .endpoints import connections, ports, presets
from .errors import register_exception_handlers

MOCK_DEVICES_PATH = "mock_devices.json"
MOCK_PRESETS_PATH = "mock_presets.json"


def _mock_mode() -> bool:
    return os.environ.get("STUDIO_MIDI_BACKEND", "").strip().lower() == "mock"


def _make_backend() -> Backend:
    if _mock_mode():
        return MockBackend()
    return AlsaBackend()


def _make_device_store() -> DeviceStore:
    if not _mock_mode():
        return DeviceStore()

    store = DeviceStore(path=MOCK_DEVICES_PATH)

    if not store.path.exists():
        store.path.write_text(json.dumps(SEED_DEVICES, indent=2), encoding="utf-8")

    return store


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    backend = _make_backend()
    devices = _make_device_store()
    app.state.backend = backend
    app.state.devices = devices
    app.state.router = Router(backend, devices)
    # Kept apart in mock mode so presets of fake devices never end up in the
    # tracked presets.json.
    app.state.presets = PresetStore(path=MOCK_PRESETS_PATH) if _mock_mode() else PresetStore()
    try:
        yield
    finally:
        backend.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Studio MIDI Router API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    app.include_router(ports.router, prefix="/api/ports", tags=["ports"])
    app.include_router(connections.router, prefix="/api/routes", tags=["routes"])
    app.include_router(presets.router, prefix="/api/presets", tags=["presets"])

    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return app


app = create_app()
