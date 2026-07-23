from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Endpoint:
    """
    Stable application-level reference to an ALSA MIDI port.

    For the prototype, matching is based on client/port names.
    Later this can include USB vendor/product IDs or explicit user mappings.
    """
    device: str
    port: str | None = None


@dataclass(frozen=True, slots=True)
class Route:
    source: Endpoint
    destination: Endpoint
    processor: str | None = None

    @property
    def is_direct(self) -> bool:
        return self.processor is None