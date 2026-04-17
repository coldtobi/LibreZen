# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from .bridge_mock import BridgeMock

from zendure_bridge.homeassistant.ha_battery_sensor import BatterySensor


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
