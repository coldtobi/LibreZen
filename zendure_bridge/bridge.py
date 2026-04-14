# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""Main bridge: subscribes to Zendure MQTT topics and maintains device state.

The MQTT bridge talks to the Zendure device, handles state updates and propagates
the information to the HApublisher to publish the information in home assistant.-

It provides an interface for HAPublisher to be able to send control commands.
"""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
import json
import threading
from typing import Any

import paho.mqtt.client as mqtt

from . import __version__
from .config import BridgeConfig
from .config import load as load_config
from .device import ZendureDevice, ZendureState
from .bridge_context import BridgeContext

from zendure_bridge.homeassistant.ha_publisher import HAPublisher

from .homeassistant.ha_entities import HAENTITIES

logger = logging.getLogger(__name__)


def setup_logging(level: str, log_file: str | None = None) -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


class ZendureBridge:
    """MQTT bridge for the Zendure SolarFlow.

    Subscribes to all device topics, parses payloads, and updates
    a ZendureDevice state object.

    Propagates the updated state to HAPublisher

    Offers an interface to control the device to HAPublisher.

    """

    lastMessageID : int = 0  # Message counter for the chatting.
    has_pending_changes: bool = False # Some changes could not be forwarded to ha_publish (because it was not ready)
    _get_all_props_timer = None  # Timer to schedule "get_all_properties"

    def __init__(self, config: BridgeConfig) -> None:
        self.config = config
        self.device = ZendureDevice(config.zendure.device_id)

        self._client = mqtt.Client(client_id=config.mqtt.client_id)
        self._client.username_pw_set(config.mqtt.username, config.mqtt.password)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        self._hapublisher = HAPublisher(config.mqtt, self.device, self)

        # Subscribe pattern covering all device topics
        z = config.zendure
        self._subscribe_topics = [
            f"/{z.app_key}/{z.device_id}/#",   # device → cloud (status, events)
            f"iot/{z.app_key}/{z.device_id}/#", # cloud → device (commands)
            # "#",  # temporär: alles mitschneiden
        ]



    # ------------------------------------------------------------------ #
    # MQTT callbacks (run in paho's network thread)                      #
    # ------------------------------------------------------------------ #

    def _on_connect(self, client: mqtt.Client, _userdata: Any, _flags: Any, rc: int) -> None:
        if rc != 0:
            logger.error("MQTT connect failed, rc=%d", rc)
            return
        logger.info("Connected to MQTT broker %s:%d", self.config.mqtt.broker, self.config.mqtt.port)
        for topic in self._subscribe_topics:
            client.subscribe(topic)
            logger.info("Subscribed to %s", topic)

        # schedule get_all_properties in a few seconds, to allow everything to be ready.
        if self._get_all_props_timer:
            self._get_all_props_timer.cancel()
        self._get_all_props_timer = threading.Timer(1.0, self.get_all_properties)
        self._get_all_props_timer.start()

    def _on_disconnect(self, _client: mqtt.Client, _userdata: Any, rc: int) -> None:
        if rc != 0:
            logger.warning("Unexpected disconnect (rc=%d), paho will reconnect", rc)
        if self._get_all_props_timer:
            self._get_all_props_timer.cancel()
        self.has_pending_changes = False  # invalidate stale data.

    def _on_message(self, _client: mqtt.Client, _userdata: Any, message: mqtt.MQTTMessage) -> None:
        topic = message.topic
        logger.debug("← %s (%d bytes)", topic, len(message.payload))
        logger.debug("  %s" , message.payload)

        changed = self.device.update_from_payload(topic, message.payload)
        state = self.device.state

        # defer processing if HAPublisher is not yet ready
        if not self._hapublisher.is_ready and changed:
          logger.info("HAPublisher not yet ready -- defering processing updates.")
          self.has_pending_changes = True
          return

        if changed or self.has_pending_changes:
            logger.info(
                "State: SoC=%d%% PV=%dW bat=%dW home=%dW grid=%dW limit=%dW",
                state.electric_level,
                state.solar_input_power,
                state.pack_input_power,
                state.output_home_power,
                state.grid_power,
                state.output_limit,
            )

            # Update haentity values.
            for haentity in HAENTITIES:
                haentity.update(state, self)

            # Publish changed haentity values to homeassistant.
            for haentity in HAENTITIES:
                if haentity.has_changed(state):
                    self._hapublisher.publish_state(haentity, state)

        # check if discoveries or availabilties needs updates.
        for haentity in HAENTITIES:
            if haentity.has_availability_changed(state, self):
                self._hapublisher.publish_availablity(haentity, state)
            if haentity.needs_re_discovery:
                self._hapublisher.publish_ha_discovery(haentity)

        self.has_pending_changes = False


    # ------------------------------------------------------------------ #
    # Lifecycle                                                          #
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        logger.info("zendure-bridge %s starting", __version__)
        self._hapublisher.start()

        self._client.connect_async(self.config.mqtt.broker, self.config.mqtt.port)
        self._client.reconnect_delay_set(min_delay=10, max_delay=300)
        self._client.loop_start()

    def stop(self) -> None:
        logger.info("Shutting down")
        self._client.disconnect()
        self._hapublisher.stop()

    # ------------------------------------------------------------------ #
    # Protocols                                                          #
    # ------------------------------------------------------------------ #

    def write_property(self, properties: dict[str, Any], persistent: bool = False ) -> None:
        """ Set a property in the device """
        # topic to send to:
        # "iot/<app_key>/<device_id>/properties/write"
        topic = ( "iot/"
                  f"{self.config.zendure.app_key}/{self.config.zendure.device_id}"
                  "/properties/write" )

        self.lastMessageID += 1

        # 0 -> store in flash, 1 -> keep in RAM. defaults to RAM to prevent wear-out.
        if persistent:
            properties['smartMode'] = 0
        else:
            properties['smartMode'] = 1

        payload = {
            'messageId': self.lastMessageID,
            'product': self.config.zendure.product,
            'deviceId': self.config.zendure.device_id,
            'timestamp': int(time.time() * 1000),
            'properties': properties
        }
        self._client.publish(topic, json.dumps(payload,separators=(',', ':')))

    def invoke_function(self, arguments: dict[str, Any], function: str) -> None:
        """ Call the "invoke" RFC
            arguments contain the parameters for the call, needs to be prepareed
            by the caller.
        """

        # topic to send to:
        # iot/<app_key>/<device_id>/function/invoke
        topic = ( "iot/"
          f"{self.config.zendure.app_key}/{self.config.zendure.device_id}"
          "/function/invoke" )

        self.lastMessageID += 1

        payload = {
            'arguments' : [arguments],
            'deviceKey':  self.config.zendure.device_id,
            'function':  function,
            'messageId': self.lastMessageID,
            'timestamp': int(time.time() * 1000)
        }
        self._client.publish(topic, json.dumps(payload,separators=(',', ':')))


    def get_all_properties(self) -> None:
        """ get all properties from the device.

        Issues a MQTT request to trigger the device sending out all properties again.
        """

        _topic = ( "iot/"
                  f"{self.config.zendure.app_key}/{self.config.zendure.device_id}"
                  "/properties/read" )

        self.lastMessageID += 1

        _dict = {
           'timestamp': int(time.time() * 1000),
           'messageId': self.lastMessageID,
           'deviceId': self.config.zendure.device_id,
           'properties': [
                "getAll"
               ]
        }
        self._client.publish(_topic, json.dumps(_dict))

    def update_state_value(self, field_name: str, value: int) -> None:
        """ allows updating the state object with a new value, thread safe. """
        self.device.update_value(field_name, value)

    def get_zendure_state(self) -> ZendureState:
        """ get a (fresh) copy of the current state """
        return self.device.state

    def get_bridge_context(self) -> BridgeContext:
        return BridgeContext(self.config.zendure, self.config.homeassistant)






def main() -> None:
    parser = argparse.ArgumentParser(
        description="Local MQTT bridge for Zendure SolarFlow"
    )
    parser.add_argument(
        "--config", default="config.yaml",
        help="Path to config file (default: config.yaml)"
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)

    setup_logging(config.log_level, config.log_file)

    bridge = ZendureBridge(config)

    # Graceful shutdown on Ctrl-C or SIGTERM
    def _signal_handler(sig: int, frame: Any) -> None:
        bridge.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    bridge.start()

    signal.pause()

if __name__ == "__main__":
    main()
