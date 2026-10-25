from fastapi import Request

from studio_midi.backend import Backend
from studio_midi.devices import DeviceStore
from studio_midi.presets import PresetStore
from studio_midi.router import Router


def get_backend(request: Request) -> Backend:
    return request.app.state.backend


def get_midi_router(request: Request) -> Router:
    return request.app.state.router


def get_preset_store(request: Request) -> PresetStore:
    return request.app.state.presets


def get_device_store(request: Request) -> DeviceStore:
    return request.app.state.devices
