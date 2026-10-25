import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .devices import Direction, PortRef
from .models import Endpoint, Route
from .router import Router


class PresetNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DeviceRef:
    """A user-named device (see `devices.py`), looked up when recalled."""
    name: str


PresetEndpoint = DeviceRef | PortRef


@dataclass(frozen=True, slots=True)
class PresetRoute:
    source: PresetEndpoint
    destination: PresetEndpoint


@dataclass(frozen=True, slots=True)
class SkippedRoute:
    route: PresetRoute
    reason: str


class _UnresolvedEndpoint(Exception):
    pass


class PresetStore:
    """
    Named snapshots of the routing matrix.

    Each end of a route refers to a device by name when its port belonged
    to one at save time, so presets keep working after re-cabling: only
    the device's ports change. Ports without a device are kept by their
    real (client_name, port name).
    """

    def __init__(self, path: str | Path = "presets.json") -> None:
        self.path = Path(path)

    def list_names(self) -> list[str]:
        return sorted(self._load_raw(), key=str.casefold)

    def get(self, name: str) -> list[PresetRoute]:
        presets = self._load_raw()

        if name not in presets:
            raise PresetNotFoundError(f"Unknown preset: {name!r}")

        return [_route_from_dict(item) for item in presets[name]]

    def save(self, name: str, routes: list[PresetRoute]) -> list[PresetRoute]:
        presets = self._load_raw()
        routes = sorted(set(routes), key=_sort_key)
        presets[name] = [_route_to_dict(route) for route in routes]
        self._save(presets)
        return routes

    def save_current(self, name: str, router: Router) -> list[PresetRoute]:
        return self.save(name, capture(router))

    def delete(self, name: str) -> None:
        presets = self._load_raw()

        if name not in presets:
            raise PresetNotFoundError(f"Unknown preset: {name!r}")

        del presets[name]
        self._save(presets)

    def recall(self, name: str, router: Router) -> list[SkippedRoute]:
        """
        Make the routing match the preset. Routes that can't be made right
        now (an unknown device, a port that isn't plugged in, a blocked
        self-route) are skipped and returned with the reason, rather than
        failing the whole recall.
        """
        resolved, skipped = _resolve(self.get(name), router)

        for route, reason in router.replace_routes(set(resolved)).items():
            skipped.append(SkippedRoute(resolved[route], reason))

        return skipped

    def _load_raw(self) -> dict[str, list[dict]]:
        if not self.path.exists():
            return {}

        contents = self.path.read_text(encoding="utf-8").strip()

        if not contents:
            return {}

        data = json.loads(contents)

        if not isinstance(data, dict):
            raise ValueError(f"Preset file {str(self.path)!r} must contain a JSON object")

        return data

    def _save(self, presets: dict[str, list[dict]]) -> None:
        self.path.write_text(
            json.dumps(presets, indent=2),
            encoding="utf-8",
        )


def capture(router: Router) -> list[PresetRoute]:
    """The current routing, referring to ports by device name where possible."""
    sources = router.devices.names_by_port("source")
    destinations = router.devices.names_by_port("destination")

    return [
        PresetRoute(
            source=_preset_endpoint(route.source, sources),
            destination=_preset_endpoint(route.destination, destinations),
        )
        for route in router.routes
    ]


def matches_current(routes: list[PresetRoute], router: Router) -> bool:
    """
    Whether the current routing is exactly what recalling `routes` would
    produce right now.
    """
    resolved, _ = _resolve(routes, router)
    return router.matches(set(resolved))


def label(endpoint: PresetEndpoint) -> str:
    if isinstance(endpoint, DeviceRef):
        return endpoint.name

    return f"{endpoint.client_name} · {endpoint.port_name}"


def _preset_endpoint(endpoint: Endpoint, names: dict[PortRef, str]) -> PresetEndpoint:
    port = PortRef(client_name=endpoint.device, port_name=endpoint.port or "")
    name = names.get(port)
    return DeviceRef(name=name) if name is not None else port


def _resolve(
    routes: list[PresetRoute], router: Router
) -> tuple[dict[Route, PresetRoute], list[SkippedRoute]]:
    resolved = {}
    skipped = []

    for preset_route in routes:
        try:
            route = Route(
                source=_endpoint(preset_route.source, "source", router),
                destination=_endpoint(preset_route.destination, "destination", router),
            )
        except _UnresolvedEndpoint as exc:
            skipped.append(SkippedRoute(preset_route, str(exc)))
            continue

        resolved[route] = preset_route

    return resolved, skipped


def _endpoint(endpoint: PresetEndpoint, direction: Direction, router: Router) -> Endpoint:
    if isinstance(endpoint, PortRef):
        return Endpoint(device=endpoint.client_name, port=endpoint.port_name)

    device = router.devices.get(endpoint.name)

    if device is None:
        raise _UnresolvedEndpoint(f"No device named {endpoint.name!r}")

    port = getattr(device, direction)

    if port is None:
        raise _UnresolvedEndpoint(f"{device.name!r} has no {direction} port")

    return Endpoint(device=port.client_name, port=port.port_name)


def _sort_key(route: PresetRoute) -> tuple:
    return (label(route.source).casefold(), label(route.destination).casefold())


def _route_to_dict(route: PresetRoute) -> dict:
    return {
        "source": _endpoint_to_dict(route.source),
        "destination": _endpoint_to_dict(route.destination),
    }


def _route_from_dict(data: dict) -> PresetRoute:
    return PresetRoute(
        source=_endpoint_from_dict(data["source"]),
        destination=_endpoint_from_dict(data["destination"]),
    )


def _endpoint_to_dict(endpoint: PresetEndpoint) -> dict:
    if isinstance(endpoint, DeviceRef):
        return {"device": endpoint.name}

    return asdict(endpoint)


def _endpoint_from_dict(data: dict) -> PresetEndpoint:
    if "device" in data:
        return DeviceRef(name=data["device"])

    return PortRef(client_name=data["client_name"], port_name=data["port_name"])
