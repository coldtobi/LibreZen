# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from dataclasses import dataclass

from .ha_sensor import HASensor
from ..device import ZendureState
from ..zendure_protocols import ZendureController


@dataclass
class BatterySensor(HASensor):

    def update(self, state: ZendureState, zencontrol: ZendureController)-> None:
        # pack_input_power -> DISCHARGE power
        # output_pack_power -> CHARGE power.
        if state.pack_input_power > 0:
            _bat_pwr = - state.pack_input_power
        elif state.output_pack_power > 0:
            _bat_pwr = state.output_pack_power
        else:
            # zendure sets value <20 to zero, so du some guesswork based on input/output power.
            _bat_pwr = state.solar_input_power - state.output_home_power

        # update both the state snapshot and the global state (as bat_pwr is syntentic, not from the device)
        state.battery_charge_power = _bat_pwr
        zencontrol.update_state_value(self.field_name, _bat_pwr)
