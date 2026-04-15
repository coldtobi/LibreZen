# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import logging
logger = logging.getLogger(__name__)

from dataclasses import dataclass
from typing import Any

from .ha_control import HAControl
from ..zendure_protocols import ZendureController
from ..device import ZendureState, _PROPERTY_MAP


@dataclass
class HASwitchControl(HAControl):
    """Home Assistant MQTT Switch control.

    Publishes a switch that accepts typical payloads from HA ("ON"/"OFF", "1"/"0", "true"/"false").
    When not synthetic it will map the control to the corresponding Zendure property (reverse lookup
    in _PROPERTY_MAP) and call `zencontrol.write_property` with the integer value (1/0).
    """

    is_expert: bool = False
    is_syntetic: bool = False
    payload_on: str = "ON"
    payload_off: str = "OFF"

    @property
    def ha_component_type(self) -> str:
        return "switch"

    def _build_ha_discovery_dict(self, zencontrol: ZendureController) -> dict[str, Any]:
        _dict = super()._build_ha_discovery_dict(zencontrol)
        # include explicit payloads so HA knows what to send
        _extra = {
            'payload_on': self.payload_on,
            'payload_off': self.payload_off,
        }
        return (_dict | _extra)

    def get_display_value(self, state: ZendureState) -> str | None:
        # represent the binary state as ON/OFF for Home Assistant
        val = self.get_value(state)
        if val is None:
              return None
        try:
            is_on = bool(int(val))
        except Exception:
            is_on = bool(val)
        return self.payload_on if is_on else self.payload_off

    def _payload_to_int(self, mqttpayload: bytes) -> int:
        received = mqttpayload.decode().strip().lower()
        if received in (self.payload_on.lower(), 'on', '1', 'true', 'yes'):
            return 1
        if received in (self.payload_off.lower(), 'off', '0', 'false', 'no'):
            return 0
        raise ValueError(f"Invalid payload for switch: {received}")

    def handle_command(self, mqttpayload: bytes, zenstate: ZendureState, zencontrol: ZendureController) -> None:
        try:
            value = self._payload_to_int(mqttpayload)

            if not self.is_syntetic:
                # find corresponding Zendure property key
                _keys = [key for key, val in _PROPERTY_MAP.items() if val == self.field_name]
                assert len(_keys) == 1, "Property not found or duplicate definition."
                properties = {_keys[0]: value}
                zencontrol.write_property(properties)
            else:
                # update local state only
                zencontrol.update_state_value(self.field_name, value)
                setattr(zenstate, self.field_name, value)

        except (AssertionError, ValueError) as e:
            logger.error("Error handling switch command for %s: %s", self.field_name, e)

    def is_available(self, _state: ZendureState, zencontrol: ZendureController) -> bool:
        # expert controls are available only if expert_mode has been configured.
        return (not self.is_expert) or zencontrol.get_bridge_context().haconfig.expert_mode
