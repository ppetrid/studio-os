import json
from dataclasses import asdict
from pathlib import Path
from .models import Endpoint, Route
from .router import Router


class SceneStore:
    def __init__(self, path: str | Path = "scenes.json") -> None:
        self.path = Path(path)

    def list_names(self) -> list[str]:
        return sorted(self._load_raw())

    def get(self, name: str) -> set[Route]:
        scenes = self._load_raw()

        try:
            raw_routes = scenes[name]
        except KeyError as exc:
            raise KeyError(f"Unknown scene: {name!r}") from exc

        return {
            Route(
                source=Endpoint(**item["source"]),
                destination=Endpoint(**item["destination"]),
                processor=item.get("processor"),
            )
            for item in raw_routes
        }

    def save(self, name: str, routes: set[Route]) -> None:
        scenes = self._load_raw()

        scenes[name] = [
            {
                "source": asdict(route.source),
                "destination": asdict(route.destination),
                "processor": route.processor,
            }
            for route in sorted(
                routes,
                key=lambda route: (
                    route.source.device,
                    route.destination.device,
                    route.processor or "",
                ),
            )
        ]

        self.path.write_text(
            json.dumps(scenes, indent=2),
            encoding="utf-8",
        )

    def delete(self, name: str) -> None:
        scenes = self._load_raw()

        if name not in scenes:
            raise KeyError(f"Unknown scene: {name!r}")

        del scenes[name]

        self.path.write_text(
            json.dumps(scenes, indent=2),
            encoding="utf-8",
        )

    def activate(self, name: str, router: Router) -> None:
        router.replace_routes(self.get(name))

    def _load_raw(self) -> dict[str, list[dict]]:
        if not self.path.exists():
            return {}

        contents = self.path.read_text(encoding="utf-8").strip()

        if not contents:
            return {}

        data = json.loads(contents)

        if not isinstance(data, dict):
            raise ValueError("Scene file must contain a JSON object")

        return data
