# test_ha_sensors.py

from zendure_bridge.ha_sensors import HASensor, BatterySensor,HANumberControl
from zendure_bridge.device import ZendureState, ZendureDevice
from zendure_bridge.bridge_context import BridgeContext
import zendure_bridge

from typing import Any
import json

def test_load_test_config() -> None:
    ''' Ensure that the unit test config can be loaded '''
    bridgeconfig = zendure_bridge.config.load("tests/config.yaml")
    assert bridgeconfig.homeassistant.discovery_prefix == "homeassistant_python_tests"


class BridgeMock():

    def __init__(self) -> None:
        self.bridgeconfig = zendure_bridge.config.load("tests/config.yaml")
        z = self.bridgeconfig.zendure
        self.device = ZendureDevice(z.device_id)

    def update_state_value(self, field_name: str, value: int) -> None:
        """ allows updating the state object with a new value, thread safe. """
        self.device.update_value(field_name, value)

    def write_property(self, propetries: dict[str, Any]) -> None:
        pass

    def invoke_function(self, propetries: dict[str, Any]) -> None:
        pass

    def update_ha_entity(self, field_name: str) -> None:
        pass

    def get_zendure_state(self) -> ZendureState:
        return self.device.state

    def get_bridge_context(self) -> BridgeContext:
        return BridgeContext(self.bridgeconfig.zendure, self.bridgeconfig.homeassistant)


## HAControl

## HANumberControl

def test_hanumber_get_discovery_topic() -> None:
    sensor = HANumberControl("TestNumberControl", "solar_input_power", "W", 0, 100, 10, "power")
    mock = BridgeMock()
    topic = sensor.get_discovery_topic(mock)
    assert topic == "homeassistant_python_tests/number/zendure_12345678_solar_input_power/config"

def test_hanumber_get_state_topic() -> None:
    sensor = HANumberControl("TestNumberControl", "solar_input_power", "W", 0, 100, 10, "power")
    mock = BridgeMock()
    topic = sensor.get_state_topic(mock)
    assert topic == "homeassistant_python_tests/number/zendure_12345678_solar_input_power/state"

def test_hanumber_get_ha_json() -> None:
    sensor = HANumberControl("TestNumberControl", "solar_input_power", "W", 0, 100, 10, "power")
    mock = BridgeMock()
    result = json.loads(sensor.get_ha_json(mock))

    assert result["name"] == "TestNumberControl"
    assert result["min"] == 0
    assert result["max"] == 100
    assert result["step"] == 10
    assert result["unit_of_measurement"] == "W"
    assert result["device_class"] == "power"
    assert result["state_topic"] == sensor.get_state_topic(mock)
    assert result["command_topic"] == sensor.get_command_topic(mock)
    assert result["availability_topic"] == sensor.get_availabilty_topic(mock)
    zen_device_id = mock.get_bridge_context().zenconfig.device_id
    assert result["unique_id"] == f"zendure_{zen_device_id}_solar_input_power"
    assert result["device"]["identifiers"] == [f"zendure_{zen_device_id}"]

    expected_keys = {
        "name", "availability_topic", "state_topic", "command_topic", "unique_id", "device",
        "unit_of_measurement", "min", "max", "step", "device_class"
    }
    assert result.keys() == expected_keys



## HASensor

def test_sensor_get_discovery_topic() -> None:
    sensor = HASensor("TestSensor", "solar_input_power", "W", "power")
    mock = BridgeMock()
    topic = sensor.get_discovery_topic(mock)
    assert topic == "homeassistant_python_tests/sensor/zendure_12345678_solar_input_power/config"

def test_sensor_get_state_topic() -> None:
    sensor = HASensor("TestSensor", "solar_input_power", "W", "power")
    mock = BridgeMock()
    topic = sensor.get_state_topic(mock)
    assert topic == "homeassistant_python_tests/sensor/zendure_12345678_solar_input_power/state"

def test_sensor_get_ha_json() -> None:
    sensor = HASensor("TestSensor", "solar_input_power", "W", "power")
    mock = BridgeMock()
    zen_device_id = mock.get_bridge_context().zenconfig.device_id

    result = json.loads(sensor.get_ha_json(mock))
    assert result["name"] == "TestSensor"
    assert result["unit_of_measurement"] == "W"
    assert result["device_class"] == "power"
    assert result["state_topic"] == sensor.get_state_topic(mock)
    assert result["availability_topic"] == sensor.get_availabilty_topic(mock)
    assert result["unique_id"] == f"zendure_{zen_device_id}_solar_input_power"
    assert result["device"]["identifiers"] == [f"zendure_{zen_device_id}"]

    expected_keys = {
        "name", "availability_topic", "state_topic", "unique_id", "device",
        "unit_of_measurement", "device_class"
    }
    assert result.keys() == expected_keys


def test_sensor_get_value() -> None:
    # Arrange
    sensor = HASensor("Solar", "solar_input_power", "W", "power")
    state = ZendureState()
    state.solar_input_power = 42

    # Act & Assert
    assert sensor.get_value(state) == 42
    assert sensor.get_value(state) == state.solar_input_power

def test_sensor_has_changed() -> None :
    # Arrange
    sensor = HASensor("Solar", "solar_input_power", "W", "power")
    state = ZendureState()
    state.solar_input_power = 42

    # Act & Assert
    assert sensor.has_changed(state)
    # test if change state has been consumed.
    assert not sensor.has_changed(state)

    # No change when set the same value
    state.solar_input_power = 42
    assert not sensor.has_changed(state)

    # Bu a change detected when set to a different value.
    state.solar_input_power = 21
    assert sensor.has_changed(state)



def test_batterysensor_update() -> None:
    # Arrange
    bm = BridgeMock()
    sensor = BatterySensor("Battery Charge Power", "battery_charge_power", "W", "power")
    state = bm.device.state
    state.pack_input_power = 0
    state.output_pack_power = 0
    state.output_home_power = 0
    state.solar_input_power = 0
    sensor.update(state, bm)

    # Test if power is 0
    assert state.battery_charge_power == 0

    # Ensure that the global state has been update as well.
    permastate = bm.device.state
    assert state.battery_charge_power == permastate.battery_charge_power

    # Set Input power over the "cut off" number and check if that is echoed.
    state.pack_input_power = 100
    state.output_pack_power = 0
    state.output_home_power = 200
    state.solar_input_power = 200
    sensor.update(state, bm)
    assert state.battery_charge_power == -100

    # Ensure that the global state has been update as well.
    permastate = bm.device.state
    assert state.battery_charge_power == permastate.battery_charge_power

    # Set Output power over the "cut off" number and check if that is echoed.
    state.pack_input_power = 0
    state.output_pack_power = 100
    state.output_home_power = 200
    state.solar_input_power = 200
    sensor.update(state, bm)
    assert state.battery_charge_power == 100

    # Ensure that the global state has been update as well.
    permastate = bm.device.state
    assert state.battery_charge_power == permastate.battery_charge_power

    # Set Input power below the "cut off" number and check if that is echoed.
    state.pack_input_power = 0
    state.output_pack_power = 0
    state.output_home_power = 0
    state.solar_input_power = 20
    sensor.update(state, bm)
    assert state.battery_charge_power == 20

    # Ensure that the global state has been update as well.
    permastate = bm.device.state
    assert state.battery_charge_power == permastate.battery_charge_power

    # Set Output power over the "cut off" number and check if that is echoed.
    state.pack_input_power = 0
    state.output_pack_power = 0
    state.output_home_power = 20
    state.solar_input_power = 0
    sensor.update(state, bm)
    assert state.battery_charge_power == -20

    # Ensure that the global state has been update as well.
    permastate = bm.device.state
    assert state.battery_charge_power == permastate.battery_charge_power

    # Ensure has_changed works.
    assert sensor.has_changed(state)
    assert not sensor.has_changed(state)

    # Ensure get_value returns the correct value
    assert sensor.get_value(state) == state.battery_charge_power

    # Ensure that the global state has been update as well.
    permastate = bm.device.state
    assert state.battery_charge_power == permastate.battery_charge_power
