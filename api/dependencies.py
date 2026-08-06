from fastapi import Request

from studio_midi.backend import AlsaBackend
from studio_midi.router import Router
from studio_midi.scenes import SceneStore


def get_backend(request: Request) -> AlsaBackend:
    return request.app.state.backend


def get_midi_router(request: Request) -> Router:
    return request.app.state.router


def get_scene_store(request: Request) -> SceneStore:
    return request.app.state.scenes
