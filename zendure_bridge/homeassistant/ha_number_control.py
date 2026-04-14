# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from typing import Any
from dataclasses import dataclass

from ..device import ZendureState, _PROPERTY_MAP
from ..zendure_protocols import ZendureController

from .ha_control import HAControl

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
            'device_class' : self.device_class,
            'mode' : self.display_mode
        }
        return (_dict | _extra)

    def _get_command_properties(self, mqttpayload: bytes) -> dict[str, int] :
        """ map state's field_name to Zendure's property name and assign the value from the MQTT control payload. """

        # reverse dict lookup to determine the proper Zendure property for this Control.
        _keys = [ key for key,val in _PROPERTY_MAP.items() if val == self.field_name ]
        assert len(_keys) == 1 , "Property not found or duplicate defintion."
        # generate dict and assign mqtt payload value.
        _properties = {
            _keys[0]: int(mqttpayload.decode())
        }
        return _properties


    def handle_command(self,
                       mqttpayload: bytes, _zenstate: ZendureState,
                       zencontrol: ZendureController) -> None:
        """ Handle a numeric value sent from homeassistant to be sent to the zendure.

            This will just set the properties associated with the HAConrol, if some command
            needs extra properties to be set, needs to be overriden.
        """
        _properties = self._get_command_properties(mqttpayload)
        zencontrol.write_property(_properties)

    def is_available(self, _state: ZendureState, zencontrol: ZendureController) -> bool:
        # expert controls are available only if expert_mode has been configured.
        return ( not self.is_expert ) or zencontrol.get_bridge_context().haconfig.expert_mode

