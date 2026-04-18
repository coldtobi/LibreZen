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

from ..device import ZendureState
from ..bridge_components import BridgeComponents

@dataclass
class HAControl(HAEntity):
    """ Baseclass for Control Entities for Homeassistant """

    def _build_ha_discovery_dict(self, bc: BridgeComponents) -> dict[str, Any]:
        _dict = super()._build_ha_discovery_dict(bc)
        _dict['command_topic'] = self.get_command_topic(bc)
        return _dict

    def get_command_topic(self, bc: BridgeComponents) -> str:
        """ assemble the MQTT topic to control this HAControl. """
        haconfig = bc.config.homeassistant
        zenconfig = bc.config.zendure
        return f"{haconfig.discovery_prefix}/{self.ha_component_type}/zendure_{zenconfig.device_id}_{self.field_name}/set"

    def handle_command(self, _mqttpayload: bytes, _zenstate: ZendureState, bc: BridgeComponents) -> None:
        raise NotImplementedError
