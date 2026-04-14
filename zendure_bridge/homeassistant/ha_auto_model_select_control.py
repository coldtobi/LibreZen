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
from ..zendure_protocols import ZendureController

logger = logging.getLogger(__name__)

@dataclass
class HAAutoModelSelectControl(HASelectControl):
    """ MQTT Select Control for the "autoModel" property. """

    def handle_command(self, mqttpayload:bytes, zenstate:ZendureState, _zencontrol:ZendureController) -> None:
        received = mqttpayload.decode()
        _keys = [ key for key,val in self.lookup.items() if val == received ]
        if not _keys:
            logger.error("invalid autoMode %s received.", received)
            return
        assert len(_keys) == 1 , f"duplicate defintion of automode {received}"

        autoModel = int(_keys[0])

        if autoModel == zenstate.auto_model:
            # autoModel not changed.
            return

        arguments : dict[str,int] = {}
        # Note: currently only "0" "8" and "9" implemented.
        match autoModel:
            case 0 | 6 | 7:
                arguments["autoModelProgram"] = 0
            case 8 | 9 :
                arguments["autoModelProgram"] = zenstate.auto_model_program
                arguments["autoModelValue"]   = zenstate.auto_model_value
            case 10:
                arguments["autoModelProgram"] = 1
        arguments["msgType"] = 1
        arguments["autoModel"] = autoModel

        _zencontrol.invoke_function(arguments, "deviceAutomation")
