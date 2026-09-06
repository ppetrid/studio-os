import json
from pathlib import Path


class AliasStore:
    """
    User-defined display names for individual device ports.

    Keyed by the real (client_name, port name) reported by the backend —
    not client/port ids, since ALSA assigns those dynamically and they
    aren't stable across reconnects or restarts. It's fine for the file to
    hold aliases for ports that aren't currently plugged in, and fine for a
    listed port to have no matching alias.
    """

    def __init__(self, path: str | Path = "aliases.json") -> None:
        self.path = Path(path)

    def get(self, client_name: str | None, port_name: str) -> str | None:
        if client_name is None:
            return None

        return self._load_raw().get(client_name, {}).get(port_name)

    def set(self, client_name: str, port_name: str, alias: str) -> None:
        aliases = self._load_raw()
        aliases.setdefault(client_name, {})[port_name] = alias
        self._save(aliases)

    def delete(self, client_name: str, port_name: str) -> None:
        aliases = self._load_raw()

        if port_name not in aliases.get(client_name, {}):
            return

        del aliases[client_name][port_name]

        if not aliases[client_name]:
            del aliases[client_name]

        self._save(aliases)

    def _load_raw(self) -> dict[str, dict[str, str]]:
        if not self.path.exists():
            return {}

        contents = self.path.read_text(encoding="utf-8").strip()

        if not contents:
            return {}

        data = json.loads(contents)

        if not isinstance(data, dict):
            raise ValueError("Alias file must contain a JSON object")

        return data

    def _save(self, aliases: dict[str, dict[str, str]]) -> None:
        self.path.write_text(
            json.dumps(aliases, indent=2, sort_keys=True),
            encoding="utf-8",
        )
