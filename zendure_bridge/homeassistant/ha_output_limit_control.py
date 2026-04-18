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

from .ha_number_control import HANumberControl

from ..device import ZendureState
from ..bridge_components import BridgeComponents

@dataclass
class HAOutputLimitControl(HANumberControl):
    """ HAControl for OutputLimit.

        (needs to set acMode, therefore overriden)
    """
    def handle_command(self, mqttpayload: bytes, _zenstate: ZendureState,
                       bc: BridgeComponents) -> None:

        try:
            _properties = self._get_command_properties(mqttpayload)
            _properties["acMode"] = 2
            self._get_zencontrol(bc).write_property(_properties)
        except ValueError:
            logger.error(f"value %s for %s out of range: %d < xx < %d",
                         mqttpayload.decode(), self.field_name, self.min, self.max)

    def is_available(self, state:ZendureState, bc: BridgeComponents ) -> bool:
        if not super().is_available(state, bc):
            return False
        return state.auto_model == 0
