# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from typing import Protocol, Any
from abc import abstractmethod

from zendure_bridge.ha_protocols import HomeAssistantUpdateEntity
from zendure_bridge.bridge_context import BridgeContext
from zendure_bridge.device import ZendureState


class ZendurePropertyWriter(Protocol):
    """ This protocol is to invoke writing a property / state to the Zendure device without the HAEntity needing to know the device object."""
    @abstractmethod
    def write_property(self, propetries: dict[str, Any]) -> None:
        ...


class ZendureCommandInvoker(Protocol):
    @abstractmethod
    def invoke_function(self, propetries: dict[str, Any]) -> None:
        ...


class ZendureUpdateStateValue(Protocol):
    """ This protocol is to allow updating a state into the global state object with thread safety."""
    @abstractmethod
    def update_state_value(self, field_name: str, value: int) -> None:
        ...


class ZendureCurrentStateProvider(Protocol):
    """ This protocol gets a copy of the current ZendureState Object. """
    @abstractmethod
    def get_zendure_state(self) -> ZendureState:
        ...


class ZendureContextProvider(Protocol):
    @abstractmethod
    def get_bridge_context(self) -> BridgeContext:
        ...



class ZendureController(ZendurePropertyWriter,
                        ZendureCommandInvoker,
                        ZendureUpdateStateValue,
                        HomeAssistantUpdateEntity,
                        ZendureCurrentStateProvider,
                        ZendureContextProvider,
                        Protocol):
    ...