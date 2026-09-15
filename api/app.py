import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from studio_midi.aliases import AliasStore
from studio_midi.backend import AlsaBackend, Backend
from studio_midi.mock_backend import SEED_ALIASES, MockBackend
from studio_midi.router import Router
from studio_midi.scenes import SceneStore

from .endpoints import connections, ports, scenes
from .errors import register_exception_handlers

MOCK_ALIASES_PATH = "mock_aliases.json"


def _mock_mode() -> bool:
    return os.environ.get("STUDIO_MIDI_BACKEND", "").strip().lower() == "mock"


def _make_backend() -> Backend:
    if _mock_mode():
        return MockBackend()
    return AlsaBackend()


def _make_alias_store() -> AliasStore:
    if not _mock_mode():
        return AliasStore()

    store = AliasStore(path=MOCK_ALIASES_PATH)

    if not store.path.exists():
        for client_name, ports_ in SEED_ALIASES.items():
            for port_name, alias in ports_.items():
                store.set(client_name, port_name, alias)

    return store


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    backend = _make_backend()
    app.state.backend = backend
    app.state.router = Router(backend)
    app.state.scenes = SceneStore()
    app.state.aliases = _make_alias_store()
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
    app.include_router(scenes.router, prefix="/api/scenes", tags=["scenes"])

    frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return app


app = create_app()
