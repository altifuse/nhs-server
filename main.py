from __future__ import annotations

import yaml

from mqtt import NHSMQTTEntity
from nhs_serial import NHSSerialListener


def main():
    config = _load_config()
    mqtt_entity = NHSMQTTEntity(**config['mqtt'])
    listener = NHSSerialListener(callback=mqtt_entity.update, **config['serial'])
    listener.start()


def _load_config(path: str = 'config.yaml') -> dict:
    with open(path) as file:
        return yaml.load(file, yaml.SafeLoader)


if __name__ == '__main__':
    main()
