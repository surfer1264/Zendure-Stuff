"""Module for the Hyper2000 device integration in Home Assistant."""

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from custom_components.zendure_ha.device import ZendureLegacy

_LOGGER = logging.getLogger(__name__)


class SuperBaseV6400(ZendureLegacy):
    def __init__(self, hass: HomeAssistant, deviceId: str, prodName: str, definition: Any, parent: str | None = None) -> None:
        """Initialise SuperBaseV6400."""
        super().__init__(hass, deviceId, definition["deviceName"], prodName, definition, parent)
        self.powerMin = -900
        self.powerMax = 800

    def writePower(self, power: int, inprogram: bool) -> None:
        delta = abs(power - self.powerAct)
        if delta <= 1 and inprogram:
            _LOGGER.info(f"Update power {self.name} => no action [power {power}]")
            return

        _LOGGER.info(f"Update power {self.name} => {power}")
        self.mqttInvoke({
            "arguments": [
                {
                    "autoModelProgram": 2 if inprogram else 0,
                    "autoModelValue": {
                        "chargingType": 0 if power >= 0 else 1,
                        "chargingPower": 0 if power >= 0 else -power,
                        "freq": 0,
                        "outPower": max(0, power),
                    },
                    "msgType": 1,
                    "autoModel": 8 if inprogram else 0,
                }
            ],
            "function": "deviceAutomation",
        })
