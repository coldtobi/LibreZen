# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from .bridge_mock import BridgeMock

from zendure_bridge.homeassistant.ha_number_control import HANumberControl

import json


def test_hanumber_get_discovery_topic() -> None:
    sensor = HANumberControl("TestNumberControl", "solar_input_power", "W", 0, 100, 10, "power")
    mock = BridgeMock()
    topic = sensor.get_discovery_topic(mock.bc)
    assert topic == "homeassistant_python_tests/number/zendure_12345678_solar_input_power/config"


def test_hanumber_get_state_topic() -> None:
    sensor = HANumberControl("TestNumberControl", "solar_input_power", "W", 0, 100, 10, "power")
    mock = BridgeMock()
    topic = sensor.get_state_topic(mock.bc)
    assert topic == "homeassistant_python_tests/number/zendure_12345678_solar_input_power/state"


def test_hanumber_get_ha_json() -> None:
    sensor = HANumberControl("TestNumberControl", "solar_input_power", "W", 0, 100, 10, "power")
    mock = BridgeMock()
    result = json.loads(sensor.get_ha_json(mock.bc))
    zen_device_id = mock.bc.config.zendure.device_id

    assert result["name"] == "TestNumberControl"
    assert result["min"] == 0
    assert result["max"] == 100
    assert result["step"] == 10
    assert result["unit_of_measurement"] == "W"
    assert result["device_class"] == "power"
    assert result["state_topic"] == sensor.get_state_topic(mock.bc)
    assert result["command_topic"] == sensor.get_command_topic(mock.bc)
    assert result["availability_topic"] == sensor.get_availabilty_topic(mock.bc)
    assert result["mode"] == sensor.display_mode
    assert result["unique_id"] == f"zendure_{zen_device_id}_solar_input_power"
    assert result["device"]["identifiers"] == [f"zendure_{zen_device_id}"]

    expected_keys = {
        "name", "availability_topic", "state_topic", "command_topic", "unique_id", "device",
        "unit_of_measurement", "min", "max", "step", "device_class", "mode"
    }
    assert result.keys() == expected_keys
