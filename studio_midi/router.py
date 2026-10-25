from alsa_midi import PortInfo

from .backend import AmbiguousPortError, Backend, PortNotFoundError
from .devices import DeviceStore, PortRef
from .models import Endpoint, Route


class ProcessedRouteNotImplementedError(NotImplementedError):
    pass


class SelfRouteBlockedError(RuntimeError):
    pass


# Reasons a route can't be made right now, which `replace_routes` skips
# instead of failing on.
_UNAVAILABLE_ROUTE_ERRORS = (
    PortNotFoundError,
    AmbiguousPortError,
    SelfRouteBlockedError,
    ProcessedRouteNotImplementedError,
)


def _endpoint(port: PortInfo) -> Endpoint:
    return Endpoint(device=port.client_name or "", port=port.name)


def _ref_endpoint(ref: PortRef) -> Endpoint:
    return Endpoint(device=ref.client_name, port=ref.port_name)


def _connection_key(source: PortInfo, destination: PortInfo) -> tuple:
    return (
        source.client_id,
        source.port_id,
        destination.client_id,
        destination.port_id,
    )


class Router:
    def __init__(self, backend: Backend, devices: DeviceStore) -> None:
        self.backend = backend
        self.devices = devices

    @property
    def routes(self) -> list[Route]:
        """
        Direct routes currently connected in the backend.

        Read live on every access rather than tracked in memory, so they
        survive restarts of this process and include connections made
        outside of it (e.g. with `aconnect`).
        """
        return [
            Route(source=_endpoint(source), destination=_endpoint(destination))
            for source, destination in self.backend.list_connections()
        ]

    @property
    def blocked_routes(self) -> list[Route]:
        """
        Routes `connect` refuses: each device's source into its own
        destination, unless the device allows self-routing.
        """
        return [
            Route(
                source=_ref_endpoint(device.source),
                destination=_ref_endpoint(device.destination),
            )
            for device in self.devices.list()
            if device.source is not None
            and device.destination is not None
            and not device.allow_self_route
        ]

    def connect(self, route: Route) -> None:
        if not route.is_direct:
            self._connect_processed(route)
            return

        source, destination = self._resolve(route)
        self._check_allowed(source, destination)

        if self._is_connected(source, destination):
            return

        self.backend.connect(source, destination)

    def disconnect(self, route: Route) -> None:
        if not route.is_direct:
            self._disconnect_processed(route)
            return

        source, destination = self._resolve(route)

        if not self._is_connected(source, destination):
            return

        self.backend.disconnect(source, destination)

    def replace_routes(self, desired_routes: set[Route]) -> dict[Route, str]:
        """
        Reconcile the backend's connections with `desired_routes` as far as
        practical: remove obsolete connections, then add missing ones.

        Desired routes that can't be made right now (a port that isn't
        plugged in or is ambiguous, a blocked self-route) are skipped rather
        than failing the whole change, and returned with the reason why.
        """
        desired, skipped = self._resolve_all(desired_routes)

        current = {
            _connection_key(source, destination): (source, destination)
            for source, destination in self.backend.list_connections()
        }

        to_remove = [current[key] for key in current.keys() - desired.keys()]
        to_add = [desired[key] for key in desired.keys() - current.keys()]

        for source, destination in to_remove:
            self.backend.disconnect(source, destination)

        try:
            for source, destination in to_add:
                self.backend.connect(source, destination)
        except Exception:
            # Best-effort restoration of the previous state.
            for source, destination in to_remove:
                try:
                    self.backend.connect(source, destination)
                except Exception:
                    pass
            raise

        return skipped

    def matches(self, desired_routes: set[Route]) -> bool:
        """
        Whether the current connections are exactly the routes from
        `desired_routes` that could be made right now.
        """
        desired, _ = self._resolve_all(desired_routes)
        current = {
            _connection_key(source, destination)
            for source, destination in self.backend.list_connections()
        }
        return desired.keys() == current

    def _resolve_all(
        self, routes: set[Route]
    ) -> tuple[dict[tuple, tuple[PortInfo, PortInfo]], dict[Route, str]]:
        resolved = {}
        skipped = {}

        for route in routes:
            try:
                if not route.is_direct:
                    raise ProcessedRouteNotImplementedError(
                        f"Processor {route.processor!r} is not implemented yet"
                    )

                source, destination = self._resolve(route)
                self._check_allowed(source, destination)
            except _UNAVAILABLE_ROUTE_ERRORS as exc:
                skipped[route] = str(exc)
                continue

            resolved[_connection_key(source, destination)] = (source, destination)

        return resolved, skipped

    def _resolve(self, route: Route) -> tuple[PortInfo, PortInfo]:
        return (
            self.backend.resolve_source(route.source),
            self.backend.resolve_destination(route.destination),
        )

    def _check_allowed(self, source: PortInfo, destination: PortInfo) -> None:
        device = self.devices.find("source", PortRef.from_port(source))

        if (
            device is not None
            and not device.allow_self_route
            and device.destination == PortRef.from_port(destination)
        ):
            raise SelfRouteBlockedError(
                f"Can't route {device.name!r} into itself "
                "(allow_self_route is off for this device)"
            )

    def _is_connected(self, source: PortInfo, destination: PortInfo) -> bool:
        key = _connection_key(source, destination)
        return any(
            _connection_key(*connection) == key
            for connection in self.backend.list_connections()
        )

    def _connect_processed(self, route: Route) -> None:
        raise ProcessedRouteNotImplementedError(
            f"Processor {route.processor!r} is not implemented yet"
        )

    def _disconnect_processed(self, route: Route) -> None:
        raise ProcessedRouteNotImplementedError(
            f"Processor {route.processor!r} is not implemented yet"
        )
