from alsa_midi import PortInfo

from .backend import Backend
from .models import Endpoint, Route


class ProcessedRouteNotImplementedError(NotImplementedError):
    pass


def _endpoint(port: PortInfo) -> Endpoint:
    return Endpoint(device=port.client_name or "", port=port.name)


def _connection_key(source: PortInfo, destination: PortInfo) -> tuple:
    return (
        source.client_id,
        source.port_id,
        destination.client_id,
        destination.port_id,
    )


class Router:
    def __init__(self, backend: Backend) -> None:
        self.backend = backend

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

    def connect(self, route: Route) -> None:
        if not route.is_direct:
            self._connect_processed(route)
            return

        source, destination = self._resolve(route)

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

    def replace_routes(self, desired_routes: set[Route]) -> None:
        """
        Reconcile the backend's connections with `desired_routes` as far as
        practical: remove obsolete connections, then add missing ones.

        Every desired route is resolved up front, so an unknown or ambiguous
        port fails before anything has been changed.
        """
        desired = {}

        for route in desired_routes:
            if not route.is_direct:
                raise ProcessedRouteNotImplementedError(
                    f"Processor {route.processor!r} is not implemented yet"
                )

            source, destination = self._resolve(route)
            desired[_connection_key(source, destination)] = (source, destination)

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

    def _resolve(self, route: Route) -> tuple[PortInfo, PortInfo]:
        return (
            self.backend.resolve_source(route.source),
            self.backend.resolve_destination(route.destination),
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
