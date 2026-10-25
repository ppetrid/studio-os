from fastapi import APIRouter, Depends, status

from studio_midi.router import Router
from studio_midi.scenes import SceneStore

from ..dependencies import get_midi_router, get_scene_store
from ..schemas import RouteModel, SceneModel

router = APIRouter()


@router.get("", response_model=list[str])
def list_scenes(scenes: SceneStore = Depends(get_scene_store)):
    return scenes.list_names()


@router.get("/{name}", response_model=SceneModel)
def get_scene(name: str, scenes: SceneStore = Depends(get_scene_store)):
    routes = scenes.get(name)
    return SceneModel(name=name, routes=[RouteModel.from_domain(r) for r in routes])


@router.put("/{name}", response_model=SceneModel)
def save_scene(
    name: str,
    routes: list[RouteModel],
    scenes: SceneStore = Depends(get_scene_store),
):
    scenes.save(name, {route.to_domain() for route in routes})
    return SceneModel(name=name, routes=routes)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scene(name: str, scenes: SceneStore = Depends(get_scene_store)):
    scenes.delete(name)


@router.post("/{name}/activate", response_model=list[RouteModel])
def activate_scene(
    name: str,
    scenes: SceneStore = Depends(get_scene_store),
    midi_router: Router = Depends(get_midi_router),
):
    scenes.activate(name, midi_router)
    return [RouteModel.from_domain(r) for r in midi_router.routes]
