# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from .ha_sensor import HASensor

class SocSensor (HASensor):
    pass

#    für future me:
#    def update(self, state: ZendureState) -> None :
#        # some math to determine the current energy level in Wh.
#        # possibly guessing, but doing a integration of charging-power / discharging-power
#        # to determine the current charge level.
#        # possibly also have some rough file-based "experience" lookup value to have something after restart.
#        # this is future!
#        # this class can even store the calculated information in ZendureState, so that other sensors can derive
#        # information from this as well (e.g a sensor "CapacityWh" or "BatteryHealth")
