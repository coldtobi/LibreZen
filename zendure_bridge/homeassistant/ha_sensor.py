# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from dataclasses import dataclass
from typing import Any

from .ha_entity import HAEntity
from zendure_bridge.bridge_components import BridgeComponents


@dataclass
class HASensor(HAEntity):
    """ Sensor for Homeassistant defintion and handling."""

    unit: str
    device_class: str    # HA device_class: "power", "battery", "energy"

    @property
    def ha_component_type(self) -> str:
        return "sensor"

    def _build_ha_discovery_dict(self, bc: BridgeComponents) -> dict[str, Any]:

        _dict = super()._build_ha_discovery_dict(bc)
        _dict['device_class'] = self.device_class
        if self.unit:
            _dict['unit_of_measurement'] = self.unit

        return _dict
