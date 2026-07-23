from alsa_midi import PortType, SequencerClient


def main() -> None:
    client = SequencerClient("studio-discovery")

    print("MIDI sources — devices that can send MIDI:")
    source_ports = client.list_ports(
        input=True,
        type=PortType.MIDI_GENERIC | PortType.HARDWARE,
    )

    for port in source_ports:
        print(
            f"  {port.client_id}:{port.port_id} "
            f"{port.client_name!r} / {port.name!r}"
        )

    print("\nMIDI destinations — devices that can receive MIDI:")
    destination_ports = client.list_ports(
        output=True,
        type=PortType.MIDI_GENERIC | PortType.HARDWARE,
    )

    for port in destination_ports:
        print(
            f"  {port.client_id}:{port.port_id} "
            f"{port.client_name!r} / {port.name!r}"
        )


if __name__ == "__main__":
    main()
