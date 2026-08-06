from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from studio_midi.backend import AlsaBackend
from studio_midi.router import Router
from studio_midi.scenes import SceneStore

from .endpoints import connections, ports, scenes
from .errors import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    backend = AlsaBackend()
    app.state.backend = backend
    app.state.router = Router(backend)
    app.state.scenes = SceneStore()
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

    return app


app = create_app()
