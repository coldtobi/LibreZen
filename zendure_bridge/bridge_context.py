# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from attr import dataclass
from zendure_bridge.config import ZendureConfig, HAConfig

@dataclass
class BridgeContext:
    zenconfig: ZendureConfig
    haconfig: HAConfig