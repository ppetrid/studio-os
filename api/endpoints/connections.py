from fastapi import APIRouter, Depends, status

from studio_midi.models import Route
from studio_midi.router import Router

from ..dependencies import get_midi_router
from ..schemas import RouteModel

router = APIRouter()


def _sort_key(route: Route) -> tuple:
    return (
        route.source.device,
        route.source.port or "",
        route.destination.device,
        route.destination.port or "",
        route.processor or "",
    )


@router.get("", response_model=list[RouteModel])
def list_routes(midi_router: Router = Depends(get_midi_router)):
    routes = sorted(midi_router.routes, key=_sort_key)
    return [RouteModel.from_domain(route) for route in routes]


@router.get("/blocked", response_model=list[RouteModel])
def list_blocked_routes(midi_router: Router = Depends(get_midi_router)):
    routes = sorted(midi_router.blocked_routes, key=_sort_key)
    return [RouteModel.from_domain(route) for route in routes]


@router.post("", response_model=RouteModel, status_code=status.HTTP_201_CREATED)
def create_route(route: RouteModel, midi_router: Router = Depends(get_midi_router)):
    domain_route = route.to_domain()
    midi_router.connect(domain_route)
    return RouteModel.from_domain(domain_route)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(route: RouteModel, midi_router: Router = Depends(get_midi_router)):
    midi_router.disconnect(route.to_domain())
