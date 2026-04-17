# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from typing import Any
import os

from zendure_bridge.device import ZendureState, ZendureDevice
from zendure_bridge.bridge_context import BridgeContext
import zendure_bridge

class BridgeMock():

    def __init__(self) -> None:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.bridgeconfig = zendure_bridge.config.load(f"{dir_path}/config.yaml")
        assert self.bridgeconfig.homeassistant.discovery_prefix == "homeassistant_python_tests"
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
