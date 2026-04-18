# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from typing import Protocol, Any

class ZendurePropertyWriter(Protocol):
    """ This protocol is to invoke writing a property / state to the Zendure device without the HAEntity needing to know the device object."""
    def write_property(self, propetries: dict[str, Any]) -> None:
        ...

class ZendureCommandInvoker(Protocol):
    def invoke_function(self, arguments: dict[str, Any], function: str) -> None:
        ...

class ZendureController(ZendurePropertyWriter,
                        ZendureCommandInvoker,
                        Protocol):
    ...
