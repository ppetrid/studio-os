from fastapi import APIRouter, Depends, status

from studio_midi.aliases import AliasStore, Direction

from ..dependencies import get_alias_store
from ..schemas import AliasModel, PortRefModel

router = APIRouter()


@router.put("/{direction}", response_model=AliasModel)
def set_alias(
    direction: Direction,
    alias: AliasModel,
    aliases: AliasStore = Depends(get_alias_store),
):
    aliases.set(direction, alias.client_name, alias.port_name, alias.alias)
    return alias


@router.delete("/{direction}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alias(
    direction: Direction,
    port: PortRefModel,
    aliases: AliasStore = Depends(get_alias_store),
):
    aliases.delete(direction, port.client_name, port.port_name)
