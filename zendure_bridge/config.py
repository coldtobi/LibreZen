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
    product: str = "solarFlow"
    get_all_properties_interval: int = 60  # seconds


@dataclass
class HAConfig:
    discovery_prefix: str = "homeassistant"
    device_name: str = "Zendure SolarFlow"
    model_name: str = "Hub 1200"
    expert_mode: bool = False


@dataclass
class NodeRedConfig:
    """Configuration for the NodeRed MQTT publisher."""
    enabled: bool = False
    broker: str = ""
    port: int = 1883
    username: str = ""
    password: str = ""
    client_id: str = "zendure-bridge-nodered"
    topic_prefix: str = "zendure"  # Topics: <prefix>/<device_id>/state/<field>

    def __post_init__(self) -> None:
        # If no broker configured, disable automatically
        if not self.broker:
            self.enabled = False

@dataclass
class BridgeConfig:
    mqtt: MqttConfig
    zendure: ZendureConfig
    homeassistant: HAConfig
    nodered: NodeRedConfig
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
            get_all_properties_interval=int(z_raw.get("get_all_properties_interval", 60)),
        )

        ha_raw = raw.get("homeassistant", {})
        ha = HAConfig(
            discovery_prefix=ha_raw.get("discovery_prefix", "homeassistant"),
            device_name=ha_raw.get("device_name", "Zendure SolarFlow"),
            model_name=ha_raw.get("model_name", "Hub 1200"),
            expert_mode=ha_raw.get("expert_mode", False)
        )

        nr_raw = raw.get("nodered", {})
        nodered = NodeRedConfig(
            enabled=nr_raw.get("enabled", False),
            broker=nr_raw.get("broker", ""),
            port=int(nr_raw.get("port", 1883)),
            username=nr_raw.get("username", ""),
            password=nr_raw.get("password", ""),
            client_id=nr_raw.get("client_id", "zendure-bridge-nodered"),
            topic_prefix=nr_raw.get("topic_prefix", "zendure"),
        )

        log_raw = raw.get("logging", {})

        return BridgeConfig(
            mqtt=mqtt,
            zendure=zendure,
            homeassistant=ha,
            nodered=nodered,
            log_level=log_raw.get("level", "INFO").upper(),
            log_file=log_raw.get("file"),
        )

    except KeyError as e:
        raise ValueError(f"Missing required config key: {e}") from e
