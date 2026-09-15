import json
from pathlib import Path

from alsa_midi import PortInfo

from .backend import Backend

DEFAULT_PORTS_PATH = Path("mock_ports.json")
DEFAULT_CONNECTIONS_PATH = Path("mock_connections.json")

SEED_PORTS = {
    "sources": [
        {"client_id": 1, "port_id": 1, "client_name": "Yamaha CP88", "name": "MIDI OUT 1"},
        {"client_id": 2, "port_id": 1, "client_name": "Novation Peak", "name": "MIDI OUT 1"},
        {"client_id": 3, "port_id": 1, "client_name": "Hammond Xk-3", "name": "MIDI OUT 1"},
        {"client_id": 4, "port_id": 1, "client_name": "Kurzweil PC-3X", "name": "MIDI OUT 1"},
        {"client_id": 5, "port_id": 1, "client_name": "Novation BassStation", "name": "MIDI OUT 1"},
        {"client_id": 6, "port_id": 1, "client_name": "Yamaha TG77", "name": "MIDI OUT 1"},
        {"client_id": 7, "port_id": 1, "client_name": "Arturia Beatstep", "name": "MIDI OUT 1"},
    ],
    "destinations": [
        {"client_id": 1, "port_id": 1, "client_name": "Yamaha CP88", "name": "MIDI IN 1"},
        {"client_id": 2, "port_id": 1, "client_name": "Novation Peak", "name": "MIDI IN 1"},
        {"client_id": 3, "port_id": 1, "client_name": "Hammond Xk-3", "name": "MIDI IN 1"},
        {"client_id": 4, "port_id": 1, "client_name": "Kurzweil PC-3X", "name": "MIDI IN 1"},
        {"client_id": 5, "port_id": 1, "client_name": "Novation BassStation", "name": "MIDI IN 1"},
        {"client_id": 6, "port_id": 1, "client_name": "Yamaha TG77", "name": "MIDI IN 1"},
        {"client_id": 7, "port_id": 1, "client_name": "Dreadbox Erebus", "name": "MIDI IN 1"},
    ],
}

# A few fake devices pre-aliased, so the UI has something to show for the
# feature out of the box. The rest are left unaliased on purpose, to also
# exercise the fall-back-to-real-name path.
SEED_ALIASES = {
    "Hammond Xk-3": {
        "MIDI OUT 1": "Organ Rig Out",
        "MIDI IN 1": "Organ Rig In",
    },
    "Kurzweil PC-3X": {
        "MIDI OUT 1": "Stage Piano Out",
        "MIDI IN 1": "Stage Piano In",
    },
}


def _port_from_dict(data: dict) -> PortInfo:
    port = PortInfo(
        client_id=data["client_id"],
        port_id=data["port_id"],
        name=data["name"],
    )
    port.client_name = data["client_name"]
    return port


def _port_key(port: PortInfo) -> list:
    return [port.client_id, port.port_id]


class MockBackend(Backend):
    """
    Fake backend for UI development, standing in for a real ALSA sequencer.

    Ports are seeded into `ports_path` on first use (editable by hand to add
    or remove fake devices). Connections are persisted to `connections_path`
    so subscriptions survive server restarts, the same way real ALSA
    subscriptions would.
    """

    def __init__(
        self,
        ports_path: str | Path = DEFAULT_PORTS_PATH,
        connections_path: str | Path = DEFAULT_CONNECTIONS_PATH,
    ) -> None:
        self.ports_path = Path(ports_path)
        self.connections_path = Path(connections_path)

        if not self.ports_path.exists():
            self._write_json(self.ports_path, SEED_PORTS)

    def close(self) -> None:
        pass

    def list_sources(self) -> list[PortInfo]:
        return [_port_from_dict(item) for item in self._read_ports()["sources"]]

    def list_destinations(self) -> list[PortInfo]:
        return [_port_from_dict(item) for item in self._read_ports()["destinations"]]

    def connect(self, source: PortInfo, destination: PortInfo) -> None:
        connections = self._read_connections()
        pair = [_port_key(source), _port_key(destination)]

        if pair not in connections:
            connections.append(pair)
            self._write_json(self.connections_path, connections)

    def disconnect(self, source: PortInfo, destination: PortInfo) -> None:
        connections = self._read_connections()
        pair = [_port_key(source), _port_key(destination)]

        if pair in connections:
            connections.remove(pair)
            self._write_json(self.connections_path, connections)

    def _read_ports(self) -> dict:
        if not self.ports_path.exists():
            return SEED_PORTS

        return json.loads(self.ports_path.read_text(encoding="utf-8"))

    def _read_connections(self) -> list:
        if not self.connections_path.exists():
            return []

        contents = self.connections_path.read_text(encoding="utf-8").strip()

        if not contents:
            return []

        return json.loads(contents)

    def _write_json(self, path: Path, data) -> None:
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
