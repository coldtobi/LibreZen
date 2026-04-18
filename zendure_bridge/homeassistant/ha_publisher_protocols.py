# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from typing import Protocol

from .ha_entity import HAEntity
from ..device import ZendureState


class HAPublisherReadinessProvider(Protocol):
    @property
    def is_ready(self) -> bool:
        ...

class HAPublisherStatePublisher(Protocol):
    def publish_state(self, haentity: HAEntity, state: ZendureState) -> None:
        ...

class HAPublisherStateAvailabiltyPublisher(Protocol):
    def publish_availability(self, haentity: HAEntity, state: ZendureState) -> None:
        ...

class HAPublisherDiscoveryPublisher(Protocol):
    def publish_ha_discovery(self, haentity: HAEntity) -> None:
        ...

class HAPublisherProtocols(HAPublisherReadinessProvider,
                           HAPublisherStatePublisher,
                           HAPublisherStateAvailabiltyPublisher,
                           HAPublisherDiscoveryPublisher,
                           Protocol):
    ...