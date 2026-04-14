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

from ..config import MqttConfig
from ..device import ZendureDevice
from ..zendure_protocols import ZendureController
from ..device import ZendureState

logger = logging.getLogger(__name__)

class HAPublisher:
    """Homeassistent MQTT Publisher

    Publishes the Zendure data to the homeassistant MQTT
    based on the ZendureDevice state.
    """

    is_ready: bool = False # Connected to the HA Broker and sent all discoveries / availabilities -> we are ready to accept data.

    def __init__(self,
                 mqttconfig: MqttConfig, zendevice: ZendureDevice, zencontrol: ZendureController ) -> None:

        self.mqttconfig = mqttconfig
        self.zendevice = zendevice
        self.zencontrol = zencontrol

        # client talks to the homeassistant mqtt server.
        self._client = mqtt.Client(client_id=mqttconfig.client_id)
        self._client.username_pw_set(mqttconfig.ha_username, mqttconfig.ha_password)

        self._client.on_connect = self._on_connect
        self._client.on_connect_fail = self._on_connect_fail
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        # Subscribe pattern covering all device topics which can command things
        self._subscribe_topics: list[str] = []
        for haent in HAENTITIES:
            if isinstance(haent, HAControl) :
                logger.info("command_topic: %s" , str(haent.get_command_topic(zencontrol)))
                self._subscribe_topics.append(haent.get_command_topic(zencontrol))


    def _on_connect(self, client: mqtt.Client, _userdata: Any, _flags: Any, rc: int) -> None:

        if rc != 0:
            logger.error("MQTT connect failed, rc=%d", rc)
            return

        logger.info("Connected to MQTT broker %s:%d", self.mqttconfig.ha_broker, self.mqttconfig.ha_port)

        for topic in self._subscribe_topics:
            logger.info("Subscribing to: %s", topic)
            client.subscribe(topic)

        for haentity in HAENTITIES:
            # send initial discovery and initial availability.
            self.publish_ha_discovery(haentity)
            self.publish_availablity(haentity, self.zencontrol.get_zendure_state())

        self.is_ready = True


    def _on_connect_fail(self, client: mqtt.Client, _userdata: Any) -> None:
        logger.warning("Connect to MQTT broker %s:%d failed.", self.mqttconfig.ha_broker, self.mqttconfig.ha_port)


    def _on_disconnect(self, client: mqtt.Client, _userdata: Any, rc: int) -> None:
        if rc != 0:
            logger.warning("Unexpected disconnect (rc=%d), paho will reconnect", rc)
        self.is_ready = False


    def _on_message(self, _client: mqtt.Client, _userdata: Any, message: mqtt.MQTTMessage) -> None:
        topic = message.topic
        for haent in HAENTITIES:
            if isinstance(haent, HAControl) and topic == haent.get_command_topic(self.zencontrol):
                state = self.zendevice.state
                haent.handle_command(message.payload, state, self.zencontrol)
                return

        logger.warning("received unexpected topic: %s", topic)

    # ----------#
    # Lifecycle #
    # ----------#

    def start(self) -> None:
        logger.info("connecting to homeassistant mqtt broker at %s ", self.mqttconfig.ha_broker)
        self._client.loop_start()
        self._client.connect_async(self.mqttconfig.ha_broker, self.mqttconfig.ha_port)
        self._client.reconnect_delay_set(min_delay=1, max_delay=120)

    def stop(self) -> None:
        logger.info("Shutting down")
        self._client.disconnect()

    # ----------------#
    # Topic Managment #
    # ----------------#

    def publish_ha_discovery(self, haentity: HAEntity) -> None:
        logger.info("sending discovery for %s", haentity.name)
        self._client.publish(
            haentity.get_discovery_topic(self.zencontrol),
            haentity.get_ha_json(self.zencontrol),
            retain=True)

    # Hilfsmethode um topics wieder im homeassistant zu löschen. muss vor dem umbennen aufgerufen werden.
    def unpublish_discoveries(self) -> None:
        for sensor in HAENTITIES:
            self._client.publish(
                sensor.get_discovery_topic(self.zencontrol),
                payload="",
                retain=True)

    # -------------#
    # Topic States #
    # -------------#
    def publish_state(self, haentity: HAEntity, state: ZendureState) -> None:
        """ publish the state (the value) of an entity """
        logger.debug("sending state for %s, value %s", haentity.name, haentity.get_display_value(state))
        self._client.publish(
            haentity.get_state_topic(self.zencontrol),
            haentity.get_display_value(state),
            retain=False
        )


    def publish_availablity(self, haentity: HAEntity, state: ZendureState) -> None:
        """ publish availabiltiy of a state / control.

            availabilty will only be published if it has changed since the last time, or if always=True
        """
        topic = haentity.get_availabilty_topic(self.zencontrol)
        payload = "online" if haentity.is_available(state, self.zencontrol) else "offline"
        logger.debug("Availabilty for %s is now %s", haentity.name, payload)
        self._client.publish(topic, payload, retain=True)
