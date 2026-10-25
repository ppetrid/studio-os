import argparse
from studio_midi.backend import AlsaBackend
from studio_midi.devices import DeviceStore
from studio_midi.models import Endpoint, Route
from studio_midi.presets import DeviceRef, PresetRoute, PresetStore, label
from studio_midi.router import Router


def make_route(source: str, destination: str) -> Route:
    return Route(
        source=Endpoint(device=source),
        destination=Endpoint(device=destination),
    )


def parse_preset_route(value: str) -> PresetRoute:
    try:
        source, destination = value.split(":", maxsplit=1)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid route {value!r}; expected source:destination"
        ) from exc

    return PresetRoute(source=DeviceRef(source), destination=DeviceRef(destination))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    connect = commands.add_parser("connect")
    connect.add_argument("source")
    connect.add_argument("destination")

    disconnect = commands.add_parser("disconnect")
    disconnect.add_argument("source")
    disconnect.add_argument("destination")

    save_preset = commands.add_parser("save-preset")
    save_preset.add_argument("name")
    save_preset.add_argument(
        "routes",
        nargs="*",
        type=parse_preset_route,
        help='Routes between device names, formatted as "source:destination". '
        "Defaults to the current routing.",
    )

    recall_preset = commands.add_parser("recall-preset")
    recall_preset.add_argument("name")

    commands.add_parser("list-presets")

    return parser


def main() -> int:
    args = build_parser().parse_args()

    backend = AlsaBackend()
    router = Router(backend, DeviceStore())
    presets = PresetStore()

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

            case "save-preset":
                if args.routes:
                    presets.save(args.name, args.routes)
                else:
                    presets.save_current(args.name, router)
                print(f"Saved preset {args.name!r}")

            case "recall-preset":
                skipped = presets.recall(args.name, router)
                print(f"Recalled preset {args.name!r}")
                for item in skipped:
                    print(
                        f"  skipped {label(item.route.source)} → "
                        f"{label(item.route.destination)}: {item.reason}"
                    )

            case "list-presets":
                for name in presets.list_names():
                    print(name)

        return 0

    finally:
        backend.close()


if __name__ == "__main__":
    raise SystemExit(main())
