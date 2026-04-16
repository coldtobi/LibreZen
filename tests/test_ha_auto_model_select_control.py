# tests for HAAutoModelSelectControl
from zendure_bridge.homeassistant.ha_auto_model_select_control import HAAutoModelSelectControl
from zendure_bridge.device import _PROPERTY_MAP_AUTO_MODELS

from zendure_bridge.device import ZendureState, ZendureDevice
from zendure_bridge.bridge_context import BridgeContext
import zendure_bridge

from typing import Any

class MockController():

    def __init__(self) -> None:
        self.bridgeconfig = zendure_bridge.config.load("tests/config.yaml")
        z = self.bridgeconfig.zendure
        self.device = ZendureDevice(z.device_id)
        # capture last interactions for tests
        self.last_written: dict[str, Any] | None = None
        self.last_invoked: dict[str, Any] | None = None

    def update_state_value(self, field_name: str, value: int) -> None:
        """ allows updating the state object with a new value, thread safe. """
        self.device.update_value(field_name, value)

    def write_property(self, propetries: dict[str, Any], persistent: bool = False) -> None:
        """Mock implementation that records the last written properties.

        The real bridge may publish this to MQTT; tests can inspect `last_written`.
        """
        # store a copy so tests can assert on it
        self.last_written = dict(propetries)

    def invoke_function(self, arguments: dict[str, Any], function:str) -> None:
        """Mock implementation that records the last invoked function and its arguments."""
        self.last_invoked = {"function": function, "arguments": dict(arguments)}

    def update_ha_entity(self, field_name: str) -> None:
        pass

    def get_zendure_state(self) -> ZendureState:
        return self.device.state

    def get_bridge_context(self) -> BridgeContext:
        return BridgeContext(self.bridgeconfig.zendure, self.bridgeconfig.homeassistant)



def test_generate_invoke_parameters_contains_camelcase_keys() -> None:
    # Use the control's default lookup (should reflect device mapping)
    ctrl = HAAutoModelSelectControl("AutoModel", "auto_model", lookup = _PROPERTY_MAP_AUTO_MODELS)
    params = ctrl._generate_invoke_parameters(automodelprogram=2, automodel=9, automodelvalue=1794)

    assert params["autoModelProgram"] == 2
    assert params["autoModelValue"] == 1794
    assert params["msgType"] == 1
    assert params["autoModel"] == 9


def test_handle_command_invokes_deviceAutomation_with_camelcase_arguments() -> None:
    # Use the control's default lookup coming from device mapping
    ctrl = HAAutoModelSelectControl("AutoModel", "auto_model", lookup = _PROPERTY_MAP_AUTO_MODELS)

    state = ZendureState()
    # ensure program/value are None so handle_command will set defaults
    state.auto_model_program = None
    state.auto_model_value = None
    state.auto_model = 0

    mock = MockController()

    # send payload corresponding to lookup value for automodel 9
    payload = ctrl.lookup[9].encode()
    ctrl.handle_command(payload, state, mock)

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
