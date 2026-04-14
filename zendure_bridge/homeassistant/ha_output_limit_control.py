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

from ..device import ZendureState
from ..zendure_protocols import ZendureController

from .ha_number_control import HANumberControl

@dataclass
class HAOutputLimitControl(HANumberControl):
    """ HAControl for OutputLimit.

        (needs to set acMode, therefore overriden)
    """
    def handle_command(self, mqttpayload: bytes, _zenstate: ZendureState,
                       zencontrol: ZendureController) -> None:

        try:
            _properties = self._get_command_properties(mqttpayload)
            _properties["acMode"] = 2
            zencontrol.write_property(_properties)
        except ValueError:
            logger.error(f"value %s for %s out of range: %d < xx < %d",
                         mqttpayload.decode(), self.field_name, self.min, self.max)

    def is_available(self, state:ZendureState, zencontrol:ZendureController)->bool:
        if not super().is_available(state, zencontrol):
            return False
        return state.auto_model == 0
