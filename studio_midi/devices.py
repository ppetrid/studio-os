import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Literal

from alsa_midi import PortInfo

Direction = Literal["source", "destination"]


class DeviceNameTakenError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class PortRef:
    """
    A port by its real (client_name, port name) — not client/port ids,
    since ALSA assigns those dynamically and they aren't stable across
    reconnects or restarts.
    """
    client_name: str
    port_name: str

    @classmethod
    def from_port(cls, port: PortInfo) -> "PortRef":
        return cls(client_name=port.client_name or "", port_name=port.name)


@dataclass(frozen=True, slots=True)
class Device:
    name: str
    source: PortRef | None = None
    destination: PortRef | None = None

    # Allow routing this device's source into its own destination, e.g.
    # for a keyboard played with Local Off. Blocked by default, since it's
    # usually a MIDI loop.
    allow_self_route: bool = False


class DeviceStore:
    """
    User-named devices, each linking at most one source port and one
    destination port — e.g. "CP88" for a multi-port interface's In 3 and
    Out 3. Giving a source and a destination the same name is what links
    them; names match case-insensitively.

    The device, not the physical port, is the stable identity: after
    re-cabling, only the device's ports change, and anything referring to
    the device by name follows. Devices may refer to ports that aren't
    currently plugged in. A device left with no ports is dropped.
    """

    def __init__(self, path: str | Path = "devices.json") -> None:
        self.path = Path(path)

    def list(self) -> list[Device]:
        return sorted(self._load().values(), key=lambda device: device.name.casefold())

    def find(self, direction: Direction, port: PortRef) -> Device | None:
        return next(
            (
                device
                for device in self._load().values()
                if getattr(device, direction) == port
            ),
            None,
        )

    def names_by_port(self, direction: Direction) -> dict[PortRef, str]:
        return {
            getattr(device, direction): device.name
            for device in self._load().values()
            if getattr(device, direction) is not None
        }

    def assign(self, direction: Direction, port: PortRef, name: str) -> Device:
        """
        Make `port` the `direction` port of the device called `name`,
        creating the device if needed, and return the updated device.
        """
        devices = self._load()
        existing = next(
            (device for device in devices.values() if device.name.casefold() == name.casefold()),
            None,
        )
        current = getattr(existing, direction) if existing else None

        if current is not None and current != port:
            raise DeviceNameTakenError(
                f"{existing.name!r} already uses "
                f"{current.client_name} · {current.port_name} as its {direction}"
            )

        # A port belongs to at most one device per direction.
        for other in list(devices.values()):
            if getattr(other, direction) == port:
                devices[other.name] = replace(other, **{direction: None})

        base = devices[existing.name] if existing else Device(name=name)
        device = replace(base, **{direction: port})
        devices[device.name] = device

        self._save(devices)
        return device

    def unassign(self, direction: Direction, port: PortRef) -> None:
        devices = self._load()
        device = next(
            (device for device in devices.values() if getattr(device, direction) == port),
            None,
        )

        if device is None:
            return

        devices[device.name] = replace(device, **{direction: None})
        self._save(devices)

    def _load(self) -> dict[str, Device]:
        if not self.path.exists():
            return {}

        contents = self.path.read_text(encoding="utf-8").strip()

        if not contents:
            return {}

        data = json.loads(contents)

        if not isinstance(data, dict):
            raise ValueError(f"Device file {str(self.path)!r} must contain a JSON object")

        return {
            name: Device(
                name=name,
                source=_port_ref(item.get("source")),
                destination=_port_ref(item.get("destination")),
                allow_self_route=bool(item.get("allow_self_route", False)),
            )
            for name, item in data.items()
        }

    def _save(self, devices: dict[str, Device]) -> None:
        data = {}

        for device in devices.values():
            if device.source is None and device.destination is None:
                continue

            item = {}

            if device.source is not None:
                item["source"] = asdict(device.source)
            if device.destination is not None:
                item["destination"] = asdict(device.destination)
            if device.allow_self_route:
                item["allow_self_route"] = True

            data[device.name] = item

        self.path.write_text(
            json.dumps(data, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def _port_ref(data: dict | None) -> PortRef | None:
    if data is None:
        return None

    return PortRef(client_name=data["client_name"], port_name=data["port_name"])
