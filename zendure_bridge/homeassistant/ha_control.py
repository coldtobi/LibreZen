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

from ..zendure_protocols import ZendureController
from ..device import ZendureState

@dataclass
class HAControl(HAEntity):
    """ Baseclass for Control Entities for Homeassistant """

    def _build_ha_discovery_dict(self, zencontrol: ZendureController)-> dict[str, Any]:
        _dict = super()._build_ha_discovery_dict(zencontrol)
        _dict['command_topic'] = self.get_command_topic(zencontrol)
        return _dict

    def get_command_topic(self, zencontrol: ZendureController) -> str:
        """ assemble the MQTT topic to control this HAControl. """
        haconfig = zencontrol.get_bridge_context().haconfig
        zenconfig = zencontrol.get_bridge_context().zenconfig
        return f"{haconfig.discovery_prefix}/{self.ha_component_type}/zendure_{zenconfig.device_id}_{self.field_name}/set"

    def handle_command(self, _mqttpayload: bytes, _zenstate: ZendureState, _zencontrol: ZendureController) -> None:
        raise NotImplementedError
