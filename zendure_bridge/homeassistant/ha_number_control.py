# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import logging

from typing import Any
from dataclasses import dataclass

from ..device import ZendureState, _PROPERTY_MAP
from ..zendure_protocols import ZendureController

from .ha_control import HAControl

logger = logging.getLogger(__name__)

@dataclass
class HANumberControl(HAControl):
    """ A numeric HAControl """
    unit: str           # Unit of measurement
    min: int            # minimum value
    max: int            # maximum value
    step: int           # step size
    device_class: str   # HA device_class: "power", "battery", "energy"
    display_mode: str = "auto"    # "auto", "box" or "slider"

    is_expert: bool = False
    is_syntetic: bool = False   # not a property of the zendure device, so don't send it to it.

    @property
    def ha_component_type(self) -> str:
        return "number"

    def _build_ha_discovery_dict(self, zencontrol: ZendureController)-> dict[str, Any]:
        _dict = super()._build_ha_discovery_dict(zencontrol)
        _extra = {
            'unit_of_measurement' : self.unit,
            'min' : self.min,
            'max' : self.max,
            'step' : self.step,
            'mode' : self.display_mode
        }
        if self.device_class:
            _extra['device_class'] = self.device_class
        return (_dict | _extra)

    def _get_command_properties(self, mqttpayload: bytes) -> dict[str, int] :
        """ map state's field_name to Zendure's property name and assign the value from the MQTT control payload.

        The value is clamped to self.min < value < self.max.
         """

        # reverse dict lookup to determine the proper Zendure property for this Control.
        _keys = [ key for key,val in _PROPERTY_MAP.items() if val == self.field_name ]
        assert len(_keys) == 1 , "Property not found or duplicate defintion."
        # generate dict and assign mqtt payload value.
        value = int(mqttpayload.decode())
        if not self.min < value < self.max:
            raise(ValueError)

        _properties = {
            _keys[0]: value
        }
        return _properties


    def handle_command(self,
                       mqttpayload: bytes, zenstate: ZendureState,
                       zencontrol: ZendureController) -> None:
        """ Handle a numeric value sent from homeassistant to be sent to the zendure.

            This will just set the properties associated with the HAConrol, if some command
            needs extra properties to be set, needs to be overriden.
        """
        try:
            if not self.is_syntetic:
                _properties = self._get_command_properties(mqttpayload)
                zencontrol.write_property(_properties)
            else:
                value = int(mqttpayload.decode())
                if not self.min < value < self.max:
                    raise(ValueError)
                zencontrol.update_state_value(self.field_name, value)
                setattr(zenstate, self.field_name, value)
        except ValueError:
            logger.error(f"value %s for %s out of range: %d < xx < %d",
                         mqttpayload.decode(), self.field_name, self.min, self.max)

    def is_available(self, _state: ZendureState, zencontrol: ZendureController) -> bool:
        # expert controls are available only if expert_mode has been configured.
        return ( not self.is_expert ) or zencontrol.get_bridge_context().haconfig.expert_mode

