from fastapi import APIRouter, Depends

from studio_midi.backend import AlsaBackend

from ..dependencies import get_backend
from ..schemas import PortModel

router = APIRouter()


@router.get("/sources", response_model=list[PortModel])
def list_sources(backend: AlsaBackend = Depends(get_backend)):
    return [PortModel.from_domain(port) for port in backend.list_sources()]


@router.get("/destinations", response_model=list[PortModel])
def list_destinations(backend: AlsaBackend = Depends(get_backend)):
    return [PortModel.from_domain(port) for port in backend.list_destinations()]
