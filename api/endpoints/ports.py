from typing import Literal

from fastapi import APIRouter, Depends, status

from studio_midi.backend import Backend
from studio_midi.devices import DeviceStore, Direction, PortRef

from ..dependencies import get_backend, get_device_store
from ..schemas import DeviceAssignmentModel, DeviceModel, PortModel, PortRefModel

router = APIRouter()

PortsDirection = Literal["sources", "destinations"]

_DEVICE_DIRECTION: dict[str, Direction] = {
    "sources": "source",
    "destinations": "destination",
}


@router.get("/sources", response_model=list[PortModel])
def list_sources(
    backend: Backend = Depends(get_backend),
    devices: DeviceStore = Depends(get_device_store),
):
    names = devices.names_by_port("source")
    return [
        PortModel.from_domain(port, device_name=names.get(PortRef.from_port(port)))
        for port in backend.list_sources()
    ]


@router.get("/destinations", response_model=list[PortModel])
def list_destinations(
    backend: Backend = Depends(get_backend),
    devices: DeviceStore = Depends(get_device_store),
):
    names = devices.names_by_port("destination")
    return [
        PortModel.from_domain(port, device_name=names.get(PortRef.from_port(port)))
        for port in backend.list_destinations()
    ]


@router.put("/{direction}/device", response_model=DeviceModel)
def assign_device(
    direction: PortsDirection,
    assignment: DeviceAssignmentModel,
    devices: DeviceStore = Depends(get_device_store),
):
    device = devices.assign(
        _DEVICE_DIRECTION[direction],
        assignment.to_domain(),
        assignment.device,
    )
    return DeviceModel.from_domain(device)


@router.delete("/{direction}/device", status_code=status.HTTP_204_NO_CONTENT)
def unassign_device(
    direction: PortsDirection,
    port: PortRefModel,
    devices: DeviceStore = Depends(get_device_store),
):
    devices.unassign(_DEVICE_DIRECTION[direction], port.to_domain())
