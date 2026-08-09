from collections.abc import Iterable
from alsa_midi import PortInfo, PortType, SequencerClient
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
