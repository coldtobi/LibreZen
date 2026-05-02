# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import logging

logger = logging.getLogger(__name__)

from typing import Any
from dataclasses import dataclass

from .ha_control import HAControl

from ..device import ZendureState, _PROPERTY_MAP
from ..bridge_components import BridgeComponents

@dataclass
class HANumberControl(HAControl):
    """ A numeric HAControl """
    unit: str           # Unit of measurement
    min: int            # minimum value
    max: int            # maximum value
    step: int           # step size
    device_class: str   # HA device_class: "power", "battery", "energy"
    display_mode: str = "auto"    # "auto", "box" or "slider"

    _is_expert: bool = False      # expert settings are only sent to homeassistant if enabled in config.
    _is_synthetic: bool = False   # not a property of the zendure device, so don't send it to it.


    @property
    def ha_component_type(self) -> str:
        return "number"


    @property
    def is_expert(self) -> bool:
        return self._is_expert


    @property
    def is_synthetic(self) -> bool:
        return self._is_synthetic


    def _build_ha_discovery_dict(self, bc: BridgeComponents) -> dict[str, Any]:
        _dict = super()._build_ha_discovery_dict(bc)
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
        if not self.min <= value <= self.max:
            raise(ValueError)

        _properties = {
            _keys[0]: value
        }
        return _properties


    def handle_command(self,
                       mqttpayload: bytes, zenstate: ZendureState,
                       bc: BridgeComponents) -> None:
        """ Handle a numeric value sent from homeassistant to be sent to the zendure.

            This will just set the properties associated with the HAConrol, if some command
            needs extra properties to be set, needs to be overriden.
        """
        try:
            if not self.is_synthetic:
                properties = self._get_command_properties(mqttpayload)
                self._get_zencontrol(bc).write_property(properties)
            else:
                value = int(mqttpayload.decode())
                if not self.min < value < self.max:
                    raise(ValueError)
                bc.device.update_value(self.field_name, value)
                setattr(zenstate, self.field_name, value)
        except ValueError:
            logger.error(f"value %s for %s out of range: %d < xx < %d",
                         mqttpayload.decode(), self.field_name, self.min, self.max)

    def is_available(self, _state: ZendureState, bc: BridgeComponents) -> bool:
        # expert controls are available only if expert_mode has been configured.
        return ( not self.is_expert ) or bc.config.homeassistant.expert_mode
