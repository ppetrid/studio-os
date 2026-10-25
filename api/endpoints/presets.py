from fastapi import APIRouter, Depends, status

from studio_midi.presets import PresetRoute, PresetStore, matches_current
from studio_midi.router import Router

from ..dependencies import get_midi_router, get_preset_store
from ..schemas import (
    PresetModel,
    PresetNameModel,
    PresetRouteModel,
    RecallResultModel,
    RouteModel,
    SkippedRouteModel,
)

router = APIRouter()

# Preset names are user-typed and may contain "/", so they always travel in
# the JSON body rather than the URL.


def _preset_model(name: str, routes: list[PresetRoute], midi_router: Router) -> PresetModel:
    return PresetModel(
        name=name,
        routes=[PresetRouteModel.from_domain(route) for route in routes],
        current=matches_current(routes, midi_router),
    )


@router.get("", response_model=list[PresetModel])
def list_presets(
    presets: PresetStore = Depends(get_preset_store),
    midi_router: Router = Depends(get_midi_router),
):
    return [
        _preset_model(name, presets.get(name), midi_router)
        for name in presets.list_names()
    ]


@router.put("", response_model=PresetModel)
def save_preset(
    preset: PresetNameModel,
    presets: PresetStore = Depends(get_preset_store),
    midi_router: Router = Depends(get_midi_router),
):
    """Save the current routing under `name`, replacing any preset by that name."""
    routes = presets.save_current(preset.name, midi_router)
    return _preset_model(preset.name, routes, midi_router)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_preset(
    preset: PresetNameModel,
    presets: PresetStore = Depends(get_preset_store),
):
    presets.delete(preset.name)


@router.post("/recall", response_model=RecallResultModel)
def recall_preset(
    preset: PresetNameModel,
    presets: PresetStore = Depends(get_preset_store),
    midi_router: Router = Depends(get_midi_router),
):
    skipped = presets.recall(preset.name, midi_router)
    return RecallResultModel(
        routes=[RouteModel.from_domain(route) for route in midi_router.routes],
        skipped=[SkippedRouteModel.from_domain(item) for item in skipped],
    )
