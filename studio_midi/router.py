from .backend import Backend
from .models import Route


class ProcessedRouteNotImplementedError(NotImplementedError):
    pass


class Router:
    def __init__(self, backend: Backend) -> None:
        self.backend = backend

        # Routes created during this application process.
        #
        # This is sufficient for the first prototype. Later, this should be
        # replaced by inspection of the actual ALSA subscription graph.
        self._managed_routes: set[Route] = set()

    @property
    def managed_routes(self) -> frozenset[Route]:
        return frozenset(self._managed_routes)

    def connect(self, route: Route) -> None:
        if not route.is_direct:
            self._connect_processed(route)
            return

        if route in self._managed_routes:
            return

        source = self.backend.resolve_source(route.source)
        destination = self.backend.resolve_destination(route.destination)

        self.backend.connect(source, destination)
        self._managed_routes.add(route)

    def disconnect(self, route: Route) -> None:
        if not route.is_direct:
            self._disconnect_processed(route)
            return

        source = self.backend.resolve_source(route.source)
        destination = self.backend.resolve_destination(route.destination)

        self.backend.disconnect(source, destination)
        self._managed_routes.discard(route)

    def replace_routes(self, desired_routes: set[Route]) -> None:
        """
        Atomically reconcile the routes managed by this process as far as
        practical: remove obsolete routes, then add missing ones.
        """
        routes_to_remove = self._managed_routes - desired_routes
        routes_to_add = desired_routes - self._managed_routes

        for route in routes_to_remove:
            self.disconnect(route)

        try:
            for route in routes_to_add:
                self.connect(route)
        except Exception:
            # Best-effort restoration of the previous managed state.
            for route in routes_to_remove:
                try:
                    self.connect(route)
                except Exception:
                    pass
            raise

    def _connect_processed(self, route: Route) -> None:
        raise ProcessedRouteNotImplementedError(
            f"Processor {route.processor!r} is not implemented yet"
        )

    def _disconnect_processed(self, route: Route) -> None:
        raise ProcessedRouteNotImplementedError(
            f"Processor {route.processor!r} is not implemented yet"
        )
