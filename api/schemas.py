from typing import Annotated

from alsa_midi import PortInfo
from pydantic import BaseModel, StringConstraints

from studio_midi.devices import Device, PortRef
from studio_midi.models import Endpoint, Route
from studio_midi.presets import DeviceRef, PresetEndpoint, PresetRoute, SkippedRoute

NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class EndpointModel(BaseModel):
    device: str
    port: str | None = None

    def to_domain(self) -> Endpoint:
        return Endpoint(device=self.device, port=self.port)

    @classmethod
    def from_domain(cls, endpoint: Endpoint) -> "EndpointModel":
        return cls(device=endpoint.device, port=endpoint.port)


class RouteModel(BaseModel):
    source: EndpointModel
    destination: EndpointModel
    processor: str | None = None

    def to_domain(self) -> Route:
        return Route(
            source=self.source.to_domain(),
            destination=self.destination.to_domain(),
            processor=self.processor,
        )

    @classmethod
    def from_domain(cls, route: Route) -> "RouteModel":
        return cls(
            source=EndpointModel.from_domain(route.source),
            destination=EndpointModel.from_domain(route.destination),
            processor=route.processor,
        )


class PortModel(BaseModel):
    client_id: int
    port_id: int | None
    client_name: str | None
    name: str
    device_name: str | None = None

    @classmethod
    def from_domain(cls, port: PortInfo, device_name: str | None = None) -> "PortModel":
        return cls(
            client_id=port.client_id,
            port_id=port.port_id,
            client_name=port.client_name,
            name=port.name,
            device_name=device_name,
        )


class PortRefModel(BaseModel):
    client_name: str
    port_name: str

    def to_domain(self) -> PortRef:
        return PortRef(client_name=self.client_name, port_name=self.port_name)

    @classmethod
    def from_domain(cls, ref: PortRef) -> "PortRefModel":
        return cls(client_name=ref.client_name, port_name=ref.port_name)


class DeviceAssignmentModel(PortRefModel):
    device: NonBlankStr


class DeviceModel(BaseModel):
    name: str
    source: PortRefModel | None
    destination: PortRefModel | None
    allow_self_route: bool

    @classmethod
    def from_domain(cls, device: Device) -> "DeviceModel":
        return cls(
            name=device.name,
            source=PortRefModel.from_domain(device.source) if device.source else None,
            destination=(
                PortRefModel.from_domain(device.destination) if device.destination else None
            ),
            allow_self_route=device.allow_self_route,
        )


class DeviceRefModel(BaseModel):
    device: str


class PresetRouteModel(BaseModel):
    # Each end is a device name, or a real port for ports without a device.
    source: DeviceRefModel | PortRefModel
    destination: DeviceRefModel | PortRefModel

    @classmethod
    def from_domain(cls, route: PresetRoute) -> "PresetRouteModel":
        return cls(
            source=_preset_endpoint_model(route.source),
            destination=_preset_endpoint_model(route.destination),
        )


def _preset_endpoint_model(endpoint: PresetEndpoint) -> DeviceRefModel | PortRefModel:
    if isinstance(endpoint, DeviceRef):
        return DeviceRefModel(device=endpoint.name)

    return PortRefModel.from_domain(endpoint)


class PresetModel(BaseModel):
    name: str
    routes: list[PresetRouteModel]

    # Whether the current routing is exactly what recalling this preset
    # would produce right now.
    current: bool


class PresetNameModel(BaseModel):
    name: NonBlankStr


class SkippedRouteModel(BaseModel):
    route: PresetRouteModel
    reason: str

    @classmethod
    def from_domain(cls, skipped: SkippedRoute) -> "SkippedRouteModel":
        return cls(route=PresetRouteModel.from_domain(skipped.route), reason=skipped.reason)


class RecallResultModel(BaseModel):
    routes: list[RouteModel]
    skipped: list[SkippedRouteModel]
