from alsa_midi import PortInfo
from pydantic import BaseModel

from studio_midi.models import Endpoint, Route


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

    @classmethod
    def from_domain(cls, port: PortInfo) -> "PortModel":
        return cls(
            client_id=port.client_id,
            port_id=port.port_id,
            client_name=port.client_name,
            name=port.name,
        )


class SceneModel(BaseModel):
    name: str
    routes: list[RouteModel]
