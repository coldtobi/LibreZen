# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Tobias Frost <tobi@coldtobi.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import logging
from typing import Any

import paho.mqtt.client as mqtt

from .ha_entity import HAEntity
from .ha_control import HAControl
from .ha_entities import HAENTITIES

from ..device import ZendureState
from ..bridge_components import BridgeComponents

logger = logging.getLogger(__name__)

class HAPublisher:
    """Homeassistent MQTT Publisher

    Publishes the Zendure data to the homeassistant MQTT
    based on the ZendureDevice state.
    """
    _bc: BridgeComponents

    _is_ready: bool = False # Connected to the HA Broker and sent all discoveries / availabilities -> we are ready to accept data.

    def __init__(self, bc: BridgeComponents) -> None:
        self.bc = bc
        # mqttconfig: MqttConfig, zendevice: ZendureDevice, zencontrol: ZendureController ) -> None:


    # ----------#
    # Lifecycle #
    # ----------#

    def start(self) -> None:
        mqttconfig = self.bc.config.mqtt
        logger.info("connecting to homeassistant mqtt broker at %s ", mqttconfig.ha_broker)

        # keeping track of discovery / availability sent, to judge whether we are ready.
        self.discovery_mid : list[int] = []

        # MQTT client talks to the homeassistant mqtt server.
        self._client = mqtt.Client(client_id=mqttconfig.client_id)
        self._client.username_pw_set(mqttconfig.ha_username, mqttconfig.ha_password)
        self._client.on_connect = self._on_connect
        self._client.on_connect_fail = self._on_connect_fail
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.on_publish = self._on_publish

        # Subscribe pattern covering all device topics which can command things
        self._subscribe_topics: list[str] = []
        for haent in HAENTITIES:
            if isinstance(haent, HAControl) :
                logger.info("command_topic: %s" , str(haent.get_command_topic(self.bc)))
                self._subscribe_topics.append(haent.get_command_topic(self.bc))

        self._client.loop_start()
        self._client.connect_async(mqttconfig.ha_broker, mqttconfig.ha_port)
        self._client.reconnect_delay_set(min_delay=1, max_delay=120)

    def stop(self) -> None:
        logger.info("Shutting down")
        self._is_ready = False
        self._client.disconnect()


    # ----------- #
    # MQTT Client #
    # ----------- #

    def _on_connect(self, client: mqtt.Client, _userdata: Any, _flags: Any, rc: int) -> None:
        assert self.bc.bridge is not None
        mqttconfig = self.bc.config.mqtt

        self.discovery_mid.clear()
        if rc != 0:
            logger.error("MQTT connect failed, rc=%d", rc)
            return

        logger.info("Connected to MQTT broker %s:%d", mqttconfig.ha_broker, mqttconfig.ha_port)

        for topic in self._subscribe_topics:
            logger.info("Subscribing to: %s", topic)
            client.subscribe(topic)

        for haentity in HAENTITIES:
            # send initial discovery and initial availability.
            self.publish_ha_discovery(haentity)
            self.publish_availability(haentity, self.bc.device.state)

    def _on_publish(self,_client: mqtt.Client, _userdata: Any, mid: int) -> None:
        # Hack to get a "_is_ready" signal - tracking all discovery/availability
        # publications and be ready when all has been sent.
        if mid in self.discovery_mid:
            self.discovery_mid.remove(mid)
            if (not self._is_ready) and (not self.discovery_mid):
                logger.info("HAPublisher is now declared ready.")
                self._is_ready = True

    def _on_connect_fail(self, client: mqtt.Client, _userdata: Any) -> None:
        mqttconfig = self.bc.config.mqtt
        logger.warning("Connect to MQTT broker %s:%d failed.", mqttconfig.ha_broker, mqttconfig.ha_port)
        self.discovery_mid.clear()

    def _on_disconnect(self, client: mqtt.Client, _userdata: Any, rc: int) -> None:
        if rc != 0:
            logger.warning("Unexpected disconnect (rc=%d), paho will reconnect", rc)
        self._is_ready = False
        self.discovery_mid.clear()

    def _on_message(self, _client: mqtt.Client, _userdata: Any, message: mqtt.MQTTMessage) -> None:
        assert self.bc.device is not None
        topic = message.topic
        state = self.bc.device.state
        for haent in HAENTITIES:
            if isinstance(haent, HAControl) and topic == haent.get_command_topic(self.bc):
                haent.handle_command(message.payload, state, self.bc)
                return

        logger.warning("received unexpected topic: %s", topic)


    # ----------------#
    # Topic Managment #
    # ----------------#

    def publish_ha_discovery(self, haentity: HAEntity) -> None:
        logger.info("sending discovery for %s", haentity.name)
        mid = self._client.publish(
            haentity.get_discovery_topic(self.bc),
            haentity.get_ha_json(self.bc),
            retain=True)
        self.discovery_mid.append(mid.mid)

    # Hilfsmethode um topics wieder im homeassistant zu löschen. muss vor dem umbennen aufgerufen werden.
    def unpublish_discoveries(self) -> None:
        for sensor in HAENTITIES:
            self._client.publish(
                sensor.get_discovery_topic(self.bc),
                payload="",
                retain=True)

    # -------------------------#
    # Topic States / Protocols #
    # -------------------------#

    def publish_state(self, haentity: HAEntity, state: ZendureState) -> None:
        """ publish the state (the value) of an entity """
        payload = haentity.get_display_value(state)
        if payload is None:
            logger.debug("skipping state publish for %s, value is None", haentity.name)
            return
        topic = haentity.get_state_topic(self.bc)
        logger.debug("sending state for %s to %s, value %s", haentity.name, topic, payload)
        self._client.publish(topic, payload, retain=True)

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    def publish_availability(self, haentity: HAEntity, state: ZendureState) -> None:
        """ publish availabiltiy of a state / control.

            availabilty will only be published if it has changed since the last time, or if always=True
        """
        topic = haentity.get_availabilty_topic(self.bc)
        payload = "online" if haentity.is_available(state, self.bc) else "offline"
        logger.debug("Availabilty for %s is now %s", haentity.name, payload)
        mid = self._client.publish(topic, payload, retain=True)
        self.discovery_mid.append(mid.mid)

