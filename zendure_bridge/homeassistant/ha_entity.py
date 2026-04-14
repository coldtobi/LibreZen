# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import json

from typing import cast, Any

from dataclasses import dataclass, field

from ..zendure_protocols import ZendureController
from ..device import ZendureState

@dataclass
class HAEntity:
    """ Baseclass for HA entities, like sensors and control items. """

    name: str            # human readable caption for Homeassistant.
    field_name: str      # fiels of the dataclass ZendureState-Feldname, including for syntetic, derived sensors or controls.

    _last_availability: bool = field(default=True, init=False) # for the change detection of the availablity.

    _cached_display_value: int | str | None = field(default=None, init=False)

    needs_re_discovery: bool = field(default=False, init=False) # discovery information has changed, needs to be re-sent

    @property
    def ha_component_type(self) -> str:
        raise NotImplementedError

    def get_ha_json(self, zencontrol: ZendureController) -> str:
        """ generate JSON to advertise the HAEntity to homassistant.

            The call to this function consumes/resets the 'needs_re_discovery'.
        """

        self.needs_re_discovery = False
        return json.dumps(self._build_ha_discovery_dict(zencontrol))

    def get_state_topic(self, zencontrol: ZendureController) -> str:
        """ generate mqtt topic string for homeassistant to publish a state """
        ctx = zencontrol.get_bridge_context()
        haconfig = ctx.haconfig
        zenconfig = ctx.zenconfig
        return f"{haconfig.discovery_prefix}/{self.ha_component_type}/zendure_{zenconfig.device_id}_{self.field_name}/state"

    def get_discovery_topic(self, zencontrol: ZendureController) -> str:
        """ generate mqtt topic string for homeassistant to publish a discovery topic. """
        ctx = zencontrol.get_bridge_context()
        haconfig = ctx.haconfig
        zenconfig = ctx.zenconfig
        return f"{haconfig.discovery_prefix}/{self.ha_component_type}/zendure_{zenconfig.device_id}_{self.field_name}/config"

    def get_availabilty_topic(self, zencontrol: ZendureController) -> str:
        ctx = zencontrol.get_bridge_context()
        haconfig = ctx.haconfig
        zenconfig = ctx.zenconfig
        return f"{haconfig.discovery_prefix}/{self.ha_component_type}/zendure_{zenconfig.device_id}_{self.field_name}/availability"

    def _build_ha_discovery_dict(self, zencontrol: ZendureController) -> dict[str, Any]:
        """ build a dict containing all information for homeassisent's discovery of an entity.

            subclasses ammend this information, eg. to add HAControl specific information.
        """
        ctx = zencontrol.get_bridge_context()
        haconfig = ctx.haconfig
        zenconfig = ctx.zenconfig

        _dict = {
            'name': self.name,
            'state_topic': self.get_state_topic(zencontrol),
            'availability_topic': self.get_availabilty_topic(zencontrol),
            'unique_id': f"zendure_{zenconfig.device_id}_{self.field_name}",
            'device': {
                "identifiers": [f"zendure_{zenconfig.device_id}"],
                "name": haconfig.device_name,
                "model": haconfig.model_name,
            }
        }
        return _dict

    def update(self, state: ZendureState, zencontrol: ZendureController) -> None:
        pass

    def get_value(self, state: ZendureState) -> int :
        """ retrieve value - by default mapped directly to the state. """
        return cast(int, getattr(state, self.field_name))

    def get_display_value(self, state: ZendureState) -> int | str:
        """Return the value to publish to HA. Override for string representations."""
        return self.get_value(state)

    def has_changed(self , state: ZendureState) -> bool :
        """ query if an information has been changed, e.g to avoid sending the same values to homeassistant again and again.

        A call to this function will consume the "has changed" state.
        """
        value = self.get_display_value(state)
        if value != self._cached_display_value:
            self._cached_display_value = value
            return True
        return False

    def is_available(self, _state: ZendureState, _zencontrol: ZendureController) -> bool:
        return True  # default: immer verfügbar

    def has_availability_changed(self, state: ZendureState, zencontrol: ZendureController) -> bool:
        available = self.is_available(state, zencontrol)
        if available != self._last_availability:
            self._last_availability = available
            return True
        return False

