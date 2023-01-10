from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

import yaml
from paho.mqtt import client as mqtt
from serial import Serial, PARITY_NONE, STOPBITS_ONE, EIGHTBITS
from serial.threaded import ReaderThread, FramedPacket


class MQTTTopic:
    def __init__(self, *, name: str, client: mqtt.Client):
        self.name = name
        self._client = client

    def publish(self, *, payload: str, retain: bool = True):
        self._client.publish(topic=self.name, payload=payload, retain=retain)


class NHSMQTTEntity:
    STATE_OFF = 'OFF'
    STATE_ON = 'ON'
    STATE_UNKNOWN = 'UNKNOWN'
    MINIMUM_PUBLISH_RATE = 5

    def __init__(self, *, root_topic_name: str = 'NHSUPS', host: str = 'localhost', port: int = 1883,
                 username: str = None, password: str = None):
        self._mqtt_client = mqtt.Client("nhs-server")
        self._attributes_topic = MQTTTopic(name=f'{root_topic_name}/attributes', client=self._mqtt_client)
        self._lwt_topic = MQTTTopic(name=f'{root_topic_name}/LWT', client=self._mqtt_client)
        self._state_topic = MQTTTopic(name=f'{root_topic_name}/state', client=self._mqtt_client)

        self._initialize_mqtt_client(host=host, port=port, username=username, password=password)

        self._latest_packet: Optional[NHSProtocol] = None
        self._last_published_age = 0

    def update(self, packet: NHSProtocol) -> None:
        if packet != self._latest_packet or self.outdated:
            self._state_topic.publish(payload=self._get_state_payload(packet=packet))
            self._attributes_topic.publish(payload=self._get_attributes_payload(packet=packet))
            self._latest_packet = packet
            self._last_published_age = 0
        else:
            self._last_published_age += 1

    @property
    def outdated(self):
        return self._last_published_age >= self.MINIMUM_PUBLISH_RATE

    def _initialize_mqtt_client(self, *, host: str, port: int, username: str, password: str) -> None:
        if username and password:
            self._mqtt_client.username_pw_set(username=username, password=password)
        self._mqtt_client.will_set(topic=self._lwt_topic.name, payload='Offline', retain=True)
        self._mqtt_client.connect(host=host, port=port)
        self._lwt_topic.publish(payload='Online')
        self._mqtt_client.loop_start()

    def _get_state_payload(self, *, packet: NHSProtocol) -> str:
        return self.STATE_OFF if packet.grid_down else self.STATE_ON

    @staticmethod
    def _get_attributes_payload(*, packet: NHSProtocol) -> str:
        return json.dumps(vars(packet))


@dataclass
class NHSProtocol:
    rms_in_volts: int
    battery_volts: int
    load_percent: int
    min_rms_in_volts: int
    max_rms_in_volts: int
    rms_out_volts: int
    temp_celsius: int
    charger_amperes: float
    battery_on: bool
    low_battery: bool
    grid_down: bool
    grid_short_outage: bool
    rms_in_220: bool
    rms_out_220: bool
    bypass_on: bool
    charging: bool

    def __eq__(self, other: NHSProtocol) -> bool:
        return not other or self.grid_down == other.grid_down


class NHSSerialListener:
    def __init__(self, *, callback, port='/dev/TTYS0', baud_rate=2400, byte_size=EIGHTBITS, parity=PARITY_NONE,
                 stop_bits=STOPBITS_ONE, xonxoff=False, rtscts=False, dsrdtr=False):
        listener = Serial(port=port, baudrate=baud_rate, bytesize=byte_size, parity=parity, stopbits=stop_bits,
                          xonxoff=xonxoff, rtscts=rtscts, dsrdtr=dsrdtr)
        self._reader = ReaderThread(listener, NHSSerialReader.get_factory(callback=callback))

    def start(self) -> None:
        self._reader.run()


class NHSSerialReader(FramedPacket):
    LENGTH = 19
    START = b'\xff'
    STOP = b'\xfe'

    def __init__(self, *, callback):
        super().__init__()
        self._callback = callback

    def handle_packet(self, packet: bytearray) -> None:
        if self._is_packet_incomplete(packet=packet):
            return

        status_raw = format(packet[16], '08b')
        status_raw = [int(item) for item in status_raw]
        self._callback(
            NHSProtocol(
                rms_in_volts=packet[2] + packet[3],
                battery_volts=packet[4] + packet[5],
                load_percent=packet[6],
                min_rms_in_volts=packet[7] + packet[8],
                max_rms_in_volts=packet[9] + packet[10],
                rms_out_volts=packet[11] + packet[12],
                temp_celsius=packet[13] + packet[14],
                charger_amperes=packet[15] * 750 / 25,
                battery_on=bool(status_raw[7]),
                low_battery=bool(status_raw[6]),
                grid_down=bool(status_raw[5]),
                grid_short_outage=bool(status_raw[4]),
                rms_in_220=bool(status_raw[3]),
                rms_out_220=bool(status_raw[2]),
                bypass_on=bool(status_raw[1]),
                charging=bool(status_raw[0])
            )
        )

    def _is_packet_incomplete(self, *, packet: bytearray) -> bool:
        return len(packet) != self.LENGTH

    @staticmethod
    def get_factory(*, callback):
        def func():
            return NHSSerialReader(callback=callback)

        return func


def main():
    config = _load_config()
    mqtt_entity = NHSMQTTEntity(**config['mqtt'])
    listener = NHSSerialListener(callback=mqtt_entity.update, **config['serial'])
    listener.start()


def _load_config() -> dict:
    with open('config.yaml') as file:
        return yaml.load(file, yaml.SafeLoader)


if __name__ == '__main__':
    main()
