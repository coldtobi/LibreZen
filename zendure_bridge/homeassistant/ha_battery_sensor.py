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
from ..bridge_components import BridgeComponents

@dataclass
class BatterySensor(HASensor):

    def update(self, state: ZendureState, bc: BridgeComponents) -> None:
        # pack_input_power -> DISCHARGE power
        # output_pack_power -> CHARGE power.
        input_power = state.pack_input_power
        output_power = state.output_pack_power
        output_home_power = state.output_home_power
        solar_input_power = state.solar_input_power
        if (input_power is None or output_power is None
                or output_home_power is None or solar_input_power is None):
            return  # not enough information to calculate, wait for next update.

        if input_power > 0:
            _bat_pwr = -input_power
        elif output_power > 0:
            _bat_pwr = output_power
        else:
            # If neither pack input nor pack output are active, assume battery
            # power is whatever PV is feeding minus the home output.
            _bat_pwr = solar_input_power - output_home_power

        # update both the state snapshot and the global state
        # (as bat_pwr is syntentic, not from the device)
        state.battery_charge_power = _bat_pwr
        self._get_zencontrol(bc).update_state_value(self.field_name, _bat_pwr)
