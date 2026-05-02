# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import json

from typing import Any

from dataclasses import dataclass, field

from ..device import ZendureState

from ..bridge_components import BridgeComponents
from zendure_bridge.zendure_protocols import ZendureController

@dataclass
class HAEntity:
    """ Baseclass for HA entities, like sensors and control items. """


    name: str            # human readable caption for Homeassistant.
    field_name: str      # fiels of the dataclass ZendureState-Feldname, including for synthetic, derived sensors or controls.

    _publish_to_ha: bool         # This entity is for / controled by homeassistant
    _publish_to_nodered: bool    # This entity is for / controled by NodeRED


    _last_availability: bool = field(default=True, init=False) # for the change detection of the availability.

    _cached_display_value: int | str | None = field(default=None, init=False)

    @property
    def ha_component_type(self) -> str:
        raise NotImplementedError

    @property
    def is_expert(self) -> bool:
        ''' Expert-Settings cannot be controled by homeassistant if the expert mode is off. '''
        return False

    @property
    def is_synthetic(self) -> bool:
        ''' A synthetic Entity is not backed up by the Zendure Device, it is manufactored in this programm. '''
        return False

    @property
    def publish_to_ha(self) -> bool:
        ''' This Entity should be made known to Homeassistant '''
        return self._publish_to_ha

    @property
    def publish_to_nodered(self) -> bool:
        ''' This Entity's state should be sent to NodeRed - and if a HAControl controlled by it. '''
        return self._publish_to_nodered

    def _get_zencontrol(self, bc: BridgeComponents) -> ZendureController:
        assert bc.bridge is not None
        return bc.bridge

    def get_ha_json(self, bc: BridgeComponents) -> str:
        """ generate JSON to advertise the HAEntity to homassistant. """
        return json.dumps(self._build_ha_discovery_dict(bc))

    def get_state_topic(self, bc: BridgeComponents) -> str:
        """ generate mqtt topic string for homeassistant to publish a state """
        haconfig = bc.config.homeassistant
        zenconfig = bc.config.zendure
        return f"{haconfig.discovery_prefix}/{self.ha_component_type}/zendure_{zenconfig.device_id}_{self.field_name}/state"

    def get_discovery_topic(self, bc: BridgeComponents) -> str:
        """ generate mqtt topic string for homeassistant to publish a discovery topic. """
        haconfig = bc.config.homeassistant
        zenconfig = bc.config.zendure
        return f"{haconfig.discovery_prefix}/{self.ha_component_type}/zendure_{zenconfig.device_id}_{self.field_name}/config"

    def get_availabilty_topic(self, bc: BridgeComponents) -> str:
        haconfig = bc.config.homeassistant
        zenconfig = bc.config.zendure
        return f"{haconfig.discovery_prefix}/{self.ha_component_type}/zendure_{zenconfig.device_id}_{self.field_name}/availability"

    def _build_ha_discovery_dict(self, bc: BridgeComponents) -> dict[str, Any]:
        """ build a dict containing all information for homeassisent's discovery of an entity.

            subclasses ammend this information, eg. to add HAControl specific information.
        """
        haconfig = bc.config.homeassistant
        zenconfig = bc.config.zendure

        _dict = {
            'name': self.name,
            'state_topic': self.get_state_topic(bc),
            'availability_topic': self.get_availabilty_topic(bc),
            'unique_id': f"zendure_{zenconfig.device_id}_{self.field_name}",
            'device': {
                "identifiers": [f"zendure_{zenconfig.device_id}"],
                "name": haconfig.device_name,
                "model": haconfig.model_name,
            }
        }

        # expert settings should not be enabled in homeassistant by default.
        if self.is_expert:
          _dict['enabled_by_default'] = "false"

        return _dict

    def update(self, state: ZendureState, bc: BridgeComponents) -> None:
        pass

    def get_value(self, state: ZendureState) -> int | None:
        """ retrieve value - by default mapped directly to the state.

        Returns None if the underlying state field has not been initialized.
        """
        current = getattr(state, self.field_name)
        if not isinstance(current, int):
            return None
        return current

    def get_display_value(self, state: ZendureState) -> int | str | None:
        """Return the value to publish to HA. Override for string representations."""
        return self.get_value(state)

    def has_changed(self, state: ZendureState) -> bool:
        """Query whether an entity's visible value has changed.

        This call consumes the "has changed" state by updating the internal
        cache when a change is observed. If the underlying state field has
        not been initialized (i.e. is None) we consider there to be nothing to
        report and return False. The first non-None observed value will be
        treated as a change so that the initial actual state is advertised.
        """

        # If the underlying (raw) value hasn't been set yet, don't advertise.
        if self.get_value(state) is None:
            return False

        value = self.get_display_value(state)

        if value != self._cached_display_value:
            self._cached_display_value = value
            return True

        return False

    def is_available(self, state: ZendureState, _bc: BridgeComponents) -> bool:
        """ calculate availability based on whether we know the device state.

            If a entity is syntetic, we assume it is always available by default.
        """
        return True if self.is_synthetic or self.get_value(state) is not None else False

    def has_availability_changed(self, state: ZendureState, bc: BridgeComponents) -> bool:
        available = self.is_available(state, bc)
        if available != self._last_availability:
            self._last_availability = available
            return True
        return False
