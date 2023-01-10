from __future__ import annotations

import json
from typing import Optional

from paho.mqtt import client as mqtt

from nhs import NHSProtocol


class NHSMQTTEntity:
    STATE_OFF = 0
    STATE_ON = 1
    STATE_UNKNOWN = -1

    def __init__(self, *, root_topic_name: str = 'NHSUPS', host: str = 'localhost', port: int = 1883,
                 username: str = None, password: str = None, max_time_between_messages_in_seconds: int = 5):
        print(f'Initializing MQTT entity in root topic {root_topic_name} at {host}:{port}...')
        self._mqtt_client = mqtt.Client('nhs-server')
        self._attributes_topic = _MQTTTopic(name=f'{root_topic_name}/attributes', client=self._mqtt_client)
        self._lwt_topic = _MQTTTopic(name=f'{root_topic_name}/LWT', client=self._mqtt_client)
        self._state_topic = _MQTTTopic(name=f'{root_topic_name}/state', client=self._mqtt_client)

        self._initialize_mqtt_client(host=host, port=port, username=username, password=password)

        self._latest_packet: Optional[NHSProtocol] = None
        self._last_published_age = 0
        self._max_time_between_messages_in_seconds = max_time_between_messages_in_seconds

    def update(self, packet: NHSProtocol) -> None:
        if packet != self._latest_packet or self.outdated:
            print('Publishing...')
            self._state_topic.publish(payload=self._get_state_payload(packet=packet))
            self._attributes_topic.publish(payload=self._get_attributes_payload(packet=packet))
            self._latest_packet = packet
            self._last_published_age = 0
            print('Published.')
        else:
            self._last_published_age += 1

    @property
    def outdated(self):
        return self._last_published_age >= self._max_time_between_messages_in_seconds

    def _initialize_mqtt_client(self, *, host: str, port: int, username: str, password: str) -> None:
        if username and password:
            self._mqtt_client.username_pw_set(username=username, password=password)
        self._mqtt_client.will_set(topic=self._lwt_topic.name, payload='Offline', retain=True)
        self._mqtt_client.connect(host=host, port=port)
        self._lwt_topic.publish(payload='Online')
        self._mqtt_client.loop_start()

    def _get_state_payload(self, *, packet: NHSProtocol) -> str:
        state = self.STATE_OFF if packet.grid_down else self.STATE_ON
        return json.dumps({'state': state})

    @staticmethod
    def _get_attributes_payload(*, packet: NHSProtocol) -> str:
        return json.dumps(vars(packet))


class _MQTTTopic:
    def __init__(self, *, name: str, client: mqtt.Client):
        self.name = name
        self._client = client

    def publish(self, *, payload: str, retain: bool = True):
        self._client.publish(topic=self.name, payload=payload, retain=retain)
