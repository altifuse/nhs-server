from __future__ import annotations

import yaml

from mqtt import NHSMQTTEntity
from nhs_serial import NHSSerialListener


def main():
    print('Starting NHS Stats Server...')
    config = _load_config()
    print('Configuration file loaded.')
    mqtt_entity = NHSMQTTEntity(**config['mqtt'])
    print('MQTT entity initialized.')
    listener = NHSSerialListener(callback=mqtt_entity.update, **config['serial'])
    print('Serial listener initialized.')
    listener.start()


def _load_config(path: str = 'config.yaml') -> dict:
    print(f'Loading config file from {path}...')
    with open(path) as file:
        return yaml.load(file, yaml.SafeLoader)


if __name__ == '__main__':
    main()
