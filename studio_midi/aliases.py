import json
from pathlib import Path
from typing import Literal

Direction = Literal["sources", "destinations"]

DIRECTIONS: tuple[Direction, ...] = ("sources", "destinations")


class AliasStore:
    """
    User-defined display names for individual device ports, kept separately
    for sources and destinations.

    Separate because a multi-port interface usually reports its In 1 and
    Out 1 jacks as a single ALSA port, but they needn't be cabled to the
    same device — e.g. a controller on In 1 and a sound module on Out 1.

    Keyed by the real (client_name, port name) reported by the backend —
    not client/port ids, since ALSA assigns those dynamically and they
    aren't stable across reconnects or restarts. It's fine for the file to
    hold aliases for ports that aren't currently plugged in, and fine for a
    listed port to have no matching alias.
    """

    def __init__(self, path: str | Path = "aliases.json") -> None:
        self.path = Path(path)

    def get(
        self,
        direction: Direction,
        client_name: str | None,
        port_name: str,
    ) -> str | None:
        if client_name is None:
            return None

        return (
            self._load_raw()
            .get(direction, {})
            .get(client_name, {})
            .get(port_name)
        )

    def set(
        self,
        direction: Direction,
        client_name: str,
        port_name: str,
        alias: str,
    ) -> None:
        aliases = self._load_raw()
        clients = aliases.setdefault(direction, {})
        clients.setdefault(client_name, {})[port_name] = alias
        self._save(aliases)

    def delete(self, direction: Direction, client_name: str, port_name: str) -> None:
        aliases = self._load_raw()
        clients = aliases.get(direction, {})

        if port_name not in clients.get(client_name, {}):
            return

        del clients[client_name][port_name]

        if not clients[client_name]:
            del clients[client_name]

        if not clients:
            del aliases[direction]

        self._save(aliases)

    def _load_raw(self) -> dict[str, dict[str, dict[str, str]]]:
        if not self.path.exists():
            return {}

        contents = self.path.read_text(encoding="utf-8").strip()

        if not contents:
            return {}

        data = json.loads(contents)

        if not isinstance(data, dict) or not set(data) <= set(DIRECTIONS):
            raise ValueError(
                f"Alias file {str(self.path)!r} must contain a JSON object "
                "with 'sources' and/or 'destinations' keys"
            )

        return data

    def _save(self, aliases: dict[str, dict[str, dict[str, str]]]) -> None:
        self.path.write_text(
            json.dumps(aliases, indent=2, sort_keys=True),
            encoding="utf-8",
        )
