# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from .bridge_mock import BridgeMock

from zendure_bridge.homeassistant.ha_sensor import HASensor
from zendure_bridge.device import ZendureState

import json


def test_sensor_get_discovery_topic() -> None:
    sensor = HASensor("TestSensor", "solar_input_power", "W", "power")
    mock = BridgeMock()
    topic = sensor.get_discovery_topic(mock.bc)
    assert topic == "homeassistant_python_tests/sensor/zendure_12345678_solar_input_power/config"


def test_sensor_get_state_topic() -> None:
    sensor = HASensor("TestSensor", "solar_input_power", "W", "power")
    mock = BridgeMock()
    topic = sensor.get_state_topic(mock.bc)
    assert topic == "homeassistant_python_tests/sensor/zendure_12345678_solar_input_power/state"


def test_sensor_get_ha_json() -> None:
    sensor = HASensor("TestSensor", "solar_input_power", "W", "power")
    mock = BridgeMock()
    zen_device_id = mock.bc.config.zendure.device_id

    result = json.loads(sensor.get_ha_json(mock.bc))
    assert result["name"] == "TestSensor"
    assert result["unit_of_measurement"] == "W"
    assert result["device_class"] == "power"
    assert result["state_topic"] == sensor.get_state_topic(mock.bc)
    assert result["availability_topic"] == sensor.get_availabilty_topic(mock.bc)
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


def test_sensor_has_changed_first_check() -> None:
    # Arrange
    sensor = HASensor("Solar", "solar_input_power", "W", "power")
    state = ZendureState()

    # Act & Assert
    # An unset underlying state (None) is not considered a change - nothing
    # has been received from the device yet.
    assert not sensor.has_changed(state)

    # When a concrete value is set, the first observation is a change.
    state.solar_input_power = 42
    assert sensor.has_changed(state)
    assert not sensor.has_changed(state)


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

    # But a change detected when set to a different value.
    state.solar_input_power = 21
    assert sensor.has_changed(state)
