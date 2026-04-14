# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from .ha_entity import HAEntity
from .ha_sensor import HASensor
from .ha_battery_sensor import BatterySensor
from .ha_soc_sensor import SocSensor
from .ha_enum_sensor import EnumSensor
from .ha_soc_control import HASoCControl
from .ha_output_limit_control import HAOutputLimitControl
from .ha_inverse_max_power_control import HAInvMaxPowerControl

#from .ha_number_control import HANumberControl

#from .ha_sensors import HASensor, BatterySensor, PowerSensor, SocSensor, \
#                        EnumSensor,HAOutputLimitControl,HAInvMaxPowerControl, \
#                        HASoCControl

from ..device import _PROPERTY_MAP_AUTO_MODELS

# Defintion of all HAEntities.

# This table defines the states / controls for homeassistant.
HAENTITIES = [
#### HAENTITIES ####
    #        name                           field_name              unit     device_class
    # Sensors PV side
    HASensor("Solar Input Power",          "solar_input_power",    "W",     "power"),
    HASensor("Solar Input Power Input 1",  "solar_power_1",        "W",     "power"),
    HASensor("Solar Input Power Input 2",  "solar_power_2",        "W",     "power"),
    # Sensors Battery related
    BatterySensor("Battery Power",          "battery_charge_power", "W",     "power"),
    HASensor("Power to Bat",             "output_pack_power",    "W",     "power"),
    HASensor("Power from Bat",           "pack_input_power",     "W",     "power"),
    SocSensor("Battery SoC",                "electric_level",       "%",     "battery"),

    # Sensors Inverter Side
    HASensor("Output To Home",           "output_home_power",    "W",     "power"),

    # Enum's
    EnumSensor("Auto Model",                "auto_model",           "",      "enum", _PROPERTY_MAP_AUTO_MODELS),

#### CONTROLS (and if needed their Display-Sensors) ####
#   HANumberControl(         name            field_name,            unit   min  max   step   device_class
    HAOutputLimitControl("Output Limit",     "output_limit",         "W",    0, 800,     1,  "power"),
    HAInvMaxPowerControl("Legal Inverter Limit", "inverse_max_power","W",  100,1200,   100,  "power", display_mode="box", is_expert=True),
    HASensor("Current Inverter Limit",       "inverse_max_power",    "W",                    "power"),
    HASoCControl("min SoC",               "min_soc",              "%",    0,  50,     1,  "battery"),
    HASoCControl("max SoC",               "soc_set",              "%",   70, 100,     1,  "battery"),
]


def find_sensor_obj(field_name: str) -> HAEntity | None:
    """ helper to find the HAEntity Object in the HAENTITIES list."""
    for ent in HAENTITIES:
        if ent.field_name == field_name:
            return ent
    return None
