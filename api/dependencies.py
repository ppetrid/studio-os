from fastapi import Request

from studio_midi.aliases import AliasStore
from studio_midi.backend import Backend
from studio_midi.router import Router
from studio_midi.scenes import SceneStore


def get_backend(request: Request) -> Backend:
    return request.app.state.backend


def get_midi_router(request: Request) -> Router:
    return request.app.state.router


def get_scene_store(request: Request) -> SceneStore:
    return request.app.state.scenes


def get_alias_store(request: Request) -> AliasStore:
    return request.app.state.aliases
