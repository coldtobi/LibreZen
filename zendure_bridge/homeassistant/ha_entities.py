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
from .ha_inverse_max_power_control import HAInvMaxPowerControl as HVInvMaxPwrCtrl
from .ha_auto_model_select_control import HAAutoModelSelectControl as HAAutoMmodeSelCtrl
from .ha_auto_model_value_control import HAAutoModelValueControl as HAAutoMValCtrl
from .ha_number_control import HANumberControl
from .ha_switch_control import HASwitchControl

from ..device import _PROPERTY_MAP_AUTO_MODELS

# Defintion of all HAEntities.

# This table defines the states / controls for homeassistant.
HAENTITIES = [
#### HAENTITIES ####
    #                                               Homeassistant \        / NodeRed
    #        name                           field_name             HA,   NR,   Unit     device_class
    # Sensors PV side
    HASensor("Solar Input Power",          "solar_input_power",    True, True , "W",     "power"),
    HASensor("Solar Input Power Input 1",  "solar_power_1",        True, True , "W",     "power"),
    HASensor("Solar Input Power Input 2",  "solar_power_2",        True, True , "W",     "power"),
    # Sensors Battery related
    BatterySensor("Battery Power",         "battery_charge_power", True, True , "W",     "power"),
    HASensor("Power to Bat",               "output_pack_power",    True, True , "W",     "power"),
    HASensor("Power from Bat",             "pack_input_power",     True, True , "W",     "power"),
    SocSensor("Battery SoC",               "electric_level",       True, True , "%",     "battery"),

    # Sensors Inverter Side
    HASensor("Output To Home",             "output_home_power",    True, True , "W",     "power"),

    # Enum's
    EnumSensor("Auto Model RO",            "auto_model",           True, True , "",      "enum", _PROPERTY_MAP_AUTO_MODELS),

#### CONTROLS (and if needed their Display-Sensors) ####
#                                                    Homeassistant \        / NodeRed
#   HANumberControl(         name           field_name,            HA,   NR,   unit   min  max   step   device_class
    HAOutputLimitControl("Output Limit",    "output_limit",        True, True , "W",    0, 800,     1,  "power"),
    HVInvMaxPwrCtrl("Legal Inverter Limit", "inverse_max_power",   True, True , "W",  100,1200,   100,  "power", display_mode="box", _is_expert=True),
    HASensor("Current Inverter Limit",      "inverse_max_power",   True, True , "W",                    "power"),
    HASoCControl("min SoC",                 "min_soc",             True, True , "%",    0,  50,     1,  "battery"),
    HASoCControl("max SoC",                 "soc_set",             True, True , "%",   70, 100,     1,  "battery"),
    HAAutoMmodeSelCtrl("Auto Model Ctrl",   "auto_model",          True, True , _PROPERTY_MAP_AUTO_MODELS),
    HASwitchControl("Master Switch",        "master_switch",       True, True ),
    HASwitchControl("Buzzer Switch",        "buzzer_switch",       True, True ),

# Syntetics for testing.
#                                                    Homeassistant \        / NodeRed
    HANumberControl("AutoModelProgram",     "auto_model_program",  True, True , "",     0,  2,      1,  "", display_mode="box", _is_expert=True, _is_synthetic = True),
    HAAutoMValCtrl("AutoModelValue",        "auto_model_value",    True, True , "", -1000, 1000,    1,  "", display_mode="box", _is_expert=True, _is_synthetic = True)
]


def find_sensor_objs(field_name: str, entity_type: type | None = None) -> list[HAEntity]:
    """ helper to find the HAEntity Objects in the HAENTITIES list. """
    ret: list[HAEntity] = []
    for ent in HAENTITIES:
        if ent.field_name != field_name:
            continue

        if entity_type is None or isinstance(ent, entity_type):
            ret.append(ent)

    return ret
