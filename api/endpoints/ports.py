from fastapi import APIRouter, Depends

from studio_midi.aliases import AliasStore
from studio_midi.backend import Backend

from ..dependencies import get_alias_store, get_backend
from ..schemas import PortModel

router = APIRouter()


@router.get("/sources", response_model=list[PortModel])
def list_sources(
    backend: Backend = Depends(get_backend),
    aliases: AliasStore = Depends(get_alias_store),
):
    return [
        PortModel.from_domain(
            port, alias=aliases.get("sources", port.client_name, port.name)
        )
        for port in backend.list_sources()
    ]


@router.get("/destinations", response_model=list[PortModel])
def list_destinations(
    backend: Backend = Depends(get_backend),
    aliases: AliasStore = Depends(get_alias_store),
):
    return [
        PortModel.from_domain(
            port, alias=aliases.get("destinations", port.client_name, port.name)
        )
        for port in backend.list_destinations()
    ]
