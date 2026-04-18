# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# import logging

from typing import cast
from dataclasses import dataclass

from .ha_number_control import HANumberControl

from ..device import ZendureState
from ..bridge_components import BridgeComponents


@dataclass
class HAInvMaxPowerControl(HANumberControl):
    """ HAControl for maximum Inverter Output Setting

        Limits the maximum output power, ("Legal setting" in the app)
    """
    _cached_value: int | None = None

    def update(self, state: ZendureState, bc: BridgeComponents) -> None:
        from .ha_entities import find_sensor_objs
        from .ha_output_limit_control import HAOutputLimitControl

        if state.inverse_max_power is None:
            return

        inverse_max_power = state.inverse_max_power
        output_limit = state.output_limit
        if inverse_max_power is None or output_limit is None:
            return

        # as update is called whenever _any_ state changes, limit to actual
        # changes on our value, as below might be a bit more expensive and
        # should only trigger on real changes.
        if self._cached_value == state.inverse_max_power:
            return
        self._cached_value = state.inverse_max_power

        # Tweaking Outputlimit
        ents = find_sensor_objs("output_limit", HAOutputLimitControl)
        assert ents,"Cannot find output_limit entity."
        outputlimit =  cast(HAOutputLimitControl, ents[0])

        # ensure that output limit's numeric control max is adjusted.
        if inverse_max_power < output_limit:
            fakepayload = str(state.inverse_max_power).encode()
            properties = outputlimit._get_command_properties(fakepayload)
            self._get_zencontrol(bc).write_property(properties)

        # re-set the homeassistant control's max if required.
        if outputlimit.max != inverse_max_power:
            outputlimit.max = inverse_max_power
            bc.ha_publisher.publish_ha_discovery(outputlimit)

        # hack: if the control is disabled (expert mode off), show as box
        # as sliders won't display numeric values.
        if (not self.is_available(state, bc)) and (self.display_mode != "box"):
            self.display_mode = "box"
            bc.ha_publisher.publish_ha_discovery(self)
