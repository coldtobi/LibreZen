# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from typing import Protocol
from abc import abstractmethod

class HomeAssistantUpdateEntity(Protocol):
    """ This protocol triggers an update mqtt entity sent to home assistant, for example
        after some values of a control have to be changed.

        For example, if the max value of an HANumericControl is changed,
        his needs to be sent to homeassistant.

        The HAEntity object needs already be updated with the target values.
    """
    @abstractmethod
    def update_ha_entity(self, field_name: str) -> None:
        ...
