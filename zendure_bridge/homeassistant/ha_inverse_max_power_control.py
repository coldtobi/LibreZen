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

from ..device import ZendureState
from ..zendure_protocols import ZendureController

from .ha_number_control import HANumberControl


@dataclass
class HAInvMaxPowerControl(HANumberControl):
    """ HAControl for maximum Inverter Output Setting

        Limits the maximum output power, ("Legal setting" in the app)
    """

    def update(self, state: ZendureState, zencontrol: ZendureController)->None:
        from .ha_entities import find_sensor_obj
        from .ha_output_limit_control import HAOutputLimitControl
        # Tweaking Outputlimit
        outputlimit = cast(HAOutputLimitControl, find_sensor_obj("output_limit"))
        # ensure that output limit's numeric control max is adjusted.
        if state.inverse_max_power < state.output_limit:
            fakepayload = str(state.inverse_max_power).encode()
            _properties = outputlimit._get_command_properties(fakepayload)
            zencontrol.write_property(_properties)

        # re-set the homeassistant control's max if required.
        if outputlimit.max != state.inverse_max_power:
            outputlimit.max = state.inverse_max_power
            outputlimit.needs_re_discovery = True

        # hack: if the control is disabled (expert mode off), show as box
        # as sliders won't cut it.
        if (not self.is_available(state, zencontrol)) and (self.display_mode != "box"):
            self.display_mode = "box"
            self.needs_re_discovery = True