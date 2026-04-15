# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from dataclasses import dataclass

from ..device import ZendureState, _PROPERTY_MAP
from ..zendure_protocols import ZendureController

from .ha_number_control import HANumberControl

@dataclass
class HASoCControl(HANumberControl):

    def get_value(self, state: ZendureState) -> int | None:
        value = super().get_value(state)
        if value is None:
              return None
        return int(value/10)

    def handle_command(self, mqttpayload:bytes, _zenstate: ZendureState,
                       zencontrol: ZendureController)->None :
        """ handling setting of SoC limits.

            The override is needed, as the value is scaled by the factor of 10.
            (10 % = 100)
        """
        # scaling - zendure wants value x 10
        _keys = [ key for key,val in _PROPERTY_MAP.items() if val == self.field_name ]
        assert len(_keys) == 1 , "Property not found or duplicate defintion."
        # generate dict and assign mqtt payload value.
        _properties = {
            _keys[0]: int(mqttpayload.decode())*10
        }
        zencontrol.write_property(_properties)