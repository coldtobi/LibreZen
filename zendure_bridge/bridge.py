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

import logging
import time
import json
import threading
from typing import Any

import paho.mqtt.client as mqtt

from .version import __version__

from .device import ZendureState
from .bridge_context import BridgeContext
from .bridge_components import BridgeComponents

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

    bc: BridgeComponents

    lastMessageID : int = 0  # Message counter for the chatting.
    has_pending_changes: bool = False # Some changes could not be forwarded to ha_publish (because it was not ready)
    _get_all_props_timer = None  # Timer to schedule "_get_all_properties"

    def __init__(self, bc: BridgeComponents) -> None:
        self.bc = bc


    # ------------------------------------------------------------------ #
    # Lifecycle                                                          #
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        assert self.bc is not None
        assert self.bc.device is not None
        assert self.bc.ha_publisher is not None

        # Subscribe pattern covering all device topics
        z = self.bc.config.zendure
        self._subscribe_topics = [
            f"/{z.app_key}/{z.device_id}/#",   # device → cloud (status, events)
            f"iot/{z.app_key}/{z.device_id}/#", # cloud → device (commands)
            # "#",  # temporär: alles mitschneiden
        ]

        self._client = mqtt.Client(client_id=self.bc.config.mqtt.client_id)
        self._client.connect_async(self.bc.config.mqtt.broker, self.bc.config.mqtt.port)
        self._client.reconnect_delay_set(min_delay=10, max_delay=300)
        self._client.loop_start()

    def stop(self) -> None:
        logger.info("Shutting down")
        self._client.disconnect()


    # ------------------------------------------------------------------ #
    # MQTT callbacks (run in paho's network thread)                      #
    # ------------------------------------------------------------------ #

    def _on_connect(self, client: mqtt.Client, _userdata: Any, _flags: Any, rc: int) -> None:
        if rc != 0:
            logger.error("MQTT connect failed, rc=%d", rc)
            return
        logger.info("Connected to MQTT broker %s:%d", self.bc.config.mqtt.broker, self.bc.config.mqtt.port)
        for topic in self._subscribe_topics:
            client.subscribe(topic)
            logger.info("Subscribed to %s", topic)

        # schedule _get_all_properties()
        # it will schedule itself if the timer is not running to run once a minute.
        self._get_all_properties()

    def _on_disconnect(self, _client: mqtt.Client, _userdata: Any, rc: int) -> None:
        if rc != 0:
            logger.warning("Unexpected disconnect (rc=%d), paho will reconnect", rc)
        if self._get_all_props_timer:
            self._get_all_props_timer.cancel()
        self.has_pending_changes = False  # invalidate stale data.

    def _on_message(self, _client: mqtt.Client, _userdata: Any, message: mqtt.MQTTMessage) -> None:
        assert self.bc is not None
        assert self.bc.device is not None
        assert self.bc.ha_publisher is not None
        device = self.bc.device
        hapublisher = self.bc.ha_publisher

        topic = message.topic
        logger.debug("← %s (%d bytes)", topic, len(message.payload))
        logger.debug("  %s" , message.payload)

        changed = device.update_from_payload(topic, message.payload)
        state = device.state

        # defer processing if HAPublisher is not yet ready
        if not hapublisher.is_ready and changed:
            logger.info("HAPublisher not yet ready -- defering processing updates.")
            self.has_pending_changes = True
            return

        if changed or self.has_pending_changes:
            logger.info(f"State: SoC={state.electric_level} PV={state.solar_input_power} "
                        f"bat={state.pack_input_power} home={state.output_home_power} "
                        f"grid={state.grid_power} limit={state.output_limit}")

            # Update haentity values.
            for haentity in HAENTITIES:
                haentity.update(state, self)

            # Publish changed haentity values to homeassistant.
            for haentity in HAENTITIES:
                if haentity.has_changed(state):
                    hapublisher.publish_state(haentity, state)

        # check if discoveries or availabilties needs updates.
        for haentity in HAENTITIES:
            if haentity.has_availability_changed(state, self):
                hapublisher.publish_availablity(haentity, state)
            if haentity.needs_re_discovery:
                hapublisher.publish_ha_discovery(haentity)

        self.has_pending_changes = False


    # ------------------------------------------------------------------ #
    # Protocols                                                          #
    # ------------------------------------------------------------------ #

    def write_property(self, properties: dict[str, Any], persistent: bool = False ) -> None:
        """ Set a property in the device """
        # topic to send to:
        # "iot/<app_key>/<device_id>/properties/write"
        topic = ( "iot/"
                  f"{self.bc.config.zendure.app_key}/{self.bc.config.zendure.device_id}"
                  "/properties/write" )

        self.lastMessageID += 1

        # 0 -> store in flash, 1 -> keep in RAM. defaults to RAM to prevent wear-out.
        if persistent:
            properties['smartMode'] = 0
        else:
            properties['smartMode'] = 1

        payload = {
            'messageId': self.lastMessageID,
            'product': self.bc.config.zendure.product,
            'deviceId': self.bc.config.zendure.device_id,
            'timestamp': int(time.time() * 1000),
            'properties': properties
        }
        self._client.publish(topic, json.dumps(payload,separators=(',', ':')))

    def invoke_function(self, arguments: dict[str, Any], function: str) -> None:
        """ Call the "invoke" RFC
            arguments contain the parameters for the call, needs to be prepareed
            by the caller.
        """
        topic = ( "iot/"
          f"{self.bc.config.zendure.app_key}/{self.bc.config.zendure.device_id}"
          "/function/invoke" )
        self.lastMessageID += 1
        payload = {
            'arguments' : [arguments],
            'deviceKey':  self.bc.config.zendure.device_id,
            'function':  function,
            'messageId': self.lastMessageID,
            'timestamp': int(time.time() * 1000)
        }
        logger.debug("invoke_function %s to %s, arguments %s", function, topic, json.dumps(arguments))
        self._client.publish(topic, json.dumps(payload,separators=(',', ':')))


    def _get_all_properties(self) -> None:
        """ get all properties from the device.

        Issues a MQTT request to trigger the device sending out all properties again.
        """

        topic = ( "iot/"
                  f"{self.bc.config.zendure.app_key}/{self.bc.config.zendure.device_id}"
                  "/properties/read" )

        self.lastMessageID += 1
        _dict = {
           'timestamp': int(time.time() * 1000),
           'messageId': self.lastMessageID,
           'deviceId': self.bc.config.zendure.device_id,
           'properties': [
                "getAll"
               ]
        }
        logger.debug("_get_all_properties to %s.", topic)
        self._client.publish(topic, json.dumps(_dict))

        if self._get_all_props_timer:
            self._get_all_props_timer.cancel()
        if self.bc.config.zendure.get_all_properties_interval > 0:
            self._get_all_props_timer = threading.Timer(self.bc.config.zendure.get_all_properties_interval, self._get_all_properties)
            self._get_all_props_timer.start()


    def update_state_value(self, field_name: str, value: int) -> None:
        """ allows updating the state object with a new value, thread safe. """
        assert self.bc.device is not None
        self.bc.device.update_value(field_name, value)

    def get_zendure_state(self) -> ZendureState:
        """ get a (fresh) copy of the current state """
        assert self.bc.device is not None
        return self.bc.device.state

    def get_bridge_context(self) -> BridgeContext:
        return BridgeContext(self.bc.config.zendure, self.bc.config.homeassistant)
