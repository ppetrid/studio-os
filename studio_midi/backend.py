from collections.abc import Iterable
from alsa_midi import PortInfo, PortType, SequencerClient, SubscriptionQueryType
from .models import Endpoint


class PortNotFoundError(RuntimeError):
    pass


class AmbiguousPortError(RuntimeError):
    pass


class Backend:
    """
    Common interface + port-matching logic shared by every backend
    implementation (real ALSA, mock, ...).
    """

    def list_sources(self) -> list[PortInfo]:
        raise NotImplementedError

    def list_destinations(self) -> list[PortInfo]:
        raise NotImplementedError

    def connect(self, source: PortInfo, destination: PortInfo) -> None:
        raise NotImplementedError

    def disconnect(self, source: PortInfo, destination: PortInfo) -> None:
        raise NotImplementedError

    def list_connections(self) -> list[tuple[PortInfo, PortInfo]]:
        """
        Existing (source, destination) connections between listed ports.
        """
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def resolve_source(self, endpoint: Endpoint) -> PortInfo:
        return self._resolve(
            endpoint=endpoint,
            ports=self.list_sources(),
            role="source",
        )

    def resolve_destination(self, endpoint: Endpoint) -> PortInfo:
        return self._resolve(
            endpoint=endpoint,
            ports=self.list_destinations(),
            role="destination",
        )

    def _resolve(
        self,
        endpoint: Endpoint,
        ports: Iterable[PortInfo],
        role: str,
    ) -> PortInfo:
        device_query = endpoint.device.casefold()
        port_query = endpoint.port.casefold() if endpoint.port else None

        matches: list[PortInfo] = []
        exact_matches: list[PortInfo] = []

        for port in ports:
            client_name = port.client_name.casefold()
            port_name = port.name.casefold()

            device_matches = (
                device_query in client_name
                or device_query in port_name
            )

            port_matches = (
                port_query is None
                or port_query in port_name
            )

            if device_matches and port_matches:
                matches.append(port)

                if client_name == device_query and (
                    port_query is None or port_name == port_query
                ):
                    exact_matches.append(port)

        # Prefer exact names, so e.g. "MIDI 1" doesn't also match "MIDI 10".
        # Endpoints from the UI and from scenes saved there always carry full
        # names; substring matching is a convenience for loose CLI input.
        if exact_matches:
            matches = exact_matches

        if not matches:
            raise PortNotFoundError(
                f"No {role} port matched {endpoint!r}"
            )

        if len(matches) > 1:
            descriptions = "\n".join(
                f"  {port.client_id}:{port.port_id} "
                f"{port.client_name!r} / {port.name!r}"
                for port in matches
            )

            raise AmbiguousPortError(
                f"Multiple {role} ports matched {endpoint!r}:\n"
                f"{descriptions}"
            )

        return matches[0]


class AlsaBackend(Backend):
    def __init__(self, client_name: str = "studio-router") -> None:
        self.client = SequencerClient(client_name)

    def close(self) -> None:
        self.client.close()

    def list_sources(self) -> list[PortInfo]:
        """
        Ports that can send MIDI to another ALSA client.
        """
        return self.client.list_ports(
            input=True,
            type=PortType.MIDI_GENERIC | PortType.HARDWARE,
        )

    def list_destinations(self) -> list[PortInfo]:
        """
        Ports that can receive MIDI from another ALSA client.
        """
        return self.client.list_ports(
            output=True,
            type=PortType.MIDI_GENERIC | PortType.HARDWARE,
        )

    def connect(
        self,
        source: PortInfo,
        destination: PortInfo,
    ) -> None:
        self.client.subscribe_port(source, destination)

    def disconnect(
        self,
        source: PortInfo,
        destination: PortInfo,
    ) -> None:
        self.client.unsubscribe_port(source, destination)

    def list_connections(self) -> list[tuple[PortInfo, PortInfo]]:
        """
        Live ALSA subscriptions from a listed source to a listed destination.

        ALSA keeps these after the client that created them exits, so this
        includes connections made by earlier runs of this app or by other
        tools (e.g. `aconnect`).
        """
        destinations = {
            (port.client_id, port.port_id): port
            for port in self.list_destinations()
        }
        connections = []

        for source in self.list_sources():
            subscribers = self.client.list_port_subscribers(
                source,
                type=SubscriptionQueryType.READ,
            )

            for subscriber in subscribers:
                destination = destinations.get(tuple(subscriber.addr))

                if destination is not None:
                    connections.append((source, destination))

        return connections
