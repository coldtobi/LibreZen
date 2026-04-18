# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from dataclasses import dataclass
from typing import Any

from .ha_control import HAControl
from ..device import ZendureState
from ..bridge_components import BridgeComponents

@dataclass
class HASelectControl(HAControl):
    """ Implements a Homeassistant MQTT Select Control.

        Infos for the Control: https://www.home-assistant.io/integrations/select.mqtt/
    """

    lookup: dict[int, str]

    @property
    def ha_component_type(self) -> str:
        return "select"

    def get_display_value(self, state:ZendureState) -> str | None:
        numeric_value = self.get_value(state)
        if numeric_value is None:
            return None
        return self.lookup.get(numeric_value, "unknown")

    def _build_ha_discovery_dict(self, bc: BridgeComponents) -> dict[str, Any]:
        _dict = super()._build_ha_discovery_dict(bc)
        _dict['options'] = list(self.lookup.values())
        return _dict
