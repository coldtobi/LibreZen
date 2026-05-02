from .bridge_mock import BridgeMock

from zendure_bridge.homeassistant.ha_switch_control import HASwitchControl

import json


def test_haswitch_get_discovery_topic() -> None:
    sensor = HASwitchControl("TestSwitch", "buzzer_switch", True, True)
    mock = BridgeMock()
    topic = sensor.get_ha_discovery_topic(mock.bc)
    assert topic == "homeassistant_python_tests/switch/zendure_12345678_buzzer_switch/config"


def test_haswitch_get_state_topic_and_command_topic() -> None:
    sensor = HASwitchControl("TestSwitch", "buzzer_switch", True, True)
    mock = BridgeMock()
    state_topic = sensor.get_ha_state_topic(mock.bc)
    cmd_topic = sensor.get_command_topic(mock.bc)
    assert state_topic == "homeassistant_python_tests/switch/zendure_12345678_buzzer_switch/state"
    assert cmd_topic == "homeassistant_python_tests/switch/zendure_12345678_buzzer_switch/set"


def test_haswitch_get_ha_json_contains_payloads_and_command() -> None:
    sensor = HASwitchControl("TestSwitch", "buzzer_switch", True, True)
    mock = BridgeMock()
    result = json.loads(sensor.get_ha_json(mock.bc))
    # basic keys from HAEntity + command_topic and payloads
    assert result["name"] == "TestSwitch"
    assert result["state_topic"] == sensor.get_ha_state_topic(mock.bc)
    assert result["availability_topic"] == sensor.get_ha_availabilty_topic(mock.bc)
    assert result["command_topic"] == sensor.get_command_topic(mock.bc)
    assert result["payload_on"] == sensor.payload_on
    assert result["payload_off"] == sensor.payload_off


def test_haswitch_handle_command_synthetic_updates_state() -> None:
    # Synthetic controls should update only the local state via update_state_value
    sensor = HASwitchControl("Master Switch", "master_switch", True, True, _is_synthetic=True)
    mock = BridgeMock()
    zenstate = mock.get_zendure_state()

    # Ensure initial state is 0
    zenstate.master_switch = 0
    sensor.handle_command(b"ON", zenstate, mock.bc)
    assert zenstate.master_switch == 1
    # ensure device global state was updated
    assert mock.get_zendure_state().master_switch == 1

    # ensure that the last written properties were not updated (since it's synthetic)
    assert mock.last_written is None


def test_haswitch_handle_command_non_synthetic_writes_property() -> None:
    # Non-Synthetic controls should via write_properties.
    sensor = HASwitchControl("Buzzer", "buzzer_switch", True, True, _is_synthetic=False)
    mock = BridgeMock()
    zenstate = mock.get_zendure_state()

    # send OFF payload and expect write_property to be called with the Zendure property key
    sensor.handle_command(b"off", zenstate, mock.bc)
    assert mock.last_written is not None
    # reverse mapping in device._PROPERTY_MAP maps 'buzzerSwitch' -> 'buzzer_switch'
    assert mock.last_written == {"buzzerSwitch": 0}
