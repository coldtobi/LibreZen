# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .zendure_protocols import ZendureController
    from .homeassistant.ha_publisher_protocols import HAPublisherProtocols
    from .device import ZendureDevice
    from zendure_bridge.config import BridgeConfig

@dataclass
class BridgeComponents:

    config: BridgeConfig
    _device: ZendureDevice | None = None
    _ha_publisher: HAPublisherProtocols | None = None
    _bridge: ZendureController | None = None

    @property
    def device(self) -> ZendureDevice:
        assert self._device is not None
        return self._device

    @property
    def ha_publisher(self) -> HAPublisherProtocols:
        assert self._ha_publisher is not None
        return self._ha_publisher

    @property
    def bridge(self) -> ZendureController:
        assert self._bridge is not None
        return self._bridge
