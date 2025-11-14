"""Base class for Zendure entities."""

from dataclasses import dataclass


@dataclass
class FuseGroup:
    """Zendure Fuse Group."""

    name: str = ""
    deviceId: str = ""
    maxpower: int = 0
    minpower: int = 0
    powerAvail: int = 0
    powerUsed: int = 0
