# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from zendure_bridge.homeassistant.ha_auto_model_select_control import HAAutoModelSelectControl
from zendure_bridge.device import _PROPERTY_MAP_AUTO_MODELS

from zendure_bridge.device import ZendureState

from .bridge_mock import BridgeMock

def test_generate_invoke_parameters_contains_camelcase_keys() -> None:
    # Use the control's default lookup (should reflect device mapping)
    ctrl = HAAutoModelSelectControl("AutoModel", "auto_model", True, True, lookup = _PROPERTY_MAP_AUTO_MODELS)
    params = ctrl._generate_invoke_parameters(automodelprogram=2, automodel=9, automodelvalue=1794)

    assert params["autoModelProgram"] == 2
    assert params["autoModelValue"] == 1794
    assert params["msgType"] == 1
    assert params["autoModel"] == 9


def test_handle_command_invokes_deviceAutomation() -> None:
    # Use the control's default lookup coming from device mapping
    ctrl = HAAutoModelSelectControl("AutoModel", "auto_model", True, True, lookup = _PROPERTY_MAP_AUTO_MODELS)

    state = ZendureState()
    # ensure program/value are None so handle_command will set defaults
    state.auto_model_program = None
    state.auto_model_value = None
    state.auto_model = 0

    mock = BridgeMock()

    # send payload corresponding to lookup value for automodel 9
    payload = ctrl.lookup[9].encode()
    ctrl.handle_command(payload, state, mock.bc)

    # defaults should have been set
    assert mock.get_zendure_state().auto_model_program == 1
    assert mock.get_zendure_state().auto_model_value == 0

    assert mock.last_invoked is not None
    assert mock.last_invoked["function"] == "deviceAutomation"

    # arguments dict should contain camelCase keys
    args = mock.last_invoked["arguments"]
    assert args["autoModel"] == 9
    assert args["autoModelProgram"] == 1
    assert args["autoModelValue"] == 0
