# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# example payload for setting automode 9:
#  {
#    "arguments": [ {"autoModelProgram":1,"autoModelValue":1794,"msgType":1,"autoModel":9} ],
#    "deviceKey":"<device_id>",
#    "function":"deviceAutomation",
#    "messageId":<random>,
#    "timestamp":1775837446
#  }



import logging

from dataclasses import dataclass

from .ha_select_control import HASelectControl

from ..device import ZendureState
from ..bridge_components import BridgeComponents

logger = logging.getLogger(__name__)

@dataclass
class HAAutoModelSelectControl(HASelectControl):
    """ MQTT Select Control for the "autoModel" property.

        This allows incvoking the different "autoModel" deviceAutomation programms as
        defined in _PROPERTY_MAP_AUTO_MODELS. The control value is set by the AutoModelValue property,
        see HAAutoModelValueControl.

        This control is only closed-loop-control, development and testing purposes, as the
        autoModel property is not intended to be set by the user. The underlaying deviceAutomation feature
        needs constant updating of its autoModelValue, not really suitable for (manual) user interaction.
        (the control might still be made available for the experienced user wanting to do the control
        loop entirely in homeassistant.
    """
    def _generate_invoke_parameters(self, automodelprogram:int, automodel:int, automodelvalue:int) -> dict[str, int]:
        arguments : dict[str,int] = {}
        # Note: currently only "0" "8" and "9" implemented.
        match automodel:
            case 0 | 6 | 7:
                arguments["autoModelProgram"] = 0
            case 8 | 9 :
                arguments["autoModelProgram"] = automodelprogram
                arguments["autoModelValue"] = automodelvalue
                arguments["msgType"] = 1
            case 10:
                arguments["autoModelProgram"] = 1
        arguments["autoModel"] = automodel
        return arguments


    def handle_command(self, mqttpayload:bytes, zenstate:ZendureState, bc: BridgeComponents) -> None:
        autoModelProgram = zenstate.auto_model_program
        autoModelValue = zenstate.auto_model_value
        zencontrol = self._get_zencontrol(bc)
        # Use default values if not set (this functionality is debug/development only, as this whole class is only for development and testing purposes.)
        if autoModelProgram is None:
            autoModelProgram = 1
            bc.device.update_value("auto_model_program", 1)
        if autoModelValue is None:
            autoModelValue = 0
            bc.device.update_value("auto_model_value", 0)

        received = mqttpayload.decode()
        _keys = [ key for key,val in self.lookup.items() if val == received ]
        if not _keys:
            logger.error("invalid autoMode %s received.", received)
            return
        assert len(_keys) == 1 , f"duplicate defintion of autoMode {received}"
        autoModel = int(_keys[0])

        if autoModel == zenstate.auto_model:
            # autoModel not changed.
            return

        arguments = self._generate_invoke_parameters(autoModelProgram, autoModel, autoModelValue)
        zencontrol.invoke_function(arguments, "deviceAutomation")
