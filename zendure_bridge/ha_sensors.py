# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# import logging

import json

from typing import cast, Any
from dataclasses import dataclass, field

from zendure_bridge.device import ZendureState, _PROPERTY_MAP, _PROPERTY_MAP_AUTO_MODELS
from zendure_bridge.zendure_protocols import ZendureController

@dataclass
class HAEntity:
    """ Baseclass for HA entities, like sensors and control items. """

    name: str            # human readable caption for Homeassistant.
    field_name: str      # fiels of the dataclass ZendureState-Feldname, including for syntetic, derived sensors or controls.

    _have_received_value: bool = field(default=False, init=False) # is the state valid (did we get any value for it)
    _last_value: int = field(default=0, init=False)     # for change detection of the state value
    _last_availability: bool = field(default=True, init=False) # for the change detection of the availablity.

    needs_re_discovery: bool = field(default=False, init=False) # discovery information has changed, needs to be re-sent

    @property
    def ha_component_type(self) -> str:
        raise NotImplementedError

    def get_ha_json(self, zencontrol: ZendureController) -> str:
        """ generate JSON to advertise the HAEntity to homassistant.

            The call to this function consumes/resets the 'needs_re_discovery'.
        """

        self.needs_re_discovery = False
        return json.dumps(self._build_ha_discovery_dict(zencontrol))

    def get_state_topic(self, zencontrol: ZendureController) -> str:
        """ generate mqtt topic string for homeassistant to publish a state """
        haconfig = zencontrol.get_bridge_context().haconfig
        zenconfig = zencontrol.get_bridge_context().zenconfig
        return f"{haconfig.discovery_prefix}/{self.ha_component_type}/zendure_{zenconfig.device_id}_{self.field_name}/state"

    def get_discovery_topic(self, zencontrol: ZendureController) -> str:
        """ generate mqtt topic string for homeassistant to publish a discovery topic. """
        haconfig = zencontrol.get_bridge_context().haconfig
        zenconfig = zencontrol.get_bridge_context().zenconfig
        return f"{haconfig.discovery_prefix}/{self.ha_component_type}/zendure_{zenconfig.device_id}_{self.field_name}/config"

    def get_availabilty_topic(self, zencontrol: ZendureController) -> str:
        haconfig = zencontrol.get_bridge_context().haconfig
        zenconfig = zencontrol.get_bridge_context().zenconfig
        return f"{haconfig.discovery_prefix}/{self.ha_component_type}/zendure_{zenconfig.device_id}_{self.field_name}/availability"

    def _build_ha_discovery_dict(self, zencontrol: ZendureController) -> dict[str, Any]:
        """ build a dict containing all information for homeassisent's discovery of an entity.

            subclasses ammend this information, eg. to add HAControl specific information.
        """
        haconfig = zencontrol.get_bridge_context().haconfig
        zenconfig = zencontrol.get_bridge_context().zenconfig

        _dict = {
            'name': self.name,
            'state_topic': self.get_state_topic(zencontrol),
            'availability_topic': self.get_availabilty_topic(zencontrol),
            'unique_id': f"zendure_{zenconfig.device_id}_{self.field_name}",
            'device': {
                "identifiers": [f"zendure_{zenconfig.device_id}"],
                "name": haconfig.device_name,
                "model": haconfig.model_name,
            }
        }
        return _dict

    def update(self, state: ZendureState, zencontrol: ZendureController) -> None:
        """ override, when a state needs some math or logic to be useful.

        state is only a copy of the global states, changes to the state will be only temporary saved,
        as the device should confirm the new value via mqtt to make it "permamenet"

        The lifetime of the temporary change will extended so that HAPublisher will detect the change and publish the value to homeassisten, though.

        To generate syntentic states, the "UpdateStateValue" protocol of ZendureController can be use to save values to the state object permanetly
        without the device needing to confirm the value.
        """
        if not self._have_received_value:
            # fake a changed value, to ensure we send out at least once initially.
            # (if it happens that the new value is the init value)
            self._last_value = self.get_value(state) + 1
            self._have_received_value = True
        pass

    def get_value(self, state: ZendureState) -> int :
        """ retrieve value - by default mapped directly to the state. """
        return cast(int, getattr(state, self.field_name))

    def get_display_value(self, state: ZendureState) -> int | str:
        """Return the value to publish to HA. Override for string representations."""
        return self.get_value(state)

    def has_changed(self , state: ZendureState) -> bool :
        """ query if an information has been changed, e.g to avoid sending the same values to homeassistant again and again.

        A call to this function will consume the "has changed" state.
        """
        if not self._have_received_value:
            return False
        value = self.get_value(state)
        ret = (value != self._last_value)
        if (ret):
            self._last_value = value
        return ret

    def is_available(self, _state: ZendureState, _zencontrol: ZendureController) -> bool:
        return True  # default: immer verfügbar

    def has_availability_changed(self, state: ZendureState, zencontrol: ZendureController) -> bool:
        available = self.is_available(state, zencontrol)
        if available != self._last_availability:
            self._last_availability = available
            return True
        return False

def find_sensor_obj(field_name: str) -> HAEntity | None:
    """ helper to find the HAEntity Object in the HAENTITIES list."""
    for ent in HAENTITIES:
        if ent.field_name == field_name:
            return ent
    return None


@dataclass
class HAControl(HAEntity):
    """ Baseclass for Control Entities for Homeassistant
    """

    def _build_ha_discovery_dict(self, zencontrol: ZendureController)-> dict[str, Any]:
        _dict = super()._build_ha_discovery_dict(zencontrol)
        _dict['command_topic'] = self.get_command_topic(zencontrol)
        return _dict

    def get_command_topic(self, zencontrol: ZendureController) -> str:
        """ assemble the MQTT topic to control this HAControl. """
        haconfig = zencontrol.get_bridge_context().haconfig
        zenconfig = zencontrol.get_bridge_context().zenconfig
        return f"{haconfig.discovery_prefix}/{self.ha_component_type}/zendure_{zenconfig.device_id}_{self.field_name}/set"

    def handle_command(self, _mqttpayload: bytes, _zenstate: ZendureState, _zencontrol: ZendureController) -> None:
        raise NotImplementedError  # abstrakt


@dataclass
class HANumberControl(HAControl):
    """ A numeric HAControl """
    unit: str           # Unit of measurement
    min: int            # minimum value
    max: int            # maximum value
    step: int           # step size
    device_class: str   # HA device_class: "power", "battery", "energy"
    display_mode: str = "auto"    # "auto", "box" or "slider"

    is_expert: bool = False

    @property
    def ha_component_type(self) -> str:
        return "number"

    def _build_ha_discovery_dict(self, zencontrol: ZendureController)-> dict[str, Any]:
        _dict = super()._build_ha_discovery_dict(zencontrol)
        _extra = {
            'unit_of_measurement' : self.unit,
            'min' : self.min,
            'max' : self.max,
            'step' : self.step,
            'device_class' : self.device_class,
            'mode' : self.display_mode
        }
        return (_dict | _extra)

    def _get_command_properties(self, mqttpayload: bytes) -> dict[str, int] :
        """ map state's field_name to Zendure's property name and assign the value from the MQTT control payload. """

        # reverse dict lookup to determine the proper Zendure property for this Control.
        _keys = [ key for key,val in _PROPERTY_MAP.items() if val == self.field_name ]
        assert len(_keys) == 1 , "Property not found or duplicate defintion."
        # generate dict and assign mqtt payload value.
        _properties = {
            _keys[0]: int(mqttpayload.decode())
        }
        return _properties

    def handle_command(self,
                       mqttpayload: bytes, _zenstate: ZendureState,
                       zencontrol: ZendureController) -> None:
        """ Handle a numeric value sent from homeassistant to be sent to the zendure.

            This will just set the properties associated with the HAConrol, if some command
            needs extra properties to be set, needs to be overriden.
        """
        _properties = self._get_command_properties(mqttpayload)
        zencontrol.write_property(_properties)

    def is_available(self, _state: ZendureState, zencontrol: ZendureController) -> bool:
        # expert controls are available only if expert_mode has been configured.
        return ( not self.is_expert ) or zencontrol.get_bridge_context().haconfig.expert_mode


@dataclass
class HAOutputLimitControl(HANumberControl):
    """ HAControl for OutputLimit.

        (needs to set acMode, therefore overriden)
    """
    def handle_command(self, mqttpayload: bytes, _zenstate: ZendureState,
                       zencontrol: ZendureController) -> None:

        _properties = self._get_command_properties(mqttpayload)
        _properties["acMode"] = 2
        zencontrol.write_property(_properties)

    def is_available(self, state:ZendureState, zencontrol:ZendureController)->bool:
        if not super().is_available(state, zencontrol):
            return False
        return state.auto_model == 0

@dataclass
class HAInvMaxPowerControl(HANumberControl):
    """ HAControl for maximum Inverter Output Setting

        Limits the maximum output power, ("Legal setting" in the app)
    """

    def update(self, state: ZendureState, zencontrol: ZendureController)->None:
        # Tweaking Outputlimit
        outputlimit = cast(HAOutputLimitControl, find_sensor_obj("output_limit"))
        # ensure that output limit's numeric control max is adjusted.
        if state.inverse_max_power < state.output_limit:
            fakepayload = str(state.inverse_max_power).encode()
            _properties = outputlimit._get_command_properties(fakepayload)
            zencontrol.write_property(_properties)

        # re-set the homeassistant control's max if required.
        if outputlimit.max != state.inverse_max_power:
            outputlimit.max = state.inverse_max_power
            outputlimit.needs_re_discovery = True

        # hack: if the control is disabled (expert mode off), show as box
        # as sliders won't cut it.
        if (not self.is_available(state, zencontrol)) and (self.display_mode != "box"):
            self.display_mode = "box"
            self.needs_re_discovery = True


@dataclass
class HASoCControl(HANumberControl):
    def get_value(self, state: ZendureState) -> int:
        return int(super().get_value(state)/10)

    def handle_command(self, mqttpayload:bytes, _zenstate: ZendureState,
                       zencontrol: ZendureController)->None :

        # scaling - zendure wants value x 10
        _keys = [ key for key,val in _PROPERTY_MAP.items() if val == self.field_name ]
        assert len(_keys) == 1 , "Property not found or duplicate defintion."
        # generate dict and assign mqtt payload value.
        _properties = {
            _keys[0]: int(mqttpayload.decode())*10
        }
        zencontrol.write_property(_properties)

@dataclass
class HASelectControl(HAControl):
    @property
    def ha_component_type(self) -> str:
        return "select"

@dataclass
class HASwitchControl(HAControl):
    @property
    def ha_component_type(self) -> str:
        return "switch"

@dataclass
class HASensor(HAEntity):
    """ Sensor for Homeassistant defintion and handling."""

    unit: str
    device_class: str    # HA device_class: "power", "battery", "energy"

    @property
    def ha_component_type(self) -> str:
        return "sensor"

    def _build_ha_discovery_dict(self, zencontrol: ZendureController) -> dict[str, Any]:

        _dict = super()._build_ha_discovery_dict(zencontrol)
        _dict['device_class'] = self.device_class
        if self.unit:
            _dict['unit_of_measurement'] = self.unit

        return _dict

    def get_ha_json(self, zencontrol: ZendureController) -> str:
        """ generate JSON to advertise Sensor defintion (json) to homassistant."""
        return json.dumps(self._build_ha_discovery_dict(zencontrol))

class BatterySensor(HASensor):

    def update(self, state: ZendureState, zencontrol: ZendureController)-> None:
        # pack_input_power -> DISCHARGE power
        # output_pack_power -> CHARGE power.
        if state.pack_input_power > 0:
            _bat_pwr = - state.pack_input_power
        elif state.output_pack_power > 0:
            _bat_pwr = state.output_pack_power
        else:
            # zendure sets value <20 to zero, so du some guesswork based on input/output power.
            _bat_pwr = state.solar_input_power - state.output_home_power

        # update both the state snapshot and the global state (as bat_pwr is syntentic, not from the device)
        state.battery_charge_power = _bat_pwr
        zencontrol.update_state_value(self.field_name, _bat_pwr)

@dataclass
class EnumSensor(HASensor):

    lookup: dict[int, str]

    def get_display_value(self, state: ZendureState) -> str:
        numeric_value = self.get_value(state)
        return self.lookup.get(numeric_value, "unknown")

    def _build_ha_discovery_dict(self, zencontrol: ZendureController)-> dict[str, Any]:
        _dict = super()._build_ha_discovery_dict(zencontrol)
        _dict['options'] = list(self.lookup.values())
        return _dict

# für später!
class PowerSensor (HASensor):
    pass

class SocSensor (HASensor):
    pass

#    für future me:
#    def update(self, state: ZendureState) -> None :
#        # someget_ha_json math to determine the current energy level in Wh.
#        # possibly guessing, but doing a integration of charging-power / discharging-power
#        # to determine the current charge level.
#        # possibly also have some rough file-based "experience" lookup value to have something after restart.
#        # this is future!
#        # this class can even store the calculated information in ZendureState, so that other sensors can derive
#        # information from this as well (e.g a sensor "CapacityWh" or "BatteryHealth")

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
    PowerSensor("Power to Bat",             "output_pack_power",    "W",     "power"),
    PowerSensor("Power from Bat",           "pack_input_power",     "W",     "power"),
    SocSensor("Battery SoC",                "electric_level",       "%",     "battery"),

    # Sensors Inverter Side
    PowerSensor("Output To Home",           "output_home_power",    "W",     "power"),

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


