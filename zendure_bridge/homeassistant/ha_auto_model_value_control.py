# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
from dataclasses import dataclass
from typing import cast

from .ha_number_control import HANumberControl

from ..device import ZendureState
from ..zendure_protocols import ZendureController

@dataclass
class HAAutoModelValueControl(HANumberControl):

    def handle_command(self, mqttpayload:bytes, zenstate:ZendureState, zencontrol:ZendureController) -> None:
        """ call invoke function for the device automatin "automodel" 

            implemented only for autoModel 8 and 9.
        """
        oldvalue = zenstate.auto_model_value
        super().handle_command(mqttpayload, zenstate, zencontrol)
        if oldvalue == zenstate.auto_model_value:
            return

        autoModel = zenstate.auto_model
        if (autoModel != 8 and autoModel != 9):
            return
        autoModelProgram = zenstate.auto_model_program
        autoModelValue = zenstate.auto_model_value

        from .ha_entities import find_sensor_objs
        from .ha_auto_model_select_control import HAAutoModelSelectControl
        ents = find_sensor_objs("auto_model", HAAutoModelSelectControl)
        assert ents,"Cannot find output_limit entity."
        ha_amsctrl = cast(HAAutoModelSelectControl, ents[0])
        arguments = ha_amsctrl._generate_invoke_parameters(autoModelProgram, autoModel, autoModelValue)
        zencontrol.invoke_function(arguments, "deviceAutomation")
