"""Module for the Solarflow2400AC device integration in Home Assistant."""

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.zendure_ha.device import ZendureZenSdk
from custom_components.zendure_ha.sensor import ZendureRestoreSensor, ZendureSensor

_LOGGER = logging.getLogger(__name__)


class SolarFlow1600(ZendureZenSdk):
    def __init__(self, hass: HomeAssistant, deviceId: str, prodName: str, definition: Any) -> None:
        """Initialise SolarFlow1600."""
        super().__init__(hass, deviceId, prodName, definition["productModel"], definition)
        self.setLimits(-1600, 1600)
        self.maxSolar = -1600
        self.offGrid = ZendureSensor(self, "gridOffPower", None, "W", "power", "measurement")
        self.aggrOffGrid = ZendureRestoreSensor(self, "aggrGridOffPower", None, "kWh", "energy", "total", 2)

    @property
    def pwr_offgrid(self) -> int:
        """Get the offgrid power."""
        return self.offGrid.asInt
