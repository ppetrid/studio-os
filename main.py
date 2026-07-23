import argparse
from studio_midi.backend import AlsaBackend
from studio_midi.models import Endpoint, Route
from studio_midi.router import Router
from studio_midi.scenes import SceneStore


def make_route(source: str, destination: str) -> Route:
    return Route(
        source=Endpoint(device=source),
        destination=Endpoint(device=destination),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    connect = commands.add_parser("connect")
    connect.add_argument("source")
    connect.add_argument("destination")

    disconnect = commands.add_parser("disconnect")
    disconnect.add_argument("source")
    disconnect.add_argument("destination")

    save_scene = commands.add_parser("save-scene")
    save_scene.add_argument("name")
    save_scene.add_argument(
        "routes",
        nargs="+",
        help='Routes formatted as "source:destination"',
    )

    activate_scene = commands.add_parser("activate-scene")
    activate_scene.add_argument("name")

    commands.add_parser("list-scenes")

    return parser


def parse_route(value: str) -> Route:
    try:
        source, destination = value.split(":", maxsplit=1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid route {value!r}; expected source:destination"
        ) from exc

    return make_route(source, destination)


def main() -> int:
    args = build_parser().parse_args()

    backend = AlsaBackend()
    router = Router(backend)
    scenes = SceneStore()

    try:
        match args.command:
            case "connect":
                route = make_route(args.source, args.destination)
                router.connect(route)
                print(f"Connected {args.source} → {args.destination}")

            case "disconnect":
                route = make_route(args.source, args.destination)
                router.disconnect(route)
                print(f"Disconnected {args.source} → {args.destination}")

            case "save-scene":
                routes = {parse_route(value) for value in args.routes}
                scenes.save(args.name, routes)
                print(f"Saved scene {args.name!r}")

            case "activate-scene":
                scenes.activate(args.name, router)
                print(f"Activated scene {args.name!r}")

            case "list-scenes":
                for name in scenes.list_names():
                    print(name)

        return 0

    finally:
        backend.close()


if __name__ == "__main__":
    raise SystemExit(main())
