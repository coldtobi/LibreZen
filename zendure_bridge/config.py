# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Configuration loader for zendure-bridge.

Reads config.yaml from the current directory or a path given on the
command line. Validates required fields and provides typed access.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # python3-yaml / pyyaml

logger = logging.getLogger(__name__)


@dataclass
class MqttConfig:
    broker: str
    port: int
    username: str
    password: str
    client_id: str = "zendure-bridge"
    ha_broker: str = ""
    ha_port: int = 1883
    ha_username: str = ""
    ha_password: str = ""

    def __post_init__(self) -> None:
        # Default: HA broker = Zendure broker
        if not self.ha_broker:
            self.ha_broker = self.broker
        if not self.ha_username:
            self.ha_username = self.username
        if not self.ha_password:
            self.ha_password = self.password


@dataclass
class ZendureConfig:
    app_key: str
    device_id: str
    max_output_power: int = 600
    min_soc: int = 10
    product: str = "solarFlow"


@dataclass
class HAConfig:
    discovery_prefix: str = "homeassistant"
    device_name: str = "Zendure SolarFlow"
    model_name: str = "Hub 1200"
    expert_mode: bool = False


@dataclass
class BridgeConfig:
    mqtt: MqttConfig
    zendure: ZendureConfig
    homeassistant: HAConfig
    log_level: str = "INFO"
    log_file: str | None = None


def load(path: str | Path = "config.yaml") -> BridgeConfig:
    """Load and validate configuration from a YAML file."""

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            f"Copy config.yaml.example to config.yaml and fill in your values."
        )

    with config_path.open() as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    try:
        mqtt_raw = raw["mqtt"]
        mqtt = MqttConfig(
            broker=mqtt_raw["broker"],
            port=int(mqtt_raw.get("port", 1883)),
            username=mqtt_raw["username"],
            password=mqtt_raw["password"],
            client_id=mqtt_raw.get("client_id", "zendure-bridge"),
            ha_broker=mqtt_raw.get("ha_broker", ""),
            ha_port=int(mqtt_raw.get("ha_port", 1883)),
            ha_username=mqtt_raw.get("ha_username", ""),
            ha_password=mqtt_raw.get("ha_password", ""),
        )

        z_raw = raw["zendure"]
        zendure = ZendureConfig(
            app_key=z_raw["app_key"],
            device_id=z_raw["device_id"],
            product=z_raw.get("product", "solarFlow"),
            max_output_power=int(z_raw.get("max_output_power", 600)),
            min_soc=int(z_raw.get("min_soc", 10)),

        )

        ha_raw = raw.get("homeassistant", {})
        ha = HAConfig(
            discovery_prefix=ha_raw.get("discovery_prefix", "homeassistant"),
            device_name=ha_raw.get("device_name", "Zendure SolarFlow"),
            model_name=ha_raw.get("model_name", "Hub 1200"),
            expert_mode=ha_raw.get("expert_mode", False)
        )

        log_raw = raw.get("logging", {})

        return BridgeConfig(
            mqtt=mqtt,
            zendure=zendure,
            homeassistant=ha,
            log_level=log_raw.get("level", "INFO").upper(),
            log_file=log_raw.get("file"),
        )

    except KeyError as e:
        raise ValueError(f"Missing required config key: {e}") from e
