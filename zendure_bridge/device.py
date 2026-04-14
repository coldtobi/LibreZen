# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Zendure device state model.

Parses incoming MQTT payloads from the Zendure SolarFlow and maintains
a consolidated state dictionary. Thread-safe via internal Lock.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PackState:
    """State of a single battery pack."""

    sn: str
    soc_level: int = 0          # % state of charge
    power: int = 0              # W (positive = charging)
    state: int = 0              # 2 = charging, 3 = discharging
    max_temp: int = 0           # °C * 100 (e.g. 2801 = 28.01°C)
    total_vol: int = 0          # mV total voltage
    max_vol: int = 0            # mV max cell voltage
    min_vol: int = 0            # mV min cell voltage
    soh: int = 1000             # state of health, 1000 = 100%

    @property
    def temp_celsius(self) -> float:
        return self.max_temp / 100.0

    @property
    def soh_percent(self) -> float:
        return self.soh / 10.0


@dataclass
class ZendureState:
    """Consolidated state of the Zendure SolarFlow hub."""

    # Power values (W)
    solar_input_power: int = 0      # total PV input
    solar_power_1: int = 0          # PV string 1
    solar_power_2: int = 0          # PV string 2
    pack_input_power: int = 0       # battery charging power
    output_home_power: int = 0      # output to home
    output_pack_power: int = 0      # output from battery
    output_pack_power_cylce: int = 0 # unknown.
    grid_power: int = 0             # unknown.
    inverse_max_power: int = 600    # inverter output limit (W)
    output_limit: int = 0           # current output limit (W)
    input_limit: int = 0            # unknown.

    pack_input_power_cycle: int = 0 # unknown.
    output_home_power_cycle: int = 0 # unknown.
    solar_power_1_cycle: int = 0    # unknown.
    solar_power_2_cycle: int = 0    # unknown.

    # State
    electric_level: int = 0         # overall SoC (%)
    soc_set: int = 1000             # target SoC * 10 (1000 = 100%)
    min_soc: int = 100              # min SoC * 10 (100 = 10%)
    master_switch: int = 0          # 0 = off, 1 = on
    auto_model: int = 0             # see mapping _PROPERTY_MAP_AUTO_MODELS
    pack_state: int = 0             # 1 = charging, 2 = discharging, 0 = idle
    hub_state: int = 0              # 1 = turn hub off after discharge, 2 = standby
    pack_num: int = 0               # number of batteries.
    wifi_state:int = 0              # something with wifi…
    buzzer_switch: int = 0          # Buzzer On(=1)/Off(=0)
    input_mode: int = 0             # unknown, zendure github suggests "DC input mode" they write: "car charger(1), solar energy"
    blue_ota: int = 0               # unknown.
    bypass_active: int = 0          # If the battery is bypassed (1) or not (0)
    bypass_mode: int = 0            # mode selection for the bypass switch. see mapping _PROPERTY_MAP_BYPASS_MODES
    bypass_auto_recover: int = 0    # reset bypass mode automatically after a day.
    smart_mode: int = 1             # store paremetes in flash(=0), keep it in RAM(=1). Recommended value is 1
    smart_power: int = 0            # unknown.
    heat_state: int = 0             # the battery is being heated(=1).
    ac_mode: int = 0                # charge=1, discharge=2 - see zenSDK openapi.yaml



    # Misc Information
    master_soft_version: int = 0    # (Master) software version. bit-coded: MMMM mmmm rrrr rrrr
                                    # The example below: 2.0.45 is transmitted as 8237 = 0x2045
                                    # MMMM = Mayor Version eg. 0010      -> 2
                                    # mmmm = Minor Version eg. 0000      -> 0
                                    # rrrr = Revision      eg. 0010 1101 -> 45
    master_haer_Version: int = 0    # Some software version.
    inverter_pv_brand: int = 0      # Inverter Pre-configuration, see _PROPERTY_MAP_PV_MODELS

    # Timing
    remain_out_time: int = 0        # minutes remaining discharge
    remain_input_time: int = 0      # unkown, maybe minutes remaining charge. always reported as "59940" so far.

    # Packs
    packs: dict[str, PackState] = field(default_factory=dict)

    # Raw – everything else lands here
    extra: dict[str, Any] = field(default_factory=dict)


    # Syntectics / Calculated through sensors.
    battery_charge_power: int = 0    # Current Battery Charging/Discharging Power
    auto_model_value: int = 0        # control value for autoMode 8 and 9
    auto_model_program = 1           # autoModelProgram value for automode 9


# Mapping from Zendure JSON property names to ZendureState field names.
# Extend this as you discover more properties.
# Infos: https://github.com/Zendure/developer-device-data-report
#        https://github.com/epicRE/zendure_ble
#        https://github.com/Zendure/zenSDK/blob/main/docs/en_properties.md
_PROPERTY_MAP: dict[str, str] = {
    "solarInputPower":   "solar_input_power",             #!  R  - PV Input kumuliert
    "solarPower1":       "solar_power_1",                 #!  R  - PV Panel 1 Power
    "solarPower2":       "solar_power_2",                 #!  R  - PV Panel 2 Power
    "packInputPower":    "pack_input_power",              #! R  - Entladeleistung Batterie
    "outputHomePower":   "output_home_power",             #! R  - Leistung an Wechselrichter
    "outputPackPower":   "output_pack_power",             #! R  - Ladeleistung Batterie
    "outputPackPowerCycle": "output_pack_power_cylce",    #-      unbekannt.
    "gridPower":         "grid_power",                    #-      unbekannt.
    "inverseMaxPower":   "inverse_max_power",             #! RW - Inverter Power Limit ("legal" setting)
    "outputLimit":       "output_limit",                  #! RW - Soll-Ausgangsleistung zum Inverter
    "inputLimit":        "input_limit",                   #-      unbekannt. (immer 0)
    "electricLevel":     "electric_level",                #! R  - Battery charge level in %
    "socSet":            "soc_set",                       #! RW - Ladegrenze SoC (wann voll) Einheit: %*10
    "minSoc":            "min_soc",                       #! RW - Entladegrenze SoC. Einheit: %*10
    "masterSwitch":      "master_switch",                 #-      unbekannt, vermutlich Hauptschalter
    "autoModel":         "auto_model",                    # R  - Modus "deviceAutomation" - siehe unten.
    "packState":         "pack_state",                    # R  - 0=neutral, 1=laden, 2=entladen
    "hubState":          "hub_state",                     # RW - Modus "abschalten" (Wert 1) oder "entladen beenden" (Wert 0) bei MinSoc
    "remainOutTime":     "remain_out_time",               # R  - Zeit bis leer. (einheit minuten?)
    "remainInputTime":   "remain_input_time",             #      unbekannt. (immer 59940)
    "packInputPowerCycle":   "pack_input_power_cycle",    #      unbekannt.
    "outputHomePowerCycle":  "output_home_power_cycle",   #      unbekannt.
    "solarPower1Cycle":  "solar_power_1_cycle",           #      unbekannt.
    "solarPower2Cycle":  "solar_power_2_cycle",           #      unbekannt.
    "packNum":           "pack_num",                      # R  - Anzahl Batterien
    "wifiState":         "wifi_state",                    #      unbekannt, irgendwas mit wifi.
    "buzzerSwitch":      "buzzer_switch",                 # RW - Buzzer an/aus.
    "masterSoftVersion": "master_soft_version",           # R  - vermutl. Softwareversion "Master"
    "masterhaerVersion": "master_haer_Version",           #      unbekannte Version.
    "inputMode":         "input_mode",                    #      unbekannt. (github: DC input mode(1: car charger 2: solar energy)
    "blueOta":           "blue_ota",                      #      unbekannt.
    "pvBrand":           "inverter_pv_brand",             #      Wechselrichter-Hersteller, siehe unten
    "pass":              "bypass_active",                 # R  - If the battery is bypassed (1) or not (0)
    "passMode":          "bypass_mode",                   # RW - Bypass Modus, siehe unten für mapping.
    "autoRecover":       "bypass_auto_recover",           # RW - Bypass Modus automatisch rückstellen? (1=ja)
    "smartMode":         "smart_mode",                    # RW - Flash write behavior - 0 -> write to flash, 1 -> keep in RAM (recommened to avoid flash wear)
    "smartPower":        "smart_power",                   #      unbekannt.
    "heatState":         "heat_state",                    # R  - Batterie wird geheizt.
    "acMode":            "ac_mode",                       #      unbekannt, vermutlich mit Netzstrom-Eingangsmodus zu tun. (manueller ausgangsleistung setzen setzt dies auch auf "2")
}

# Mapping der "Auto Modes"
# Einstellen der AutoModes geschieht über
#   iot/…/…/function/invoke
# mit Payload
#   arguments: [{'autoModelProgram': 0, 'autoModel': 0}]
#   deviceKey: QYJpX6Y0     function: deviceAutomation      messageId: 13565892     timestamp: 1775113787
# (Achtung: ggf. noch weiter Parameter!
_PROPERTY_MAP_AUTO_MODELS: dict[int, str] = {
    0:  "manual_control",          # keine selbständige Steuerung.
#    6:  "priority_battery",        # Akkuprioritätsmodus.            ### NOT IMPLEMENTED IN HAAutoModelSelectControl ###
#    7:  "time_mode",               # Terminmodus.                    ### NOT IMPLEMENTED IN HAAutoModelSelectControl ###
    8:  "smart_matching_mode",     # Intellegenter Abgleich Modus
    9:  "smart_ct_mode",           # Intellegenter CT Mode ("Shelly")
#   10:  "market_mode",             # Follow the prices…              ### NOT IMPLEMENTED IN HAAutoModelSelectControl ###
}

# pvBrand Mapping - es ist unbekannt was es eigentlich tut…
_PROPERTY_MAP_PV_MODELS: dict[int, str] = {
    0:  "others",
    1:  "hoymiles",
    2:  "enphase",
    3:  "apsystems",
    4:  "anker",
    5:  "deye",
    6:  "bosswerk",             # note, reads back as "others" after setting in app.
    7:  "tsun",
}

# Bypass Modi
_PROPERTY_MAP_BYPASS_MODES: dict[int, str] = {
    0:  "auto",
    1:  "always_off",
    2:  "always_on",
}

_PACK_PROPERTY_MAP: dict[str, str] = {
    "socLevel":   "soc_level",
    "power":      "power",
    "state":      "state",
    "maxTemp":    "max_temp",
    "totalVol":   "total_vol",
    "maxVol":     "max_vol",                            # max cell voltage of pack (assumed)
    "minVol":     "min_vol",                            # minimum cell voltage of pack (assumed)
    "soh":        "soh",
}


class ZendureDevice:
    """Thread-safe state container for one Zendure SolarFlow hub.

    Call update_from_payload() from the MQTT on_message callback.
    Read state via the .state property (returns a snapshot copy).
    """

    def __init__(self, device_id: str) -> None:
        self.device_id = device_id
        self._state = ZendureState()
        self._lock = threading.Lock()
        self._message_count = 0

    def update_from_payload(self, topic: str, raw_payload: bytes) -> bool:
        """Parse a raw MQTT payload and merge it into the device state.

        Returns True if any state changed, False otherwise.
        """
        if len(raw_payload) > 4096:
            logger.warning("Oversized payload on %s (%d bytes), skipping", topic, len(raw_payload))
            return False

        try:
            payload: dict[str, Any] = json.loads(raw_payload)
        except json.JSONDecodeError as e:
            logger.debug("JSON parse error on %s: %s", topic, e)
            return False

        with self._lock:
            self._message_count += 1
            changed = False

            if topic.endswith("/properties/report") or topic.endswith("/properties/write"):
                changed |= self._merge_properties(payload.get("properties", {}))
                changed |= self._merge_pack_data(payload.get("packData", []))

            elif topic.endswith("/function/invoke"):
                # Log what the cloud is sending as control commands – useful for analysis
                for arg in payload.get("arguments", []):
                    logger.debug("Cloud → device command: %s", arg)

        return changed

    def _merge_properties(self, props: dict[str, Any]) -> bool:
        changed = False
        for raw_key, value in props.items():
            field_name = _PROPERTY_MAP.get(raw_key)
            if field_name:
                if getattr(self._state, field_name) != value:
                    setattr(self._state, field_name, value)
                    changed = True
            else:
                # Unknown property – store in extra, log at DEBUG
                if self._state.extra.get(raw_key) != value:
                    self._state.extra[raw_key] = value
                    logger.debug("Unknown property: %s = %s", raw_key, value)
                    changed = True
        return changed

    def _merge_pack_data(self, pack_data: list[dict[str, Any]]) -> bool:
        changed = False
        for pack_dict in pack_data:
            sn = pack_dict.get("sn")
            if not sn:
                continue
            if sn not in self._state.packs:
                self._state.packs[sn] = PackState(sn=sn)
                changed = True
            pack = self._state.packs[sn]
            for raw_key, value in pack_dict.items():
                field_name = _PACK_PROPERTY_MAP.get(raw_key)
                if field_name and getattr(pack, field_name) != value:
                    setattr(pack, field_name, value)
                    changed = True
        return changed

    def update_value(self, field_name: str, value: int ) -> None:
        """ thread-safe update of single value """
        with self._lock:
            setattr(self._state, field_name, value)

    @property
    def state(self) -> ZendureState:
        """Return a snapshot of the current state (not a live reference)."""
        with self._lock:
            # Shallow copy of state + deep copy of packs dict
            import copy
            return copy.copy(self._state)

    @property
    def message_count(self) -> int:
        with self._lock:
            return self._message_count

    def __repr__(self) -> str:
        s = self._state
        return (
            f"ZendureDevice({self.device_id!r} "
            f"SoC={s.electric_level}% "
            f"PV={s.solar_input_power}W "
            f"out={s.output_home_power}W "
            f"grid={s.grid_power}W "
            f"msgs={self._message_count})"
        )
